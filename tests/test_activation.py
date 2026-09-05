"""Synthetic-only activation QA; no network, provider account, or customer input."""
import copy
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

from beanfit.activation import ActivationError, Ledger, canonical, digest
from beanfit.apify_actor import run
from beanfit.report import CONTRACT_VERSION, InputRejected, generate_report


PROFILE = dict(device_chip='Apple M3 Pro', memory_gib=18, use_case='coding',
               operating_system='macOS 15.6 arm64')
TOKEN = 'synthetic-download-token-00000000000001'


class MemoryStore:
    def __init__(self, profile):
        self.values = {'INPUT': json.dumps(profile).encode()}

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        self.values.pop(key, None)

    def put(self, key, value, content_type=None):
        self.values[key] = value


def actor_producer(profile):
    """Run the actual adapter and report generator, preserving Actor hashes."""
    store = MemoryStore(profile)
    ticks = iter((100, 101))
    result = run(store, generate=generate_report, revision='a' * 40,
                 memory_mib=128, generated_at='2026-09-05T00:00:00Z',
                 clock=lambda: next(ticks))
    if result != 0:
        raise AssertionError('synthetic Actor failed')
    assert 'INPUT' not in store.values
    return (store.values['OUTPUT'], store.values['REPORT.md'],
            store.values['REPORT.json'])


class FakeStripe:
    """Models provider idempotency independently of the ledger connection."""
    def __init__(self):
        self.sessions = {}
        self.refunds = {}
        self.create_calls = []
        self.refund_calls = []
        self.refund_reads = []
        self.checkout_error = None
        self.refund_error = None
        self.refund_status = 'succeeded'
        self.lock = threading.Lock()

    def create_checkout(self, order_id, success, cancel):
        with self.lock:
            self.create_calls.append(order_id)
            sid = 'cs_test_' + digest(order_id)[:20]
            self.sessions.setdefault(sid, dict(id=sid, livemode=False,
                client_reference_id=order_id, mode='payment', status='complete',
                payment_status='paid', amount_total=1200, currency='usd',
                metadata={'contract': CONTRACT_VERSION, 'order_id': order_id},
                payment_intent='pi_' + digest(order_id)[:20]))
            if self.checkout_error:
                raise self.checkout_error
            return copy.deepcopy(self.sessions[sid])

    def get_checkout(self, session):
        return copy.deepcopy(self.sessions[session])

    def refund_full(self, payment_intent, order_id):
        with self.lock:
            self.refund_calls.append((payment_intent, order_id))
            self.refunds.setdefault(order_id, dict(id='re_' + digest(order_id)[:20],
                payment_intent=payment_intent, amount=1200, currency='usd'))
            if self.refund_error:
                raise self.refund_error
            return dict(self.refunds[order_id], status=self.refund_status)

    def get_refund(self, refund_id, payment_intent, order_id):
        self.refund_reads.append((refund_id, payment_intent, order_id))
        return dict(self.refunds[order_id], status=self.refund_status)


def event(session, identity='evt_synthetic_paid'):
    return dict(id=identity, livemode=False, type='checkout.session.completed',
                data={'object': {'id': session}})


class ActivationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = str(Path(self.tmp.name) / 'ledger.sqlite')
        self.clock = 1788566400
        self.ledger = Ledger(self.path, now=lambda: self.clock)
        self.addCleanup(lambda: self.ledger.close())
        self.stripe = FakeStripe()

    def accept(self, suffix='one', profile=None):
        return self.ledger.accept('synthetic-' + suffix, profile or PROFILE,
                                  synthetic=True, token=TOKEN)[0]

    def paid(self, suffix='one'):
        oid = self.accept(suffix)
        sid = self.ledger.checkout(oid, self.stripe)
        self.ledger.payment(event(sid, 'evt_' + suffix.replace('-', '_')), self.stripe)
        return oid

    def delivered(self):
        oid = self.paid()
        self.ledger.fulfill(oid, PROFILE, actor_producer)
        self.ledger.download(oid, TOKEN)
        return oid

    def reopen(self):
        self.ledger.close()
        self.ledger = Ledger(self.path, now=lambda: self.clock)

    def count(self, table):
        return self.ledger.db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]

    def effects(self):
        return self.ledger.db.execute('SELECT COUNT(DISTINCT effect_key) FROM effects').fetchone()[0]

    def test_intent_dedup_conflict_and_bearer_not_recoverable(self):
        oid = self.accept()
        self.assertEqual(oid, self.accept())
        with self.assertRaisesRegex(ActivationError, 'INTENT_CONFLICT'):
            self.accept(profile=dict(PROFILE, memory_gib=32))
        with self.assertRaisesRegex(ActivationError, 'TOKEN_MISMATCH'):
            self.ledger.accept('synthetic-one', PROFILE, synthetic=True,
                               token='different-synthetic-token-000000000000')
        self.assertEqual(self.count('orders'), 1)
        self.assertEqual(self.count('events'), 1)
        self.assertNotIn(TOKEN, canonical(self.ledger.order(oid)))

    def test_intent_replay_across_date_and_restart_returns_original_order(self):
        oid = self.accept()
        self.clock += 86400
        self.reopen()
        self.assertEqual(self.accept(), oid)
        self.assertNotEqual(self.accept('new-day').split('-')[1], oid.split('-')[1])

    def test_live_intake_and_unsupported_profiles_rejected_before_acceptance(self):
        for synthetic in (False, None, 1):
            with self.subTest(synthetic=synthetic), self.assertRaises(ActivationError):
                self.ledger.accept('synthetic-one', PROFILE, synthetic=synthetic)
        for profile in (dict(PROFILE, device_chip='Intel'),
                        dict(PROFILE, minimum_context_tokens=32768),
                        dict(PROFILE, constraints='special workload'),
                        dict(PROFILE, email='synthetic@example.invalid'),
                        dict(PROFILE, memory_gib=True)):
            with self.subTest(profile=profile), self.assertRaises(InputRejected):
                self.accept(profile=profile)
        self.assertEqual(self.count('orders'), 0)
        self.assertEqual(self.count('events'), 0)
        self.assertEqual(self.stripe.create_calls, [])

    def test_checkout_unknown_restart_reuses_provider_identity(self):
        oid = self.accept()
        self.stripe.checkout_error = TimeoutError('synthetic transport failure')
        with self.assertRaises(TimeoutError):
            self.ledger.checkout(oid, self.stripe)
        self.assertEqual(self.ledger.order(oid)['state'], 'CHECKOUT_UNKNOWN')
        self.reopen()
        self.stripe.checkout_error = None
        session = self.ledger.checkout(oid, self.stripe)
        self.assertEqual(self.ledger.checkout(oid, self.stripe), session)
        self.assertEqual(self.stripe.create_calls, [oid, oid])
        self.assertEqual(len(self.stripe.sessions), 1)

    def test_simultaneous_checkout_claims_share_one_provider_session(self):
        oid = self.accept()
        barrier = threading.Barrier(2)
        base_create = self.stripe.create_checkout
        def delayed_create(*args):
            barrier.wait(timeout=5)
            return base_create(*args)
        self.stripe.create_checkout = delayed_create
        def worker(_):
            ledger = Ledger(self.path, now=lambda: self.clock)
            try:
                return ledger.checkout(oid, self.stripe)
            finally:
                ledger.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            sessions = list(pool.map(worker, (1, 2)))
        self.assertEqual(sessions[0], sessions[1])
        self.assertEqual(len(self.stripe.create_calls), 2)
        self.assertEqual(len(self.stripe.sessions), 1)
        self.assertEqual([row['event_id'] for row in self.ledger.audit()['events']],
                         ['accepted', 'checkout-intent', 'checkout'])

    def test_expired_unknown_checkout_requires_reconciliation_without_new_call(self):
        oid = self.accept()
        self.stripe.checkout_error = TimeoutError()
        with self.assertRaises(TimeoutError):
            self.ledger.checkout(oid, self.stripe)
        self.clock += 23 * 3600
        with self.assertRaisesRegex(ActivationError, 'RECONCILE_CHECKOUT_NO_RETRY'):
            self.ledger.checkout(oid, self.stripe)
        self.assertEqual(len(self.stripe.create_calls), 1)

    def test_paid_duplicate_event_and_distinct_event_same_effect(self):
        oid = self.paid()
        sid = self.ledger.order(oid)['session']
        for ev in (event(sid, 'evt_one'), event(sid, 'evt_second_notification')):
            self.assertEqual(self.ledger.payment(ev, self.stripe), oid)
        self.assertEqual(self.effects(), 1)
        self.assertEqual(self.count('effects'), 2)
        self.assertEqual([row['event_id'] for row in self.ledger.audit()['events']],
                         ['accepted', 'checkout-intent', 'checkout', 'evt_one'])

    def test_duplicate_event_alias_cannot_be_reused_for_another_payment(self):
        oid = self.paid()
        self.ledger.payment(event(self.ledger.order(oid)['session'], 'evt_alias'), self.stripe)
        second = self.accept('two')
        sid = self.ledger.checkout(second, self.stripe)
        with self.assertRaisesRegex(ActivationError, 'EVENT_CONFLICT'):
            self.ledger.payment(event(sid, 'evt_alias'), self.stripe)
        self.assertEqual(self.ledger.order(second)['state'], 'CHECKOUT')

    def test_paid_conflicting_reused_event_rejected(self):
        first = self.paid()
        second = self.accept('two')
        sid = self.ledger.checkout(second, self.stripe)
        with self.assertRaisesRegex(ActivationError, 'EVENT_CONFLICT'):
            self.ledger.payment(event(sid, 'evt_one'), self.stripe)
        self.assertEqual(self.ledger.order(second)['state'], 'CHECKOUT')
        self.assertEqual(self.ledger.order(first)['state'], 'PAID')

    def test_paid_binding_uses_fresh_provider_read_not_event_claims(self):
        oid = self.accept()
        sid = self.ledger.checkout(oid, self.stripe)
        base = copy.deepcopy(self.stripe.sessions[sid])
        bad_fields = dict(livemode=True, id='cs_test_other', mode='subscription',
                          status='open', payment_status='unpaid', amount_total=1199,
                          currency='eur', metadata={}, payment_intent='pi/evil')
        for key, value in bad_fields.items():
            with self.subTest(field=key):
                self.stripe.sessions[sid] = dict(base, **{key: value})
                with self.assertRaises(ActivationError):
                    self.ledger.payment(event(sid), self.stripe)
                self.assertEqual(self.ledger.order(oid)['state'], 'CHECKOUT')
        self.stripe.sessions[sid] = base
        malicious = event(sid)
        malicious['data']['object'].update(amount_total=1, customer_email='discard@example.invalid')
        self.ledger.payment(malicious, self.stripe)
        self.assertNotIn('discard@example.invalid', canonical(self.ledger.audit()))

    def test_unbound_session_and_live_event_fail_closed(self):
        oid = self.accept()
        sid = self.stripe.create_checkout(oid, '', '')['id']
        with self.assertRaisesRegex(ActivationError, 'UNBOUND_CHECKOUT'):
            self.ledger.payment(event(sid), self.stripe)
        ev = event(sid)
        ev['livemode'] = True
        with self.assertRaisesRegex(ActivationError, 'LIVE_EVENT_DISABLED'):
            self.ledger.payment(ev, self.stripe)

    def test_real_actor_hashes_fulfill_then_authenticated_retry_after_restart(self):
        oid = self.paid()
        self.assertEqual(self.ledger.fulfill(oid, PROFILE, actor_producer), 0)
        self.assertEqual(self.ledger.order(oid)['state'], 'READY')
        for bad in ('wrong-token', None):
            with self.assertRaisesRegex(ActivationError, 'DOWNLOAD_DENIED'):
                self.ledger.download(oid, bad)
        self.assertEqual(self.ledger.order(oid)['state'], 'READY')
        first = self.ledger.download(oid, TOKEN)
        self.reopen()
        self.assertEqual(self.ledger.download(oid, TOKEN), first)
        self.assertEqual(self.ledger.fulfill(oid, PROFILE,
            lambda _: self.fail('retry regenerated artifact')), 0)
        self.assertEqual(self.count('artifacts'), 1)
        self.assertEqual([row['event_id'] for row in self.ledger.audit()['events']],
                         ['accepted', 'checkout-intent', 'checkout', 'evt_one', 'ready-0', 'download-0'])

    def test_corrupted_artifact_is_never_delivered(self):
        oid = self.paid()
        self.ledger.fulfill(oid, PROFILE, actor_producer)
        self.ledger.db.execute('UPDATE artifacts SET markdown=? WHERE order_id=?', (b'tamper', oid))
        with self.assertRaisesRegex(ActivationError, 'ARTIFACT_CORRUPT'):
            self.ledger.download(oid, TOKEN)
        self.assertIsNone(self.ledger.order(oid)['delivered_at'])

    def test_fulfillment_rejects_wrong_accepted_input_before_producer(self):
        oid = self.paid()
        with self.assertRaisesRegex(ActivationError, 'FULFILL_INPUT_CONFLICT'):
            self.ledger.fulfill(oid, dict(PROFILE, memory_gib=64),
                                lambda _: self.fail('producer reached'))
        self.assertEqual(self.count('artifacts'), 0)

    def test_partial_artifact_database_failure_rolls_back_publication(self):
        oid = self.paid()
        self.ledger.db.executescript("""CREATE TRIGGER fail_ready BEFORE UPDATE ON orders
          WHEN NEW.state='READY' BEGIN SELECT RAISE(ABORT,'synthetic disk failure'); END;""")
        with self.assertRaises(sqlite3.IntegrityError):
            self.ledger.fulfill(oid, PROFILE, actor_producer)
        self.assertEqual(self.count('artifacts'), 0)
        self.assertEqual(self.ledger.order(oid)['state'], 'PAID')

    def test_producer_hash_or_input_tampering_never_publishes(self):
        for failure in ('markdown', 'structured', 'success_marker', 'input'):
            with self.subTest(failure=failure):
                oid = self.paid(failure.replace('_', '-'))
                def producer(profile):
                    output, markdown, structured = actor_producer(profile)
                    if failure == 'markdown':
                        markdown += 'tamper'
                    elif failure == 'structured':
                        structured['new_field'] = 'tamper'
                    elif failure == 'success_marker':
                        output['status'] = 'FAILED'
                    else:
                        from beanfit.apify_actor import _digest
                        structured['accepted_inputs']['memory_gib'] = 64
                        output['report_json_sha256'] = _digest(structured)
                    return output, markdown, structured
                with self.assertRaisesRegex(ActivationError, 'FULFILLMENT_FAILED'):
                    self.ledger.fulfill(oid, PROFILE, producer)
                self.assertEqual(self.ledger.order(oid)['state'], 'RETRY')
                with self.assertRaisesRegex(ActivationError, 'DOWNLOAD_STATE'):
                    self.ledger.download(oid, TOKEN)
        self.assertEqual(self.count('artifacts'), 0)

    def test_one_retry_at_fifteen_minutes_then_freeze_and_refund(self):
        oid = self.paid()
        calls = []
        def broken(_):
            calls.append(1)
            raise RuntimeError('synthetic-private-detail-must-not-escape')
        with self.assertRaisesRegex(ActivationError, 'FULFILLMENT_FAILED'):
            self.ledger.fulfill(oid, PROFILE, broken)
        self.reopen()
        self.clock += 899
        with self.assertRaisesRegex(ActivationError, 'RETRY_NOT_DUE'):
            self.ledger.fulfill(oid, PROFILE, broken)
        self.assertEqual(len(calls), 1)
        self.clock += 1
        with self.assertRaisesRegex(ActivationError, 'FULFILLMENT_FAILED'):
            self.ledger.fulfill(oid, PROFILE, broken)
        self.assertEqual(self.ledger.order(oid)['state'], 'DELIVERY_FAILED')
        self.clock += 900
        with self.assertRaises(ActivationError):
            self.ledger.fulfill(oid, PROFILE, broken)
        self.assertEqual(len(calls), 2)
        self.assertNotIn('synthetic-private-detail', canonical(self.ledger.audit()))
        self.assertEqual(self.ledger.refund(oid, self.stripe), 'REFUNDED')

    def test_retry_recovers_and_correction_has_separate_attempt_allowance(self):
        oid = self.paid()
        with self.assertRaises(ActivationError):
            self.ledger.fulfill(oid, PROFILE, lambda _: (_ for _ in ()).throw(TimeoutError()))
        self.clock += 900
        self.ledger.fulfill(oid, PROFILE, actor_producer)
        self.ledger.download(oid, TOKEN)
        self.ledger.correction(oid, PROFILE)
        self.ledger.fulfill(oid, PROFILE, actor_producer)
        self.assertEqual(self.ledger.order(oid)['state'], 'READY')
        self.assertEqual(self.count('artifacts'), 2)

    def test_one_included_correction_with_no_new_checkout_or_payment(self):
        oid = self.delivered()
        corrected = dict(PROFILE, memory_gib=36)
        self.clock += 7 * 86400
        self.ledger.correction(oid, corrected)
        with self.assertRaisesRegex(ActivationError, 'DOWNLOAD_STATE'):
            self.ledger.download(oid, TOKEN)
        self.ledger.fulfill(oid, corrected, actor_producer)
        result = self.ledger.download(oid, TOKEN)
        self.assertEqual(json.loads(result['structured'])['accepted_inputs']['memory_gib'], 36)
        with self.assertRaisesRegex(ActivationError, 'ONE_CORRECTION_ONLY'):
            self.ledger.correction(oid, PROFILE)
        self.assertEqual(self.count('artifacts'), 2)
        self.assertEqual(len(self.stripe.sessions), 1)
        self.assertEqual(self.count('effects'), 1)

    def test_correction_window_expired_and_clock_rollback_rejected(self):
        oid = self.delivered()
        delivery_time = self.clock
        for time in (delivery_time - 1, delivery_time + 7 * 86400 + 1):
            self.clock = time
            with self.assertRaisesRegex(ActivationError, 'CORRECTION_WINDOW'):
                self.ledger.correction(oid, PROFILE)
        self.assertEqual(self.ledger.order(oid)['revision'], 0)

    def test_refund_unknown_restart_pending_then_success_uses_one_identity(self):
        oid = self.delivered()
        self.stripe.refund_error = TimeoutError()
        with self.assertRaises(TimeoutError):
            self.ledger.refund(oid, self.stripe)
        self.assertEqual(self.ledger.order(oid)['state'], 'REFUND_PENDING')
        with self.assertRaisesRegex(ActivationError, 'DOWNLOAD_STATE'):
            self.ledger.download(oid, TOKEN)
        self.reopen()
        self.stripe.refund_error = None
        for status in ('pending', 'failed', 'canceled', 'requires_action'):
            self.stripe.refund_status = status
            self.assertEqual(self.ledger.refund(oid, self.stripe), 'REFUND_PENDING')
        self.stripe.refund_status = 'succeeded'
        self.assertEqual(self.ledger.refund(oid, self.stripe), 'REFUNDED')
        calls = len(self.stripe.refund_calls)
        self.assertEqual(self.ledger.refund(oid, self.stripe), 'REFUNDED')
        self.assertEqual(len(self.stripe.refund_calls), calls)
        self.assertEqual(len(set(self.stripe.refund_calls)), 1)
        self.assertEqual(len(self.stripe.refunds), 1)

    def test_known_pending_refund_uses_get_even_after_idempotency_window(self):
        oid = self.paid()
        self.stripe.refund_status = 'pending'
        self.ledger.refund(oid, self.stripe)
        self.clock += 23 * 3600
        self.assertEqual(self.ledger.refund(oid, self.stripe), 'REFUND_PENDING')
        self.assertEqual(len(self.stripe.refund_calls), 1)
        self.assertEqual(len(self.stripe.refund_reads), 1)

    def test_expired_unknown_refund_requires_reconciliation_without_new_post(self):
        oid = self.paid()
        self.stripe.refund_error = TimeoutError()
        with self.assertRaises(TimeoutError):
            self.ledger.refund(oid, self.stripe)
        self.clock += 23 * 3600
        with self.assertRaisesRegex(ActivationError, 'RECONCILE_REFUND_NO_RETRY'):
            self.ledger.refund(oid, self.stripe)
        self.assertEqual(len(self.stripe.refund_calls), 1)

    def test_refund_result_binding_rejected_and_remains_pending(self):
        oid = self.paid()
        self.stripe.refunds[oid] = dict(id='re_fake', payment_intent='pi_other',
                                       amount=1200, currency='usd')
        with self.assertRaisesRegex(ActivationError, 'REFUND_BINDING'):
            self.ledger.refund(oid, self.stripe)
        self.assertEqual(self.ledger.order(oid)['state'], 'REFUND_PENDING')

    def test_audit_append_only_chain_and_zero_recognition_through_refund(self):
        oid = self.delivered()
        self.ledger.refund(oid, self.stripe)
        audit = self.ledger.audit()
        self.assertEqual(audit['classification'], 'EXCLUDED_TEST')
        for field in ('real_gross_cents', 'real_net_cents', 'promotion_eligible_cents'):
            self.assertEqual(audit[field], 0)
        for row in audit['events']:
            self.assertEqual(row['payer_class'], 'TEST')
            self.assertEqual(row['acquisition'], 'SYNTHETIC')
            for key, value in row.items():
                if key.endswith('_delta'):
                    self.assertEqual(value, 0)
        for previous, current in zip(audit['events'], audit['events'][1:]):
            self.assertEqual(previous['new_state'], current['prior_state'])
        self.assertEqual([row['event_id'] for row in audit['events']][-2], 'refund-intent')
        for sql in ('DELETE FROM events', "UPDATE events SET body='tampered'"):
            with self.assertRaisesRegex(sqlite3.IntegrityError, 'APPEND_ONLY'):
                self.ledger.db.execute(sql)
        self.assertEqual(audit, self.ledger.audit())

    def test_two_connections_concurrent_payment_and_fulfillment_publish_once(self):
        oid = self.accept()
        sid = self.ledger.checkout(oid, self.stripe)
        barrier = threading.Barrier(2)
        generated = []

        def worker(number):
            ledger = Ledger(self.path, now=lambda: self.clock)
            try:
                barrier.wait(timeout=5)
                ledger.payment(event(sid, 'evt_parallel_' + str(number)), self.stripe)
                def producer(profile):
                    generated.append(number)
                    return actor_producer(profile)
                ledger.fulfill(oid, PROFILE, producer)
                return ledger.download(oid, TOKEN)
            finally:
                ledger.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, (1, 2)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(len(generated), 1)
        self.assertEqual(self.effects(), 1)
        self.assertEqual(self.count('artifacts'), 1)
        identities = [row['event_id'] for row in self.ledger.audit()['events']]
        self.assertEqual(identities[:3], ['accepted', 'checkout-intent', 'checkout'])
        self.assertEqual(identities[4:], ['ready-0', 'download-0'])
        self.assertEqual(sum(value.startswith('evt_parallel_') for value in identities), 1)


if __name__ == '__main__':
    unittest.main()
