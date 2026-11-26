import json
import tomllib

import numpy as np
import pytest
import yaml
from PIL import Image, ImageDraw

from modellab.consent import Ledger
from modellab.image_data import ImageRules, build_image_dataset, soft_mask
from modellab.planners import plan_video
from modellab.registry import Registry

BG = (151, 199, 252)       # the concept sheets' light blue
NAVY = (61, 59, 87)        # suit colour
SHADOW = (117, 154, 208)   # floor shadow measured on the real sheet (0.8 x background)


def _figure(d, x, y, w=120, h=260, shadow=True):
    if shadow:
        d.ellipse([x - 20, y + h - 10, x + w + 20, y + h + 12], fill=SHADOW)
    d.rectangle([x, y, x + w, y + h], fill=NAVY)
    d.ellipse([x + 20, y - 60, x + w - 20, y + 10], fill=(234, 121, 48))  # orange head


def _sheet(path, rows, cols, cell=(400, 400), touching=False):
    img = Image.new("RGB", (cell[0] * cols, cell[1] * rows), BG)
    d = ImageDraw.Draw(img)
    for r in range(rows):
        for c in range(cols):
            _figure(d, c * cell[0] + 140, r * cell[1] + 90)
    if touching:  # a wide arm from figure 0 that reaches into cell 1's area
        d.rectangle([260, 150, cell[0] + 160, 170], fill=NAVY)  # joins figure 1 (starts at x=540)
    img.save(path)
    return path


def _config(tmp_path, sheets):
    cfg = {"trigger": "mntr fox", "source_id": "art",
           "backgrounds": [{"name": "white background", "color": "#FFFFFF"},
                           {"name": "grey background", "color": "#808080"}],
           "sheets": sheets}
    p = tmp_path / "sheets.yaml"
    p.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return p


def _ledger(tmp_path, scopes):
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump({"assets": [{"id": "art", "scopes": scopes}]}), encoding="utf-8")
    return Ledger.load(p)


def test_shadow_is_removed_but_navy_suit_kept():
    bg = np.array(BG, dtype=np.float32)
    px = np.array([[SHADOW, NAVY, (42, 38, 60), (239, 55, 53)]], dtype=np.float32)
    alpha = soft_mask(px, bg, ImageRules())
    assert alpha[0, 0] == 0.0          # shadow
    assert alpha[0, 1:].min() == 1.0   # suit, trousers, tie


@pytest.mark.parametrize("split", ["grid", "components"])
def test_builds_captioned_images_on_each_background(tmp_path, split):
    sheet = _sheet(tmp_path / "s.png", 1, 2)
    cfg = _config(tmp_path, [{"file": "s.png", "grid": [1, 2], "split": split, "framing": "full body",
                              "cells": ["front view", "side view"]}])
    out = tmp_path / "out"
    summary = build_image_dataset(cfg, _ledger(tmp_path, ["image_training"]), out, mode="research")
    assert summary["images"] == 4 and summary["figures"] == 2 and summary["rejected"] == 0
    assert (out / "images" / "s00_c01_b0.txt").read_text().strip() == "mntr fox, full body, side view, white background"
    img = np.asarray(Image.open(out / "images" / "s00_c00_b1.png").convert("RGB"))
    assert tuple(img[2, 2]) == (128, 128, 128)        # new background
    assert not np.any(np.all(np.abs(img.astype(int) - SHADOW) < 6, axis=2))  # no blue shadow left


def test_components_keep_neighbouring_figures_apart(tmp_path):
    _sheet(tmp_path / "s.png", 1, 2, touching=False)
    cfg = _config(tmp_path, [{"file": "s.png", "grid": [1, 2], "split": "components", "framing": "full body",
                              "cells": ["a", "b"]}])
    out = tmp_path / "out"
    build_image_dataset(cfg, _ledger(tmp_path, ["image_training"]), out, mode="research")
    a = Image.open(out / "images" / "s00_c00_b0.png")
    b = Image.open(out / "images" / "s00_c01_b0.png")
    # Each crop holds one figure: aspect stays tall, not two figures side by side.
    assert a.height > a.width and b.height > b.width


def test_touching_figures_are_rejected_in_component_mode(tmp_path):
    _sheet(tmp_path / "s.png", 1, 2, touching=True)
    cfg = _config(tmp_path, [{"file": "s.png", "grid": [1, 2], "split": "components", "framing": "full body",
                              "cells": ["a", "b"]}])
    out = tmp_path / "out"
    summary = build_image_dataset(cfg, _ledger(tmp_path, ["image_training"]), out, mode="research")
    assert summary["images"] == 0
    reasons = json.loads((out / "rejects.jsonl").read_text().splitlines()[0])["reasons"][0]
    assert "could not separate figures" in reasons


def test_empty_cell_and_caption_count_are_rejected(tmp_path):
    img = Image.new("RGB", (800, 400), BG)
    _figure(ImageDraw.Draw(img), 140, 90)
    img.save(tmp_path / "half.png")
    _sheet(tmp_path / "s.png", 1, 2)
    cfg = _config(tmp_path, [
        {"file": "half.png", "grid": [1, 2], "framing": "full body", "cells": ["a", "b"]},
        {"file": "s.png", "grid": [1, 2], "framing": "full body", "cells": ["only one"]},
    ])
    out = tmp_path / "out"
    summary = build_image_dataset(cfg, _ledger(tmp_path, ["image_training"]), out, mode="research")
    assert summary["figures"] == 1
    text = (out / "rejects.jsonl").read_text()
    assert "almost empty cell" in text and "1 captions for a 1x2 grid" in text


def test_commercial_mode_needs_commercial_rights(tmp_path):
    _sheet(tmp_path / "s.png", 1, 1)
    cfg = _config(tmp_path, [{"file": "s.png", "grid": [1, 1], "framing": "full body", "cells": ["a"]}])
    summary = build_image_dataset(cfg, _ledger(tmp_path, ["image_training"]), tmp_path / "o1", mode="commercial")
    assert summary["images"] == 0 and summary["rejected"] == 1
    summary = build_image_dataset(cfg, _ledger(tmp_path, ["image_training", "commercial_use"]),
                                  tmp_path / "o2", mode="commercial")
    assert summary["images"] == 2


def test_plan_video_accepts_an_image_dataset(tmp_path, models_path, monkeypatch):
    from conftest import ROOT
    monkeypatch.chdir(ROOT)
    _sheet(tmp_path / "s.png", 1, 1)
    cfg = _config(tmp_path, [{"file": "s.png", "grid": [1, 1], "framing": "full body", "cells": ["a"]}])
    build_image_dataset(cfg, _ledger(tmp_path, ["image_training"]), tmp_path / "ds", mode="research")
    plan = plan_video("configs/video_lora.yaml", Registry.load(models_path), tmp_path / "ds", tmp_path / "runs")
    ds = tomllib.loads((tmp_path / "runs" / "fox-pilot-v1" / "dataset.toml").read_text())
    assert ds["datasets"][0]["image_directory"].endswith("ds/images")
    assert "video_directory" not in ds["datasets"][0]
    assert plan["images"] == 2 and plan["clips"] == 0
