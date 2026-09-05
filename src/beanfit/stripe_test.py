"""Bounded Stripe TEST adapter. No live mode, account setup, or customer input API.

Protocol sources (retrieved 2026-09-05): https://docs.stripe.com/api/versioning,
/api/checkout/sessions/create, /api/idempotent_requests, /api/refunds/create,
and https://docs.stripe.com/webhooks#verify-manually. This transport does not
provide durable deduplication; the order ledger must do that beyond Stripe's
at-least-24-hour idempotency retention window.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

CONTRACT = "BF-CER-v1.0"
AMOUNT_CENTS = 1200
CURRENCY = "usd"
API_VERSION = "2026-08-26.dahlia"
API_ORIGIN = "https://api.stripe.com"
MAX_RESPONSE_BYTES = 262144
MAX_WEBHOOK_BYTES = 262144
MAX_SIGNATURE_BYTES = 4096


class StripeTestError(ValueError):
    """Public error text deliberately excludes credentials/provider payloads."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise StripeTestError("Stripe redirects are disabled")


def _identifier(value, prefix=""):
    if (not isinstance(value, str) or len(value) > 200
            or not re.fullmatch(re.escape(prefix) + r"[A-Za-z0-9_-]+", value)):
        raise StripeTestError("Invalid synthetic identifier")
    return value


def _local_url(value):
    if not isinstance(value, str) or len(value) > 2048 or any(ord(c) < 33 for c in value):
        raise StripeTestError("Synthetic return URL must use localhost HTTP")
    try:
        parts = urlsplit(value)
        port = parts.port
        valid = (parts.scheme == "http" and parts.hostname in ("localhost", "127.0.0.1", "::1")
                 and not parts.username and not parts.password and not parts.fragment
                 and (port is None or 1 <= port <= 65535))
    except ValueError:
        valid = False
    if not valid:
        raise StripeTestError("Synthetic return URL must use localhost HTTP")
    return value


def _pairs_unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _json_object(raw):
    try:
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs_unique,
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError, AttributeError):
        raise StripeTestError("Invalid Stripe JSON response") from None
    if not isinstance(result, dict):
        raise StripeTestError("Expected Stripe object")
    return result


def _test_object(value, kind):
    if value.get("object") != kind or value.get("livemode") is not False:
        raise StripeTestError("Expected test-mode Stripe object")
    return value


def _idempotency(operation, identity):
    digest = hashlib.sha256(f"{CONTRACT}:{operation}:{identity}".encode()).hexdigest()
    return f"bfcer-test-{operation}-{digest}"


class StripeTestClient:
    """Test-key-only client; injected opener is a trusted unit-test seam."""

    def __init__(self, api_key: str, *, opener=None, timeout: float = 10.0):
        if not isinstance(api_key, str) or not re.fullmatch(r"(?:sk|rk)_test_[A-Za-z0-9]{1,256}", api_key):
            raise StripeTestError("A Stripe test secret or restricted key is required")
        if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
                or not math.isfinite(timeout) or not 0 < timeout <= 30):
            raise StripeTestError("Timeout must be greater than zero and at most 30 seconds")
        self._api_key = api_key
        self._timeout = timeout
        self._opener = opener if opener is not None else build_opener(ProxyHandler({}), NoRedirect())

    def _request(self, method, path, fields=None, idempotency_key=None):
        # Paths are generated internally; independently reject any alternate origin.
        url = API_ORIGIN + path
        parts = urlsplit(url)
        if (parts.scheme != "https" or parts.netloc != "api.stripe.com"
                or not path.startswith("/v1/") or parts.query or parts.fragment):
            raise StripeTestError("Invalid Stripe endpoint")
        headers = {"Authorization": f"Bearer {self._api_key}", "Stripe-Version": API_VERSION,
                   "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        data = urlencode(fields).encode("ascii") if fields is not None else None
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                if response.geturl() != url or not 200 <= response.status < 300:
                    raise StripeTestError("Unexpected Stripe response")
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except StripeTestError:
            raise
        except Exception:
            raise StripeTestError("Stripe test request failed; reconcile before retry") from None
        if len(raw) > MAX_RESPONSE_BYTES:
            raise StripeTestError("Stripe response exceeds size limit")
        return _json_object(raw)

    def create_checkout(self, order_id: str, success_url: str, cancel_url: str) -> dict:
        _identifier(order_id)
        fields = {
            "mode": "payment", "payment_method_types[0]": "card",
            "line_items[0][price_data][currency]": CURRENCY,
            "line_items[0][price_data][unit_amount]": str(AMOUNT_CENTS),
            "line_items[0][price_data][product_data][name]": "Beanfit compatibility evidence report (synthetic test)",
            "line_items[0][quantity]": "1", "client_reference_id": order_id,
            "metadata[order_id]": order_id, "metadata[contract]": CONTRACT,
            "payment_intent_data[metadata][order_id]": order_id,
            "payment_intent_data[metadata][contract]": CONTRACT,
            "success_url": _local_url(success_url), "cancel_url": _local_url(cancel_url),
            "automatic_tax[enabled]": "false", "allow_promotion_codes": "false",
        }
        return _test_object(self._request("POST", "/v1/checkout/sessions", fields,
                            _idempotency("checkout", order_id)), "checkout.session")

    def get_checkout(self, session_id: str) -> dict:
        _identifier(session_id, "cs_test_")
        result = _test_object(self._request("GET", f"/v1/checkout/sessions/{session_id}"), "checkout.session")
        if result.get("id") != session_id:
            raise StripeTestError("Stripe object identifier mismatch")
        return result

    def get_payment_intent(self, payment_intent_id: str) -> dict:
        _identifier(payment_intent_id, "pi_")
        result = _test_object(self._request("GET", f"/v1/payment_intents/{payment_intent_id}"), "payment_intent")
        if result.get("id") != payment_intent_id:
            raise StripeTestError("Stripe object identifier mismatch")
        return result

    def _paid_test_order(self, payment_intent_id: str, order_id: str):
        _identifier(order_id)
        intent = self.get_payment_intent(payment_intent_id)
        if (intent.get("status") != "succeeded" or type(intent.get("amount")) is not int
                or intent["amount"] != AMOUNT_CENTS or intent.get("currency") != CURRENCY
                or intent.get("metadata") != {"order_id": order_id, "contract": CONTRACT}):
            raise StripeTestError("Refund requires matching paid test order")

    def refund_full(self, payment_intent_id: str, order_id: str) -> dict:
        self._paid_test_order(payment_intent_id, order_id)
        fields = {"payment_intent": payment_intent_id, "amount": str(AMOUNT_CENTS),
                  "metadata[order_id]": order_id, "metadata[contract]": CONTRACT}
        result = self._request("POST", "/v1/refunds", fields,
                               _idempotency("refund", payment_intent_id))
        return self._refund_object(result, payment_intent_id, order_id)

    def get_refund(self, refund_id: str, payment_intent_id: str, order_id: str) -> dict:
        """Read current refund status; replaying the POST can return stale status."""
        _identifier(refund_id, "re_")
        self._paid_test_order(payment_intent_id, order_id)
        result = self._request("GET", f"/v1/refunds/{refund_id}")
        self._refund_object(result, payment_intent_id, order_id)
        if result.get("id") != refund_id:
            raise StripeTestError("Stripe object identifier mismatch")
        return result

    @staticmethod
    def _refund_object(result, payment_intent_id, order_id):
        # Refunds have no livemode field in Stripe's schema. The retrieved PI and
        # test API key establish mode; never synthesize a provider livemode field.
        if (result.get("object") != "refund" or not isinstance(result.get("id"), str)
                or not re.fullmatch(r"re_[A-Za-z0-9]+", result["id"])
                or ("livemode" in result and result["livemode"] is not False)
                or result.get("payment_intent") != payment_intent_id
                or type(result.get("amount")) is not int or result["amount"] != AMOUNT_CENTS
                or result.get("currency") != CURRENCY
                or result.get("metadata") != {"order_id": order_id, "contract": CONTRACT}):
            raise StripeTestError("Refund response does not match test order")
        return result


def verify_webhook(raw: bytes, signature: str, secret: str, now: float) -> dict:
    """Authenticate exact bytes, check freshness, return test event; ledger dedups."""
    if (not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_WEBHOOK_BYTES
            or not isinstance(signature, str) or not 0 < len(signature) <= MAX_SIGNATURE_BYTES
            or not isinstance(secret, str) or not re.fullmatch(r"whsec_[A-Za-z0-9]{1,256}", secret)
            or isinstance(now, bool) or not isinstance(now, (float, int)) or not math.isfinite(now)):
        raise StripeTestError("Invalid webhook verification inputs")
    timestamps, signatures = [], []
    for part in signature.split(","):
        key, sep, value = part.strip().partition("=")
        if not sep:
            raise StripeTestError("Malformed webhook signature")
        if key == "t":
            timestamps.append(value)
        elif key == "v1":
            if not re.fullmatch(r"[a-fA-F0-9]{64}", value):
                raise StripeTestError("Malformed webhook signature")
            signatures.append(value.lower())
    if (len(timestamps) != 1 or not re.fullmatch(r"[0-9]{1,12}", timestamps[0])
            or not signatures):
        raise StripeTestError("Malformed webhook signature")
    timestamp = timestamps[0]
    expected = hmac.new(secret.encode(), timestamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
    matches = [hmac.compare_digest(expected, candidate) for candidate in signatures]
    if not any(matches) or abs(now - int(timestamp)) > 300:
        raise StripeTestError("Webhook signature or timestamp rejected")
    return _test_object(_json_object(raw), "event")
