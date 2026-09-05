"""Private BF-CER adapter. Only default KVS traffic; never emits billing events."""
import hashlib
import json
import os
from pathlib import Path
import re
import time
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

MAX_INPUT_BYTES = 32_768
OUTPUT_KEYS = ("OUTPUT", "REPORT.md", "REPORT.json", "METRICS")


class StorageError(RuntimeError):
    """Intentionally excludes response bodies, headers, URLs, and credentials."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise StorageError("STORAGE_REDIRECT_REJECTED")


class ApifyStore:
    def __init__(self, store_id, token, opener=None):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", store_id or "") or not token:
            raise StorageError("STORAGE_CONFIGURATION_INVALID")
        self._base = "https://api.apify.com/v2/key-value-stores/" + store_id + "/records/"
        self._token = token
        self._opener = opener or build_opener(ProxyHandler({}), NoRedirect())

    def request(self, method, key, body=None, content_type="application/json"):
        if key not in (*OUTPUT_KEYS, "INPUT"):
            raise StorageError("STORAGE_KEY_REJECTED")
        request = Request(self._base + key, data=body, method=method,
                          headers={"Authorization": "Bearer " + self._token,
                                   "Content-Type": content_type})
        try:
            with self._opener.open(request, timeout=15) as response:
                limit = MAX_INPUT_BYTES if key == "INPUT" else 1_048_576
                return response.read(limit + 1) if method == "GET" else b""
        except HTTPError as error:
            status_code = error.code
            error.close()
            if status_code == 404 and method in ("GET", "DELETE"):
                return None
            raise StorageError("STORAGE_REQUEST_FAILED") from None
        except Exception:
            raise StorageError("STORAGE_REQUEST_FAILED") from None

    def get(self, key):
        return self.request("GET", key)

    def delete(self, key):
        self.request("DELETE", key)

    def put(self, key, value, content_type="application/json"):
        body = value.encode("utf-8") if isinstance(value, str) else json.dumps(value, sort_keys=True, allow_nan=False).encode("utf-8")
        self.request("PUT", key, body, content_type)


def verify_provenance(manifest_path, root):
    """Manifest lists every Python source, including this adapter and catalog."""
    manifest = json.loads(Path(manifest_path).read_text())
    if not re.fullmatch(r"[0-9a-f]{40}", manifest.get("repository_revision", "")):
        raise RuntimeError("PROVENANCE_INVALID")
    expected = manifest.get("source_sha256", {})
    actual = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (Path(root) / "src").rglob("*.py")}
    if not actual or actual != expected:
        raise RuntimeError("PROVENANCE_INVALID")
    return manifest


def _json_record(value):
    return json.loads(value) if isinstance(value, (bytes, str)) else value


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate input field")
        result[key] = value
    return result


def _digest(value):
    data = value.encode("utf-8") if isinstance(value, str) else json.dumps(value, sort_keys=True, allow_nan=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def run(store, *, generate, revision, memory_mib, generated_at=None, clock=time.monotonic, source_sha256=None):
    """Injected store/clock/generator make failure and privacy behavior testable."""
    started = clock()
    status = "FAILED"
    code = "INTERNAL_FAILURE"
    try:
        # Delete even malformed/oversize input or a failed read. Fail closed if
        # deletion cannot be confirmed. No input is ever written to a log.
        try:
            raw = store.get("INPUT")
        finally:
            store.delete("INPUT")
        if raw is None:
            # A platform retry after input consumption must preserve a committed
            # report. Verify both artifacts against the last commit marker.
            prior = _json_record(store.get("OUTPUT"))
            if prior and prior.get("status") == "SUCCEEDED":
                md = store.get("REPORT.md")
                md = md.decode("utf-8") if isinstance(md, bytes) else md
                structured = _json_record(store.get("REPORT.json"))
                if (prior.get("report_markdown_sha256") == _digest(md)
                        and prior.get("report_json_sha256") == _digest(structured)):
                    return 0
                # Preserve evidence for operator inspection; never claim success.
                return 1
        for key in OUTPUT_KEYS:
            store.delete(key)
        if raw is None or len(raw) > MAX_INPUT_BYTES:
            raise ValueError("invalid input")
        payload = json.loads(raw, object_pairs_hook=_unique_object,
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        stamp = generated_at or datetime.now(timezone.utc).isoformat()
        result = generate(payload, generated_at=stamp, repository_revision=revision)
        result["deployment_provenance"] = {"repository_revision": revision,
                                            "source_manifest_sha256": _digest(source_sha256) if source_sha256 else None}
        markdown = result["markdown"]
        store.put("REPORT.md", markdown, "text/markdown; charset=utf-8")
        store.put("REPORT.json", result)
        status, code = "SUCCEEDED", "REPORT_GENERATED"
    except (ValueError, UnicodeDecodeError) as error:
        if getattr(error, "code", None) == "NEEDS_REVIEW":
            status, code = "NEEDS_REVIEW", "MANUAL_REVIEW_REQUIRED"
        else:
            status, code = "REJECTED", "INVALID_INPUT_REDACT_AND_RESUBMIT"
    except Exception:
        pass
    elapsed = max(0.0, clock() - started)
    metrics = {"elapsed_seconds": elapsed, "allocated_memory_mib": memory_mib,
               "estimated_compute_units": elapsed / 3600 * memory_mib / 1024,
               "measurement_scope": "adapter wall time through report writes; excludes startup and final receipt writes",
               "billed_cost_usd": None, "billing_events_emitted": 0,
               "cost_note": "CU estimate only; operator must retrieve platform run usage and actual cost."}
    output = {"contract_version": "BF-CER-v1.0", "status": status, "code": code,
              "report_markdown_key": "REPORT.md" if status == "SUCCEEDED" else None,
              "report_json_key": "REPORT.json" if status == "SUCCEEDED" else None,
              "metrics_key": "METRICS"}
    if status == "SUCCEEDED":
        output["report_markdown_sha256"] = _digest(markdown)
        output["report_json_sha256"] = _digest(result)
    try:
        if status != "SUCCEEDED":
            for key in ("OUTPUT", "REPORT.md", "REPORT.json"):
                store.delete(key)
        store.put("METRICS", metrics)
        # OUTPUT is the commit marker: consumers must never consume reports
        # unless this final write says SUCCEEDED.
        store.put("OUTPUT", output)
    except Exception:
        return 1
    return 0 if status == "SUCCEEDED" else 1


def main():
    try:
        from beanfit.report import generate_report
        root = Path(__file__).resolve().parents[2]
        manifest = verify_provenance(root / "build-manifest.json", root)
        env = os.environ
        if env.get("ACTOR_INPUT_KEY", "INPUT") != "INPUT":
            raise RuntimeError("INPUT_KEY_UNSUPPORTED")
        store = ApifyStore(env.get("ACTOR_DEFAULT_KEY_VALUE_STORE_ID") or env.get("APIFY_DEFAULT_KEY_VALUE_STORE_ID"), env.get("APIFY_TOKEN"))
        memory = int(env.get("ACTOR_MEMORY_MBYTES") or env.get("APIFY_MEMORY_MBYTES", "0"))
        if not 1 <= memory <= 1024:
            raise RuntimeError("MEMORY_LIMIT_INVALID")
        return run(store, generate=generate_report, revision=manifest["repository_revision"], memory_mib=memory,
                   source_sha256=manifest["source_sha256"])
    except Exception:
        print("BF-CER actor failed; inspect non-secret deployment configuration.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
