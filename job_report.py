"""Opt-in production status reporter for OpsHub (schema_version 1.0).

Usage:
  python job_report.py running research 5 "pipeline starting"
  python job_report.py awaiting_approval approval 100 "render complete" "episodes/ep1"

Environment:
  OPSHUB_JOB_ID        job id from the repository_dispatch payload
  HUB_URL / OPSHUB_URL hub origin
  HUB_WEBHOOK_SECRET   HMAC key shared with OpsHub

Contract:
  * no job id -> no-op (manual runs are unaffected)
  * hub not configured -> skipped with a printed reason (never fatal)
  * reporting failure -> logged, returns an error dict (never aborts a render)
"""

import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request

STUDIO = "deep-history"


def _env(env, key, default=""):
    source = os.environ if env is None else env
    return str(source.get(key, default) or "").strip()


def hub_url(env=None):
    return (_env(env, "HUB_URL") or _env(env, "OPSHUB_URL")).rstrip("/")


def sign(secret, body):
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _default_transport(method, url, headers, body):
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def report(status, stage, progress=0, detail="", output="", qa=None,
           env=None, transport=None):
    job = _env(env, "OPSHUB_JOB_ID")
    if not job:
        return {"skipped": "no job id"}
    url = hub_url(env)
    secret = _env(env, "HUB_WEBHOOK_SECRET")
    if not url or not secret:
        print("[job] skipped: hub not configured (needs HUB_URL + HUB_WEBHOOK_SECRET)")
        return {"skipped": "hub misconfigured"}

    payload = {
        "schema_version": "1.0",
        "job_id": job,
        "studio": _env(env, "OPSHUB_STUDIO", STUDIO),
        "status": status,
        "stage": stage,
        "progress": int(progress),
        "detail": str(detail)[:1000],
        "output": str(output)[:500],
        "qa": qa or {},
        "reported_at": int(time.time()),
    }
    body = json.dumps(payload, separators=(",", ":")).encode()
    headers = {
        "Content-Type": "application/json",
        "x-hub-signature-256": sign(secret, body),
        "User-Agent": "studio-job-report/1.0",
    }
    fn = transport or _default_transport
    try:
        code, text = fn("POST", url + "/jobs/" + job + "/status", headers, body)
        if code < 200 or code >= 300:
            print(f"[job] hub rejected status update: {code} {text[:160]}")
            return {"error": code, "detail": text[:200]}
        return {"status": code}
    except Exception as exc:  # noqa: BLE001 - reporting must never break a render
        print(f"[job] reporting failed (non-fatal): {exc}")
        return {"error": str(exc)[:200]}


def main(argv):
    if len(argv) < 3:
        print("usage: python job_report.py <status> <stage> [progress] [detail] [output]")
        return 2
    status, stage = argv[1], argv[2]
    progress = argv[3] if len(argv) > 3 else 0
    detail = argv[4] if len(argv) > 4 else ""
    output = argv[5] if len(argv) > 5 else ""
    try:
        progress = int(progress)
    except (TypeError, ValueError):
        progress = 0
    result = report(status, stage, progress, detail, output)
    print(f"[job] {status}/{stage} -> {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
