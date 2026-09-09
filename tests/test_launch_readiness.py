"""Adversarial offline evidence checks; no real accounts or provider calls."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from beanfit.apify_fulfillment import ACTOR_ID, BUILD_ID, BUILD_NUMBER, ApifyTestClient, _gate
from beanfit.activation import ActivationError
from beanfit.launch_readiness import intake_preview, review_snapshot
from beanfit.provider_evidence import access_evidence, pricing_evidence, stripe_account_evidence
from tests.test_activation import PROFILE
from tests.test_stripe_test import Opener

NOW = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]


def fixture():
    requirements = dict(currently_due=[], past_due=[], pending_verification=[], errors=[],
                        eventually_due=[], disabled_reason=None)
    return dict(schema_version=1,
                apify=dict(observed_at=NOW.isoformat(), expected_owner_id='syntheticOwner',
                           actor=dict(id=ACTOR_ID, userId='syntheticOwner', isPublic=False, pricingInfos=[]),
                           run=dict(id='syntheticRun', actId=ACTOR_ID, userId='syntheticOwner',
                                    buildId=BUILD_ID, buildNumber=BUILD_NUMBER,
                                    defaultKeyValueStoreId='syntheticStore', generalAccess='RESTRICTED'),
                           store=dict(id='syntheticStore', userId='syntheticOwner', generalAccess='RESTRICTED')),
                stripe=dict(observed_at=NOW.isoformat(), expected_account_id='acct_SYNTHETIC',
                            account=dict(id='acct_SYNTHETIC', object='account', charges_enabled=True,
                                         payouts_enabled=True, details_submitted=True,
                                         requirements=copy.deepcopy(requirements),
                                         future_requirements=copy.deepcopy(requirements))))


class EvidenceTests(unittest.TestCase):
    def test_pricing_matrix_keeps_missing_and_free_records_blocked(self):
        for value, expected in ((None, True), ([], True), ({}, False), (False, False),
                                (0, False), ('', False), ([{'pricingModel': 'FREE'}], False),
                                ([{'pricingModel': 'PAY_PER_EVENT'}], False)):
            with self.subTest(value=value):
                self.assertIs(pricing_evidence({'pricingInfos': value})['inactive_proved'], expected)
                self.assertFalse(pricing_evidence({'pricingInfos': value, 'pricingInfo': {}})['inactive_proved'])
        self.assertEqual(pricing_evidence({})['pricing_infos'], 'MISSING')
        self.assertFalse(pricing_evidence({})['inactive_proved'])

    def test_access_matrix_never_resolves_inheritance(self):
        for value in (None, False, {}, [], 'FOLLOW_USER_SETTING', 'ANYONE_WITH_ID_CAN_READ',
                      'ANYONE_WITH_NAME_CAN_READ', 'SECRET'):
            self.assertFalse(access_evidence({'generalAccess': value})['restricted_proved'])
            self.assertNotIn('SECRET', json.dumps(access_evidence({'generalAccess': value})))
        self.assertEqual(access_evidence({'generalAccess': 'FOLLOW_USER_SETTING'})['state'], 'INHERITED_UNRESOLVED')
        self.assertTrue(access_evidence({'generalAccess': 'RESTRICTED'})['restricted_proved'])

    def test_stripe_is_configuration_only_and_minimizes_values(self):
        account = fixture()['stripe']['account']
        result = stripe_account_evidence(account)
        self.assertTrue(result['configuration_clear'])
        self.assertFalse(result['live_mode_proved'])
        self.assertFalse(result['payout_received_proved'])
        account.update(email='PRIVATE', external_accounts={'bank': 'SECRET'}, metadata={'key': 'SECRET'})
        account['requirements']['errors'] = [{'reason': 'PRIVATE SECRET'}]
        result = stripe_account_evidence(account)
        self.assertFalse(result['configuration_clear'])
        self.assertNotIn('SECRET', json.dumps(result))
        self.assertNotIn('PRIVATE', json.dumps(result))

    def test_stripe_requires_strict_booleans_and_explicit_requirements(self):
        for key in ('charges_enabled', 'payouts_enabled', 'details_submitted'):
            for value in (1, 'true', None, False, []):
                account = fixture()['stripe']['account']
                account[key] = value
                self.assertFalse(stripe_account_evidence(account)['configuration_clear'])
        for section in ('requirements', 'future_requirements'):
            for key in ('currently_due', 'past_due', 'pending_verification', 'errors', 'eventually_due', 'disabled_reason'):
                account = fixture()['stripe']['account']
                del account[section][key]
                self.assertFalse(stripe_account_evidence(account)['configuration_clear'])
        for value in (None, [], 'SECRET', {}):
            self.assertFalse(stripe_account_evidence(value)['configuration_clear'])

    def test_preflight_diagnostics_and_malformed_provider_plan_fail_closed(self):
        for plan in (None, [], 'SECRET', {'tier': 'FREE', 'isEnabled': True, 'monthlyUsageCreditsUsd': 5}):
            user = dict(id='syntheticOwner', isPaying=False, plan=plan)
            actor = fixture()['apify']['actor'].copy()
            del actor['pricingInfos']
            opener = Opener(*[{'data': v} for v in (user, {'limits': None, 'current': []}, actor, {})])
            proof = ApifyTestClient('synthetic', opener=opener).preflight(include_evidence=True)
            self.assertEqual(proof['pricing_evidence']['pricing_infos'], 'MISSING')
            self.assertFalse(proof['pricing_inactive'])
            self.assertNotIn('SECRET', json.dumps(proof))
            with self.assertRaises(ActivationError):
                _gate(proof)
            self.assertEqual(len(opener.calls), 4)
            self.assertTrue(all(req.method == 'GET' for req, _ in opener.calls))


class ReadinessTests(unittest.TestCase):
    def test_passing_snapshot_cannot_authorize_any_launch_or_prove_provider(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            result = review_snapshot(fixture(), now=NOW)
        self.assertEqual(result['snapshot_checks'], 'PASS')
        self.assertEqual(result['status'], 'NO_GO')
        self.assertFalse(result['launch_authorized'])
        self.assertEqual(result['evidence_class'], 'UNVERIFIED_LOCAL_SNAPSHOT')
        self.assertEqual(result['provider_calls'], 0)
        self.assertTrue(result['external_gates'])

    def test_timestamp_per_provider_and_boundaries(self):
        for provider in ('apify', 'stripe'):
            for stamp in (None, '', 'invalid', NOW.replace(tzinfo=None).isoformat(),
                          '2026-09-09T10:59:59Z', '2026-09-09T12:00:01Z'):
                data = fixture()
                data[provider]['observed_at'] = stamp
                result = review_snapshot(data, now=NOW)
                self.assertIn(provider.upper() + '_OBSERVATION_NOT_FRESH', result['snapshot_blockers'])
        data = fixture()
        data['apify']['observed_at'] = '2026-09-09T11:00:00Z'
        self.assertEqual(review_snapshot(data, now=NOW)['snapshot_checks'], 'PASS')

    def test_missing_malformed_public_inherited_and_identity_mismatch(self):
        for value in (None, [], False, 'SECRET', {}):
            result = review_snapshot(value, now=NOW)
            self.assertEqual(result['snapshot_checks'], 'BLOCKED')
            self.assertNotIn('SECRET', json.dumps(result))
        mutations = [
            ('apify', 'actor', 'id', 'other'), ('apify', 'actor', 'userId', None),
            ('apify', 'actor', 'isPublic', 0), ('apify', 'run', 'buildId', 'other'),
            ('apify', 'run', 'generalAccess', 'FOLLOW_USER_SETTING'),
            ('apify', 'store', 'generalAccess', 'ANYONE_WITH_ID_CAN_READ'),
            ('apify', 'store', 'id', 'other'), ('apify', 'store', 'userId', 'other'),
            ('stripe', 'account', 'id', 'acct_OTHER')]
        for provider, obj, key, value in mutations:
            data = fixture()
            data[provider][obj][key] = value
            self.assertEqual(review_snapshot(data, now=NOW)['snapshot_checks'], 'BLOCKED')

    def test_intake_supported_review_rejected_no_values_or_checkout(self):
        for profile, status in ((PROFILE, 'SUPPORTED'),
                                (dict(PROFILE, minimum_context_tokens=32768), 'NEEDS_REVIEW'),
                                (dict(PROFILE, constraints='Prefer a smaller model'), 'NEEDS_REVIEW'),
                                (dict(PROFILE, constraints='password SECRET'), 'INVALID_INPUT'),
                                (dict(PROFILE, memory_gib=True), 'INVALID_INPUT')):
            result = intake_preview(profile)
            self.assertEqual(result['status'], status)
            self.assertFalse(result['checkout_allowed'])
            self.assertFalse(result['input_retained'])
            self.assertNotIn('SECRET', json.dumps(result))

    def test_cli_strict_json_exit_codes_and_redaction(self):
        cases = [('review', '{}', 2, 'NO_GO'),
                 ('intake', json.dumps(PROFILE), 0, 'SUPPORTED'),
                 ('intake', json.dumps(dict(PROFILE, minimum_context_tokens=32768)), 2, 'NEEDS_REVIEW'),
                 ('review', '{"x": 1, "x": 2}', 1, 'INVALID_JSON'),
                 ('review', '{"x":NaN}', 1, 'INVALID_JSON'),
                 ('review', 'SECRET' * 50000, 1, 'INVALID_JSON')]
        for action, value, code, status in cases:
            proc = subprocess.run([sys.executable, str(ROOT / 'scripts/launch_preflight.py'), action],
                                  input=value, text=True, capture_output=True, timeout=10)
            self.assertEqual(proc.returncode, code, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)['status'], status)
            self.assertEqual(proc.stderr, '')
            self.assertNotIn('SECRET', proc.stdout)
