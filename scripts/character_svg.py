"""Generate the presenter as SVG: one shared head and body, six poses.

Because the face, suit, and glasses come from the same code for every pose,
they stay identical. Output: assets/character/<pose>.svg and reference_sheet.png.
Usage: python scripts/character_svg.py
"""

from pathlib import Path

import cairosvg

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "character"

# Locked palette (from docs/character-bible.md)
SUIT = "#26466E"
SHIRT = "#FFFFFF"
TIE = "#DC323C"
SKIN = "#FFCC99"
HAIR = "#3C281E"
BLUSH = "#FF8C8C"
INK = "#1E1E28"
W = 800
H = 1000  # taller canvas so hands at y=860 stay in frame

ARMS = {
    # pose: (left hand (x,y), right hand (x,y)); shoulders fixed at (cx-190,600) and (cx+190,600)
    "idle": ((-215, 860), (215, 860)),
    "thinking": ((-215, 860), (70, 470)),
    "pointing": ((-215, 860), (330, 430)),
    "happy": ((-300, 300), (300, 300)),
    "worried": ((-250, 430), (250, 430)),
    "celebrate": ((-290, 260), (290, 260)),
}


def svg_pose(pose: str) -> str:
    cx = W // 2
    (lx, ly), (rx, ry) = ARMS[pose]
    lhand = (cx + lx, ly)
    rhand = (cx + rx, ry)
    parts = []
    # Arms behind body
    for sh, hd in (((cx - 190, 600), lhand), ((cx + 190, 600), rhand)):
        parts.append(f'<line x1="{sh[0]}" y1="{sh[1]}" x2="{hd[0]}" y2="{hd[1]}" stroke="{SUIT}" stroke-width="52" stroke-linecap="round"/>')
        parts.append(f'<circle cx="{hd[0]}" cy="{hd[1]}" r="30" fill="{SKIN}"/>')
    # Body
    parts.append(f'<rect x="{cx-200}" y="560" width="400" height="440" rx="60" fill="{SUIT}"/>')
    parts.append(f'<polygon points="{cx-60},560 {cx+60},560 {cx},680" fill="{SHIRT}"/>')
    parts.append(f'<polygon points="{cx-18},580 {cx+18},580 {cx+26},660 {cx},700 {cx-26},660" fill="{TIE}"/>')
    parts.append(f'<rect x="{cx-40}" y="500" width="80" height="60" fill="{SKIN}"/>')
    # Head
    parts.append(f'<ellipse cx="{cx}" cy="350" rx="180" ry="180" fill="{SKIN}"/>')
    parts.append(f'<path d="M {cx-185},380 A 190,205 0 0 1 {cx+185},380 Z" fill="{HAIR}"/>')
    parts.append(f'<ellipse cx="{cx-197}" cy="285" rx="22" ry="55" fill="{HAIR}"/>')
    parts.append(f'<ellipse cx="{cx+197}" cy="285" rx="22" ry="55" fill="{HAIR}"/>')
    # Glasses and eyes (same geometry in every pose)
    for ex in (cx - 80, cx + 80):
        parts.append(f'<circle cx="{ex}" cy="360" r="40" fill="none" stroke="{INK}" stroke-width="8"/>')
        parts.append(f'<circle cx="{ex}" cy="360" r="14" fill="{INK}"/>')
    parts.append(f'<line x1="{cx-40}" y1="360" x2="{cx+40}" y2="360" stroke="{INK}" stroke-width="8"/>')
    # Brows: worried tilts inward-up
    if pose == "worried":
        parts.append(f'<line x1="{cx-120}" y1="300" x2="{cx-50}" y2="275" stroke="{INK}" stroke-width="10" stroke-linecap="round"/>')
        parts.append(f'<line x1="{cx+50}" y1="275" x2="{cx+120}" y2="300" stroke="{INK}" stroke-width="10" stroke-linecap="round"/>')
    # Cheeks
    parts.append(f'<ellipse cx="{cx-130}" cy="432" rx="20" ry="12" fill="{BLUSH}"/>')
    parts.append(f'<ellipse cx="{cx+130}" cy="432" rx="20" ry="12" fill="{BLUSH}"/>')
    # Mouth by pose
    if pose == "worried":
        parts.append(f'<path d="M {cx-50},480 Q {cx},440 {cx+50},480" fill="none" stroke="{INK}" stroke-width="10" stroke-linecap="round"/>')
    elif pose == "celebrate":
        parts.append(f'<ellipse cx="{cx}" cy="460" rx="45" ry="35" fill="{INK}"/>')
    elif pose == "thinking":
        parts.append(f'<line x1="{cx-25}" y1="460" x2="{cx+25}" y2="460" stroke="{INK}" stroke-width="10" stroke-linecap="round"/>')
    else:
        parts.append(f'<path d="M {cx-60},430 Q {cx},480 {cx+60},430" fill="none" stroke="{INK}" stroke-width="10" stroke-linecap="round"/>')
    body = "\n  ".join(parts)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'
            f'  <title>presenter-{pose}</title>\n  {body}\n</svg>\n')


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for pose in ARMS:
        (OUT / f"{pose}.svg").write_text(svg_pose(pose), encoding="utf-8")
        cairosvg.svg2png(url=str(OUT / f"{pose}.svg"), write_to=str(OUT / f"{pose}.png"), background_color="#FFFFFF")
    # Reference sheet: 3 x 2 grid
    from PIL import Image
    tiles = [Image.open(OUT / f"{p}.png").convert("RGB").resize((400, 500)) for p in ARMS]
    sheet = Image.new("RGB", (1200, 1000), "#FFFFFF")
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 3) * 400, (i // 3) * 500))
    sheet.save(OUT / "reference_sheet.png")
    print("wrote", len(tiles), "poses to", OUT)


if __name__ == "__main__":
    main()
