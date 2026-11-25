"""Production: cards -> segments -> video with optional voiceover (9:16, 1080x1920)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont

from .schemas import Brief

W, H, FPS = 1080, 1920, 30

FONT_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
FONT_REG = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _font(paths: list[str], size: int) -> ImageFont.FreeTypeFont:
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size=size)


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


def make_card(text: str, product: str, brief: Brief, out: Path, image: Path | None) -> Path:
    bg_top = _hex(brief.background)
    bg_bot = tuple(max(0, v - 40) for v in bg_top)
    img = Image.new("RGB", (W, H), bg_top)
    draw = ImageDraw.Draw(img)
    for y in range(H):  # vertical gradient
        t = y / H
        col = tuple(int(bg_top[i] * (1 - t) + bg_bot[i] * t) for i in range(3))
        draw.line([(0, y), (W, y)], fill=col)

    if image is not None:
        photo = Image.open(image).convert("RGBA")
        photo.thumbnail((W - 160, 900))
        x = (W - photo.width) // 2
        img.paste(photo, (x, 200), photo)  # alpha mask keeps transparent PNG backgrounds
        text_y = 1180
    else:
        text_y = 760

    label_font = _font(FONT_REG, 44)
    draw.text((W // 2, 90), product, font=label_font, fill=(230, 230, 230), anchor="mm")

    font = _font(FONT_BOLD, 88)
    lines = _wrap(draw, text, font, W - 160)
    line_h = 110
    y0 = text_y - (len(lines) - 1) * line_h // 2
    for i, line in enumerate(lines):
        draw.text((W // 2, y0 + i * line_h), line, font=font, fill=(255, 255, 255), anchor="mm")

    accent = _hex(brief.accent)
    draw.rectangle([(W // 2 - 90, y0 + len(lines) * line_h + 30), (W // 2 + 90, y0 + len(lines) * line_h + 42)], fill=accent)

    img.save(out)
    return out


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(json.loads(out)["format"]["duration"])


def make_voice(text: str, lang: str, out: Path) -> Path | None:
    """Text-to-speech via gTTS (needs internet). Returns None if unavailable."""
    try:
        gTTS(text=text, lang=lang).save(str(out))
        return out
    except Exception:
        return None


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def render_video(
    brief: Brief,
    product: str,
    lang: str,
    work: Path,
    out: Path,
    target_seconds: int,
    image: Path | None = None,
    use_voice: bool = True,
) -> tuple[Path, bool]:
    """Render brief to MP4. Returns (path, has_voice)."""
    work.mkdir(parents=True, exist_ok=True)
    voice = make_voice(" ".join(b.voiceover for b in brief.beats if b.voiceover), lang, work / "voice.mp3") if use_voice else None
    has_voice = voice is not None

    # Per-beat durations: proportional to word count if we have voice, else equal split.
    if has_voice:
        total = probe_duration(voice)
        weights = [max(1, len(b.voiceover.split())) for b in brief.beats]
    else:
        total = float(target_seconds)
        weights = [1] * len(brief.beats)
    durations = [total * w / sum(weights) for w in weights]

    segs: list[Path] = []
    for i, (beat, d) in enumerate(zip(brief.beats, durations)):
        card = make_card(beat.on_screen, product, brief, work / f"card_{i}.png", image)
        seg = work / f"seg_{i}.mp4"
        _run([
            "ffmpeg", "-y", "-loop", "1", "-i", str(card), "-t", f"{d:.3f}",
            "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            str(seg),
        ])
        segs.append(seg)

    # Concat from the work dir so the list's relative file names resolve.
    (work / "segments.txt").write_text("".join(f"file '{s.name}'\n" for s in segs))
    silent = work / "video.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "segments.txt", "-c", "copy", "video.mp4"],
                   cwd=work, check=True, capture_output=True)

    out.parent.mkdir(parents=True, exist_ok=True)
    if has_voice:
        _run([
            "ffmpeg", "-y", "-i", str(silent), "-i", str(voice),
            "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", str(out),
        ])
    else:
        _run([
            "ffmpeg", "-y", "-i", str(silent), "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", str(out),
        ])
    shutil.rmtree(work, ignore_errors=True)
    return out, has_voice
