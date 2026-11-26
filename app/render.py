"""Production: scene images -> short clips with a slow camera move -> one MP4 (9:16, 1080x1920)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont

from .illustrate import draw_art
from .schemas import Beat, Brief

W, H, FPS = 1080, 1920, 30
ART_Y = 150  # top of the illustration panel
TEXT_Y = 1330  # centre of the on-screen text

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


def make_scene(beat: Beat, product: str, brief: Brief, out: Path, image: Path | None) -> Path:
    """One scene: gradient background, product label, illustration (or product photo), on-screen text."""
    bg_top = _hex(brief.background)
    bg_bot = tuple(max(0, v - 40) for v in bg_top)
    img = Image.new("RGB", (W, H), bg_top)
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        draw.line([(0, y), (W, y)], fill=tuple(int(bg_top[i] * (1 - t) + bg_bot[i] * t) for i in range(3)))

    draw.text((W // 2, 90), product, font=_font(FONT_REG, 44), fill=(230, 230, 230), anchor="mm")

    if image is not None:  # product photo takes the place of the illustration
        photo = Image.open(image).convert("RGBA")
        photo.thumbnail((W - 160, 1000))
        img.paste(photo, ((W - photo.width) // 2, ART_Y + 40), photo)
    elif brief.character:
        art = draw_art(beat.visual.pose, beat.visual.prop)
        img.paste(art, (0, ART_Y), art)

    font = _font(FONT_BOLD, 84)
    lines = _wrap(draw, beat.on_screen, font, W - 160)
    line_h = 104
    y0 = TEXT_Y - (len(lines) - 1) * line_h // 2
    for i, line in enumerate(lines):
        draw.text((W // 2, y0 + i * line_h), line, font=font, fill=(255, 255, 255), anchor="mm")
    accent = _hex(brief.accent)
    bar_y = y0 + len(lines) * line_h + 24
    draw.rectangle([(W // 2 - 90, bar_y), (W // 2 + 90, bar_y + 12)], fill=accent)

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


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, check=True, capture_output=True, cwd=cwd)


def _clip(card: Path, seg: Path, seconds: float) -> None:
    """Hold the scene picture for its duration with a slow zoom-in (camera move)."""
    frames = max(1, int(round(seconds * FPS)))
    zoom = f"zoompan=z='1+0.06*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS}"
    _run([
        "ffmpeg", "-y", "-loop", "1", "-t", f"{seconds:.3f}", "-i", str(card),
        "-vf", zoom, "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(seg),
    ])


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
    """Render brief to MP4. Returns (path, has_voice). Each scene's length follows its narration."""
    work.mkdir(parents=True, exist_ok=True)
    narration = " ".join(b.voiceover for b in brief.beats if b.voiceover)
    voice = make_voice(narration, lang, work / "voice.mp3") if use_voice else None
    has_voice = voice is not None

    if has_voice:
        total = probe_duration(voice)
        weights = [max(1, len(b.voiceover.split())) for b in brief.beats]
    else:
        total = float(target_seconds)
        weights = [1] * len(brief.beats)
    durations = [total * w / sum(weights) for w in weights]

    names: list[str] = []
    for i, (beat, d) in enumerate(zip(brief.beats, durations)):
        card = make_scene(beat, product, brief, work / f"scene_{i}.png", image)
        seg = work / f"seg_{i}.mp4"
        _clip(card, seg, d)
        names.append(seg.name)

    (work / "segments.txt").write_text("".join(f"file '{n}'\n" for n in names))
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "segments.txt", "-c", "copy", "video.mp4"], cwd=work)

    out.parent.mkdir(parents=True, exist_ok=True)
    silent = work / "video.mp4"
    if has_voice:
        _run(["ffmpeg", "-y", "-i", str(silent), "-i", str(voice),
              "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", str(out)])
    else:
        _run(["ffmpeg", "-y", "-i", str(silent), "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
              "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", str(out)])
    shutil.rmtree(work, ignore_errors=True)
    return out, has_voice
