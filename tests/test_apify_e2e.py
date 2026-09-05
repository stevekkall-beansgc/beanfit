"""Offline end-to-end: real report, HTTP serialization, storage and replay."""
import io
import json
import unittest
from urllib.error import HTTPError

from beanfit.apify_actor import ApifyStore, run
from beanfit.report import generate_report


class StorageAPI:
    def __init__(self, value):
        self.records = {'INPUT':json.dumps(value).encode()}
        self.methods = []

    def open(self, req, timeout):
        self.methods.append(req.method)
        key = req.full_url.rsplit('/', 1)[1]
        if req.method == 'PUT':
            self.records[key] = req.data
        elif req.method == 'DELETE':
            self.records.pop(key, None)
        elif key not in self.records:
            raise HTTPError(req.full_url, 404, 'missing', {}, None)
        return io.BytesIO(self.records.get(key, b''))


class EndToEndTests(unittest.TestCase):
    def test_real_report_over_storage_transport_then_replay(self):
        value = dict(device_chip='Apple M4 Pro', memory_gib=48,
                     use_case='coding', operating_system='macOS 15.6 arm64')
        api = StorageAPI(value)
        store = ApifyStore('synthetic-store', 'synthetic-token', api)
        options = dict(generate=generate_report, revision='e8ec4507b89b3b0471894515e1f80794eb92664f',
                       memory_mib=128, generated_at='2026-09-04T00:00:00Z')
        self.assertEqual(run(store, **options), 0)
        report = json.loads(api.records['REPORT.json'])
        self.assertEqual(report['ranked_options'][0]['runtime_tag'], 'deepseek-coder-v2:16b')
        self.assertEqual(api.records['REPORT.md'].decode(), report['markdown'])
        self.assertNotIn('INPUT', api.records)
        before = dict(api.records)
        self.assertEqual(run(store, **options), 0)
        self.assertEqual(before, api.records)
        self.assertNotIn('POST', api.methods)

    def test_actual_report_rejection_removes_sensitive_input(self):
        api = StorageAPI({'token':'SYNTHETIC_PRIVATE_CANARY'})
        store = ApifyStore('synthetic-store','synthetic-token',api)
        self.assertEqual(run(store, generate=generate_report, revision='a'*40, memory_mib=128), 1)
        self.assertNotIn('INPUT', api.records)
        self.assertNotIn(b'SYNTHETIC_PRIVATE_CANARY', b''.join(api.records.values()))
        self.assertEqual(json.loads(api.records['OUTPUT'])['status'], 'REJECTED')
