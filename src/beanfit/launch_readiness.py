"""Offline launch evidence review and supported-input preview; no provider IO."""
from datetime import datetime
import re

from beanfit.apify_fulfillment import ACTOR_ID, BUILD_ID, BUILD_NUMBER
from beanfit.provider_evidence import (access_evidence, object_or_empty,
                                      pricing_evidence, stripe_account_evidence)
from beanfit.report import InputRejected, NeedsReview, validate_input

EXTERNAL_GATES = (
    'APIFY_FRESH_FREE_CREDIT_AND_PINNED_BUILD_PREFLIGHT',
    'APIFY_DEFAULT_ACCESS_AND_PRICING_PROVIDER_REVIEW',
    'APIFY_SYNTHETIC_FULFILLMENT_DELETION_AND_COST_RECEIPT',
    'STRIPE_AUTHORIZED_TEST_CHECKOUT_SIGNED_EVENT_REFUND_RECEIPT',
    'STRIPE_LIVE_ACCOUNT_TAX_FEES_AND_PAYOUT_DESTINATION_OWNER_REVIEW',
    'CUSTOMER_HTTPS_INTAKE_PRIVATE_DELIVERY_AND_RETENTION',
    'STAFFED_SLA_CORRECTION_REFUND_AND_INCIDENT_ROUTES',
    'CATALOG_FRESHNESS_AND_LIVE_ORDER_ACCOUNTING_REVIEW',
    'EXPLICIT_BOUNDED_LIVE_OFFER_AND_OPT_IN_OUTREACH_AUTHORIZATION',
)


def intake_preview(profile):
    """Discard submitted values; make neither an order nor a checkout."""
    try:
        validate_input(profile)
        status = 'SUPPORTED'
    except NeedsReview:
        status = 'NEEDS_REVIEW'
    except InputRejected:
        status = 'INVALID_INPUT'
    return dict(status=status, checkout_allowed=False, order_created=False,
                input_retained=False, review_dispatched=False,
                proposed_amount_cents=1200, currency='usd')


def _identifier(value, prefix=''):
    return isinstance(value, str) and re.fullmatch(re.escape(prefix) + r'[A-Za-z0-9]{1,100}', value) is not None


def review_snapshot(snapshot, *, now):
    """Local snapshots are unverified assertions, even when all checks pass.

    Timestamps belong to individual provider observations. One fresh provider
    observation cannot refresh evidence from another. Freshness window is one hour.
    """
    snapshot = object_or_empty(snapshot)
    blockers = []
    if type(snapshot.get('schema_version')) is not int or snapshot['schema_version'] != 1:
        blockers.append('SNAPSHOT_SCHEMA_REQUIRED')
    observations = {}
    for provider in ('apify', 'stripe'):
        section = object_or_empty(snapshot.get(provider))
        try:
            stamp = datetime.fromisoformat(section.get('observed_at', '').replace('Z', '+00:00'))
            fresh = stamp.tzinfo is not None and 0 <= (now - stamp).total_seconds() <= 3600
        except (ValueError, TypeError, AttributeError, OverflowError):
            fresh = False
        observations[provider] = 'FRESH' if fresh else 'MISSING_STALE_OR_FUTURE'
        if not fresh:
            blockers.append(provider.upper() + '_OBSERVATION_NOT_FRESH')
    apify = object_or_empty(snapshot.get('apify'))
    actor, run, store = (object_or_empty(apify.get(k)) for k in ('actor', 'run', 'store'))
    pricing = pricing_evidence(actor)
    run_access, store_access = access_evidence(run), access_evidence(store)
    if not pricing['inactive_proved']:
        blockers.append('APIFY_PRICING_NOT_PROVED_INACTIVE')
    if actor.get('isPublic') is not False:
        blockers.append('APIFY_PRIVATE_ACTOR_NOT_PROVED')
    owner = apify.get('expected_owner_id')
    if not (_identifier(owner) and actor.get('id') == ACTOR_ID and actor.get('userId') == owner):
        blockers.append('APIFY_ACTOR_OWNER_BINDING_REQUIRED')
    if not (_identifier(run.get('id')) and run.get('actId') == ACTOR_ID
            and run.get('buildId') == BUILD_ID and run.get('buildNumber') == BUILD_NUMBER
            and _identifier(owner) and run.get('userId') == owner
            and _identifier(store.get('id')) and store.get('id') == run.get('defaultKeyValueStoreId')
            and store.get('userId') == owner):
        blockers.append('APIFY_RUN_STORE_BINDING_REQUIRED')
    for kind, access in (('RUN', run_access), ('STORE', store_access)):
        if not access['restricted_proved']:
            blockers.append('APIFY_' + kind + '_ACCESS_' + access['state'])
    stripe = object_or_empty(snapshot.get('stripe'))
    account = object_or_empty(stripe.get('account'))
    stripe_result = stripe_account_evidence(account)
    blockers.extend(stripe_result['blockers'])
    account_id = stripe.get('expected_account_id')
    if not (_identifier(account_id, 'acct_') and account.get('id') == account_id):
        blockers.append('STRIPE_ACCOUNT_BINDING_REQUIRED')
    return dict(schema_version=1, status='NO_GO', evidence_class='UNVERIFIED_LOCAL_SNAPSHOT',
                snapshot_checks='BLOCKED' if blockers else 'PASS', observations=observations,
                apify=dict(pricing=pricing, run_access=run_access, store_access=store_access),
                stripe=stripe_result, snapshot_blockers=blockers,
                external_gates=list(EXTERNAL_GATES), provider_calls=0,
                provider_mutations=0, launch_authorized=False)
