"""Evaluate generated clips for character consistency.

CPU proxies (cheap, imperfect):
  palette  - colour histogram overlap with the reference character image (suit, skin, tie colours)
  shape    - perceptual-hash similarity to the reference
  drift    - how much frames differ from each other within a clip (identity stability)
These catch obvious failures (wrong colours, a different character, flicker). They cannot judge
pose or expression; for that, send `vlm_checklist()` with sampled frames to a VLM, or review by hand.
"""

from __future__ import annotations

import subprocess
import tempfile
from itertools import combinations
from pathlib import Path

import numpy as np
from PIL import Image


def sample_frames(video: str | Path, n: int = 6) -> list[Image.Image]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    duration = float(out or 0)
    if duration <= 0:
        raise ValueError(f"cannot read duration of {video}")
    frames = []
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(n):
            t = duration * (i + 0.5) / n
            png = Path(tmp) / f"f{i}.png"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video),
                            "-frames:v", "1", str(png)], check=True, capture_output=True)
            frames.append(Image.open(png).convert("RGB").copy())
    return frames


def _hist(img: Image.Image, bins: int = 8) -> np.ndarray:
    arr = np.asarray(img.resize((128, 128))).reshape(-1, 3) // (256 // bins)
    idx = arr[:, 0] * bins * bins + arr[:, 1] * bins + arr[:, 2]
    h = np.bincount(idx, minlength=bins ** 3).astype(np.float64)
    return h / h.sum()


def palette_similarity(a: Image.Image, b: Image.Image) -> float:
    """Histogram intersection, 0..1."""
    return float(np.minimum(_hist(a), _hist(b)).sum())


def _ahash(img: Image.Image, size: int = 16) -> np.ndarray:
    g = np.asarray(img.convert("L").resize((size, size)), dtype=np.float64)
    return g > g.mean()


def shape_similarity(a: Image.Image, b: Image.Image) -> float:
    ha, hb = _ahash(a), _ahash(b)
    return float(1 - np.count_nonzero(ha != hb) / ha.size)


def evaluate_clip(video: str | Path, reference: str | Path, n_frames: int = 6,
                  min_palette: float = 0.5, min_shape: float = 0.6, min_stability: float = 0.7) -> dict:
    ref = Image.open(reference).convert("RGB")
    frames = sample_frames(video, n_frames)
    palette = [palette_similarity(f, ref) for f in frames]
    shape = [shape_similarity(f, ref) for f in frames]
    pairs = [shape_similarity(a, b) for a, b in combinations(frames, 2)] or [1.0]
    result = {
        "file": str(video),
        "palette_mean": round(float(np.mean(palette)), 3),
        "shape_mean": round(float(np.mean(shape)), 3),
        "stability": round(float(np.mean(pairs)), 3),
    }
    problems = []
    if result["palette_mean"] < min_palette:
        problems.append("colours differ from the reference character")
    if result["shape_mean"] < min_shape:
        problems.append("overall shape differs from the reference character")
    if result["stability"] < min_stability:
        problems.append("frames change a lot within the clip (possible identity drift or flicker)")
    result["problems"] = problems
    return result


def vlm_checklist(narration: str, pose: str | None = None, prop: str | None = None) -> str:
    """Prompt for a VLM judge, to be sent together with the sampled frames."""
    checks = [
        "Is the same cartoon presenter shown in every frame (same face, glasses, hair, navy suit, red tie)?",
        "Does the character look like the reference image provided?",
    ]
    if pose:
        checks.append(f"Is the presenter in the pose: {pose}?")
    if prop:
        checks.append(f"Is this prop clearly visible: {prop}?")
    checks += [
        f"Does the scene match this narration: \"{narration}\"?",
        "Is there any distortion, extra limbs, melted faces, or unreadable text?",
    ]
    lines = "\n".join(f"{i}. {q}" for i, q in enumerate(checks, 1))
    return ("You are checking frames from a short video against a character reference.\n"
            f"Answer each question with yes or no and one short reason.\n{lines}\n"
            "Finish with PASS if every answer is acceptable, otherwise FAIL.")
