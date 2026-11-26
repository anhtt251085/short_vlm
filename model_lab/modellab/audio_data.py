"""Build a speech training dataset: validate recordings, normalise transcripts, enforce consent.

Input: a CSV with columns  path,text,speaker_id,accent[,style]
       (paths are relative to the CSV file)
Output (in out_dir):
  wavs/<id>.wav     accepted audio (converted to the target format when --fix is used)
  manifest.jsonl    accepted items with metrics
  rejects.jsonl     rejected items with reasons
  summary.json      minutes per accent and speaker
  metadata.csv      LJSpeech-style export   (id|raw text|normalised text)
  metadata.list     MeloTTS-style export    (path|speaker|LANG|text)
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import wave
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from .consent import Ledger, needed_scopes
from .textnorm_vi import normalize as normalize_vi


@dataclass
class AudioRules:
    sample_rate: int = 24000
    min_seconds: float = 1.0
    max_seconds: float = 15.0
    max_clip_ratio: float = 0.001
    max_edge_silence: float = 0.75
    silence_db: float = -40.0
    min_rms_db: float = -35.0
    min_chars_per_sec: float = 5.0
    max_chars_per_sec: float = 30.0


class AudioFormatError(ValueError):
    pass


def read_wav(path: Path) -> tuple[np.ndarray, int, int]:
    """Return (mono float samples in -1..1, sample rate, original channel count). PCM 16-bit only."""
    try:
        with wave.open(str(path), "rb") as w:
            if w.getsampwidth() != 2:
                raise AudioFormatError(f"{w.getsampwidth() * 8}-bit audio; expected 16-bit PCM")
            sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
            raw = w.readframes(n)
    except wave.Error as e:
        raise AudioFormatError(f"not a PCM WAV file ({e})") from e
    data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    return data, sr, ch


def convert(src: Path, dst: Path, sample_rate: int) -> None:
    """Convert any audio file to 16-bit mono WAV at the target rate."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-ac", "1", "-ar", str(sample_rate),
         "-sample_fmt", "s16", str(dst)],
        check=True, capture_output=True,
    )


def _db(x: float) -> float:
    return float(20 * np.log10(max(x, 1e-12)))


def measure(samples: np.ndarray, sr: int, rules: AudioRules) -> dict:
    duration = len(samples) / sr if sr else 0.0
    peak = float(np.max(np.abs(samples))) if len(samples) else 0.0
    clip_ratio = float(np.mean(np.abs(samples) >= 0.999)) if len(samples) else 0.0
    rms = float(np.sqrt(np.mean(samples ** 2))) if len(samples) else 0.0

    # Leading and trailing silence, measured in 10 ms frames.
    frame = max(1, int(sr * 0.01))
    n_frames = len(samples) // frame
    if n_frames:
        frames = samples[: n_frames * frame].reshape(n_frames, frame)
        frame_db = 20 * np.log10(np.sqrt(np.mean(frames ** 2, axis=1)) + 1e-12)
        loud = np.where(frame_db > rules.silence_db)[0]
        if len(loud):
            lead = loud[0] * frame / sr
            trail = (n_frames - 1 - loud[-1]) * frame / sr
        else:
            lead = trail = duration
    else:
        lead = trail = duration
    return {
        "duration": round(duration, 3), "peak": round(peak, 4), "clip_ratio": round(clip_ratio, 5),
        "rms_db": round(_db(rms), 2), "lead_silence": round(lead, 3), "trail_silence": round(trail, 3),
    }


def _speaking_rate(text: str, metrics: dict) -> float:
    letters = sum(1 for c in text if c.isalpha())
    voiced = max(0.1, metrics["duration"] - metrics["lead_silence"] - metrics["trail_silence"])
    return letters / voiced


def check_audio(metrics: dict, sr: int, channels: int, rules: AudioRules, fixed: bool) -> list[str]:
    problems = []
    if not fixed and sr != rules.sample_rate:
        problems.append(f"sample rate {sr} Hz, expected {rules.sample_rate} (use --fix)")
    if not fixed and channels != 1:
        problems.append(f"{channels} channels, expected mono (use --fix)")
    if metrics["duration"] < rules.min_seconds:
        problems.append(f"too short ({metrics['duration']}s < {rules.min_seconds}s)")
    if metrics["duration"] > rules.max_seconds:
        problems.append(f"too long ({metrics['duration']}s > {rules.max_seconds}s); split it")
    if metrics["clip_ratio"] > rules.max_clip_ratio:
        problems.append(f"clipping ({metrics['clip_ratio']:.3%} of samples)")
    if metrics["rms_db"] < rules.min_rms_db:
        problems.append(f"too quiet ({metrics['rms_db']} dBFS)")
    if max(metrics["lead_silence"], metrics["trail_silence"]) > rules.max_edge_silence:
        problems.append("long silence at start or end; trim it")
    return problems


def normalize_text(text: str, accent: str, accents: dict) -> str:
    info = accents.get(accent, {})
    if info.get("language") == "vi":
        return normalize_vi(text, dialect=info.get("dialect", "north"))
    return " ".join(text.split())


def build_audio_dataset(
    csv_path: str | Path,
    ledger: Ledger,
    accents: dict,
    out_dir: str | Path,
    rules: AudioRules | None = None,
    mode: str = "commercial",
    fix: bool = False,
    lang_codes: dict | None = None,
) -> dict:
    rules = rules or AudioRules()
    csv_path, out_dir = Path(csv_path), Path(out_dir)
    wav_dir = out_dir / "wavs"
    wav_dir.mkdir(parents=True, exist_ok=True)
    lang_codes = lang_codes or {"vi": "VI", "en": "EN"}
    scopes = needed_scopes("tts_training", mode)

    accepted, rejected = [], []
    with csv_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for i, row in enumerate(rows):
        speaker, accent = (row.get("speaker_id") or "").strip(), (row.get("accent") or "").strip()
        text = (row.get("text") or "").strip()
        src = (csv_path.parent / (row.get("path") or "")).resolve()
        item_id = f"{speaker or 'unknown'}_{i:05d}"
        reasons: list[str] = []

        ok, why = ledger.check_speaker(speaker, scopes)
        if not ok:
            reasons.append(why)
        if accent not in accents:
            reasons.append(f"unknown accent '{accent}'")
        else:
            rec = ledger.speakers.get(speaker)
            if rec and rec.accent and rec.accent != accent:
                reasons.append(f"accent '{accent}' does not match speaker's consented accent '{rec.accent}'")
        if not text:
            reasons.append("empty transcript")
        if not src.exists():
            reasons.append(f"file not found: {row.get('path')}")

        metrics: dict = {}
        dst = wav_dir / f"{item_id}.wav"
        if not reasons:
            try:
                if fix:
                    convert(src, dst, rules.sample_rate)
                    samples, sr, ch = read_wav(dst)
                else:
                    samples, sr, ch = read_wav(src)
                metrics = measure(samples, sr, rules)
                reasons += check_audio(metrics, sr, ch, rules, fixed=fix)
            except (AudioFormatError, subprocess.CalledProcessError) as e:
                reasons.append(f"unreadable audio: {e} (use --fix)" if not fix else f"conversion failed: {e}")

        norm = normalize_text(text, accent, accents) if text else ""
        if not reasons:
            rate = _speaking_rate(norm, metrics)
            metrics["chars_per_sec"] = round(rate, 2)
            if not (rules.min_chars_per_sec <= rate <= rules.max_chars_per_sec):
                reasons.append(f"speaking rate {rate:.1f} chars/s looks wrong; check the transcript matches the audio")

        record = {"id": item_id, "source": row.get("path"), "speaker": speaker, "accent": accent,
                  "style": (row.get("style") or "neutral").strip(), "text_raw": text, "text": norm, **metrics}
        if reasons:
            if dst.exists():
                dst.unlink()
            rejected.append({**record, "reasons": reasons})
            continue
        if not fix:
            shutil.copyfile(src, dst)
        record["audio"] = f"wavs/{dst.name}"
        accepted.append(record)

    _write_jsonl(out_dir / "manifest.jsonl", accepted)
    _write_jsonl(out_dir / "rejects.jsonl", rejected)
    _export_ljspeech(out_dir, accepted)
    _export_melotts(out_dir, accepted, accents, lang_codes)
    summary = summarize(accepted, rejected)
    summary["mode"] = mode
    summary["rules"] = asdict(rules)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def summarize(accepted: list[dict], rejected: list[dict]) -> dict:
    by_accent: dict[str, float] = {}
    by_speaker: dict[str, float] = {}
    for r in accepted:
        by_accent[r["accent"]] = by_accent.get(r["accent"], 0.0) + r["duration"] / 60
        by_speaker[r["speaker"]] = by_speaker.get(r["speaker"], 0.0) + r["duration"] / 60
    return {
        "accepted": len(accepted),
        "rejected": len(rejected),
        "minutes_total": round(sum(by_accent.values()), 2),
        "minutes_by_accent": {k: round(v, 2) for k, v in sorted(by_accent.items())},
        "minutes_by_speaker": {k: round(v, 2) for k, v in sorted(by_speaker.items())},
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _export_ljspeech(out_dir: Path, rows: list[dict]) -> None:
    with (out_dir / "metadata.csv").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(f"{r['id']}|{r['text_raw']}|{r['text']}\n")


def _export_melotts(out_dir: Path, rows: list[dict], accents: dict, lang_codes: dict) -> None:
    with (out_dir / "metadata.list").open("w", encoding="utf-8") as f:
        for r in rows:
            lang = lang_codes.get(accents[r["accent"]]["language"], "EN")
            # Speaker names carry the accent so one model can learn several accents.
            f.write(f"{(out_dir / r['audio']).resolve()}|{r['speaker']}|{lang}|{r['text']}\n")


def load_manifest(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
