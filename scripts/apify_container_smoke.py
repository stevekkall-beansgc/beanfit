"""Run inside the built image: production entrypoint, synthetic storage, no network."""
import io
import json
import os
from urllib.error import HTTPError
import beanfit.apify_actor as actor

class StorageAPI:
    def __init__(self):
        self.records = {}
    def open(self, req, timeout):
        assert req.full_url.startswith('https://api.apify.com/v2/key-value-stores/synthetic/records/')
        key=req.full_url.rsplit('/',1)[1]
        if req.method=='DELETE':
            self.records.pop(key,None)
        elif req.method=='PUT':
            self.records[key]=req.data
        elif key not in self.records:
            raise HTTPError(req.full_url,404,'missing',{},None)
        return io.BytesIO(self.records.get(key,b''))

storage=StorageAPI()
actor.build_opener=lambda *args:storage
os.environ.update(APIFY_TOKEN='synthetic-local-only',ACTOR_DEFAULT_KEY_VALUE_STORE_ID='synthetic',ACTOR_MEMORY_MBYTES='128')
input_data=dict(device_chip='Apple M4 Pro',memory_gib=48,use_case='coding',operating_system='macOS 15.6 arm64')
storage.records['INPUT']=json.dumps(input_data).encode()
assert actor.main()==0
assert 'INPUT' not in storage.records
assert json.loads(storage.records['OUTPUT'])['status']=='SUCCEEDED'
report=json.loads(storage.records['REPORT.json'])
assert report['ranked_options'][0]['runtime_tag']=='deepseek-coder-v2:16b'
assert report['deployment_provenance']['source_manifest_sha256']
before=dict(storage.records)
assert actor.main()==0
assert storage.records==before
storage.records['INPUT']=json.dumps(dict(input_data,minimum_context_tokens=32768)).encode()
assert actor.main()==1
assert json.loads(storage.records['OUTPUT'])['status']=='NEEDS_REVIEW'
assert 'INPUT' not in storage.records and 'REPORT.json' not in storage.records
storage.records['INPUT']=b'{"constraints":"PRIVATE_CANARY", "constraints":""}'
assert actor.main()==1
assert json.loads(storage.records['OUTPUT'])['status']=='REJECTED'
assert b'PRIVATE_CANARY' not in b''.join(storage.records.values())
print(json.dumps({'container_smoke':'PASS','real_entrypoint':True,'source_manifest_verified':True,'cases':['success','identical-retry','manual-review','duplicate-key-rejection'],'network':'disabled','platform_cost_usd':None,'billing_events':0}))
