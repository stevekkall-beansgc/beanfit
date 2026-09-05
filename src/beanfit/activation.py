"""BF-CER synthetic activation harness. No live mode or customer intake exists.

SQLite is the single-writer claim, append-only audit, and private artifact store.
Transport calls are injected; local fixtures do not prove provider behavior.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from beanfit.report import CONTRACT_VERSION, validate_input
from beanfit.apify_actor import _digest as actor_digest


class ActivationError(RuntimeError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value).encode()).hexdigest()


def require(condition, code):
    if not condition:
        raise ActivationError(code)


class Ledger:
    def __init__(self, path, *, now):
        self.now = now
        self.db = sqlite3.connect(path, timeout=10, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        PRAGMA foreign_keys=ON;
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=FULL;
        CREATE TABLE IF NOT EXISTS orders(
          id TEXT PRIMARY KEY, intent_hash TEXT UNIQUE NOT NULL, input_hash TEXT NOT NULL, accepted_at INTEGER NOT NULL,
          state TEXT NOT NULL, session TEXT UNIQUE, payment_intent TEXT UNIQUE,
          checkout_started INTEGER, refund_started INTEGER, refund_id TEXT UNIQUE, revision INTEGER NOT NULL DEFAULT 0,
          token_hash TEXT NOT NULL, delivered_at INTEGER, attempts INTEGER NOT NULL DEFAULT 0, retry_at INTEGER);
        CREATE TABLE IF NOT EXISTS effects(
          event_id TEXT PRIMARY KEY, effect_key TEXT NOT NULL, payload_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS artifacts(
          order_id TEXT NOT NULL REFERENCES orders(id), revision INTEGER NOT NULL,
          markdown BLOB NOT NULL, structured BLOB NOT NULL, manifest TEXT NOT NULL,
          PRIMARY KEY(order_id,revision));
        CREATE TABLE IF NOT EXISTS events(
          sequence INTEGER PRIMARY KEY, transaction_id TEXT NOT NULL REFERENCES orders(id),
          event_id TEXT NOT NULL, body TEXT NOT NULL, previous_hash TEXT NOT NULL,
          hash TEXT NOT NULL, UNIQUE(transaction_id,event_id));
        CREATE TRIGGER IF NOT EXISTS immutable_event_update BEFORE UPDATE ON events
          BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_event_delete BEFORE DELETE ON events
          BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END;
        ''')

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def close(self):
        self.db.close()

    def order(self, order_id):
        row = self.db.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
        require(row is not None, 'UNKNOWN_ORDER')
        return dict(row)

    def _event(self, order_id, event_id, prior, new, receipt):
        previous = self.db.execute('SELECT hash FROM events ORDER BY sequence DESC LIMIT 1').fetchone()
        previous = previous[0] if previous else '0' * 64
        latest = self.db.execute('SELECT body FROM events WHERE transaction_id=? ORDER BY sequence DESC LIMIT 1',(order_id,)).fetchone()
        if latest: prior = json.loads(latest[0])['new_state']
        body = dict(event_time=datetime.fromtimestamp(self.now(), timezone.utc).isoformat(),
                    transaction_id=order_id, event_id=event_id, lane='CASH',
                    offer_version=CONTRACT_VERSION, prior_state=prior, new_state=new,
                    gross_delta=0, platform_fee_delta=0, refund_delta=0, direct_cost_delta=0,
                    economic_cost_delta=0, net_cash_delta=0, eligible_net_delta=0,
                    payer_class='TEST', acquisition='SYNTHETIC', receipt=receipt,
                    notes='EXCLUDED_TEST; nominal amounts are test assertions only')
        text = canonical(body)
        self.db.execute('INSERT INTO events(transaction_id,event_id,body,previous_hash,hash) VALUES(?,?,?,?,?)',
                        (order_id,event_id,text,previous,hashlib.sha256((previous+text).encode()).hexdigest()))

    def accept(self, intent_id, profile, *, synthetic, token=None):
        require(synthetic is True, 'CUSTOMER_INTAKE_DISABLED')
        require(isinstance(intent_id, str) and re.fullmatch(r'synthetic-[a-z0-9-]{1,80}', intent_id), 'SYNTHETIC_INTENT_REQUIRED')
        normalized = validate_input(profile)  # fail before acceptance/payment; do not retain raw data
        date = datetime.fromtimestamp(self.now(), timezone.utc).strftime('%Y%m%d')
        order_id = f'AR-{date}-CASH-' + digest(intent_id)[:24]
        token = token or secrets.token_urlsafe(32)
        require(isinstance(token,str) and len(token)>=32, 'TOKEN_TOO_SHORT')
        with self.transaction():
            existing = self.db.execute('SELECT * FROM orders WHERE intent_hash=?',(digest(intent_id),)).fetchone()
            if existing:
                require(existing['input_hash']==digest(normalized),'INTENT_CONFLICT')
                # A retry may not rotate or recover a bearer token.
                require(hmac.compare_digest(existing['token_hash'], digest(token)), 'TOKEN_MISMATCH')
                return existing['id'], token
            self.db.execute('INSERT INTO orders(id,intent_hash,input_hash,accepted_at,state,token_hash) VALUES(?,?,?,?,?,?)',
                            (order_id,digest(intent_id),digest(normalized),int(self.now()),'ACCEPTED',digest(token)))
            self._event(order_id,'accepted','ORDERED','ACCEPTED','synthetic-intake')
        return order_id, token

    def checkout(self, order_id, client):
        with self.transaction():
            order = self.order(order_id)
            if order['session']:
                return order['session']
            require(order['state'] in ('ACCEPTED','CHECKOUT_UNKNOWN'),'CHECKOUT_STATE')
            started = order['checkout_started']
            require(started is None or 0 <= self.now()-started < 23*3600,'RECONCILE_CHECKOUT_NO_RETRY')
            if started is None:
                self._event(order_id,'checkout-intent','ACCEPTED','ORDERED','test-checkout-intent-before-request')
            self.db.execute('UPDATE orders SET state=?,checkout_started=COALESCE(checkout_started,?) WHERE id=?',
                            ('CHECKOUT_UNKNOWN',int(self.now()),order_id))
        # Unknown outcome survives process/network failure. Same provider key on retry.
        session = client.create_checkout(order_id,'http://127.0.0.1:4242/success','http://127.0.0.1:4242/cancel')
        require(session.get('livemode') is False and isinstance(session.get('id'),str) and
                session['id'].startswith('cs_test_') and session.get('client_reference_id')==order_id,
                'CHECKOUT_RESPONSE_BINDING')
        with self.transaction():
            prior = self.order(order_id)
            require(prior['session'] in (None,session['id']), 'CHECKOUT_CONFLICT')
            if prior['session'] is None:
                self.db.execute('UPDATE orders SET session=?,state=? WHERE id=?',(session['id'],'CHECKOUT',order_id))
                self._event(order_id,'checkout','ACCEPTED','ORDERED',session['id'])
        return session['id']

    def payment(self, event, client, *, expected_order_id=None):
        """Caller supplies signature-verified event; fresh Stripe read is authoritative."""
        require(event.get('livemode') is False, 'LIVE_EVENT_DISABLED')
        require(event.get('type') in ('checkout.session.completed','checkout.session.async_payment_succeeded'), 'UNHANDLED_EVENT')
        require(isinstance(event.get('id'),str) and re.fullmatch(r'evt_[A-Za-z0-9_]+',event['id']), 'EVENT_ID')
        obj = event.get('data',{}).get('object',{})
        require(isinstance(obj.get('id'),str) and obj['id'].startswith('cs_test_'),'SESSION_ID')
        session = client.get_checkout(obj['id'])
        oid = session.get('client_reference_id')
        require(session.get('livemode') is False and session.get('id')==obj['id'] and
                session.get('mode')=='payment' and session.get('status')=='complete' and
                session.get('payment_status')=='paid' and type(session.get('amount_total')) is int and
                session['amount_total']==1200 and session.get('currency')=='usd' and
                session.get('metadata',{}).get('contract')==CONTRACT_VERSION and
                session.get('metadata',{}).get('order_id')==oid,'PAYMENT_BINDING')
        require(expected_order_id is None or oid==expected_order_id,'UNEXPECTED_ORDER')
        pi = session.get('payment_intent')
        require(isinstance(pi,str) and re.fullmatch(r'pi_[A-Za-z0-9_]+',pi), 'PAYMENT_INTENT')
        # Canonical effect ignores PII/event timestamps; two events can describe same payment.
        effect = 'paid:' + session['id']
        safe_hash = digest(dict(session=session['id'],order=oid,pi=pi,amount=1200,currency='usd'))
        with self.transaction():
            order = self.order(oid)
            require(order['session']==session['id'], 'UNBOUND_CHECKOUT')
            prior = self.db.execute('SELECT * FROM effects WHERE event_id=? OR effect_key=?',(event['id'],effect)).fetchall()
            if prior:
                require(all(p['effect_key']==effect and p['payload_hash']==safe_hash for p in prior),'EVENT_CONFLICT')
                self.db.execute('INSERT OR IGNORE INTO effects VALUES(?,?,?)',(event['id'],effect,safe_hash))
                return oid
            require(order['state']=='CHECKOUT','PAYMENT_STATE')
            self.db.execute('INSERT INTO effects VALUES(?,?,?)',(event['id'],effect,safe_hash))
            self.db.execute('UPDATE orders SET payment_intent=?,state=? WHERE id=?',(pi,'PAID',oid))
            self._event(oid,event['id'],'ORDERED','CREDITED',pi)
        return oid

    def fulfill(self, order_id, profile, producer):
        """Atomic local-only production; one retry at 15 minutes, then freeze.

        SQLite rollback covers crash recovery because the producer is deterministic
        and local with no external effects. Remote Actor invocation is prohibited
        here: it needs a persisted remote run intent/reconciliation adapter.
        """
        normalized = validate_input(profile)
        failed = False
        with self.transaction():
            order = self.order(order_id)
            require(digest(normalized)==order['input_hash'],'FULFILL_INPUT_CONFLICT')
            revision = order['revision']
            if order['state'] in ('READY','DELIVERED'):
                self._verified_artifact(order_id,revision)
                return revision
            require(order['state'] in ('PAID','CORRECTION','RETRY'),'FULFILL_STATE')
            require(order['retry_at'] is None or self.now() >= order['retry_at'],'RETRY_NOT_DUE')
            require(order['attempts'] < 2,'RETRY_EXHAUSTED')
            try:
                output, md, structured = producer(profile)
                require(output.get('status')=='SUCCEEDED','NO_SUCCESS_MARKER')
                md = md.encode() if isinstance(md,str) else md
                parsed = json.loads(structured) if isinstance(structured,(bytes,str)) else structured
                require(output.get('report_markdown_sha256')==digest(md) and
                        output.get('report_json_sha256')==actor_digest(parsed),'REPORT_HASH_MISMATCH')
                require(parsed['accepted_inputs']==normalized,'REPORT_INPUT_MISMATCH')
                structured = canonical(parsed).encode()
                manifest=canonical(dict(markdown_sha256=digest(md),json_sha256=digest(structured)))
            except Exception:
                failed = True
                state = 'RETRY' if order['attempts']==0 else 'DELIVERY_FAILED'
                self.db.execute('UPDATE orders SET state=?,attempts=attempts+1,retry_at=? WHERE id=?',
                                (state,int(self.now())+900,order_id))
                self._event(order_id,f'failure-{revision}-{order["attempts"]}',
                            'CREDITED','DELIVERY_FAILED','sanitized-local-fulfillment-failure')
            if not failed:
                self.db.execute('INSERT INTO artifacts VALUES(?,?,?,?,?)',(order_id,revision,md,structured,manifest))
                self.db.execute('UPDATE orders SET state=?,attempts=attempts+1 WHERE id=?',('READY',order_id))
                self._event(order_id,f'ready-{revision}','CREDITED','EARNED',digest(manifest))
        require(not failed,'FULFILLMENT_FAILED')
        return revision

    def _verified_artifact(self, oid, revision):
        row=self.db.execute('SELECT * FROM artifacts WHERE order_id=? AND revision=?',(oid,revision)).fetchone()
        require(row is not None,'ARTIFACT_MISSING')
        manifest=json.loads(row['manifest'])
        require(digest(row['markdown'])==manifest['markdown_sha256'] and digest(row['structured'])==manifest['json_sha256'],'ARTIFACT_CORRUPT')
        return row

    def download(self, order_id, token):
        with self.transaction():
            order=self.order(order_id)
            require(isinstance(token,str) and hmac.compare_digest(digest(token),order['token_hash']),'DOWNLOAD_DENIED')
            require(order['state'] in ('READY','DELIVERED'),'DOWNLOAD_STATE')
            row=self._verified_artifact(order_id,order['revision'])
            if order['state']=='READY':
                self.db.execute('UPDATE orders SET state=?,delivered_at=COALESCE(delivered_at,?) WHERE id=?',('DELIVERED',int(self.now()),order_id))
                self._event(order_id,f'download-{order["revision"]}','EARNED','DELIVERED',digest(row['manifest']))
            return dict(markdown=row['markdown'],structured=row['structured'],manifest=json.loads(row['manifest']))

    def correction(self, order_id, profile):
        normalized=validate_input(profile)
        with self.transaction():
            order=self.order(order_id)
            require(order['state']=='DELIVERED' and order['revision']==0,'ONE_CORRECTION_ONLY')
            require(0<=self.now()-order['delivered_at']<=7*86400,'CORRECTION_WINDOW')
            self.db.execute('UPDATE orders SET state=?,revision=1,attempts=0,retry_at=NULL,input_hash=? WHERE id=?',('CORRECTION',digest(normalized),order_id))
            self._event(order_id,'correction','DELIVERED','ACCEPTED','included-revision-1-no-charge')

    def refund(self, order_id, client):
        with self.transaction():
            order=self.order(order_id)
            if order['state']=='REFUNDED': return 'REFUNDED'
            require(order['payment_intent'] and order['state'] in ('PAID','READY','DELIVERED','CORRECTION','REFUND_PENDING','RETRY','DELIVERY_FAILED'), 'REFUND_STATE')
            started=order['refund_started']
            require(order['refund_id'] is not None or started is None or 0<=self.now()-started<23*3600,'RECONCILE_REFUND_NO_RETRY')
            if started is None:
                self._event(order_id,'refund-intent','CREDITED','EXCLUDED_TEST','test-refund-requested-not-yet-succeeded')
            self.db.execute('UPDATE orders SET state=?,refund_started=COALESCE(refund_started,?) WHERE id=?',('REFUND_PENDING',int(self.now()),order_id))
        result=(client.get_refund(order['refund_id'],order['payment_intent'],order_id) if order['refund_id']
                else client.refund_full(order['payment_intent'],order_id))
        require(result.get('payment_intent')==order['payment_intent'] and type(result.get('amount')) is int and result['amount']==1200 and
                result.get('currency')=='usd' and isinstance(result.get('id'),str) and re.fullmatch(r're_[A-Za-z0-9_]+',result['id']), 'REFUND_BINDING')
        require(result.get('status') in ('succeeded','pending','failed','canceled','requires_action'),'REFUND_STATUS')
        with self.transaction():
            current=self.order(order_id)
            if current['state']=='REFUNDED':return 'REFUNDED'
            require(current['refund_id'] in (None,result['id']),'REFUND_CONFLICT')
            self.db.execute('UPDATE orders SET refund_id=? WHERE id=?',(result['id'],order_id))
            if result['status']=='succeeded':
                self.db.execute('UPDATE orders SET state=? WHERE id=?',('REFUNDED',order_id))
                self._event(order_id,result['id'],'CREDITED','REFUNDED',result['id'])
            # Failed/pending/unknown never restores fulfillment or creates a new charge.
        return self.order(order_id)['state']

    def audit(self):
        previous='0'*64
        rows=self.db.execute('SELECT * FROM events ORDER BY sequence').fetchall()
        for row in rows:
            require(row['previous_hash']==previous and row['hash']==hashlib.sha256((previous+row['body']).encode()).hexdigest(),'AUDIT_CHAIN')
            previous=row['hash']
        return dict(events=[json.loads(r['body']) for r in rows],chain_head=previous,
                    classification='EXCLUDED_TEST',real_gross_cents=0,real_net_cents=0,promotion_eligible_cents=0)
