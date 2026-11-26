import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CONFIGS = ROOT / "configs"


def make_wav(path: Path, sr=24000, seconds=3.0, channels=1, amp=0.3, clip=False, silence=0.0):
    t = np.arange(int(sr * seconds)) / sr
    tone = amp * np.sin(2 * np.pi * 220 * t) * (1 + 0.3 * np.sin(2 * np.pi * 3 * t))
    if clip:
        tone = np.clip(tone * 10, -1, 1)
    if silence:
        pad = np.zeros(int(sr * silence))
        tone = np.concatenate([pad, tone, pad])
    data = (np.clip(tone, -1, 1) * 32767).astype("<i2")
    if channels > 1:
        data = np.repeat(data[:, None], channels, axis=1).reshape(-1)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())
    return path


def make_clip(path: Path, w=544, h=960, fps=16, seconds=2.0, source=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if source is None:
        inp = ["-f", "lavfi", "-i", f"testsrc=size={w}x{h}:rate={fps}"]
    else:
        inp = ["-loop", "1", "-framerate", str(fps), "-i", str(source)]
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inp, "-t", str(seconds),
                    "-vf", f"scale={w}:{h}", "-pix_fmt", "yuv420p", "-c:v", "libx264", str(path)],
                   check=True, capture_output=True)
    return path


LEDGER = """
speakers:
  - id: spk_north_m01
    accent: vi-north
    voice_types: [presenter-male-warm]
    signed: 2026-01-01
    scopes: [tts_training, voice_conversion, commercial_use]
  - id: spk_research_only
    accent: vi-south
    voice_types: [presenter-female-bright]
    signed: 2026-01-01
    scopes: [tts_training]
  - id: spk_revoked
    accent: vi-north
    voice_types: [presenter-female-bright]
    signed: 2026-01-01
    revoked: true
    scopes: [tts_training, commercial_use]
assets:
  - id: renders
    kind: video
    source: own_render
    scopes: [video_training, commercial_use]
"""


@pytest.fixture
def ledger_path(tmp_path):
    p = tmp_path / "consent.yaml"
    p.write_text(LEDGER, encoding="utf-8")
    return p


@pytest.fixture
def voices_path():
    return CONFIGS / "voices.yaml"


@pytest.fixture
def models_path():
    return CONFIGS / "models.yaml"
