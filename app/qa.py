"""Automated checks on a rendered video (no model needed).

A VLM-based frame check can be added later; these checks catch the common
technical failures: wrong aspect ratio, too long/short, missing audio.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

MAX_SECONDS = 60
MIN_SECONDS = 5
MAX_BYTES = 287 * 1024 * 1024  # common platform upload limit


def check_video(path: Path, expect_voice: bool) -> list[dict]:
    info = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_type,width,height",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout)
    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    duration = float(info["format"]["duration"])
    size = int(info["format"]["size"])

    checks = [
        {"name": "vertical_1080x1920", "ok": bool(video and video["width"] == 1080 and video["height"] == 1920)},
        {"name": "duration_in_range", "ok": MIN_SECONDS <= duration <= MAX_SECONDS, "value": round(duration, 2)},
        {"name": "has_audio_track", "ok": audio is not None},
        {"name": "size_under_limit", "ok": size <= MAX_BYTES, "value": size},
    ]
    if expect_voice:
        checks.append({"name": "voiceover_present", "ok": audio is not None})
    return checks
