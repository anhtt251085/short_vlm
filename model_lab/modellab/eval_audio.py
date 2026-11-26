"""Evaluate generated speech.

CPU checks: duration, loudness, clipping, edge silence, speaking rate.
Intelligibility: word error rate (WER) between the script and a speech-recogniser transcript.
The recogniser is pluggable: pass any function path -> text (for example a Whisper wrapper).
Speaker similarity needs a speaker-embedding model; it is not included yet.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from .audio_data import AudioRules, check_audio, measure, read_wav
from .textnorm_vi import normalize as normalize_vi


def _edit_distance(a: list[str], b: list[str]) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, y in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y))
        prev = cur
    return prev[-1]


def _tokens(text: str) -> list[str]:
    cleaned = "".join(c.lower() if c.isalnum() or c.isspace() else " " for c in text)
    return cleaned.split()


def wer(reference: str, hypothesis: str) -> float:
    ref, hyp = _tokens(reference), _tokens(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return _edit_distance(ref, hyp) / len(ref)


def cer(reference: str, hypothesis: str) -> float:
    ref = [c for c in reference.lower() if not c.isspace()]
    hyp = [c for c in hypothesis.lower() if not c.isspace()]
    if not ref:
        return 0.0 if not hyp else 1.0
    return _edit_distance(ref, hyp) / len(ref)


def evaluate_clip(
    wav_path: str | Path,
    script: str,
    language: str = "vi",
    dialect: str = "north",
    transcribe: Callable[[str], str] | None = None,
    rules: AudioRules | None = None,
) -> dict:
    rules = rules or AudioRules()
    samples, sr, ch = read_wav(Path(wav_path))
    metrics = measure(samples, sr, rules)
    # Generated audio should already be in the target format, so format issues count.
    problems = check_audio(metrics, sr, ch, rules, fixed=False)
    result = {"file": str(wav_path), **metrics, "problems": problems}
    if transcribe is not None:
        hyp = transcribe(str(wav_path))
        ref = normalize_vi(script, dialect) if language == "vi" else script
        hyp_n = normalize_vi(hyp, dialect) if language == "vi" else hyp
        result.update({"transcript": hyp, "wer": round(wer(ref, hyp_n), 4), "cer": round(cer(ref, hyp_n), 4)})
    return result


def whisper_transcriber(model_name: str = "small", language: str = "vi") -> Callable[[str], str]:
    """Optional: requires `pip install openai-whisper` (and ideally a GPU)."""
    import whisper  # imported lazily so the rest of the package works without it

    model = whisper.load_model(model_name)
    return lambda path: model.transcribe(path, language=language)["text"]
