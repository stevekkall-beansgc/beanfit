import hashlib
import hmac
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs

from beanfit.stripe_test import (
    AMOUNT_CENTS, API_VERSION, CONTRACT, MAX_RESPONSE_BYTES, MAX_WEBHOOK_BYTES,
    NoRedirect, StripeTestClient, StripeTestError, verify_webhook,
)

KEY = 'sk_test_syntheticFixtureOnly'
SECRET = 'whsec_syntheticFixtureOnly'
META = {'order_id': 'order-1', 'contract': CONTRACT}


def checkout(**kwargs):
    return dict({'id': 'cs_test_123', 'object': 'checkout.session', 'livemode': False}, **kwargs)


def intent(**kwargs):
    return dict({'id': 'pi_123', 'object': 'payment_intent', 'livemode': False,
                 'status': 'succeeded', 'amount': 1200, 'currency': 'usd', 'metadata': META}, **kwargs)


def refund(**kwargs):
    return dict({'id': 're_123', 'object': 'refund', 'payment_intent': 'pi_123',
                 'amount': 1200, 'currency': 'usd', 'metadata': META, 'status': 'succeeded'}, **kwargs)


class Response:
    status = 200

    def __init__(self, value, url):
        self.raw = value if isinstance(value, bytes) else json.dumps(value).encode()
        self.url = url
        self.read_limit = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def geturl(self):
        return self.url

    def read(self, limit):
        self.read_limit = limit
        return self.raw[:limit]


class Opener:
    def __init__(self, *results):
        self.results = iter(results)
        self.calls = []
        self.responses = []

    def open(self, req, timeout):
        self.calls.append((req, timeout))
        result = next(self.results)
        if isinstance(result, Exception):
            raise result
        response = result if isinstance(result, Response) else Response(result, req.full_url)
        self.responses.append(response)
        return response


class StripeTransportTests(unittest.TestCase):
    def test_create_fixed_offer_and_idempotency(self):
        opener = Opener(checkout(), checkout())
        client = StripeTestClient(KEY, opener=opener)
        for _ in range(2):
            client.create_checkout('order-1', 'http://localhost:8080/success', 'http://127.0.0.1/cancel')
        first, second = [call[0] for call in opener.calls]
        fields = parse_qs(first.data.decode())
        self.assertEqual(first.full_url, 'https://api.stripe.com/v1/checkout/sessions')
        self.assertEqual(first.method, 'POST')
        self.assertEqual(first.get_header('Authorization'), 'Bearer ' + KEY)
        self.assertEqual(first.get_header('Stripe-version'), API_VERSION)
        self.assertEqual(first.get_header('Idempotency-key'), second.get_header('Idempotency-key'))
        self.assertEqual(fields['line_items[0][price_data][unit_amount]'], [str(AMOUNT_CENTS)])
        self.assertEqual(fields['line_items[0][price_data][currency]'], ['usd'])
        self.assertEqual(fields['line_items[0][quantity]'], ['1'])
        self.assertEqual(fields['payment_method_types[0]'], ['card'])
        self.assertEqual(fields['payment_intent_data[metadata][contract]'], [CONTRACT])
        self.assertEqual(fields['payment_intent_data[metadata][order_id]'], ['order-1'])
        self.assertEqual(fields['metadata[order_id]'], ['order-1'])
        self.assertEqual(fields['client_reference_id'], ['order-1'])
        self.assertNotIn('customer_email', fields)
        self.assertEqual(opener.calls[0][1], 10.0)
        self.assertEqual(opener.responses[0].read_limit, MAX_RESPONSE_BYTES + 1)

    def test_test_keys_only(self):
        for key in ('sk_live_secret', 'rk_live_secret', 'pk_test_secret', '', None,
                    'sk_test_x\nAuthorization: x', 'sk_test_'):
            with self.subTest(key=key), self.assertRaises(StripeTestError):
                StripeTestClient(key)
        StripeTestClient('rk_test_syntheticFixtureOnly', opener=Opener())

    def test_timeout_bounded(self):
        for value in (None, True, 0, -1, 31, float('inf'), float('nan')):
            with self.subTest(value=value), self.assertRaises(StripeTestError):
                StripeTestClient(KEY, timeout=value)

    def test_default_disables_proxies_and_redirects(self):
        with patch('beanfit.stripe_test.build_opener') as build:
            StripeTestClient(KEY)
        proxy, redirect = build.call_args.args
        self.assertEqual(proxy.proxies, {})
        self.assertIsInstance(redirect, NoRedirect)
        with self.assertRaises(StripeTestError):
            redirect.redirect_request(None, None, 302, '', {}, 'https://evil.example')

    def test_url_and_id_reject_before_network(self):
        opener = Opener()
        client = StripeTestClient(KEY, opener=opener)
        for url in ('https://localhost/a', 'http://localhost.evil/a', 'http://evil/a',
                    'http://localhost@evil/a', 'http://user@localhost/a', 'http://localhost:0/a',
                    'http://localhost:bad/a', 'http://localhost/a\n', 'http://localhost/a#fragment'):
            with self.subTest(url=url), self.assertRaises(StripeTestError):
                client.create_checkout('order-1', url, 'http://localhost/cancel')
        for bad in ('../x', 'x?token=secret', 'x/other', '', None):
            with self.subTest(bad=bad), self.assertRaises(StripeTestError):
                client.get_payment_intent(bad)
        with self.assertRaises(StripeTestError):
            client.get_checkout('cs_live_123')
        self.assertEqual(opener.calls, [])

    def test_live_missing_or_wrong_objects_fail(self):
        for value in (checkout(livemode=True), checkout(livemode=0),
                      {'object': 'checkout.session'}, intent(), []):
            with self.subTest(value=value), self.assertRaises(StripeTestError):
                StripeTestClient(KEY, opener=Opener(value)).get_checkout('cs_test_123')

    def test_get_id_binding_and_no_idempotency_header(self):
        opener = Opener(checkout(), intent())
        client = StripeTestClient(KEY, opener=opener)
        client.get_checkout('cs_test_123')
        client.get_payment_intent('pi_123')
        for req, _ in opener.calls:
            self.assertEqual(req.method, 'GET')
            self.assertIsNone(req.get_header('Idempotency-key'))
        with self.assertRaises(StripeTestError):
            StripeTestClient(KEY, opener=Opener(intent(id='pi_other'))).get_payment_intent('pi_123')

    def test_transport_errors_and_invalid_json_sanitized(self):
        failures = [RuntimeError('SECRET'), HTTPError('https://SECRET', 400, 'SECRET', {}, None),
                    b'not json SECRET', b'{"livemode":false,"livemode":true}',
                    b'{"secret":NaN}', b'\xff', b'x' * (MAX_RESPONSE_BYTES + 1),
                    Response(checkout(), 'https://evil.example/SECRET')]
        for failure in failures:
            with self.subTest(kind=type(failure)):
                try:
                    StripeTestClient(KEY, opener=Opener(failure)).get_checkout('cs_test_123')
                except StripeTestError as exc:
                    self.assertNotIn('SECRET', str(exc))
                    self.assertIsNone(exc.__cause__)
                else:
                    self.fail('invalid response accepted')

    def test_refund_checks_pi_before_mutation_and_reuses_key(self):
        opener = Opener(intent(), refund(), intent(), refund(status='pending'))
        client = StripeTestClient(KEY, opener=opener)
        self.assertEqual(client.refund_full('pi_123', 'order-1')['status'], 'succeeded')
        self.assertEqual(client.refund_full('pi_123', 'order-1')['status'], 'pending')
        posts = [req for req, _ in opener.calls if req.method == 'POST']
        self.assertEqual(len(posts), 2)
        self.assertEqual(posts[0].get_header('Idempotency-key'), posts[1].get_header('Idempotency-key'))
        self.assertEqual(parse_qs(posts[0].data.decode())['amount'], ['1200'])
        self.assertNotIn('livemode', refund())
        for wrong in (intent(livemode=True), intent(amount=100), intent(amount=True),
                      intent(currency='eur'), intent(metadata={}), intent(status='processing')):
            bad_opener = Opener(wrong)
            with self.subTest(wrong=wrong), self.assertRaises(StripeTestError):
                StripeTestClient(KEY, opener=bad_opener).refund_full('pi_123', 'order-1')
            self.assertEqual(len(bad_opener.calls), 1)

    def test_refund_response_binding(self):
        for bad in (refund(amount=100), refund(payment_intent='pi_other'), refund(currency='eur'),
                    refund(livemode=True), refund(object='charge'), refund(metadata={})):
            with self.subTest(bad=bad), self.assertRaises(StripeTestError):
                StripeTestClient(KEY, opener=Opener(intent(), bad)).refund_full('pi_123', 'order-1')

    def test_get_refund_reads_fresh_status_without_mutation(self):
        opener = Opener(intent(), refund(status='pending'), intent(), refund(status='succeeded'))
        client = StripeTestClient(KEY, opener=opener)
        self.assertEqual(client.get_refund('re_123', 'pi_123', 'order-1')['status'], 'pending')
        self.assertEqual(client.get_refund('re_123', 'pi_123', 'order-1')['status'], 'succeeded')
        self.assertEqual(len(opener.calls), 4)
        for request, _ in opener.calls:
            self.assertEqual(request.method, 'GET')
            self.assertIsNone(request.get_header('Idempotency-key'))
        self.assertEqual(opener.calls[1][0].full_url, 'https://api.stripe.com/v1/refunds/re_123')

    def test_get_refund_validates_mode_and_all_bindings(self):
        for bad in (refund(id='re_other'), refund(payment_intent='pi_other'), refund(amount=1),
                    refund(currency='eur'), refund(metadata={}), refund(object='charge'),
                    refund(livemode=True)):
            with self.subTest(bad=bad), self.assertRaises(StripeTestError):
                StripeTestClient(KEY, opener=Opener(intent(), bad)).get_refund('re_123', 'pi_123', 'order-1')
        for bad in (intent(livemode=True), intent(metadata={}), intent(status='processing')):
            opener = Opener(bad)
            with self.subTest(bad=bad), self.assertRaises(StripeTestError):
                StripeTestClient(KEY, opener=opener).get_refund('re_123', 'pi_123', 'order-1')
            self.assertEqual(len(opener.calls), 1)
        opener = Opener()
        with self.assertRaises(StripeTestError):
            StripeTestClient(KEY, opener=opener).get_refund('re_123/../secret', 'pi_123', 'order-1')
        self.assertEqual(opener.calls, [])


class WebhookTests(unittest.TestCase):
    raw = b'{"object":"event","livemode":false,"id":"evt_synthetic"}'

    def signed(self, raw=None, timestamp='1000'):
        raw = self.raw if raw is None else raw
        digest = hmac.new(SECRET.encode(), timestamp.encode() + b'.' + raw, hashlib.sha256).hexdigest()
        return f't={timestamp},v1={digest}'

    def test_good_exact_raw_multiple_v1_and_boundaries(self):
        signature = self.signed() + ',v1=' + '0' * 64 + ',v0=ignored'
        for now in (700, 1000, 1300):
            self.assertEqual(verify_webhook(self.raw, signature, SECRET, now)['id'], 'evt_synthetic')

    def test_bad_signature_replay_future_and_duplicates(self):
        cases = [(self.raw, self.signed(), SECRET, 1301),
                 (self.raw, self.signed(), SECRET, 699),
                 (self.raw + b' ', self.signed(), SECRET, 1000),
                 (self.raw, self.signed(), 'whsec_wrong', 1000),
                 (self.raw, self.signed() + ',t=1000', SECRET, 1000),
                 (self.raw, self.signed().replace('v1=', 'v0='), SECRET, 1000),
                 (self.raw, 't=1000,v1=invalid', SECRET, 1000),
                 (self.raw, self.signed(), SECRET, float('nan')),
                 (self.raw, self.signed(), SECRET, True),
                 (self.raw, 'x' * 4097, SECRET, 1000),
                 (b'x' * (MAX_WEBHOOK_BYTES + 1), self.signed(), SECRET, 1000),
                 (self.raw.decode(), self.signed(), SECRET, 1000)]
        for args in cases:
            with self.subTest(raw_type=type(args[0])), self.assertRaises(StripeTestError):
                verify_webhook(*args)

    def test_authenticated_payload_still_requires_test_event_and_unique_json(self):
        for raw in (b'{"object":"event","livemode":true}', b'{"object":"event"}',
                    b'{"object":"event","livemode":0}',
                    b'{"object":"event","livemode":false,"livemode":false}',
                    b'{"object":"event","livemode":false,"value":NaN}', b'not json', b'[]'):
            with self.subTest(raw=raw), self.assertRaises(StripeTestError):
                verify_webhook(raw, self.signed(raw), SECRET, 1000)
