#!/usr/bin/env python3
"""Phase 3 production entrypoint (vendored shared pipeline).

Each studio repo runs this file. It never publishes, never enables billing and
never sends a credential anywhere except the provider it belongs to.

  python phase3_produce.py --topic "AI agents" --out artifacts/production
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from shared.production import runner  # noqa: E402
from shared.production.providers.chain import ProviderChain  # noqa: E402
from shared.production.providers.gemini import GeminiProvider  # noqa: E402
from shared.production.providers.groq import GroqProvider  # noqa: E402
from shared.production.render import ensure_tools  # noqa: E402
from shared.production.synthetic import SyntheticLLM  # noqa: E402
from shared.production.usage import UsageLedger  # noqa: E402

STUDIO_BY_DIR = {
    "faceless-studio": "trendscope",
    "faceless-turkce-studio": "true-crime",
    "deep-history-studio": "deep-history",
}


def studio_name() -> str:
    forced = os.environ.get("OPSHUB_STUDIO", "").strip()
    if forced in runner.STUDIOS:
        return forced
    return STUDIO_BY_DIR.get(os.path.basename(HERE), "trendscope")


def build_llm(env: Dict[str, str], mode: str, topic: str) -> Any:
    if mode == "synthetic":
        return SyntheticLLM(topic)
    providers = []
    if str(env.get("GROQ_API_KEY", "")).strip():
        providers.append(GroqProvider(env))
    if str(env.get("GEMINI_API_KEY", "")).strip():
        providers.append(GeminiProvider(env))
    if not providers:
        print("[phase3] no AI credential present - using synthetic content", file=sys.stderr)
        return SyntheticLLM(topic)
    return ProviderChain(providers)


def main(argv: List[str]) -> int:
    studio = studio_name()
    parser = argparse.ArgumentParser(description=f"Phase 3 production: {studio}")
    parser.add_argument("--topic", default="")
    parser.add_argument("--out", default=os.path.join("artifacts", "production"))
    parser.add_argument("--mode", default="auto", choices=["auto", "synthetic", "live"])
    parser.add_argument("--short-seconds", type=float,
                        default=float(os.environ.get("SHORT_SECONDS", "42")))
    parser.add_argument("--short-fps", type=int,
                        default=int(os.environ.get("SHORT_FPS", "30")))
    parser.add_argument("--landscape-seconds", type=float,
                        default=float(os.environ.get("LANDSCAPE_SECONDS", "480")))
    parser.add_argument("--landscape-fps", type=int,
                        default=int(os.environ.get("LANDSCAPE_FPS", "24")))
    parser.add_argument("--no-tts", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    ensure_tools()
    env = dict(os.environ)
    outdir = os.path.abspath(args.out)
    os.makedirs(outdir, exist_ok=True)
    ledger = UsageLedger(os.path.join(outdir, "usage.json"))

    ctx: Dict[str, Any] = {
        "llm": build_llm(env, args.mode, args.topic),
        "ledger": ledger,
        "outdir": outdir,
        "allow_tts": not args.no_tts,
        "ken_burns": True,
        "short_seconds": args.short_seconds,
        "short_fps": args.short_fps,
        "landscape_seconds": args.landscape_seconds,
        "landscape_fps": args.landscape_fps,
        "production_mode": "test",
        "voice": env.get("TTS_VOICE", "en-US-GuyNeural"),
        "voice_tr": env.get("TTS_VOICE_TR", "tr-TR-AhmetNeural"),
    }

    summary = runner.run_all(ctx, topic=args.topic, studios_to_run=[studio], dedupe=True)
    print(json.dumps(summary, indent=1, default=str) if args.json
          else f"{studio}: {summary['statuses']}")
    return 1 if summary["failed_or_cancelled"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
