"""Shared, dependency-free FFmpeg quality controls for studio renderers.

Defaults target vertical 1080x1920 H.264/BT.709 output. Override with
STUDIO_VIDEO_WIDTH, STUDIO_VIDEO_HEIGHT, STUDIO_VIDEO_CRF and
STUDIO_VIDEO_PRESET when runner capacity requires it.
"""
import json
import os
import subprocess

VIDEO_WIDTH = int(os.environ.get("STUDIO_VIDEO_WIDTH", "1080"))
VIDEO_HEIGHT = int(os.environ.get("STUDIO_VIDEO_HEIGHT", "1920"))


def encoder_args(fps=30, crf=None):
    """Return consistent H.264 settings; CRF controls quality, not a fixed bitrate."""
    quality = int(crf if crf is not None else os.environ.get("STUDIO_VIDEO_CRF", "19"))
    if not 15 <= quality <= 28:
        raise ValueError("STUDIO_VIDEO_CRF must be between 15 and 28")
    preset = os.environ.get("STUDIO_VIDEO_PRESET", "medium")
    if preset not in {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow"}:
        raise ValueError("Unsupported STUDIO_VIDEO_PRESET")
    return [
        "-c:v", "libx264", "-preset", preset, "-crf", str(quality),
        "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(fps),
        "-color_primaries", "bt709", "-color_trc", "bt709",
        "-colorspace", "bt709",
    ]


def probe_video(path):
    """Read stream metadata using ffprobe; raises on missing/corrupt media."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def validate_video(path, width=VIDEO_WIDTH, height=VIDEO_HEIGHT, min_fps=24):
    """Fail closed unless output has expected dimensions, H.264 video and audio."""
    data = probe_video(path)
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not video or not audio:
        raise RuntimeError(f"render QA failed: missing video or audio stream: {path}")
    if (int(video.get("width", 0)), int(video.get("height", 0))) != (width, height):
        raise RuntimeError(
            f"render QA failed: expected {width}x{height}, got "
            f"{video.get('width')}x{video.get('height')}: {path}"
        )
    if video.get("codec_name") != "h264":
        raise RuntimeError(f"render QA failed: expected H.264, got {video.get('codec_name')}")
    if video.get("pix_fmt") != "yuv420p":
        raise RuntimeError(f"render QA failed: expected yuv420p, got {video.get('pix_fmt')}")
    duration = float(data.get("format", {}).get("duration") or 0)
    if duration <= 0:
        raise RuntimeError(f"render QA failed: invalid duration: {path}")
    return {
        "width": width, "height": height, "codec": "h264",
        "duration": duration, "audio": True,
    }
