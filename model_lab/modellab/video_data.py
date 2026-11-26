"""Build a video LoRA dataset: validate clips and captions, enforce rights, export trainer layout.

Input: a CSV with columns  path,caption,source_id   (paths relative to the CSV)
Output (in out_dir):
  videos/<id>.mp4 + videos/<id>.txt   clip and caption side by side (musubi-tuner layout)
  manifest.jsonl, rejects.jsonl, summary.json
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path

from .consent import Ledger, needed_scopes


@dataclass
class VideoRules:
    width: int = 544
    height: int = 960
    aspect_tolerance: float = 0.03
    min_fps: float = 15.0
    max_fps: float = 60.0
    target_fps: int = 16
    min_seconds: float = 1.0
    max_seconds: float = 10.0
    min_caption_words: int = 5
    max_caption_words: int = 80
    trigger: str = "mntr fox"


def probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    info = json.loads(out)
    streams = info.get("streams") or []
    if not streams:
        raise ValueError("no video stream")
    s = streams[0]
    fps = float(Fraction(s.get("r_frame_rate", "0/1"))) if s.get("r_frame_rate") not in (None, "0/0") else 0.0
    return {
        "width": int(s["width"]), "height": int(s["height"]), "fps": round(fps, 3),
        "duration": round(float(info.get("format", {}).get("duration", 0.0)), 3),
    }


def reencode(src: Path, dst: Path, rules: VideoRules) -> None:
    """Crop to the target aspect, scale to the target size and frame rate, drop audio."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    vf = (f"scale={rules.width}:{rules.height}:force_original_aspect_ratio=increase,"
          f"crop={rules.width}:{rules.height},fps={rules.target_fps}")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", vf, "-an",
         "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(dst)],
        check=True, capture_output=True,
    )


def check_clip(info: dict, rules: VideoRules) -> list[str]:
    problems = []
    want = rules.width / rules.height
    have = info["width"] / info["height"] if info["height"] else 0
    if abs(have - want) / want > rules.aspect_tolerance:
        problems.append(f"aspect {info['width']}x{info['height']} does not match {rules.width}x{rules.height} (use --fix)")
    if info["width"] < rules.width or info["height"] < rules.height:
        problems.append(f"resolution {info['width']}x{info['height']} below {rules.width}x{rules.height}")
    if not (rules.min_fps <= info["fps"] <= rules.max_fps):
        problems.append(f"frame rate {info['fps']} outside {rules.min_fps}-{rules.max_fps}")
    if info["duration"] < rules.min_seconds:
        problems.append(f"too short ({info['duration']}s)")
    if info["duration"] > rules.max_seconds:
        problems.append(f"too long ({info['duration']}s > {rules.max_seconds}s); cut into shorter clips")
    return problems


def check_caption(caption: str, rules: VideoRules) -> list[str]:
    problems = []
    words = caption.split()
    if len(words) < rules.min_caption_words:
        problems.append(f"caption too short ({len(words)} words)")
    if len(words) > rules.max_caption_words:
        problems.append(f"caption too long ({len(words)} words)")
    if rules.trigger and rules.trigger.lower() not in caption.lower():
        problems.append(f"caption is missing the trigger phrase '{rules.trigger}'")
    return problems


def build_video_dataset(
    csv_path: str | Path,
    ledger: Ledger,
    out_dir: str | Path,
    rules: VideoRules | None = None,
    mode: str = "commercial",
    fix: bool = False,
) -> dict:
    rules = rules or VideoRules()
    csv_path, out_dir = Path(csv_path), Path(out_dir)
    vid_dir = out_dir / "videos"
    vid_dir.mkdir(parents=True, exist_ok=True)
    scopes = needed_scopes("video_training", mode)

    with csv_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    accepted, rejected = [], []
    for i, row in enumerate(rows):
        caption = " ".join((row.get("caption") or "").split())
        source_id = (row.get("source_id") or "").strip()
        src = (csv_path.parent / (row.get("path") or "")).resolve()
        item_id = f"clip_{i:05d}"
        dst = vid_dir / f"{item_id}.mp4"
        reasons: list[str] = []

        ok, why = ledger.check_asset(source_id, scopes)
        if not ok:
            reasons.append(why)
        reasons += check_caption(caption, rules)
        if not src.exists():
            reasons.append(f"file not found: {row.get('path')}")

        info: dict = {}
        if not reasons:
            try:
                if fix:
                    reencode(src, dst, rules)
                    info = probe(dst)
                else:
                    info = probe(src)
                reasons += check_clip(info, rules)
            except (subprocess.CalledProcessError, ValueError, KeyError) as e:
                reasons.append(f"unreadable video: {e}")

        record = {"id": item_id, "source": row.get("path"), "source_id": source_id, "caption": caption, **info}
        if reasons:
            if dst.exists():
                dst.unlink()
            rejected.append({**record, "reasons": reasons})
            continue
        if not fix:
            shutil.copyfile(src, dst)
        (vid_dir / f"{item_id}.txt").write_text(caption + "\n", encoding="utf-8")
        record["video"] = f"videos/{dst.name}"
        accepted.append(record)

    for name, items in (("manifest.jsonl", accepted), ("rejects.jsonl", rejected)):
        with (out_dir / name).open("w", encoding="utf-8") as f:
            for r in items:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary = {
        "accepted": len(accepted), "rejected": len(rejected),
        "seconds_total": round(sum(r["duration"] for r in accepted), 2),
        "mode": mode, "rules": asdict(rules),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary
