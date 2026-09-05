"""Prepared synthetic-only remote bridge; importing/testing makes no API calls.

Official API references reviewed 2026-09-05: docs.apify.com/api/v2/
actors-runs-post, actor-run-get, users-me-get, users-me-limits-get,
actor-get, actor-build-get, key-value-store-get, key-value-store-record-get.
Run starts have no assumed provider idempotency. UNKNOWN requires reconciliation.
Use one ledger for the entire workstream; independent ledgers cannot coordinate.
"""
from __future__ import annotations

import json
import math
import re
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from beanfit.activation import ActivationError, canonical, digest, require
from beanfit.apify_actor import _digest as actor_digest
from beanfit.report import CONTRACT_VERSION, validate_input

ACTOR_ID = 'X457S8llVBn25IEYB'
BUILD_ID = 'GQ41FN91r9DraYJiC'
BUILD_NUMBER = '1.0.2'
MAX_BYTES = 1048576
MAX_INPUT = 32768
ACTIVE = ('READY', 'RUNNING', 'TIMING-OUT', 'ABORTING')
TERMINAL = ('SUCCEEDED', 'FAILED', 'TIMED-OUT', 'ABORTED')


class ApifyTestError(ActivationError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ApifyTestError('APIFY_REDIRECT_DISABLED')


def _id(value):
    require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9]{1,100}', value), 'APIFY_ID_INVALID')
    return value


def _object(raw):
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError()
            obj[key] = value
        return obj
    try:
        value = json.loads(raw, object_pairs_hook=unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ApifyTestError('APIFY_INVALID_JSON') from None
    require(isinstance(value, dict), 'APIFY_OBJECT_REQUIRED')
    return value


def _number(value):
    return type(value) in (float, int) and math.isfinite(value)


class ApifyTestClient:
    def __init__(self, token, *, opener=None, timeout=10):
        require(isinstance(token, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,256}', token), 'APIFY_TOKEN_REQUIRED')
        require(_number(timeout) and 0 < timeout <= 30, 'APIFY_TIMEOUT_INVALID')
        self._token, self._timeout = token, timeout
        self._opener = opener if opener is not None else build_opener(ProxyHandler({}), NoRedirect())

    def _request(self, method, path, *, body=None, query=None, missing=False, raw=False):
        require(path.startswith('/v2/') and re.fullmatch(r'/[A-Za-z0-9/_.-]+', path)
                and '..' not in path, 'APIFY_PATH_INVALID')
        url = 'https://api.apify.com' + path + ('?' + urlencode(query) if query else '')
        headers = {'Authorization': 'Bearer ' + self._token, 'Content-Type': 'application/json'}
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                require(response.geturl() == url and 200 <= response.status < 300, 'APIFY_RESPONSE_INVALID')
                data = response.read(MAX_BYTES + 1)
        except HTTPError as error:
            code = error.code
            error.close()
            if code == 404 and missing and method == 'GET':
                return None
            raise ApifyTestError('APIFY_REQUEST_FAILED') from None
        except Exception:
            raise ApifyTestError('APIFY_REQUEST_FAILED') from None
        require(len(data) <= MAX_BYTES, 'APIFY_RESPONSE_TOO_LARGE')
        if raw:
            return data
        obj = _object(data)
        require(isinstance(obj.get('data'), dict), 'APIFY_DATA_REQUIRED')
        return obj['data']

    def preflight(self):
        # Never retain the whole user response: it may contain unrelated secrets/PII.
        user = self._request('GET', '/v2/users/me')
        limits = self._request('GET', '/v2/users/me/limits')
        actor = self._request('GET', '/v2/actors/' + ACTOR_ID)
        build = self._request('GET', '/v2/actor-builds/' + BUILD_ID)
        plan = user.get('plan', {})
        return dict(user_id=user.get('id'), plan=plan.get('tier'), enabled=plan.get('isEnabled'),
                    is_paying=user.get('isPaying'), credits=plan.get('monthlyUsageCreditsUsd'),
                    cap=limits.get('limits', {}).get('maxMonthlyUsageUsd'),
                    usage=limits.get('current', {}).get('monthlyUsageUsd'),
                    active_jobs=limits.get('current', {}).get('activeActorJobCount'),
                    actor_id=actor.get('id'), owner=actor.get('userId'), private=actor.get('isPublic') is False,
                    pricing_inactive=('pricingInfos' in actor and actor['pricingInfos'] in (None, [])
                                      and actor.get('pricingInfo') is None),
                    build_id=build.get('id'), build_actor=build.get('actId'),
                    build_number=build.get('buildNumber'), build_status=build.get('status'))

    def start(self, profile, *, synthetic=False):
        require(synthetic is True, 'CUSTOMER_INTAKE_DISABLED')
        validate_input(profile)
        body = canonical(profile).encode()
        require(len(body) <= MAX_INPUT, 'APIFY_INPUT_TOO_LARGE')
        return self._request('POST', '/v2/actors/' + ACTOR_ID + '/runs', body=body,
                             query=dict(build=BUILD_NUMBER, memory=128, timeout=60,
                                        restartOnError='false', waitForFinish=0,
                                        maxTotalChargeUsd=0.25, forcePermissionLevel='LIMITED_PERMISSIONS'))

    def get_run(self, run_id):
        return self._request('GET', '/v2/actor-runs/' + _id(run_id))

    def get_store(self, store_id):
        return self._request('GET', '/v2/key-value-stores/' + _id(store_id))

    def record(self, store_id, key):
        require(key in ('INPUT', 'OUTPUT', 'REPORT.md', 'REPORT.json', 'METRICS'), 'APIFY_KEY_INVALID')
        return self._request('GET', '/v2/key-value-stores/' + _id(store_id) + '/records/' + key,
                             missing=key == 'INPUT', raw=True)


def _schema(ledger):
    ledger.db.executescript('''
    CREATE TABLE IF NOT EXISTS remote_runs(
      order_id TEXT NOT NULL REFERENCES orders(id), revision INTEGER NOT NULL,
      attempt INTEGER NOT NULL, state TEXT NOT NULL, run_id TEXT UNIQUE,
      store_id TEXT UNIQUE, user_id TEXT NOT NULL, input_hash TEXT NOT NULL,
      output BLOB, markdown BLOB, structured BLOB, failed INTEGER NOT NULL DEFAULT 0,
      PRIMARY KEY(order_id,revision,attempt));
    CREATE UNIQUE INDEX IF NOT EXISTS one_unresolved_remote_run ON remote_runs((1))
      WHERE state IN ('STARTING','UNKNOWN','RUNNING','CACHED');
    ''')


def _gate(proof):
    require(proof.get('plan') == 'FREE' and proof.get('enabled') is True and proof.get('is_paying') is False,
            'APIFY_FREE_NONPAYING_REQUIRED')
    credits, cap, usage = (proof.get(k) for k in ('credits', 'cap', 'usage'))
    require(all(_number(v) for v in (credits, cap, usage)) and 0 < cap <= credits <= 5
            and 0 <= usage and min(cap, credits) - usage >= .25, 'APIFY_FREE_CREDIT_GATE')
    require(type(proof.get('active_jobs')) is int and proof['active_jobs'] == 0, 'APIFY_CONCURRENCY_GATE')
    _id(proof.get('user_id'))
    require(proof.get('actor_id') == ACTOR_ID and proof.get('owner') == proof['user_id']
            and proof.get('private') is True and proof.get('pricing_inactive') is True, 'APIFY_PRIVATE_UNPRICED_REQUIRED')
    require(proof.get('build_id') == BUILD_ID and proof.get('build_actor') == ACTOR_ID
            and proof.get('build_number') == BUILD_NUMBER and proof.get('build_status') == 'SUCCEEDED', 'APIFY_BUILD_GATE')


def _bound_run(run, row):
    _id(run.get('id'))
    _id(run.get('defaultKeyValueStoreId'))
    require(row['run_id'] in (None, run['id']) and row['store_id'] in (None, run['defaultKeyValueStoreId'])
            and run.get('actId') == ACTOR_ID and run.get('buildId') == BUILD_ID
            and run.get('buildNumber') == BUILD_NUMBER and run.get('userId') == row['user_id']
            and run.get('generalAccess') == 'RESTRICTED', 'APIFY_RUN_BINDING')
    options = run.get('options', {})
    require(options.get('memoryMbytes') == 128 and options.get('timeoutSecs') == 60
            and options.get('build') == BUILD_NUMBER and options.get('restartOnError') is False
            and options.get('forcePermissionLevel') == 'LIMITED_PERMISSIONS'
            and _number(options.get('maxTotalChargeUsd'))
            and 0 < options['maxTotalChargeUsd'] <= .25, 'APIFY_RUN_LIMIT_BINDING')
    require(run.get('status') in ACTIVE + TERMINAL, 'APIFY_RUN_STATUS_INVALID')
    require(not run.get('chargedEventCounts') and run.get('pricingInfo') is None, 'APIFY_UNEXPECTED_PRICING')
    for key in ('restartCount', 'rebootCount', 'resurrectCount', 'metamorph'):
        require(run.get('stats', {}).get(key, 0) == 0, 'APIFY_UNEXPECTED_RESTART')


class _StaleClaim(BaseException):
    """Bypass producer's Exception handler so a stale claim rolls back cleanly."""


def _consume(ledger, oid, profile, row):
    def cached_producer(_):
        current = ledger.order(oid)
        state = ledger.db.execute('SELECT state FROM remote_runs WHERE order_id=? AND revision=? AND attempt=?',
                                  (oid, row['revision'], row['attempt'])).fetchone()[0]
        if current['revision'] != row['revision'] or current['attempts'] != row['attempt'] or state != 'CACHED':
            raise _StaleClaim()
        ledger.db.execute('UPDATE remote_runs SET state=? WHERE order_id=? AND revision=? AND attempt=?',
                          ('CONSUMED', oid, row['revision'], row['attempt']))
        if row['failed']:
            raise ApifyTestError('APIFY_TERMINAL_FAILURE')
        return _object(row['output']), row['markdown'], _object(row['structured'])
    try:
        revision = ledger.fulfill(oid, profile, cached_producer)
    except _StaleClaim:
        return dict(status='STALE_CLAIM')
    return dict(status='READY', revision=revision)


def step(ledger, order_id, profile, client):
    """Perform at most one bounded start/poll step; never auto-retry a POST.

    Future real executions require authorized runtime credentials. This bridge
    accepts only ledger entries whose accepted event is explicitly synthetic.
    UNKNOWN is a global stop: inspect remote runs outside this adapter before any
    approved reconciliation. No function here silently clears that stop.
    """
    normalized = validate_input(profile)
    _schema(ledger)
    order = ledger.order(order_id)
    require(digest(normalized) == order['input_hash'], 'FULFILL_INPUT_CONFLICT')
    accepted = ledger.db.execute('SELECT body FROM events WHERE transaction_id=? AND event_id=?',
                                 (order_id, 'accepted')).fetchone()
    require(accepted is not None, 'SYNTHETIC_LEDGER_REQUIRED')
    event = json.loads(accepted[0])
    require(event.get('payer_class') == 'TEST' and event.get('acquisition') == 'SYNTHETIC'
            and event.get('receipt') == 'synthetic-intake', 'SYNTHETIC_LEDGER_REQUIRED')
    if order['state'] in ('READY', 'DELIVERED'):
        ledger._verified_artifact(order_id, order['revision'])
        return dict(status=order['state'], revision=order['revision'])
    require(order['state'] in ('PAID', 'CORRECTION', 'RETRY'), 'FULFILL_STATE')
    require(order['retry_at'] is None or ledger.now() >= order['retry_at'], 'RETRY_NOT_DUE')
    require(order['attempts'] < 2, 'RETRY_EXHAUSTED')
    key = (order_id, order['revision'], order['attempts'])
    row = ledger.db.execute('SELECT * FROM remote_runs WHERE order_id=? AND revision=? AND attempt=?', key).fetchone()
    if row is None:
        checked_at = ledger.now()
        proof = client.preflight()  # fresh bounded reads, never a saved historical receipt
        _gate(proof)
        require(0 <= ledger.now() - checked_at <= 60, 'APIFY_PREFLIGHT_STALE')
        with ledger.transaction():
            current = ledger.order(order_id)
            require((current['revision'], current['attempts'], current['state']) ==
                    (order['revision'], order['attempts'], order['state']), 'APIFY_ORDER_CHANGED')
            require(ledger.db.execute("SELECT 1 FROM remote_runs WHERE state IN ('STARTING','UNKNOWN','RUNNING','CACHED')").fetchone()
                    is None, 'APIFY_UNRESOLVED_RUN_NO_START')
            ledger.db.execute('INSERT INTO remote_runs(order_id,revision,attempt,state,user_id,input_hash) VALUES(?,?,?,?,?,?)',
                              (*key, 'STARTING', proof['user_id'], order['input_hash']))
        row = dict(ledger.db.execute('SELECT * FROM remote_runs WHERE order_id=? AND revision=? AND attempt=?', key).fetchone())
        try:
            run = client.start(profile, synthetic=True)
            _bound_run(run, row)
        except Exception:
            with ledger.transaction():
                ledger.db.execute('UPDATE remote_runs SET state=? WHERE order_id=? AND revision=? AND attempt=?', ('UNKNOWN', *key))
            raise ApifyTestError('APIFY_START_UNKNOWN_RECONCILE_NO_RETRY') from None
        with ledger.transaction():
            ledger.db.execute('UPDATE remote_runs SET state=?,run_id=?,store_id=? WHERE order_id=? AND revision=? AND attempt=?',
                              ('RUNNING', run['id'], run['defaultKeyValueStoreId'], *key))
        return dict(status='RUNNING', run_id=run['id'])
    row = dict(row)
    require(row['state'] not in ('UNKNOWN', 'STARTING'), 'APIFY_START_UNKNOWN_RECONCILE_NO_RETRY')
    if row['state'] == 'CACHED':
        return _consume(ledger, order_id, profile, row)
    require(row['state'] == 'RUNNING', 'APIFY_REMOTE_STATE')
    run = client.get_run(row['run_id'])
    _bound_run(run, row)
    if run['status'] in ACTIVE:
        return dict(status='RUNNING', run_id=row['run_id'])
    store = client.get_store(row['store_id'])
    require(store.get('id') == row['store_id'] and store.get('userId') == row['user_id']
            and store.get('generalAccess') == 'RESTRICTED', 'APIFY_STORE_BINDING')
    require(client.record(row['store_id'], 'INPUT') is None, 'APIFY_INPUT_RETAINED_CLEANUP_REQUIRED')
    failed = run['status'] != 'SUCCEEDED'
    output, md, structured = None, None, None
    if not failed:
        output = client.record(row['store_id'], 'OUTPUT')
        md = client.record(row['store_id'], 'REPORT.md')
        structured = client.record(row['store_id'], 'REPORT.json')
        metrics = _object(client.record(row['store_id'], 'METRICS'))
        marker, report = _object(output), _object(structured)
        require(marker.get('status') == 'SUCCEEDED' and marker.get('contract_version') == CONTRACT_VERSION
                and marker.get('report_markdown_key') == 'REPORT.md' and marker.get('report_json_key') == 'REPORT.json'
                and marker.get('report_markdown_sha256') == digest(md)
                and marker.get('report_json_sha256') == actor_digest(report)
                and report.get('accepted_inputs') == normalized and metrics.get('billing_events_emitted') == 0,
                'APIFY_ARTIFACT_BINDING')
    with ledger.transaction():
        ledger.db.execute('UPDATE remote_runs SET state=?,output=?,markdown=?,structured=?,failed=? '
                          'WHERE order_id=? AND revision=? AND attempt=? AND state=?',
                          ('CACHED', output, md, structured, int(failed), *key, 'RUNNING'))
    row = dict(ledger.db.execute('SELECT * FROM remote_runs WHERE order_id=? AND revision=? AND attempt=?', key).fetchone())
    return _consume(ledger, order_id, profile, row)
