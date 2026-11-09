#!/usr/bin/env python3
"""Report the produced job's real QA to OpsHub (schema_version 1.0).

Reads the phase3_produce.py summary, keeps the hub-issued job id, and sends the
QA verdict/scores plus manifest path. No job id means a manual run: no-op.
"""
import json
import os
import sys

from job_report import report


def main(argv):
    path = argv[1] if len(argv) > 1 else "production.json"
    try:
        with open(path) as f:
            summary = json.load(f)
    except Exception as exc:
        print(f"[report] no production summary ({exc})")
        return 0
    jobs = summary.get("jobs") or []
    if not jobs:
        print("[report] no jobs in production summary")
        return 0
    job = jobs[0]
    result = job.get("result") if isinstance(job.get("result"), dict) else {}
    status = "blocked" if result.get("verdict") == "blocked" else "awaiting_approval"
    if job.get("status") in ("failed", "cancelled"):
        status = job["status"]
    stage = "approval" if status in ("blocked", "awaiting_approval") else "done"
    qa = result if result else {"verdict": "missing", "blocking_failures": ["no QA produced"]}
    manifest = (result.get("manifest") or {}).get("path", "")
    detail = (f"verdict={qa.get('verdict', 'missing')} "
              f"synthetic={qa.get('synthetic', '?')} "
              f"weights={qa.get('weighted_score', '?')}")
    out = report(status, stage, 100 if result else 0, detail, manifest,
                 qa=qa, env={**os.environ, "OPSHUB_JOB_ID": os.environ.get("OPSHUB_JOB_ID", "")})
    print(f"[report] {status}/{stage} -> {out}")
    return 1 if out.get("error") else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
