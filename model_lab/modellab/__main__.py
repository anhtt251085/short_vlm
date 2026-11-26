"""Command line: python -m modellab <command> ...   (run from the model_lab folder)"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from . import eval_audio, eval_video
from .audio_data import AudioRules, build_audio_dataset
from .consent import Ledger
from .image_data import build_image_dataset
from .planners import load_yaml, plan_tts, plan_video, voice_matrix
from .registry import LicenceError, Registry
from .textnorm_vi import normalize
from .video_data import VideoRules, build_video_dataset

ROOT = Path(__file__).resolve().parent.parent
CONFIGS = ROOT / "configs"


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def cmd_models(a):
    reg = Registry.load(a.models)
    for e in reg.by_task(a.task):
        ok, reason = e.allowed(a.mode)
        mark = "OK     " if ok and reason == "ok" else ("RESEARCH" if ok else "BLOCKED")
        print(f"{mark}  {e.task:17} {e.id:24} {e.license}")
        if reason != "ok":
            print(f"         -> {reason}")


def cmd_normalize(a):
    print(normalize(a.text, dialect=a.dialect))


def cmd_audio_data(a):
    voices = load_yaml(a.voices)
    rules = AudioRules(sample_rate=a.sample_rate)
    summary = build_audio_dataset(a.input, Ledger.load(a.consent), voices["accents"], a.out,
                                  rules=rules, mode=a.mode, fix=a.fix)
    _print(summary)


def cmd_video_data(a):
    cfg = load_yaml(a.config)
    w, h = cfg["resolution"]
    rules = VideoRules(width=w, height=h, trigger=cfg.get("trigger", ""))
    summary = build_video_dataset(a.input, Ledger.load(a.consent), a.out, rules=rules,
                                  mode=cfg.get("mode", "commercial"), fix=a.fix)
    _print(summary)


def cmd_image_data(a):
    _print(build_image_dataset(a.sheets, Ledger.load(a.consent), a.out, mode=a.mode))


def cmd_plan_video(a):
    _print(plan_video(a.config, Registry.load(a.models), a.dataset, a.out))


def cmd_plan_tts(a):
    _print(plan_tts(a.config, Registry.load(a.models), a.dataset, a.voices, a.out))


def cmd_voices(a):
    tts_cfg = load_yaml(a.tts_config)
    rows = voice_matrix(a.voices, Ledger.load(a.consent), Registry.load(a.models),
                        vc_model=tts_cfg.get("vc_model"), manifest_path=a.manifest,
                        mode=tts_cfg.get("mode", "commercial"))
    if a.json:
        _print(rows)
        return
    print(f"{'accent':11} {'voice type':24} {'method':12} {'status':13} detail")
    for r in rows:
        print(f"{r['accent']:11} {r['voice_type']:24} {r['method']:12} {r['status']:13} {r['detail']}")


def cmd_eval_audio(a):
    transcribe = eval_audio.whisper_transcriber(a.whisper, a.language) if a.whisper else None
    _print(eval_audio.evaluate_clip(a.wav, a.script, language=a.language, dialect=a.dialect,
                                    transcribe=transcribe))


def cmd_eval_video(a):
    result = eval_video.evaluate_clip(a.video, a.reference, n_frames=a.frames)
    if a.narration:
        result["vlm_prompt"] = eval_video.vlm_checklist(a.narration, a.pose, a.prop)
    _print(result)


def cmd_doctor(a):
    checks = {"ffmpeg": bool(shutil.which("ffmpeg")), "ffprobe": bool(shutil.which("ffprobe"))}
    for mod in ("whisper", "torch"):
        try:
            __import__(mod)
            checks[mod] = True
        except ImportError:
            checks[mod] = False
    try:
        import torch
        checks["cuda_gpu"] = bool(torch.cuda.is_available())
    except ImportError:
        checks["cuda_gpu"] = False
    _print(checks)
    print("Data tools need ffmpeg and ffprobe. Training needs a CUDA GPU; whisper is optional for eval.")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="modellab", description="Data, licence, and training tools for our video and voice models.")
    sub = p.add_subparsers(dest="cmd", required=True)
    models_default = str(CONFIGS / "models.yaml")
    voices_default = str(CONFIGS / "voices.yaml")

    s = sub.add_parser("models", help="list base models and whether their licence allows our use")
    s.add_argument("--task", choices=["text_to_video", "text_to_speech", "voice_conversion"])
    s.add_argument("--mode", choices=["commercial", "research"], default="commercial")
    s.add_argument("--models", default=models_default)
    s.set_defaults(fn=cmd_models)

    s = sub.add_parser("normalize", help="normalise Vietnamese text for speech")
    s.add_argument("text")
    s.add_argument("--dialect", choices=["north", "south"], default="north")
    s.set_defaults(fn=cmd_normalize)

    s = sub.add_parser("audio-data", help="validate recordings and build a speech dataset")
    s.add_argument("--input", required=True, help="CSV: path,text,speaker_id,accent[,style]")
    s.add_argument("--consent", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--voices", default=voices_default)
    s.add_argument("--mode", choices=["commercial", "research"], default="commercial")
    s.add_argument("--sample-rate", type=int, default=24000)
    s.add_argument("--fix", action="store_true", help="convert audio to mono 16-bit at the target rate")
    s.set_defaults(fn=cmd_audio_data)

    s = sub.add_parser("video-data", help="validate clips and captions and build a video LoRA dataset")
    s.add_argument("--input", required=True, help="CSV: path,caption,source_id")
    s.add_argument("--consent", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--config", default=str(CONFIGS / "video_lora.yaml"))
    s.add_argument("--fix", action="store_true", help="crop, scale, and set frame rate to the target")
    s.set_defaults(fn=cmd_video_data)

    s = sub.add_parser("image-data", help="cut character sheets into a captioned image LoRA dataset")
    s.add_argument("--sheets", default=str(CONFIGS / "fox_sheets.yaml"))
    s.add_argument("--consent", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--mode", choices=["commercial", "research"], default="commercial")
    s.set_defaults(fn=cmd_image_data)

    s = sub.add_parser("plan-video", help="write a LoRA training job (clips or images) for a GPU machine")
    s.add_argument("--dataset", required=True)
    s.add_argument("--out", default=str(ROOT / "runs"))
    s.add_argument("--config", default=str(CONFIGS / "video_lora.yaml"))
    s.add_argument("--models", default=models_default)
    s.set_defaults(fn=cmd_plan_video)

    s = sub.add_parser("plan-tts", help="write a speech model fine-tuning job for a GPU machine")
    s.add_argument("--dataset", required=True)
    s.add_argument("--out", default=str(ROOT / "runs"))
    s.add_argument("--config", default=str(CONFIGS / "tts.yaml"))
    s.add_argument("--voices", default=voices_default)
    s.add_argument("--models", default=models_default)
    s.set_defaults(fn=cmd_plan_tts)

    s = sub.add_parser("voices", help="show the accent x voice type matrix and what is missing")
    s.add_argument("--consent", required=True)
    s.add_argument("--manifest", help="speech dataset manifest.jsonl, to count recorded minutes")
    s.add_argument("--voices", default=voices_default)
    s.add_argument("--tts-config", default=str(CONFIGS / "tts.yaml"))
    s.add_argument("--models", default=models_default)
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_voices)

    s = sub.add_parser("eval-audio", help="check a generated speech clip")
    s.add_argument("--wav", required=True)
    s.add_argument("--script", required=True, help="the text the clip should say")
    s.add_argument("--language", default="vi")
    s.add_argument("--dialect", choices=["north", "south"], default="north")
    s.add_argument("--whisper", help="Whisper model name to measure word error rate (optional)")
    s.set_defaults(fn=cmd_eval_audio)

    s = sub.add_parser("eval-video", help="check a generated clip against the character reference")
    s.add_argument("--video", required=True)
    s.add_argument("--reference", required=True)
    s.add_argument("--frames", type=int, default=6)
    s.add_argument("--narration", help="also print a VLM checklist prompt for this narration")
    s.add_argument("--pose")
    s.add_argument("--prop")
    s.set_defaults(fn=cmd_eval_video)

    s = sub.add_parser("doctor", help="check local tools and GPU")
    s.set_defaults(fn=cmd_doctor)

    a = p.parse_args(argv)
    try:
        a.fn(a)
    except LicenceError as e:
        print(f"Licence gate: {e}", file=sys.stderr)
        return 2
    except (ValueError, KeyError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except BrokenPipeError:  # output piped into head, etc.
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
