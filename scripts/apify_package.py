#!/usr/bin/env python3
"""Prepare a secret-free private SOURCE_FILES payload; never deploys."""
import hashlib
import json
from pathlib import Path
import subprocess
from check_apify_schema import validate_schema

ROOT = Path(__file__).resolve().parents[1]
BASE_REVISION = 'e8ec4507b89b3b0471894515e1f80794eb92664f'
CORE_PATHS = ('src/beanfit/catalog', 'src/beanfit/engine', 'src/beanfit/hw', 'src/beanfit/profile.py', 'src/beanfit/emit')

def prepare(root=ROOT):
    validate_schema(json.loads((root/".actor/input_schema.json").read_text()))
    # A base SHA must actually describe the unchanged original estimator/catalog.
    if subprocess.run(['git', 'diff', '--exit-code', BASE_REVISION, '--', *CORE_PATHS], cwd=root, capture_output=True).returncode:
        raise RuntimeError('Pinned Beanfit core changed; provenance review required')
    source_paths = sorted((root/'src').rglob('*.py'))
    manifest = {'repository_revision':BASE_REVISION,
                'source_sha256':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}}
    (root/'.actor/build-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
    selected = source_paths + [root/'.actor'/n for n in ('actor.json','input_schema.json','Dockerfile','build-manifest.json')] + [root/'docs/apify.md', root/'.dockerignore']
    files = [{'name':p.relative_to(root).as_posix(), 'format':'TEXT', 'content':p.read_text()} for p in selected]
    payload = {
        'name':'beanfit-compatibility-evidence-report', 'title':'Beanfit Compatibility Evidence Report',
        'description':'Private validation of BF-CER-v1.0; one device, one workload, one Markdown and JSON report.',
        'isPublic':False,
        'versions':[{'versionNumber':'1.0','sourceType':'SOURCE_FILES','buildTag':'private-test','applyEnvVarsToBuild':False,'envVars':[], 'sourceFiles':files}],
        'defaultRunOptions':{'build':'private-test','timeoutSecs':60,'memoryMbytes':128,'restartOnError':False,'forcePermissionLevel':'LIMITED_PERMISSIONS'},
        'actorStandby':{'isEnabled':False},
    }
    destination = root/'docs/apify/private-create-payload.json'
    destination.write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps({'status':'PREPARED_ONLY','source_files':len(files),'payload_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'writes_to_apify':0}))

if __name__ == '__main__':
    prepare()
