import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError

from beanfit.apify_actor import ApifyStore, MAX_INPUT_BYTES, NoRedirect, StorageError, run, verify_provenance


class Store:
    def __init__(self, raw=b'{}', fail=None):
        self.values = {'INPUT': raw}
        self.calls = []
        self.fail = fail

    def op(self, action, key):
        self.calls.append((action, key))
        if self.fail == (action, key):
            raise RuntimeError('secret must never escape')

    def get(self, key):
        self.op('get', key)
        return self.values.get(key)

    def delete(self, key):
        self.op('delete', key)
        self.values.pop(key, None)

    def put(self, key, value, content_type=None):
        self.op('put', key)
        self.values[key] = value


def report(payload, **kwargs):
    return {'markdown': '# report', 'inputs': payload, **kwargs}


class ActorTests(unittest.TestCase):
    def execute(self, store, generate=report):
        ticks = iter([100, 136])
        return run(store, generate=generate, revision='a'*40, memory_mib=128,
                   generated_at='2026-09-04T00:00:00Z', clock=lambda: next(ticks))

    def test_success_commit_marker_and_cost(self):
        store = Store()
        self.assertEqual(self.execute(store), 0)
        self.assertNotIn('INPUT', store.values)
        self.assertEqual(store.calls[1], ('delete', 'INPUT'))
        self.assertEqual(store.calls[-1], ('put', 'OUTPUT'))
        self.assertEqual(store.values['OUTPUT']['status'], 'SUCCEEDED')
        self.assertAlmostEqual(store.values['METRICS']['estimated_compute_units'], .00125)
        self.assertIsNone(store.values['METRICS']['billed_cost_usd'])
        self.assertEqual(store.values['METRICS']['billing_events_emitted'], 0)

    def test_same_store_repeat_overwrites_no_duplicate_items(self):
        store = Store()
        self.execute(store)
        before = dict(store.values)
        store.values['INPUT'] = b'{}'
        self.execute(store)
        self.assertEqual(before, store.values)

    def test_retry_missing_input_preserves_verified_success(self):
        store = Store()
        self.assertEqual(self.execute(store), 0)
        before = dict(store.values)
        self.assertEqual(self.execute(store), 0)
        self.assertEqual(before, store.values)

    def test_retry_tampering_fails_preserves_evidence(self):
        store = Store()
        self.execute(store)
        store.values['REPORT.md'] = 'tampered'
        before = dict(store.values)
        self.assertEqual(self.execute(store), 1)
        self.assertEqual(before, store.values)

    def test_invalid_input_deleted_without_echo(self):
        for raw in (b'secret', b'\xff', b'a'*(MAX_INPUT_BYTES+1), None, b'NaN'):
            with self.subTest(raw_type=type(raw)):
                store = Store(raw)
                self.assertEqual(self.execute(store), 1)
                self.assertNotIn('INPUT', store.values)
                self.assertEqual(store.values['OUTPUT']['status'], 'REJECTED')
                self.assertNotIn('secret', json.dumps(store.values))

    def test_validation_rejection_sanitized(self):
        def reject(*args, **kwargs):
            raise ValueError('secret raw input')
        store = Store()
        self.assertEqual(self.execute(store, reject), 1)
        self.assertNotIn('secret', json.dumps(store.values))

    def test_needs_review_sanitized_non_delivery(self):
        class NeedsReview(ValueError):
            code = 'NEEDS_REVIEW'
        def review(*args, **kwargs):
            raise NeedsReview('secret details must not escape')
        store = Store()
        self.assertEqual(self.execute(store, review), 1)
        self.assertEqual(store.values['OUTPUT']['status'], 'NEEDS_REVIEW')
        self.assertEqual(store.values['OUTPUT']['code'], 'MANUAL_REVIEW_REQUIRED')
        self.assertIsNone(store.values['OUTPUT']['report_json_key'])
        self.assertNotIn('INPUT', store.values)
        self.assertNotIn('REPORT.md', store.values)
        self.assertNotIn('REPORT.json', store.values)
        self.assertNotIn('secret', json.dumps(store.values))

    def test_unknown_exception_code_not_exposed(self):
        class Rejected(ValueError):
            code = 'secret'
        def reject(*args, **kwargs):
            raise Rejected('secret')
        store = Store()
        self.assertEqual(self.execute(store, reject), 1)
        self.assertEqual(store.values['OUTPUT']['status'], 'REJECTED')
        self.assertNotIn('secret', json.dumps(store.values))

    def test_duplicate_fields_rejected_before_generation(self):
        for raw in (b'{"constraints":"secret","constraints":""}',
                    b'{"installed_runtime_versions":{"mlx":"secret","mlx":"1.0"}}'):
            store = Store(raw)
            def forbidden(*args, **kwargs):
                self.fail('duplicate key input reached generator')
            self.assertEqual(self.execute(store, forbidden), 1)
            self.assertNotIn('INPUT', store.values)
            self.assertEqual(store.values['OUTPUT']['status'], 'REJECTED')
            self.assertNotIn('secret', json.dumps(store.values))

    def test_output_reads_have_larger_separate_bound(self):
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self, size):
                self.size = size
                return b'x' * min(40000, size)
        class Opener:
            def open(self, *args, **kwargs):
                self.response = Response()
                return self.response
        opener = Opener()
        store = ApifyStore('store', 'fake', opener)
        self.assertEqual(len(store.get('INPUT')), MAX_INPUT_BYTES+1)
        self.assertEqual(len(store.get('REPORT.json')), 40000)
        self.assertEqual(opener.response.size, 1_048_577)

    def test_read_failure_still_deletes(self):
        store = Store(fail=('get', 'INPUT'))
        self.assertEqual(self.execute(store), 1)
        self.assertNotIn('INPUT', store.values)

    def test_delete_failure_never_generates(self):
        store = Store(fail=('delete', 'INPUT'))
        def forbidden(*args, **kwargs):
            self.fail('generator called before privacy deletion')
        self.assertEqual(self.execute(store, forbidden), 1)
        self.assertNotIn('REPORT.md', store.values)

    def test_partial_write_cleaned_and_failure_not_success(self):
        store = Store(fail=('put', 'REPORT.json'))
        self.assertEqual(self.execute(store), 1)
        self.assertNotIn('REPORT.md', store.values)
        self.assertEqual(store.values['OUTPUT']['status'], 'FAILED')

    def test_commit_failure_nonzero(self):
        store = Store(fail=('put', 'OUTPUT'))
        self.assertEqual(self.execute(store), 1)
        self.assertNotIn('OUTPUT', store.values)

    def test_fixed_host_key_and_no_redirect(self):
        for identity in ('../../evil', 'https://evil', ''):
            with self.assertRaises(StorageError):
                ApifyStore(identity, 'test')
        with self.assertRaises(StorageError):
            ApifyStore('store', 'test').get('../evil')
        with self.assertRaises(StorageError):
            NoRedirect().redirect_request(None, None, 302, '', {}, 'https://evil')

    def test_transport_auth_and_sanitized_error(self):
        class Opener:
            def open(self, req, timeout):
                self.req, self.timeout = req, timeout
                raise HTTPError(req.full_url, 403, 'secret', {}, None)
        opener = Opener()
        with self.assertRaisesRegex(StorageError, '^STORAGE_REQUEST_FAILED$'):
            ApifyStore('abc123', 'fake-token', opener).get('INPUT')
        self.assertEqual(opener.req.full_url, 'https://api.apify.com/v2/key-value-stores/abc123/records/INPUT')
        self.assertEqual(opener.req.get_header('Authorization'), 'Bearer fake-token')
        self.assertEqual(opener.timeout, 15)

    def test_manifest_detects_changed_or_extra_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'src').mkdir()
            (root/'src/a.py').write_text('original')
            manifest = {'repository_revision':'a'*40, 'source_sha256':{'src/a.py': hashlib.sha256(b'original').hexdigest()}}
            path = root/'manifest.json'
            path.write_text(json.dumps(manifest))
            self.assertEqual(verify_provenance(path, root), manifest)
            (root/'src/b.py').write_text('extra')
            with self.assertRaises(RuntimeError):
                verify_provenance(path, root)


if __name__ == '__main__':
    unittest.main()
