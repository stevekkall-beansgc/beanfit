"""Pure, value-minimized diagnostics. These summaries never authorize a run.

Missing provider fields are unknown, never an inferred safe default. No raw
provider strings, requirement names, bank details, IDs or credentials are emitted.
"""


def object_or_empty(value):
    return value if type(value) is dict else {}


def pricing_evidence(actor):
    actor = object_or_empty(actor)
    if 'pricingInfos' not in actor:
        state = 'MISSING'
    elif actor['pricingInfos'] is None:
        state = 'NULL'
    elif type(actor['pricingInfos']) is list:
        state = 'EMPTY' if not actor['pricingInfos'] else 'NONEMPTY'
    else:
        state = 'INVALID'
    current = ('MISSING' if 'pricingInfo' not in actor else
               'NULL' if actor['pricingInfo'] is None else 'PRESENT')
    return dict(pricing_infos=state, pricing_info=current,
                inactive_proved=state in ('NULL', 'EMPTY') and current in ('MISSING', 'NULL'))


def access_evidence(resource):
    resource = object_or_empty(resource)
    value = resource.get('generalAccess')
    if 'generalAccess' not in resource:
        state = 'MISSING'
    elif value is None:
        state = 'NULL'
    elif value == 'RESTRICTED':
        state = 'RESTRICTED'
    elif value == 'FOLLOW_USER_SETTING':
        state = 'INHERITED_UNRESOLVED'
    elif value in ('ANYONE_WITH_ID_CAN_READ', 'ANYONE_WITH_NAME_CAN_READ'):
        state = 'PUBLIC'
    else:
        state = 'INVALID'
    return dict(state=state, restricted_proved=state == 'RESTRICTED')


def _boolean(value):
    return 'ENABLED' if value is True else 'DISABLED' if value is False else 'UNKNOWN'


def stripe_account_evidence(account):
    """Account configuration only; Accounts v1 has no reliable livemode flag.

    A test export cannot establish live readiness. Even enabled payouts do not
    establish a bank receipt. Unknown/hidden requirements require owner review.
    """
    account = object_or_empty(account)
    checks = {key: _boolean(account.get(key))
              for key in ('charges_enabled', 'payouts_enabled', 'details_submitted')}
    blockers = ['STRIPE_' + key.upper() + '_' + state for key, state in checks.items()
                if state != 'ENABLED']
    if account.get('object') != 'account':
        blockers.append('STRIPE_ACCOUNT_OBJECT_REQUIRED')
    requirements = {}
    for section in ('requirements', 'future_requirements'):
        obj = object_or_empty(account.get(section))
        states = {}
        for key in ('currently_due', 'past_due', 'pending_verification', 'errors', 'eventually_due'):
            value = obj.get(key)
            states[key] = ('EMPTY' if not value else 'PRESENT') if type(value) is list else 'UNKNOWN'
            if states[key] != 'EMPTY':
                blockers.append('STRIPE_' + section.upper() + '_' + key.upper() + '_' + states[key])
        states['disabled_reason'] = ('CLEAR' if obj.get('disabled_reason') is None else 'PRESENT') if 'disabled_reason' in obj else 'UNKNOWN'
        if states['disabled_reason'] != 'CLEAR':
            blockers.append('STRIPE_' + section.upper() + '_DISABLED_REASON_' + states['disabled_reason'])
        requirements[section] = states
    return dict(checks=checks, requirements=requirements, blockers=blockers,
                configuration_clear=not blockers, live_mode_proved=False,
                payout_received_proved=False)
