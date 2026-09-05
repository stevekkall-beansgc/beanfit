"""Synthetic bridge QA only: all provider operations are in-memory fakes."""
import copy
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

from beanfit.activation import ActivationError, Ledger
from beanfit.apify_actor import run
from beanfit.apify_fulfillment import (ACTOR_ID, BUILD_ID, BUILD_NUMBER, MAX_BYTES,
    ApifyTestClient, ApifyTestError, NoRedirect, step)
from beanfit.report import generate_report
from tests.test_activation import PROFILE, TOKEN, FakeStripe, MemoryStore, event
from tests.test_stripe_test import Opener, Response


def proof():
    return dict(user_id='user123', plan='FREE', enabled=True, is_paying=False,
                credits=5, cap=5, usage=.01, active_jobs=0, actor_id=ACTOR_ID,
                owner='user123', private=True, pricing_inactive=True,
                build_id=BUILD_ID, build_actor=ACTOR_ID, build_number=BUILD_NUMBER, build_status='SUCCEEDED')


def remote_run(status='RUNNING'):
    return dict(id='run123', defaultKeyValueStoreId='store123', actId=ACTOR_ID,
                buildId=BUILD_ID, buildNumber=BUILD_NUMBER, userId='user123', generalAccess='RESTRICTED',
                options=dict(memoryMbytes=128, timeoutSecs=60, build=BUILD_NUMBER,
                             restartOnError=False, forcePermissionLevel='LIMITED_PERMISSIONS', maxTotalChargeUsd=.25),
                status=status, stats=dict(restartCount=0), chargedEventCounts={}, pricingInfo=None)


class FakeApify:
    def __init__(self):
        self.proof = proof()
        self.run = remote_run()
        self.store = dict(id='store123', userId='user123', generalAccess='RESTRICTED')
        self.records = {}
        self.starts = 0
        self.reads = 0
        self.error = None
        self.before_start = lambda: None
        self.preflight_hook = lambda: None

    def preflight(self):
        self.preflight_hook()
        return copy.deepcopy(self.proof)

    def start(self, profile, *, synthetic):
        assert synthetic is True
        self.starts += 1
        self.before_start()
        if self.error:
            raise self.error
        store = MemoryStore(profile)
        ticks = iter((100, 101))
        assert run(store, generate=generate_report, revision='a' * 40, memory_mib=128,
                   generated_at='2026-09-05T00:00:00Z', clock=lambda: next(ticks)) == 0
        self.records = {k: (v.encode() if isinstance(v, str) else json.dumps(v).encode())
                        for k, v in store.values.items()}
        return copy.deepcopy(self.run)

    def get_run(self, run_id):
        assert run_id == 'run123'
        self.reads += 1
        return copy.deepcopy(self.run)

    def get_store(self, store_id):
        assert store_id == 'store123'
        return copy.deepcopy(self.store)

    def record(self, store_id, key):
        assert store_id == 'store123'
        return self.records.get(key)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'ledger.sqlite'
        self.clock = [1788600000]
        self.ledger = Ledger(self.path, now=lambda: self.clock[0])
        self.addCleanup(self.ledger.close)
        self.stripe = FakeStripe()
        self.oid = self.paid('synthetic-remote-one')
        self.client = FakeApify()

    def paid(self, identity):
        oid, _ = self.ledger.accept(identity, PROFILE, synthetic=True, token=TOKEN)
        sid = self.ledger.checkout(oid, self.stripe)
        self.ledger.payment(event(sid, 'evt_' + identity.replace('-', '_')), self.stripe)
        return oid

    def advance(self):
        return step(self.ledger, self.oid, PROFILE, self.client)

    def test_success_actual_actor_and_durable_claim(self):
        def claim_exists():
            other = Ledger(self.path, now=lambda: self.clock[0])
            try:
                row = other.db.execute('SELECT state FROM remote_runs').fetchone()
                self.assertEqual(row['state'], 'STARTING')
                self.assertFalse(self.ledger.db.in_transaction)
            finally:
                other.close()
        self.client.before_start = claim_exists
        self.assertEqual(self.advance()['status'], 'RUNNING')
        self.assertEqual(self.advance()['status'], 'RUNNING')
        self.client.run['status'] = 'SUCCEEDED'
        self.assertEqual(self.advance()['status'], 'READY')
        self.assertEqual(self.advance()['status'], 'READY')
        self.assertEqual(self.client.starts, 1)
        self.assertEqual(self.ledger.order(self.oid)['attempts'], 1)
        self.assertEqual(self.ledger.db.execute('SELECT state FROM remote_runs').fetchone()[0], 'CONSUMED')
        self.assertIn(b'Beanfit', self.ledger.download(self.oid, TOKEN)['markdown'])
        self.assertEqual(self.ledger.audit()['classification'], 'EXCLUDED_TEST')

    def test_timeout_freezes_current_and_other_order(self):
        self.client.error = TimeoutError('secret must not leak')
        with self.assertRaisesRegex(ApifyTestError, '^APIFY_START_UNKNOWN_RECONCILE_NO_RETRY$'):
            self.advance()
        with self.assertRaisesRegex(ActivationError, 'APIFY_START_UNKNOWN'):
            self.advance()
        second = self.paid('synthetic-remote-two')
        with self.assertRaisesRegex(ActivationError, 'APIFY_UNRESOLVED_RUN_NO_START'):
            step(self.ledger, second, PROFILE, self.client)
        self.assertEqual(self.client.starts, 1)
        self.assertEqual(self.ledger.order(self.oid)['attempts'], 0)

    def test_concurrent_claim_has_one_start(self):
        barrier = threading.Barrier(2)
        self.client.preflight_hook = lambda: barrier.wait(timeout=5)
        def worker():
            ledger = Ledger(self.path, now=lambda: self.clock[0])
            try:
                return step(ledger, self.oid, PROFILE, self.client)['status']
            except ActivationError as error:
                return str(error)
            finally:
                ledger.close()
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: worker(), range(2)))
        self.assertEqual(self.client.starts, 1)
        self.assertIn('RUNNING', results)
        self.assertIn('APIFY_UNRESOLVED_RUN_NO_START', results)

    def test_credit_privacy_and_build_gates(self):
        bad_values = [('plan', 'PAID'), ('enabled', False), ('is_paying', True), ('credits', 6),
                      ('cap', 6), ('cap', True), ('usage', 4.8), ('usage', float('nan')),
                      ('usage', -1), ('active_jobs', 1), ('private', False), ('pricing_inactive', False),
                      ('owner', 'other'), ('build_id', 'other'), ('build_status', 'RUNNING')]
        for key, value in bad_values:
            self.client.proof = proof()
            self.client.proof[key] = value
            with self.subTest(key=key), self.assertRaises(ActivationError):
                self.advance()
        self.assertEqual(self.client.starts, 0)

    def test_preflight_stale(self):
        self.client.preflight_hook = lambda: self.clock.__setitem__(0, self.clock[0] + 61)
        with self.assertRaisesRegex(ActivationError, 'APIFY_PREFLIGHT_STALE'):
            self.advance()
        self.assertEqual(self.client.starts, 0)

    def test_input_and_order_state_gate(self):
        with self.assertRaisesRegex(ActivationError, 'FULFILL_INPUT_CONFLICT'):
            step(self.ledger, self.oid, dict(PROFILE, memory_gib=36), self.client)
        oid, _ = self.ledger.accept('synthetic-unpaid', PROFILE, synthetic=True, token=TOKEN)
        with self.assertRaisesRegex(ActivationError, 'FULFILL_STATE'):
            step(self.ledger, oid, PROFILE, self.client)
        self.assertEqual(self.client.starts, 0)

    def test_bad_start_binding_becomes_unknown(self):
        self.client.run['buildId'] = 'other'
        with self.assertRaisesRegex(ActivationError, 'APIFY_START_UNKNOWN'):
            self.advance()
        self.assertEqual(self.ledger.db.execute('SELECT state FROM remote_runs').fetchone()[0], 'UNKNOWN')

    def test_poll_identity_store_hash_and_input_fail_closed(self):
        self.advance()
        original = remote_run('SUCCEEDED')
        for key, value in [('id', 'other'), ('buildId', 'other'), ('actId', 'other'),
                           ('defaultKeyValueStoreId', 'other'), ('generalAccess', 'PUBLIC'),
                           ('status', 'UNKNOWN'), ('chargedEventCounts', {'paid': 1})]:
            self.client.run = dict(original, **{key: value})
            with self.subTest(key=key), self.assertRaises(ActivationError):
                self.advance()
        self.client.run = original
        self.client.store['id'] = 'other'
        with self.assertRaisesRegex(ActivationError, 'APIFY_STORE_BINDING'):
            self.advance()
        self.client.store['id'] = 'store123'
        for access in (None, 'PUBLIC', 'FOLLOW_USER_SETTING'):
            self.client.store['generalAccess'] = access
            with self.subTest(access=access), self.assertRaisesRegex(ActivationError, 'APIFY_STORE_BINDING'):
                self.advance()
        del self.client.store['generalAccess']
        with self.assertRaisesRegex(ActivationError, 'APIFY_STORE_BINDING'):
            self.advance()
        self.client.store['generalAccess'] = 'RESTRICTED'
        self.client.records['INPUT'] = b'{}'
        with self.assertRaisesRegex(ActivationError, 'APIFY_INPUT_RETAINED'):
            self.advance()
        del self.client.records['INPUT']
        self.client.records['REPORT.md'] = b'tampered'
        with self.assertRaisesRegex(ActivationError, 'APIFY_ARTIFACT_BINDING'):
            self.advance()
        self.assertEqual(self.ledger.order(self.oid)['state'], 'PAID')
        self.assertEqual(self.client.starts, 1)

    def test_terminal_failure_consumes_one_retry_and_max_two(self):
        self.advance()
        self.client.run['status'] = 'FAILED'
        with self.assertRaisesRegex(ActivationError, 'FULFILLMENT_FAILED'):
            self.advance()
        self.assertEqual(self.ledger.order(self.oid)['attempts'], 1)
        with self.assertRaisesRegex(ActivationError, 'RETRY_NOT_DUE'):
            self.advance()
        self.clock[0] += 900
        self.client.run = remote_run()
        self.client.run['id'] = 'run456'
        self.client.run['defaultKeyValueStoreId'] = 'store456'
        self.assertEqual(self.advance()['status'], 'RUNNING')
        # Use exact second-run identities for read hooks.
        self.client.get_run = lambda _: dict(self.client.run, status='FAILED')
        self.client.get_store = lambda _: dict(id='store456', userId='user123', generalAccess='RESTRICTED')
        self.client.record = lambda *_: None
        with self.assertRaisesRegex(ActivationError, 'FULFILLMENT_FAILED'):
            self.advance()
        self.assertEqual(self.ledger.order(self.oid)['state'], 'DELIVERY_FAILED')
        with self.assertRaises(ActivationError):
            self.advance()
        self.assertEqual(self.client.starts, 2)

    def test_cache_survives_local_interruption_without_remote_retry(self):
        self.advance()
        self.client.run['status'] = 'SUCCEEDED'
        with patch.object(self.ledger, 'fulfill', side_effect=RuntimeError('interrupt')):
            with self.assertRaises(RuntimeError):
                self.advance()
        self.assertEqual(self.ledger.db.execute('SELECT state FROM remote_runs').fetchone()[0], 'CACHED')
        self.client.get_run = lambda _: (_ for _ in ()).throw(AssertionError('remote read during cache consume'))
        self.assertEqual(self.advance()['status'], 'READY')
        self.assertEqual(self.client.starts, 1)

    def test_poll_requires_explicit_run_safety_options(self):
        self.advance()
        for key, value in [('restartOnError', None), ('restartOnError', True),
                           ('forcePermissionLevel', None), ('forcePermissionLevel', 'FULL_PERMISSIONS'),
                           ('maxTotalChargeUsd', None), ('maxTotalChargeUsd', True),
                           ('maxTotalChargeUsd', .26), ('maxTotalChargeUsd', 0),
                           ('maxTotalChargeUsd', float('nan'))]:
            self.client.run = remote_run('SUCCEEDED')
            self.client.run['options'][key] = value
            with self.subTest(key=key, value=value), self.assertRaisesRegex(ActivationError, 'APIFY_RUN_LIMIT_BINDING'):
                self.advance()
        self.assertEqual(self.client.starts, 1)


class ApifyTransportTests(unittest.TestCase):
    def test_fixed_start_parameters_and_synthetic_gate(self):
        opener = Opener({'data': remote_run()})
        client = ApifyTestClient('syntheticTokenOnly', opener=opener)
        with self.assertRaises(ActivationError):
            client.start(PROFILE)
        client.start(PROFILE, synthetic=True)
        req, timeout = opener.calls[0]
        parts = urlsplit(req.full_url)
        self.assertEqual(parts.scheme, 'https')
        self.assertEqual(parts.netloc, 'api.apify.com')
        self.assertEqual(parts.path, '/v2/actors/' + ACTOR_ID + '/runs')
        self.assertEqual(parse_qs(parts.query), dict(build=['1.0.2'], memory=['128'], timeout=['60'],
            restartOnError=['false'], waitForFinish=['0'], maxTotalChargeUsd=['0.25'], forcePermissionLevel=['LIMITED_PERMISSIONS']))
        self.assertEqual(json.loads(req.data), PROFILE)
        self.assertEqual(timeout, 10)
        self.assertEqual(opener.responses[0].read_limit, MAX_BYTES + 1)

    def test_transport_privacy_bounds_and_404(self):
        for result in (TimeoutError('SECRET'), b'not json SECRET', b'x' * (MAX_BYTES + 1),
                       Response({'data': {}}, 'https://evil.example/SECRET')):
            with self.subTest(result_type=type(result)), self.assertRaises(ActivationError) as caught:
                ApifyTestClient('synthetic', opener=Opener(result)).get_run('run123')
            self.assertNotIn('SECRET', str(caught.exception))
        missing = HTTPError('https://api.apify.com/x', 404, 'no', {}, None)
        self.assertIsNone(ApifyTestClient('synthetic', opener=Opener(missing)).record('store123', 'INPUT'))
        with patch('beanfit.apify_fulfillment.build_opener') as build:
            ApifyTestClient('synthetic')
        self.assertEqual(build.call_args.args[0].proxies, {})
        self.assertIsInstance(build.call_args.args[1], NoRedirect)
        for bad in ('../x', 'x?secret', 'x/other'):
            with self.assertRaises(ActivationError):
                ApifyTestClient('synthetic', opener=Opener()).get_run(bad)

    def test_preflight_extracts_only_required_fields(self):
        user = dict(id='user123', isPaying=False, email='PRIVATE', proxy=dict(password='SECRET'),
                    plan=dict(tier='FREE', isEnabled=True, monthlyUsageCreditsUsd=5))
        limits = dict(limits=dict(maxMonthlyUsageUsd=5), current=dict(monthlyUsageUsd=.01, activeActorJobCount=0))
        actor = dict(id=ACTOR_ID, userId='user123', isPublic=False, pricingInfos=[])
        build = dict(id=BUILD_ID, actId=ACTOR_ID, buildNumber=BUILD_NUMBER, status='SUCCEEDED')
        opener = Opener(*[{'data': x} for x in (user, limits, actor, build)])
        result = ApifyTestClient('synthetic', opener=opener).preflight()
        self.assertEqual(result, proof())
        self.assertNotIn('SECRET', json.dumps(result))
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertTrue(all(req.method == 'GET' for req, _ in opener.calls))
        del actor['pricingInfos']
        absent = Opener(*[{'data': x} for x in (user, limits, actor, build)])
        self.assertIs(ApifyTestClient('synthetic', opener=absent).preflight()['pricing_inactive'], False)
