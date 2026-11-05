"""Fail-closed client for OpsHub's shared daily studio image-call ledger."""
import hashlib
import hmac
import json
import os
import time
import urllib.request


def reserve_image(studio, asset_key):
    """Reserve one Cloudflare request; use keyless fallback when denied/unavailable.

    The ledger counts requests, not neuron usage. It is a conservative shared
    pacing guard and cannot account for Cloudflare calls outside these studios.
    """
    hub_url = os.environ.get("HUB_URL", "").strip().rstrip("/")
    secret = os.environ.get("HUB_WEBHOOK_SECRET", "").strip()
    if not hub_url or not secret:
        print("[quota] shared ledger unavailable; skipping Cloudflare")
        return False

    run_id = os.environ.get("GITHUB_RUN_ID") or f"local-{os.getpid()}-{time.time_ns()}"
    request_id = f"{studio}:{run_id}:{str(asset_key)[:160]}"
    body = json.dumps(
        {"studio": studio, "request_id": request_id},
        separators=(",", ":"),
    ).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    req = urllib.request.Request(
        hub_url + "/ai-usage/reserve",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-hub-signature-256": "sha256=" + signature,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
        if result.get("allowed") is True:
            print(
                f"[quota] reserved {result.get('calls')}/24 global, "
                f"{result.get('studioCalls')}/10 for {studio}"
            )
            return True
        print(f"[quota] denied ({result.get('reason')}); using keyless fallback")
        return False
    except Exception as exc:
        print(f"[quota] ledger unavailable; fail-closed to keyless fallback: {exc}")
        return False
