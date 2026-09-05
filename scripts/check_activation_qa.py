#!/usr/bin/env python3
"""Use central QA with explicit isolated manifest + target overrides."""
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
qa_root=Path(os.environ.get('BF_CER_QA_ROOT',str(Path.home()/'beans/platform/qa-kit')))
spec=importlib.util.spec_from_file_location('isolated_activation_qa',qa_root/'bin/run_all.py')
qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)
def manifest():
    value=json.loads((qa_root/'manifest.json').read_text())
    for repo in value['repos']:
        if repo['name']=='beanfit':
            assert repo['e2e']['cmd']==['python3','scripts/activation_demo.py']
            repo['path']=str(root)
    return value
qa.load_manifest=manifest
qa.LOGS=Path(tempfile.mkdtemp(prefix='bfcer-central-qa-'))
print('QA receipt directory: '+str(qa.LOGS))
sys.argv=[str(qa_root/'bin/run_all.py'),'--only','beanfit','--all']
raise SystemExit(qa.main())
