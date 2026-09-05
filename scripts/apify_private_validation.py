#!/usr/bin/env python3
"""Bounded private validation only; no pricing, public access, or plan mutation."""
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler

ROOT=Path(__file__).resolve().parents[1]
RECEIPT=ROOT/'docs/apify/provider-receipt.json'
NAME='beanfit-compatibility-evidence-report'
class Stop(RuntimeError): pass
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args): raise Stop('REDIRECT_REJECTED')

def save(data):
    RECEIPT.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')

class Client:
    def __init__(self):
        p=subprocess.run(['/Users/stephenkall/beans/platform/beanlaunch/bin/bl','secret:get','autonomous-revenue-portfolio__APIFY_BOOTSTRAP_TOKEN'],capture_output=True,timeout=30)
        if p.returncode: raise Stop('VAULT_UNAVAILABLE')
        self.token=p.stdout.decode().strip()
        self.opener=build_opener(ProxyHandler({}),NoRedirect())
    def call(self,method,path,body=None,raw=False,missing=False):
        if not path.startswith('/') or '..' in path: raise Stop('INVALID_PATH')
        req=Request('https://api.apify.com/v2'+path,method=method,
                    data=None if body is None else json.dumps(body).encode(),
                    headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json'})
        try:
            with self.opener.open(req,timeout=25) as resp:
                data=resp.read(2_000_000)
        except HTTPError as e:
            code=e.code
            e.close()
            if missing and code==404:return None
            raise Stop('HTTP_'+str(code)+'_'+method) from None
        except Exception:
            raise Stop('NETWORK_OUTCOME_UNKNOWN_'+method) from None
        if raw:return data
        return json.loads(data).get('data') if data else None
    def preflight(self):
        a=self.call('GET','/users/me')
        l=self.call('GET','/users/me/limits')
        plan=a.get('plan',{})
        credits=plan.get('monthlyUsageCreditsUsd')
        cap=l.get('maxMonthlyUsageUsd',l.get('limits',{}).get('maxMonthlyUsageUsd'))
        used=l.get('current',{}).get('monthlyUsageUsd')
        if not (plan.get('id')=='FREE' and plan.get('isEnabled') is True and a.get('isPaying') is False
                and type(credits) in (int,float) and type(cap) in (int,float) and type(used) in (int,float)
                and 0 < cap <= credits <= 5 and cap-used>=.25):
            raise Stop('FREE_CREDIT_GATE_FAILED')
        return {'at':datetime.now(timezone.utc).isoformat(),'plan':'FREE','isPaying':False,
                'monthlyCreditsUsd':credits,'maxMonthlyUsageUsd':cap,'currentUsageUsd':used}

def main():
    stage=sys.argv[1]
    d=json.loads(RECEIPT.read_text()) if RECEIPT.exists() else {'task':190,'runs':[],'classification':'EXCLUDED_TEST'}
    c=Client()
    d['latest_preflight']=c.preflight();save(d)
    if stage=='inspect':
        listing=c.call('GET','/actors?limit=1000')
        items=listing.get('items',[])
        if listing.get('total',len(items))>len(items):raise Stop('ACTOR_LIST_NOT_EXHAUSTED')
        matches=[{'id':a['id'],'isPublic':a.get('isPublic')} for a in items if a.get('name')==NAME]
        d['matching_actors']=matches;save(d)
        print(json.dumps({'preflight':d['latest_preflight'],'matching_actors':matches}));return
    if stage=='create':
        if d.get('actor_id') or d.get('create_attempted'):raise Stop('RECONCILE_PRIOR_CREATE_FIRST')
        listing=c.call('GET','/actors?limit=1000')
        if listing.get('total',len(listing['items']))>len(listing['items']) or any(a.get('name')==NAME for a in listing['items']):
            raise Stop('ACTOR_EXISTENCE_AMBIGUITY')
        payload=json.loads((ROOT/'docs/apify/private-create-payload.json').read_text())
        if payload.get('isPublic') is not False or payload.get('name')!=NAME or 'pricingInfos' in payload:raise Stop('PAYLOAD_GATE')
        d['create_attempted']=True;save(d)
        a=c.call('POST','/actors',payload)
        d['actor_id']=a['id'];save(d)
        a=c.call('GET','/actors/'+d['actor_id'])
        if a.get('isPublic') is not False:raise Stop('ACTOR_PRIVACY_GATE')
        d['isPublic']=False;save(d)
        print(json.dumps({'actor_id':d['actor_id'],'isPublic':False}));return
    raise Stop('UNSUPPORTED_STAGE')

if __name__=='__main__':
    try:main()
    except Stop as e:
        print(json.dumps({'status':'STOPPED','reason':str(e)}));sys.exit(1)
    except Exception:
        print(json.dumps({'status':'STOPPED','reason':'LOCAL_OR_RESPONSE_ERROR_DETAILS_SUPPRESSED'}));sys.exit(1)
