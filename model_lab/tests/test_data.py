import csv
import json

import yaml

from conftest import make_clip, make_wav
from modellab.audio_data import build_audio_dataset
from modellab.consent import Ledger
from modellab.video_data import VideoRules, build_video_dataset

TEXT = "Xin chào các bạn, hôm nay chúng ta học kinh doanh"


def _write_csv(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path


def _reasons(out_dir):
    rows = [json.loads(l) for l in (out_dir / "rejects.jsonl").read_text(encoding="utf-8").splitlines()]
    return {r["source"]: " | ".join(r["reasons"]) for r in rows}


def test_audio_dataset_accepts_good_and_explains_rejects(tmp_path, ledger_path, voices_path):
    src = tmp_path / "rec"
    make_wav(src / "good.wav")
    make_wav(src / "clipped.wav", clip=True)
    make_wav(src / "short.wav", seconds=0.4)
    make_wav(src / "stereo44k.wav", sr=44100, channels=2)
    make_wav(src / "silent_edges.wav", silence=1.5)
    csv_path = _write_csv(tmp_path / "data.csv", ["path", "text", "speaker_id", "accent"], [
        ["rec/good.wav", "Giá 1.500.000đ cho khóa học", "spk_north_m01", "vi-north"],
        ["rec/clipped.wav", TEXT, "spk_north_m01", "vi-north"],
        ["rec/short.wav", TEXT, "spk_north_m01", "vi-north"],
        ["rec/stereo44k.wav", TEXT, "spk_north_m01", "vi-north"],
        ["rec/silent_edges.wav", TEXT, "spk_north_m01", "vi-north"],
        ["rec/good.wav", TEXT, "spk_research_only", "vi-south"],
        ["rec/good.wav", TEXT, "spk_north_m01", "vi-south"],
        ["rec/good.wav", TEXT * 6, "spk_north_m01", "vi-north"],
        ["rec/missing.wav", TEXT, "spk_north_m01", "vi-north"],
    ])
    accents = yaml.safe_load(voices_path.read_text(encoding="utf-8"))["accents"]
    out = tmp_path / "out"
    summary = build_audio_dataset(csv_path, Ledger.load(ledger_path), accents, out)

    assert summary["accepted"] == 1
    manifest = [json.loads(l) for l in (out / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    assert manifest[0]["text"] == "Giá một triệu năm trăm nghìn đồng cho khóa học"
    assert (out / manifest[0]["audio"]).exists()

    reasons = _reasons(out)
    assert "clipping" in reasons["rec/clipped.wav"]
    assert "too short" in reasons["rec/short.wav"]
    assert "sample rate 44100" in reasons["rec/stereo44k.wav"] and "channels" in reasons["rec/stereo44k.wav"]
    assert "silence" in reasons["rec/silent_edges.wav"]
    assert "file not found" in reasons["rec/missing.wav"]

    lines = (out / "metadata.list").read_text(encoding="utf-8").splitlines()
    assert lines[0].split("|")[1:3] == ["spk_north_m01", "VI"]
    assert (out / "metadata.csv").read_text(encoding="utf-8").startswith(manifest[0]["id"] + "|")


def test_audio_consent_accent_and_transcript_checks(tmp_path, ledger_path, voices_path):
    make_wav(tmp_path / "a.wav")
    csv_path = _write_csv(tmp_path / "d.csv", ["path", "text", "speaker_id", "accent"], [
        ["a.wav", TEXT, "spk_research_only", "vi-south"],
        ["a.wav", TEXT, "spk_north_m01", "vi-south"],
        ["a.wav", TEXT * 6, "spk_north_m01", "vi-north"],
    ])
    accents = yaml.safe_load(voices_path.read_text(encoding="utf-8"))["accents"]
    out = tmp_path / "out"
    build_audio_dataset(csv_path, Ledger.load(ledger_path), accents, out)
    rejects = [json.loads(l) for l in (out / "rejects.jsonl").read_text(encoding="utf-8").splitlines()]
    assert "commercial_use" in " ".join(rejects[0]["reasons"])
    assert "does not match" in " ".join(rejects[1]["reasons"])
    assert "speaking rate" in " ".join(rejects[2]["reasons"])


def test_audio_fix_converts_format(tmp_path, ledger_path, voices_path):
    make_wav(tmp_path / "s.wav", sr=44100, channels=2)
    csv_path = _write_csv(tmp_path / "d.csv", ["path", "text", "speaker_id", "accent"],
                          [["s.wav", TEXT, "spk_north_m01", "vi-north"]])
    accents = yaml.safe_load(voices_path.read_text(encoding="utf-8"))["accents"]
    summary = build_audio_dataset(csv_path, Ledger.load(ledger_path), accents, tmp_path / "out", fix=True)
    assert summary["accepted"] == 1
    assert summary["minutes_by_speaker"]["spk_north_m01"] > 0


def test_video_dataset(tmp_path, ledger_path):
    make_clip(tmp_path / "v.mp4")
    make_clip(tmp_path / "wide.mp4", w=640, h=480)
    cap = "mntr fox points at a glowing lightbulb and smiles"
    csv_path = _write_csv(tmp_path / "c.csv", ["path", "caption", "source_id"], [
        ["v.mp4", cap, "renders"],
        ["wide.mp4", cap, "renders"],
        ["v.mp4", "a man points at a lightbulb and smiles", "renders"],
        ["v.mp4", cap, "stock_footage"],
    ])
    out = tmp_path / "out"
    summary = build_video_dataset(csv_path, Ledger.load(ledger_path), out, VideoRules())
    assert summary["accepted"] == 1
    assert (out / "videos" / "clip_00000.txt").read_text(encoding="utf-8").strip() == cap
    rejects = [json.loads(l) for l in (out / "rejects.jsonl").read_text(encoding="utf-8").splitlines()]
    joined = [" ".join(r["reasons"]) for r in rejects]
    assert "aspect" in joined[0]
    assert "trigger phrase" in joined[1]
    assert "no rights record" in joined[2]

    fixed = build_video_dataset(csv_path, Ledger.load(ledger_path), tmp_path / "fixed", VideoRules(), fix=True)
    assert fixed["accepted"] == 2  # the wide clip is cropped and scaled to 544x960
