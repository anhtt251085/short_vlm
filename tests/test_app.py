import json
import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATA_DIR", str(Path(__file__).resolve().parent.parent / "data-test"))
os.environ.pop("ANTHROPIC_API_KEY", None)  # force template brief in tests

from app import brief as brief_agent  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas import ProjectIn  # noqa: E402

client = TestClient(app)


def test_template_brief_en_has_beats_and_cta():
    b = brief_agent.template_brief(ProjectIn(product_name="Bamboo stand", description="Foldable. Sturdy.", language="en"))
    assert b.hook.startswith("Meet")
    assert len(b.beats) >= 3
    assert b.cta


def test_claims_detected_in_vietnamese_and_english():
    assert "best" in brief_agent.find_claims("This is the best product")
    assert "tốt nhất" in brief_agent.find_claims("Sản phẩm tốt nhất hiện nay")
    assert brief_agent.find_claims("A plain description") == []


def test_full_flow_renders_valid_video():
    p = client.post("/api/projects", json={"product_name": "Bamboo phone stand",
                                           "description": "Foldable and lightweight. Fits all phones.",
                                           "language": "en", "target_seconds": 9, "use_voice": False}).json()
    pid = p["id"]
    b = client.post(f"/api/projects/{pid}/brief").json()
    assert b["brief"]["beats"]
    r = client.post(f"/api/projects/{pid}/render")
    assert r.status_code == 200, r.text
    body = r.json()
    assert all(c["ok"] for c in body["qa"] if c["name"] != "has_audio_track") , body["qa"]
    v = client.get(f"/api/projects/{pid}/video")
    assert v.status_code == 200 and len(v.content) > 1000
    post = client.get(f"/api/projects/{pid}/post-text").json()
    assert "#" in post["text"]


def test_render_requires_brief():
    pid = client.post("/api/projects", json={"product_name": "X"}).json()["id"]
    assert client.post(f"/api/projects/{pid}/render").status_code == 400


def test_edit_brief_and_flags_claims():
    pid = client.post("/api/projects", json={"product_name": "X", "language": "en"}).json()["id"]
    client.post(f"/api/projects/{pid}/brief")
    edited = {"hook": "Hi", "beats": [{"on_screen": "Best ever", "voiceover": "This is the best"}],
              "cta": "Buy now", "caption": "best deal", "hashtags": ["#x"]}
    r = client.put(f"/api/projects/{pid}/brief", json=edited).json()
    assert r["brief_source"] == "user"
    assert "best" in r["brief"]["claims_flags"]


def test_invalid_language_rejected():
    r = client.post("/api/projects", json={"product_name": "X", "language": "fr"})
    assert r.status_code == 422


def test_index_served():
    assert "Short Video Studio" in client.get("/").text


def test_product_image_upload_and_render(tmp_path):
    from PIL import Image
    img = tmp_path / "p.png"
    Image.new("RGB", (800, 800), (200, 80, 80)).save(img)
    pid = client.post("/api/projects", json={"product_name": "Mug", "language": "en", "use_voice": False}).json()["id"]
    with img.open("rb") as f:
        r = client.post(f"/api/projects/{pid}/image", files={"file": ("p.png", f, "image/png")})
    assert r.status_code == 200 and r.json()["image"]
    client.post(f"/api/projects/{pid}/brief")
    r = client.post(f"/api/projects/{pid}/render")
    assert r.status_code == 200 and all(c["ok"] for c in r.json()["qa"] if c["name"] != "has_audio_track")


def test_image_wrong_type_rejected(tmp_path):
    pid = client.post("/api/projects", json={"product_name": "Mug"}).json()["id"]
    r = client.post(f"/api/projects/{pid}/image", files={"file": ("x.txt", b"hi", "text/plain")})
    assert r.status_code == 400
