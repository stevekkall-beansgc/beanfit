#!/usr/bin/env python3
"""Offline end-to-end fixture; no provider call, credentials, or payment."""
import argparse
import hashlib
import hmac
import json
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from beanfit.activation import Ledger, canonical
from beanfit.apify_actor import run
from beanfit.report import generate_report
from beanfit.stripe_test import verify_webhook

PROFILE={'device_chip':'Apple M4 Pro','memory_gib':48,'use_case':'coding','operating_system':'macOS 15.6 arm64'}
BASELINE_REVISION='4ec003e8f9c7ce8de821a9c24561ce023b79526f'

def source_revision():
    import subprocess
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

class MemoryStore:
    def __init__(self, profile): self.records={'INPUT':canonical(profile).encode()}
    def get(self,key): return self.records.get(key)
    def put(self,key,value,*args): self.records[key]=value
    def delete(self,key): self.records.pop(key,None)


def producer(profile):
    revision=source_revision()
    sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'src').rglob('*.py')}
    store=MemoryStore(profile)
    code=run(store,generate=generate_report,revision=revision,memory_mib=128,
             generated_at='2026-09-05T12:00:00Z',clock=lambda:0,source_sha256=sources)
    if code or 'INPUT' in store.records: raise RuntimeError('ACTOR_FAILURE')
    return store.get('OUTPUT'),store.get('REPORT.md'),store.get('REPORT.json')


class FixtureStripe:
    """Explicit simulation. IDs have no matching provider objects."""
    def __init__(self): self.order_id=None; self.creates=0; self.refunds=0
    def create_checkout(self,order_id,*args):
        self.order_id=order_id; self.creates+=1
        return self.get_checkout('cs_test_SYNTHETIC')
    def get_checkout(self,session):
        return dict(id=session,object='checkout.session',livemode=False,mode='payment',status='complete',
                    payment_status='paid',amount_total=1200,currency='usd',payment_intent='pi_SYNTHETIC',
                    client_reference_id=self.order_id,metadata=dict(order_id=self.order_id,contract='BF-CER-v1.0'))
    def refund_full(self,pi,oid):
        self.refunds+=1
        return dict(id='re_SYNTHETIC',object='refund',payment_intent=pi,amount=1200,currency='usd',status='succeeded')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt',type=Path,help='Optional destination for a fresh synthetic receipt; no tracked file is overwritten by default')
    args=parser.parse_args()
    clock=lambda:1788609600
    with tempfile.TemporaryDirectory(prefix='bfcer-synthetic-') as tmp:
        ledger=Ledger(Path(tmp)/'ledger.sqlite',now=clock)
        provider=FixtureStripe()
        oid,token=ledger.accept('synthetic-first-dollar-demo',PROFILE,synthetic=True)
        ledger.checkout(oid,provider); ledger.checkout(oid,provider)
        event=dict(id='evt_SYNTHETIC',object='event',livemode=False,type='checkout.session.completed',data={'object':{'id':'cs_test_SYNTHETIC'}})
        raw=canonical(event).encode();secret='whsec_SYNTHETICONLY'
        signature='t='+str(clock())+',v1='+hmac.new(secret.encode(),str(clock()).encode()+b'.'+raw,hashlib.sha256).hexdigest()
        verified=verify_webhook(raw,signature,secret,clock())
        ledger.payment(verified,provider);ledger.payment(verified,provider)
        ledger.fulfill(oid,PROFILE,producer);ledger.fulfill(oid,PROFILE,producer)
        first=ledger.download(oid,token);ledger.download(oid,token)
        ledger.correction(oid,{**PROFILE,'use_case':'chat'})
        ledger.fulfill(oid,{**PROFILE,'use_case':'chat'},producer)
        second=ledger.download(oid,token)
        ledger.refund(oid,provider);ledger.refund(oid,provider)
        receipt=dict(status='OFFLINE_SYNTHETIC_PASS',provider_calls=0,provider_objects_created=0,
                     checkout_create_effects=provider.creates,refund_create_effects=provider.refunds,
                     report_revisions=2,first_artifact=first['manifest'],correction_artifact=second['manifest'],
                     audit=ledger.audit(),source_revision=source_revision(),baseline_revision=BASELINE_REVISION,
                     limitation='Fixture Stripe only; no actual checkout, provider event, remote delivery, refund, settlement, or demand proof.')
        assert provider.creates == provider.refunds == 1
        assert ledger.order(oid)['state'] == 'REFUNDED'
        assert receipt['audit']['promotion_eligible_cents'] == 0
        assert first['manifest'] != second['manifest']
        ledger.close()
    if args.receipt:
        args.receipt.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:receipt[k] for k in ('status','provider_calls','checkout_create_effects','refund_create_effects','report_revisions')}))

if __name__=='__main__':main()
