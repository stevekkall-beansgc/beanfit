#!/usr/bin/env python3
"""Read-only, value-minimized Apify free-credit preflight via BeanLaunch."""
import json
import subprocess
import urllib.request
import urllib.error

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def main():
    result = subprocess.run(['/Users/stephenkall/beans/platform/beanlaunch/bin/bl',
        'secret:get', 'autonomous-revenue-portfolio__APIFY_BOOTSTRAP_TOKEN'],
        capture_output=True, timeout=30)
    if result.returncode:
        print(json.dumps({'status':'BLOCKED', 'reason':'vault access failed'}))
        return 1
    token = result.stdout.decode().strip()
    opener = urllib.request.build_opener(NoRedirect())
    outputs = {}
    try:
        for name, path in [('account','users/me'), ('limits','users/me/limits'), ('usage','users/me/usage/monthly')]:
            req = urllib.request.Request('https://api.apify.com/v2/' + path,
                headers={'Authorization': 'Bearer ' + token})
            with opener.open(req, timeout=20) as resp:
                outputs[name] = json.load(resp)['data']
    except Exception:
        print(json.dumps({'status':'BLOCKED','reason':'authenticated read failed; details suppressed'}))
        return 1
    # Report only whitelisted technical controls; never account/payout details.
    account, limits, usage = outputs['account'], outputs['limits'], outputs['usage']
    summary = {
        'account_control_keys': [k for k in account if k in ('isPaying', 'isEnabled', 'isActorEnabled', 'plan')],
        'isPaying': account.get('isPaying'),
        'isEnabled': account.get('isEnabled'),
        'isActorEnabled': account.get('isActorEnabled'),
        'plan': {k:v for k,v in account.get('plan', {}).items() if k in ('id','isEnabled','monthlyUsageCreditsUsd')},
        'maxMonthlyUsageUsd': limits.get('maxMonthlyUsageUsd', limits.get('limits', {}).get('maxMonthlyUsageUsd')),
        'limit_current_usage': limits.get('current', {}).get('monthlyUsageUsd'),
        'usageTotalUsd': usage.get('totalUsageCreditsUsd', usage.get('totalUsageUsd')),
        'writes':0,
    }
    # 'current' holds numeric platform caps, not financial account balances.
    print(json.dumps(summary, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
