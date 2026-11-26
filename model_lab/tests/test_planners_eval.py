import tomllib

import pytest
import yaml
from PIL import Image

from conftest import make_clip, make_wav
from modellab import eval_audio, eval_video
from modellab.audio_data import build_audio_dataset
from modellab.consent import Ledger
from modellab.planners import plan_tts, plan_video, voice_matrix
from modellab.registry import LicenceError, Registry


def _video_dataset(tmp_path):
    vids = tmp_path / "ds" / "videos"
    make_clip(vids / "clip_00000.mp4")
    (vids / "clip_00000.txt").write_text("mntr fox waves at the camera happily\n", encoding="utf-8")
    return tmp_path / "ds"


def _video_cfg(tmp_path, **overrides):
    cfg = yaml.safe_load(open("configs/video_lora.yaml", encoding="utf-8").read())
    cfg.update(overrides)
    p = tmp_path / "video.yaml"
    p.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return p


@pytest.fixture(autouse=True)
def _cwd(monkeypatch):
    from conftest import ROOT
    monkeypatch.chdir(ROOT)


def test_plan_video_writes_trainer_files(tmp_path, models_path):
    plan = plan_video(_video_cfg(tmp_path), Registry.load(models_path), _video_dataset(tmp_path), tmp_path / "runs")
    run = tmp_path / "runs" / "fox-pilot-v1"
    ds = tomllib.loads((run / "dataset.toml").read_text(encoding="utf-8"))
    assert ds["general"]["resolution"] == [544, 960]
    assert ds["datasets"][0]["video_directory"].endswith("ds/videos")
    script = (run / "run.sh").read_text(encoding="utf-8")
    assert "--task t2v-1.3B" in script and "--network_dim 32" in script and "--dit_high_noise" not in script
    assert plan["clips"] == 1 and plan["cost"]["est_cost_usd"] is None


def test_plan_video_wan22_needs_high_noise_and_costs(tmp_path, models_path):
    cfg = _video_cfg(tmp_path, base_model="wan2.2-t2v-a14b")
    with pytest.raises(ValueError, match="dit_high_noise"):
        plan_video(cfg, Registry.load(models_path), _video_dataset(tmp_path), tmp_path / "runs")
    base = yaml.safe_load(open("configs/video_lora.yaml", encoding="utf-8"))
    cfg = _video_cfg(tmp_path, base_model="wan2.2-t2v-a14b",
                     paths={**base["paths"], "dit_high_noise": "/m/high.safetensors"},
                     gpu={"name": "H100", "est_hours": 10, "hourly_usd": 1.89})
    plan = plan_video(cfg, Registry.load(models_path), _video_dataset(tmp_path), tmp_path / "runs")
    script = (tmp_path / "runs" / "fox-pilot-v1" / "run.sh").read_text(encoding="utf-8")
    assert "--task t2v-A14B" in script and '--dit_high_noise "/m/high.safetensors"' in script
    assert plan["cost"]["est_cost_usd"] == 18.9


def test_plan_video_licence_gate(tmp_path, models_path):
    with pytest.raises(LicenceError):
        plan_video(_video_cfg(tmp_path, base_model="ltx-video"), Registry.load(models_path),
                   _video_dataset(tmp_path), tmp_path / "runs")


def _speech_dataset(tmp_path, ledger_path, voices_path):
    make_wav(tmp_path / "a.wav")
    (tmp_path / "d.csv").write_text("path,text,speaker_id,accent\n"
                                    "a.wav,Xin chào các bạn hôm nay học kinh doanh,spk_north_m01,vi-north\n",
                                    encoding="utf-8")
    accents = yaml.safe_load(voices_path.read_text(encoding="utf-8"))["accents"]
    build_audio_dataset(tmp_path / "d.csv", Ledger.load(ledger_path), accents, tmp_path / "speech")
    return tmp_path / "speech"


def test_plan_tts_melotts(tmp_path, ledger_path, voices_path, models_path):
    ds = _speech_dataset(tmp_path, ledger_path, voices_path)
    plan = plan_tts("configs/tts.yaml", Registry.load(models_path), ds, voices_path, tmp_path / "runs")
    script = (tmp_path / "runs" / "vi-voices-pilot-v1" / "run.sh").read_text(encoding="utf-8")
    assert "preprocess_text.py --metadata" in script and "train.sh" in script
    assert plan["warnings"] and "spk_north_m01" in plan["warnings"][0]


def test_plan_tts_gates(tmp_path, ledger_path, voices_path, models_path):
    ds = _speech_dataset(tmp_path, ledger_path, voices_path)
    cfg = tmp_path / "tts.yaml"
    cfg.write_text("run_name: r\nmode: commercial\nbase_model: vieneu-tts-v3-turbo\n", encoding="utf-8")
    with pytest.raises(LicenceError):
        plan_tts(cfg, Registry.load(models_path), ds, voices_path, tmp_path / "runs")
    cfg.write_text("run_name: r\nmode: research\nbase_model: vieneu-tts-v3-turbo\n", encoding="utf-8")
    plan_tts(cfg, Registry.load(models_path), ds, voices_path, tmp_path / "runs")
    assert "exit 1" in (tmp_path / "runs" / "r" / "run.sh").read_text(encoding="utf-8")
    cfg.write_text("run_name: r\nmode: research\nbase_model: melotts-english\n", encoding="utf-8")
    with pytest.raises(ValueError, match="languages"):
        plan_tts(cfg, Registry.load(models_path), ds, voices_path, tmp_path / "runs")


def test_voice_matrix(tmp_path, ledger_path, voices_path, models_path):
    ds = _speech_dataset(tmp_path, ledger_path, voices_path)
    reg, led = Registry.load(models_path), Ledger.load(ledger_path)
    rows = {(r["accent"], r["voice_type"]): r for r in
            voice_matrix(voices_path, led, reg, vc_model="openvoice-v2", manifest_path=ds / "manifest.jsonl")}
    assert rows[("vi-north", "presenter-male-warm")]["status"] == "need_data"
    assert rows[("vi-south", "presenter-male-warm")]["status"] == "need_speaker"
    assert rows[("vi-north", "mentor-older-calm")]["status"] == "blocked"
    research = {(r["accent"], r["voice_type"]): r for r in
                voice_matrix(voices_path, led, reg, vc_model="openvoice-v2", mode="research")}
    assert research[("vi-north", "mentor-older-calm")]["status"] == "need_speaker"


def test_wer_and_audio_eval(tmp_path):
    assert eval_audio.wer("một hai ba bốn", "một hai ba bốn") == 0
    assert eval_audio.wer("một hai ba bốn", "một ba bốn") == 0.25
    assert eval_audio.cer("abc", "abd") == pytest.approx(1 / 3)
    wav = make_wav(tmp_path / "g.wav")
    res = eval_audio.evaluate_clip(wav, "Giá 50k", transcribe=lambda p: "giá năm mươi nghìn")
    assert res["wer"] == 0 and res["problems"] == []


def test_video_eval_separates_matching_and_different_clips(tmp_path):
    ref = Image.new("RGB", (544, 960), (38, 70, 110))
    ref.paste((220, 50, 60), (200, 300, 344, 700))
    ref_path = tmp_path / "ref.png"
    ref.save(ref_path)
    same = eval_video.evaluate_clip(make_clip(tmp_path / "same.mp4", source=ref_path), ref_path)
    other = eval_video.evaluate_clip(make_clip(tmp_path / "other.mp4"), ref_path)
    assert same["problems"] == [] and same["palette_mean"] > 0.8
    assert other["palette_mean"] < same["palette_mean"] and other["problems"]
    prompt = eval_video.vlm_checklist("A worried presenter", pose="worried", prop="question")
    assert "worried" in prompt and "question" in prompt and "PASS" in prompt
