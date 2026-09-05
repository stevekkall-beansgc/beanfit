#!/usr/bin/env python3
"""Manual test-only integration driver. Never reads arbitrary customer profiles.

STRIPE_TEST_KEY / BF_CER_TEST_DOWNLOAD_TOKEN are runtime-only environment values.
For event ingestion BF_CER_WEBHOOK_SECRET is also required; stdin is raw signed
Stripe event JSON, and BF_CER_STRIPE_SIGNATURE supplies its signature header.
Do not supply keys in CLI arguments. No network calls in offline-demo.
"""
import argparse
import json
import os
import sys
import stat
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from beanfit.activation import ActivationError, Ledger
from beanfit.stripe_test import StripeTestClient, StripeTestError, verify_webhook
from activation_demo import PROFILE, producer


def check_private_file(path):
    if not path.exists() and not path.is_symlink(): return
    info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_nlink != 1:
        raise ActivationError('PRIVATE_REGULAR_FILE_REQUIRED')


def write_private(path, data):
    fd=os.open(path,os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW,0o600)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_nlink != 1:
            raise ActivationError('PRIVATE_REGULAR_FILE_REQUIRED')
        os.ftruncate(fd,0)
        with os.fdopen(fd,'wb',closefd=False) as stream:
            stream.write(data);stream.flush();os.fsync(fd)
    finally: os.close(fd)


def main():
    if os.name != 'posix' or not hasattr(os, 'O_NOFOLLOW'):
        raise ActivationError('PROVIDER_DRIVER_REQUIRES_POSIX')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['checkout','event','fulfill','download','refund','audit'])
    parser.add_argument('--state-dir',required=True,help='Private temporary state directory outside repository')
    args=parser.parse_args()
    state=Path(args.state_dir).resolve()
    if state==ROOT or ROOT in state.parents:
        raise ActivationError('STATE_MUST_BE_OUTSIDE_REPOSITORY')
    os.umask(0o077)
    state.mkdir(mode=0o700,parents=True,exist_ok=True)
    if state.stat().st_mode & 0o077:
        raise ActivationError('STATE_DIRECTORY_MUST_BE_PRIVATE')
    for name in ('ledger.sqlite','ledger.sqlite-wal','ledger.sqlite-shm','REPORT.md','REPORT.json'):
        check_private_file(state/name)
    ledger=Ledger(state/'ledger.sqlite',now=time.time)
    try:
        token=os.environ.get('BF_CER_TEST_DOWNLOAD_TOKEN','')
        if len(token)<32: raise ActivationError('RUNTIME_DOWNLOAD_TOKEN_REQUIRED')
        oid,_=ledger.accept('synthetic-provider-first-dollar',PROFILE,synthetic=True,token=token)
        if args.action=='checkout':
            client=StripeTestClient(os.environ.get('STRIPE_TEST_KEY',''))
            session_id=ledger.checkout(oid,client)
            session=client.get_checkout(session_id)
            print(json.dumps(dict(classification='EXCLUDED_TEST',session_id=session_id,test_checkout_url=session.get('url'))))
        elif args.action=='event':
            raw=sys.stdin.buffer.read(262145)
            event=verify_webhook(raw,os.environ.get('BF_CER_STRIPE_SIGNATURE',''),os.environ.get('BF_CER_WEBHOOK_SECRET',''),time.time())
            client=StripeTestClient(os.environ.get('STRIPE_TEST_KEY',''))
            ledger.payment(event,client,expected_order_id=oid)
            print(json.dumps(dict(classification='EXCLUDED_TEST',order_id=oid,state=ledger.order(oid)['state'])))
        elif args.action=='fulfill':
            ledger.fulfill(oid,PROFILE,producer)
            print(json.dumps(dict(classification='EXCLUDED_TEST',order_id=oid,state='READY')))
        elif args.action=='download':
            artifacts=ledger.download(oid,token)
            write_private(state/'REPORT.md',artifacts['markdown'])
            write_private(state/'REPORT.json',artifacts['structured'])
            print(json.dumps(dict(classification='EXCLUDED_TEST',manifest=artifacts['manifest'])))
        elif args.action=='refund':
            client=StripeTestClient(os.environ.get('STRIPE_TEST_KEY',''))
            print(json.dumps(dict(classification='EXCLUDED_TEST',state=ledger.refund(oid,client))))
        else:
            print(json.dumps(ledger.audit(),indent=2))
    finally:
        ledger.close()

if __name__=='__main__':
    try: main()
    except Exception:
        print(json.dumps(dict(status='STOPPED',reason='Test action failed; inspect ledger and reconcile provider before retry. Details suppressed.')),file=sys.stderr)
        raise SystemExit(1) from None
