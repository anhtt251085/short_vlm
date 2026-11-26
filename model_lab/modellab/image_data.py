"""Build an image LoRA dataset from character sheets on a flat background.

For each sheet: split it into a grid, cut each figure out of the flat background with a
soft mask, crop it, and composite it onto several backgrounds. Every image gets a caption
file with the trigger phrase and the parts that vary.

Output (in out_dir):
  images/<id>.png + images/<id>.txt   image and caption side by side (musubi-tuner layout)
  manifest.jsonl, rejects.jsonl, summary.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml
from PIL import Image
from scipy import ndimage

from .consent import Ledger, needed_scopes


@dataclass
class ImageRules:
    long_side: int = 1024          # output size of the longer side
    margin: float = 0.06           # padding around the figure, as a share of its size
    min_size: int = 256            # smallest acceptable figure (pixels, before resizing)
    min_fill: float = 0.03         # figure must cover at least this share of its cell
    max_fill: float = 0.90
    mask_low: float = 25.0         # colour distance from the background: fully transparent below
    mask_high: float = 60.0        # fully opaque above
    shadow_min_scale: float = 0.55  # a darker copy of the background between this and 1.0 ...
    shadow_max_residual: float = 25.0  # ... and this close in colour is a floor shadow, not the figure
    snap_window: float = 0.15      # grid cuts may move this share of a cell to find an empty line


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def background_colour(arr: np.ndarray) -> np.ndarray:
    """Median colour of the four corners."""
    k = max(4, min(arr.shape[0], arr.shape[1]) // 50)
    corners = np.concatenate([arr[:k, :k], arr[:k, -k:], arr[-k:, :k], arr[-k:, -k:]]).reshape(-1, 3)
    return np.median(corners, axis=0)


def soft_mask(arr: np.ndarray, bg: np.ndarray, rules: ImageRules) -> np.ndarray:
    dist = np.linalg.norm(arr - bg, axis=2)
    alpha = np.clip((dist - rules.mask_low) / (rules.mask_high - rules.mask_low), 0.0, 1.0)
    # Floor shadows are darker copies of the background colour. Remove them so the figure
    # does not carry a blue shadow onto other backgrounds. The navy suit is far darker
    # (about 0.2-0.35 of the background), so it is not affected.
    scale = (arr @ bg) / float(bg @ bg)
    residual = np.linalg.norm(arr - scale[..., None] * bg, axis=2)
    shadow = (scale >= rules.shadow_min_scale) & (scale <= 1.0) & (residual <= rules.shadow_max_residual)
    alpha[shadow] = 0.0
    return alpha


def _snap(profile: np.ndarray, n: int, window: float) -> list[int]:
    """Cut positions for n equal parts, each moved to the emptiest line nearby."""
    size = len(profile)
    cuts = [0]
    for k in range(1, n):
        target = round(k * size / n)
        half = max(1, int(window * size / n))
        lo, hi = max(1, target - half), min(size - 1, target + half)
        cuts.append(lo + int(np.argmin(profile[lo:hi])))
    cuts.append(size)
    return cuts


def cut_cells(sheet: Image.Image, rows: int, cols: int, bg: np.ndarray | None = None,
              rules: ImageRules | None = None):
    """Yield (index, cell array) in reading order. Cuts snap to empty lines between figures."""
    rules = rules or ImageRules()
    arr = np.asarray(sheet.convert("RGB")).astype(np.float32)
    bg = background_colour(arr) if bg is None else bg
    solid = soft_mask(arr, bg, rules) > 0.5
    ys = _snap(solid.sum(axis=1), rows, rules.snap_window)
    for r in range(rows):
        band = solid[ys[r]:ys[r + 1]]
        xs = _snap(band.sum(axis=0), cols, rules.snap_window)
        for c in range(cols):
            yield r * cols + c, arr[ys[r]:ys[r + 1], xs[c]:xs[c + 1]]


def figures_by_component(sheet: Image.Image, rows: int, cols: int, bg: np.ndarray, rules: ImageRules):
    """Yield (index, sheet array, alpha for that figure only, cell area) by finding each figure
    as a connected shape and placing it in the grid by its centre. Nothing is cut, so raised
    paws or feet near a neighbour stay whole. Raises ValueError if figures merge or a cell is empty."""
    arr = np.asarray(sheet.convert("RGB")).astype(np.float32)
    h, w = arr.shape[:2]
    alpha = soft_mask(arr, bg, rules)
    solid = alpha > 0.5
    labels, n = ndimage.label(solid, structure=np.ones((3, 3)))
    if n < rows * cols:
        raise ValueError(f"found {n} shapes for {rows * cols} figures; figures may be touching")
    sizes = ndimage.sum(solid, labels, index=np.arange(1, n + 1))
    biggest = 1 + np.argsort(sizes)[::-1][: rows * cols]
    if sizes[biggest[-1] - 1] < 0.2 * sizes[biggest[0] - 1]:
        raise ValueError("some figures are much smaller than others; figures may be touching or missing")
    centres = ndimage.center_of_mass(solid, labels, biggest)
    cells = {}
    for lab, (cy, cx) in zip(biggest, centres):
        idx = min(rows - 1, int(cy / (h / rows))) * cols + min(cols - 1, int(cx / (w / cols)))
        if idx in cells:
            raise ValueError(f"two figures fall in cell {idx}")
        cells[idx] = lab
    cell_area = (h / rows) * (w / cols)
    for idx in range(rows * cols):
        keep = ndimage.binary_dilation(labels == cells[idx], iterations=3)
        yield idx, arr, alpha * keep, cell_area


def main_figure(alpha: np.ndarray) -> np.ndarray:
    """Keep the largest connected figure (and any large parts), dropping slivers of neighbours."""
    solid = alpha > 0.5
    labels, n = ndimage.label(solid, structure=np.ones((3, 3)))
    if n <= 1:
        return alpha
    sizes = ndimage.sum(solid, labels, index=np.arange(1, n + 1))
    keep_ids = 1 + np.where(sizes >= 0.2 * sizes.max())[0]
    keep = np.isin(labels, keep_ids)
    keep = ndimage.binary_dilation(keep, iterations=3)  # keep the soft fur edge
    return alpha * keep


def extract_figure(cell: np.ndarray, bg: np.ndarray, rules: ImageRules, alpha: np.ndarray | None = None,
                   fill_area: float | None = None):
    """Return (rgb, alpha, problems, notes) for one figure.

    `cell` is the region to cut from. `alpha` limits it to one figure (computed if not given).
    `fill_area` is the area the fill checks are measured against (defaults to the region size).
    """
    if alpha is None:
        alpha = main_figure(soft_mask(cell, bg, rules))
    solid = alpha > 0.5
    fill = float(solid.sum() / (fill_area or solid.size))
    problems: list[str] = []
    notes: list[str] = []
    if fill < rules.min_fill:
        return None, None, [f"almost empty cell ({fill:.1%} figure)"], notes
    if fill > rules.max_fill:
        problems.append(f"figure fills {fill:.0%} of the cell; background may not be flat")
    ys, xs = np.where(solid)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    # A figure touching the cell edge may be cut off (e.g. a raised paw in a tight grid).
    h, w = solid.shape
    if y0 == 0 or x0 == 0 or y1 == h or x1 == w:
        notes.append("figure touches the cell edge; check it is not cut off")
    if max(y1 - y0, x1 - x0) < rules.min_size:
        problems.append(f"figure too small ({x1 - x0}x{y1 - y0} px)")
    my = int((y1 - y0) * rules.margin)
    mx = int((x1 - x0) * rules.margin)
    y0, y1 = max(0, y0 - my), min(h, y1 + my)
    x0, x1 = max(0, x0 - mx), min(w, x1 + mx)
    return cell[y0:y1, x0:x1], alpha[y0:y1, x0:x1], problems, notes


def composite(rgb: np.ndarray, alpha: np.ndarray, colour: tuple[int, int, int], long_side: int) -> Image.Image:
    bg = np.empty_like(rgb)
    bg[:] = colour
    out = rgb * alpha[..., None] + bg * (1 - alpha[..., None])
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    scale = long_side / max(img.size)
    return img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)


def build_image_dataset(config_path: str | Path, ledger: Ledger, out_dir: str | Path,
                        rules: ImageRules | None = None, mode: str = "commercial") -> dict:
    rules = rules or ImageRules()
    config_path, out_dir = Path(config_path), Path(out_dir)
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    img_dir = out_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    trigger = cfg["trigger"]
    backgrounds = cfg["backgrounds"]

    accepted, rejected = [], []
    ok, why = ledger.check_asset(cfg["source_id"], needed_scopes("image_training", mode))
    if not ok:
        rejected.append({"source": cfg["source_id"], "reasons": [why]})
        return _finish(out_dir, accepted, rejected, mode)

    for s_i, sheet_cfg in enumerate(cfg["sheets"]):
        path = (config_path.parent / sheet_cfg["file"]).resolve()
        rows, cols = sheet_cfg["grid"]
        captions = sheet_cfg["cells"]
        if len(captions) != rows * cols:
            rejected.append({"source": str(path), "reasons": [f"{len(captions)} captions for a {rows}x{cols} grid"]})
            continue
        if not path.exists():
            rejected.append({"source": str(path), "reasons": ["sheet not found"]})
            continue
        sheet = Image.open(path)
        bg = background_colour(np.asarray(sheet.convert("RGB")).astype(np.float32))
        if sheet_cfg.get("split", "grid") == "components":
            try:
                parts = [(i, region, a, area) for i, region, a, area in figures_by_component(sheet, rows, cols, bg, rules)]
            except ValueError as e:
                rejected.append({"source": str(path), "reasons": [f"could not separate figures: {e}"]})
                continue
        else:
            parts = [(i, cell, None, None) for i, cell in cut_cells(sheet, rows, cols, bg, rules)]
        for c_i, region, fig_alpha, area in parts:
            rgb, alpha, problems, notes = extract_figure(region, bg, rules, alpha=fig_alpha, fill_area=area)
            source = f"{path.name}#{c_i}"
            if problems or rgb is None:
                rejected.append({"source": source, "caption": captions[c_i], "reasons": problems})
                continue
            for b_i, back in enumerate(backgrounds):
                item_id = f"s{s_i:02d}_c{c_i:02d}_b{b_i}"
                caption = f"{trigger}, {sheet_cfg['framing']}, {captions[c_i]}, {back['name']}"
                img = composite(rgb, alpha, _hex(back["color"]), rules.long_side)
                img.save(img_dir / f"{item_id}.png")
                (img_dir / f"{item_id}.txt").write_text(caption + "\n", encoding="utf-8")
                accepted.append({"id": item_id, "source": source, "caption": caption,
                                 "width": img.width, "height": img.height, "notes": notes,
                                 "image": f"images/{item_id}.png"})
    return _finish(out_dir, accepted, rejected, mode)


def _finish(out_dir: Path, accepted: list, rejected: list, mode: str) -> dict:
    for name, rows in (("manifest.jsonl", accepted), ("rejects.jsonl", rejected)):
        with (out_dir / name).open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    figures = sorted({r["source"] for r in accepted})
    summary = {"images": len(accepted), "figures": len(figures), "rejected": len(rejected), "mode": mode,
               "notes": sorted({f"{r['source']}: {n}" for r in accepted for n in r["notes"]})}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary
