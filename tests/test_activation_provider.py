"""Provider CLI boundary checks with an injected, strictly offline Stripe API."""
import contextlib
import hashlib
import hmac
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs

from beanfit.activation import ActivationError, Ledger
from beanfit.stripe_test import StripeTestClient, StripeTestError
from tests.test_activation import actor_producer

ROOT = Path(__file__).resolve().parents[1]
with patch.object(sys, 'path', [str(ROOT / 'scripts'), *sys.path]):
    SPEC = importlib.util.spec_from_file_location('provider_under_test', ROOT / 'scripts/activation_provider.py')
    DRIVER = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(DRIVER)

TOKEN = 'synthetic-provider-token-00000000000000000'
SECRET = 'whsec_SYNTHETICBOUNDARYONLY'
NOW = 1788609600


class Response:
    status = 200
    def __init__(self, url, value):
        self.url, self.value = url, value
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def geturl(self): return self.url
    def read(self, bound): return json.dumps(self.value).encode()[:bound]


class OfflineStripe:
    def __init__(self):
        self.calls, self.sessions, self.intents, self.refunds = [], {}, {}, {}

    def open(self, request, timeout):
        self.calls.append(request)
        url = request.full_url
        if request.method == 'POST' and url.endswith('/checkout/sessions'):
            oid = parse_qs(request.data.decode())['client_reference_id'][0]
            suffix = hashlib.sha256(oid.encode()).hexdigest()[:20]
            sid, pi = 'cs_test_' + suffix, 'pi_' + suffix
            meta = dict(order_id=oid, contract='BF-CER-v1.0')
            self.sessions[sid] = dict(id=sid, object='checkout.session', livemode=False,
                client_reference_id=oid, mode='payment', status='complete', payment_status='paid',
                amount_total=1200, currency='usd', metadata=meta, payment_intent=pi,
                url='https://checkout.stripe.com/c/pay/' + sid)
            self.intents[pi] = dict(id=pi, object='payment_intent', livemode=False,
                status='succeeded', amount=1200, currency='usd', metadata=meta)
            value = self.sessions[sid]
        elif request.method == 'GET' and '/checkout/sessions/' in url:
            value = self.sessions[url.rsplit('/', 1)[1]]
        elif request.method == 'GET' and '/payment_intents/' in url:
            value = self.intents[url.rsplit('/', 1)[1]]
        elif request.method == 'POST' and url.endswith('/refunds'):
            fields = parse_qs(request.data.decode())
            pi = fields['payment_intent'][0]
            rid = 're_' + pi[3:]
            self.refunds[rid] = dict(id=rid, object='refund', payment_intent=pi,
                amount=1200, currency='usd', metadata=self.intents[pi]['metadata'], status='pending')
            value = self.refunds[rid]
        elif request.method == 'GET' and '/refunds/' in url:
            value = self.refunds[url.rsplit('/', 1)[1]]
        else:
            raise AssertionError('unexpected fake-provider request')
        return Response(url, value)


@unittest.skipUnless(os.name == 'posix' and hasattr(os, 'O_NOFOLLOW'), 'POSIX private provider driver')
class ProviderBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / 'private'
        self.api = OfflineStripe()
        self.env = dict(STRIPE_TEST_KEY='sk_test_SYNTHETICBOUNDARYONLY',
            BF_CER_TEST_DOWNLOAD_TOKEN=TOKEN, BF_CER_WEBHOOK_SECRET=SECRET)

    def invoke(self, action, *, raw=b'', env=None, state=None):
        output = io.StringIO()
        prior_umask = os.umask(0o077)
        os.umask(prior_umask)
        try:
            with patch.dict(os.environ, self.env if env is None else env, clear=True), \
                    patch.object(sys, 'argv', ['activation_provider', action, '--state-dir', str(state or self.state)]), \
                    patch.object(sys, 'stdin', io.TextIOWrapper(io.BytesIO(raw))), \
                    patch.object(DRIVER.time, 'time', return_value=NOW), \
                    patch('beanfit.stripe_test.build_opener', return_value=self.api), \
                    contextlib.redirect_stdout(output):
                DRIVER.main()
            return json.loads(output.getvalue())
        finally:
            os.umask(prior_umask)

    def signed(self, sid, identity='evt_BOUNDARY'):
        raw = json.dumps(dict(id=identity, object='event', livemode=False,
            type='checkout.session.completed', data={'object': {'id': sid}})).encode()
        signature = hmac.new(SECRET.encode(), str(NOW).encode() + b'.' + raw, hashlib.sha256).hexdigest()
        return raw, dict(self.env, BF_CER_STRIPE_SIGNATURE=f't={NOW},v1={signature}')

    def test_other_bound_order_event_cannot_mutate_ledger(self):
        self.invoke('checkout')
        ledger = Ledger(self.state / 'ledger.sqlite', now=lambda: NOW)
        try:
            oid, _ = ledger.accept('synthetic-another-order', DRIVER.PROFILE, synthetic=True, token=TOKEN)
            sid = ledger.checkout(oid, StripeTestClient(self.env['STRIPE_TEST_KEY'], opener=self.api))
            raw, env = self.signed(sid)
            with self.assertRaises(ActivationError):
                self.invoke('event', raw=raw, env=env)
            self.assertEqual(ledger.order(oid)['state'], 'CHECKOUT')
        finally:
            ledger.close()

    def test_existing_ledger_symlink_rejected_before_provider_call(self):
        self.state.mkdir(mode=0o700)
        target = Path(self.tmp.name) / 'target.sqlite'
        ledger = Ledger(target, now=lambda: NOW)
        ledger.close()
        (self.state / 'ledger.sqlite').symlink_to(target)
        with self.assertRaises(ActivationError):
            self.invoke('checkout')
        self.assertEqual(self.api.calls, [])

    def test_missing_download_token_or_invalid_key_makes_no_provider_call(self):
        for missing in ('BF_CER_TEST_DOWNLOAD_TOKEN', 'STRIPE_TEST_KEY'):
            with self.subTest(missing=missing):
                env = dict(self.env)
                env.pop(missing)
                with self.assertRaises((ActivationError, StripeTestError)):
                    self.invoke('checkout', env=env)
        with self.assertRaises(StripeTestError):
            self.invoke('checkout', env=dict(self.env, STRIPE_TEST_KEY='sk_live_SYNTHETICINVALID'))
        self.assertEqual(self.api.calls, [])

    def test_missing_or_invalid_webhook_auth_fails_before_provider_read(self):
        checkout = self.invoke('checkout')
        raw, env = self.signed(checkout['session_id'])
        before = len(self.api.calls)
        for bad in (dict(env, BF_CER_WEBHOOK_SECRET=''),
                    dict(env, BF_CER_STRIPE_SIGNATURE=''),
                    dict(env, BF_CER_WEBHOOK_SECRET='whsec_DIFFERENT')):
            with self.subTest(bad=bad), self.assertRaises(StripeTestError):
                self.invoke('event', raw=raw, env=bad)
        with self.assertRaises(StripeTestError):
            self.invoke('event', raw=raw + b' ', env=env)
        self.assertEqual(len(self.api.calls), before)

    def test_signed_live_event_and_oversized_payload_fail_before_provider_read(self):
        checkout = self.invoke('checkout')
        raw, _ = self.signed(checkout['session_id'])
        before = len(self.api.calls)
        for payload in (raw.replace(b'"livemode": false', b'"livemode": true'), b'x' * 262145):
            signature = hmac.new(SECRET.encode(), str(NOW).encode() + b'.' + payload, hashlib.sha256).hexdigest()
            env = dict(self.env, BF_CER_STRIPE_SIGNATURE=f't={NOW},v1={signature}')
            with self.assertRaises(StripeTestError):
                self.invoke('event', raw=payload, env=env)
        self.assertEqual(len(self.api.calls), before)

    def test_private_directory_and_file_modes_are_enforced(self):
        self.state.mkdir(mode=0o755)
        self.state.chmod(0o755)
        with self.assertRaisesRegex(ActivationError, 'STATE_DIRECTORY_MUST_BE_PRIVATE'):
            self.invoke('checkout')
        self.state.chmod(0o700)
        for name in ('ledger.sqlite', 'ledger.sqlite-wal', 'ledger.sqlite-shm', 'REPORT.md', 'REPORT.json'):
            with self.subTest(file=name):
                path = self.state / name
                path.touch(mode=0o644)
                path.chmod(0o644)
                with self.assertRaisesRegex(ActivationError, 'PRIVATE_REGULAR_FILE_REQUIRED'):
                    self.invoke('checkout')
                path.unlink()
        self.assertEqual(self.api.calls, [])

    def test_state_inside_repo_is_rejected_without_creation(self):
        path = ROOT / 'synthetic-provider-forbidden-state'
        self.assertFalse(path.exists())
        with self.assertRaisesRegex(ActivationError, 'STATE_MUST_BE_OUTSIDE_REPOSITORY'):
            self.invoke('checkout', state=path)
        self.assertFalse(path.exists())
        self.assertEqual(self.api.calls, [])

    def test_report_symlink_hardlink_or_broad_mode_never_truncates_target(self):
        self.state.mkdir(mode=0o700)
        target = Path(self.tmp.name) / 'synthetic-protected-target'
        target.write_bytes(b'unchanged synthetic fixture')
        target.chmod(0o600)
        report = self.state / 'REPORT.md'
        for kind in ('symlink', 'hardlink', 'broad_mode'):
            with self.subTest(kind=kind):
                if kind == 'symlink': report.symlink_to(target)
                elif kind == 'hardlink': os.link(target, report)
                else:
                    report.write_bytes(b'unchanged synthetic fixture')
                    report.chmod(0o644)
                with self.assertRaises((ActivationError, OSError)):
                    DRIVER.write_private(report, b'new content')
                self.assertEqual(target.read_bytes(), b'unchanged synthetic fixture')
                self.assertEqual(report.read_bytes(), b'unchanged synthetic fixture')
                report.unlink()

    def test_real_transport_to_ledger_event_delivery_refund_cycle(self):
        checkout = self.invoke('checkout')
        raw, env = self.signed(checkout['session_id'])
        paid = self.invoke('event', raw=raw, env=env)
        self.assertEqual(paid['state'], 'PAID')
        self.assertEqual(self.invoke('event', raw=raw, env=env), paid)
        with patch.object(DRIVER, 'producer', actor_producer):
            self.assertEqual(self.invoke('fulfill')['state'], 'READY')
        manifest = self.invoke('download')['manifest']
        for name, field in (('REPORT.md', 'markdown_sha256'), ('REPORT.json', 'json_sha256')):
            path = self.state / name
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), manifest[field])
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.invoke('refund')['state'], 'REFUND_PENDING')
        for refund in self.api.refunds.values(): refund['status'] = 'succeeded'
        self.assertEqual(self.invoke('refund')['state'], 'REFUNDED')
        self.assertEqual(sum(req.method == 'POST' and req.full_url.endswith('/refunds')
                             for req in self.api.calls), 1)
        audit = self.invoke('audit')
        self.assertEqual(audit['promotion_eligible_cents'], 0)
        for credential in self.env.values():
            self.assertNotIn(credential, json.dumps(audit))

    def test_connection_closes_on_missing_token_and_accept_conflict(self):
        closed = []
        class TrackingLedger(Ledger):
            def close(self):
                closed.append(1)
                super().close()
        with patch.object(DRIVER, 'Ledger', TrackingLedger):
            with self.assertRaises(ActivationError):
                self.invoke('audit', env={})
            self.assertEqual(len(closed), 1)
            self.invoke('audit')
            with self.assertRaises(ActivationError):
                self.invoke('audit', env=dict(self.env, BF_CER_TEST_DOWNLOAD_TOKEN='different-token-000000000000000000000'))
            self.assertEqual(len(closed), 3)


if __name__ == '__main__':
    unittest.main()


class UnsupportedProviderPlatformTests(unittest.TestCase):
    def test_non_posix_stops_before_state_or_network(self):
        with patch.object(DRIVER.os, 'name', 'nt'), patch.object(DRIVER, 'Ledger') as ledger, patch.object(DRIVER, 'StripeTestClient') as client:
            with self.assertRaisesRegex(ActivationError, 'PROVIDER_DRIVER_REQUIRES_POSIX'):
                DRIVER.main()
            ledger.assert_not_called()
            client.assert_not_called()
