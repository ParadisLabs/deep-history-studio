"""Assemble a documentary-length 16:9 cut from scene segments.

Input episodes must be explicitly listed in order. By default the opening
segment of every episode after the first is omitted to avoid repeated hooks.
Original portrait segments are preserved; the long-form uses a blurred,
letterboxed landscape treatment rather than stretching or cropping away action.
"""
import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from render_quality import validate_video

ROOT = Path(__file__).parent


def collect_segments(episode_ids, episodes_root="episodes", skip_openers=True):
    paths = []
    for index, episode_id in enumerate(episode_ids):
        folder = Path(episodes_root) / episode_id / "segments"
        if not folder.is_dir():
            raise FileNotFoundError(f"missing segment directory: {folder}")
        clips = sorted(folder.glob("seg_*.mp4"))
        if not clips:
            raise FileNotFoundError(f"no rendered scene segments in {folder}")
        if index and skip_openers:
            clips = clips[1:]
        if not clips:
            raise ValueError(f"no segments remain after opener removal for {episode_id}")
        paths.extend(clips)
    return paths


def assemble(episode_ids, output, episodes_root="episodes", skip_openers=True):
    clips = collect_segments(episode_ids, episodes_root, skip_openers)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="deep-history-long-") as tmp:
        normalized = []
        for i, clip in enumerate(clips):
            target = Path(tmp) / f"scene_{i:04d}.mp4"
            # Portrait footage is presented intact over a softly blurred 16:9
            # duplicate. Audio is copied through the filter graph and re-encoded.
            vf = (
                "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,"
                "crop=1920:1080,gblur=sigma=32[bg];"
                "[0:v]scale=608:1080:force_original_aspect_ratio=decrease[fg];"
                "[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]"
            )
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(clip),
                "-filter_complex", vf, "-map", "[v]", "-map", "0:a?",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
                "-movflags", "+faststart", str(target)
            ], check=True, capture_output=True, text=True)
            normalized.append(target)

        concat_file = Path(tmp) / "concat.txt"
        concat_file.write_text("".join(f"file '{p.as_posix()}'\\n" for p in normalized))
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-f", "concat",
            "-safe", "0", "-i", str(concat_file), "-c", "copy",
            "-movflags", "+faststart", str(output)
        ], check=True, capture_output=True, text=True)

    qa = validate_video(str(output), 1920, 1080)
    return {"output": str(output), "scenes": len(clips), "qa": qa}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", nargs="+", required=True,
                        help="episode folder IDs in narrative order")
    parser.add_argument("--output", required=True)
    parser.add_argument("--episodes-root", default="episodes")
    parser.add_argument("--keep-repeat-hooks", action="store_true",
                        help="do not remove the first scene from later episodes")
    args = parser.parse_args()
    result = assemble(args.episodes, args.output, args.episodes_root,
                      skip_openers=not args.keep_repeat_hooks)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
