"""Draw story scenes: a cartoon character in a pose, plus one prop that matches the line.

Everything is drawn with Pillow shapes, so it is free to run and easy to extend.
Add a new prop or pose by writing one function and registering it below.
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

POSES = ["idle", "thinking", "pointing", "happy", "worried", "celebrate"]
PROPS = ["none", "lightbulb", "chart_up", "checklist", "coins", "phone",
         "question", "cart", "clock", "customer", "trophy"]

ART_W, ART_H = 1080, 1040

SKIN = (255, 204, 153, 255)
HAIR = (60, 40, 30, 255)
SUIT = (38, 70, 110, 255)
SHIRT = (255, 255, 255, 255)
TIE = (220, 50, 60, 255)
DARK = (30, 30, 40, 255)
BLUSH = (255, 140, 140, 255)
GOLD = (255, 196, 40, 255)
GREEN = (46, 180, 90, 255)
GREY = (150, 155, 165, 255)
WHITE = (255, 255, 255, 255)
YELLOW = (255, 222, 90, 255)
CORAL = (240, 110, 90, 255)

_BOLD = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for p in _BOLD:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def _arm(d: ImageDraw.ImageDraw, shoulder, hand) -> None:
    d.line([shoulder, hand], fill=SUIT, width=52)
    d.ellipse([hand[0] - 30, hand[1] - 30, hand[0] + 30, hand[1] + 30], fill=SKIN)


def draw_character(d: ImageDraw.ImageDraw, cx: int, pose: str) -> None:
    """Character stands with feet at y=1000. cx is the horizontal centre."""
    # Body and tie
    d.rounded_rectangle([cx - 200, 560, cx + 200, 1000], radius=60, fill=SUIT)
    d.polygon([(cx - 60, 560), (cx + 60, 560), (cx, 680)], fill=SHIRT)
    d.polygon([(cx - 18, 580), (cx + 18, 580), (cx + 26, 660), (cx, 700), (cx - 26, 660)], fill=TIE)
    d.rectangle([cx - 40, 500, cx + 40, 560], fill=SKIN)

    # Arms by pose (shoulders at y=600)
    left_s, right_s = (cx - 190, 600), (cx + 190, 600)
    if pose == "pointing":
        _arm(d, left_s, (cx - 215, 860))
        _arm(d, right_s, (cx + 330, 430))
    elif pose == "thinking":
        _arm(d, left_s, (cx - 215, 860))
        _arm(d, right_s, (cx + 70, 470))
    elif pose in ("happy", "celebrate"):
        up = 260 if pose == "celebrate" else 300
        _arm(d, left_s, (cx - 300, up))
        _arm(d, right_s, (cx + 300, up))
    elif pose == "worried":
        _arm(d, left_s, (cx - 250, 430))
        _arm(d, right_s, (cx + 250, 430))
    else:  # idle
        _arm(d, left_s, (cx - 215, 860))
        _arm(d, right_s, (cx + 215, 860))

    # Head and hair
    d.ellipse([cx - 180, 170, cx + 180, 530], fill=SKIN)
    d.chord([cx - 185, 150, cx + 185, 380], start=180, end=360, fill=HAIR)
    d.ellipse([cx - 220, 230, cx - 175, 340], fill=HAIR)
    d.ellipse([cx + 175, 230, cx + 220, 340], fill=HAIR)

    # Glasses and eyes
    for ex in (cx - 80, cx + 80):
        d.ellipse([ex - 40, 320, ex + 40, 400], outline=DARK, width=8)
        d.ellipse([ex - 14, 346, ex + 14, 374], fill=DARK)
    d.line([(cx - 40, 360), (cx + 40, 360)], fill=DARK, width=8)

    # Eyebrows: worried brows go up on the inside
    if pose == "worried":
        d.line([(cx - 120, 300), (cx - 50, 275)], fill=DARK, width=10)
        d.line([(cx + 50, 275), (cx + 120, 300)], fill=DARK, width=10)

    # Cheeks
    d.ellipse([cx - 150, 420, cx - 110, 445], fill=BLUSH)
    d.ellipse([cx + 110, 420, cx + 150, 445], fill=BLUSH)

    # Mouth by pose
    if pose == "worried":
        d.arc([cx - 50, 440, cx + 50, 500], start=200, end=340, fill=DARK, width=10)
    elif pose == "celebrate":
        d.ellipse([cx - 45, 425, cx + 45, 495], fill=DARK)
    elif pose == "thinking":
        d.line([(cx - 25, 460), (cx + 25, 460)], fill=DARK, width=10)
    else:
        d.arc([cx - 60, 410, cx + 60, 480], start=20, end=160, fill=DARK, width=10)


def _prop_lightbulb(d, px, py):
    for r, a in ((190, 60), (150, 90)):
        d.ellipse([px - r, py - 40 - r, px + r, py - 40 + r], fill=(255, 240, 150, a))
    d.ellipse([px - 110, py - 150, px + 110, py + 70], fill=YELLOW)
    d.rectangle([px - 50, py + 60, px + 50, py + 120], fill=GREY)
    d.rectangle([px - 35, py + 120, px + 35, py + 140], fill=DARK)


def _prop_chart_up(d, px, py):
    d.line([(px - 150, py + 130), (px - 150, py - 130), (px + 150, py - 130)], fill=GREY, width=8)
    for i, h in enumerate((60, 110, 80, 150)):
        x = px - 120 + i * 70
        d.rectangle([x, py + 130 - h, x + 40, py + 130], fill=(120, 170, 230, 255))
    d.line([(px - 130, py + 90), (px - 40, py + 20), (px + 30, py + 50), (px + 130, py - 110)], fill=GREEN, width=16)
    d.ellipse([px + 115, py - 125, px + 145, py - 95], fill=GREEN)


def _prop_checklist(d, px, py):
    d.rounded_rectangle([px - 130, py - 160, px + 130, py + 160], radius=18, fill=WHITE, outline=GREY, width=6)
    for i in range(3):
        y = py - 90 + i * 90
        d.line([(px - 95, y), (px - 60, y + 25), (px - 25, y - 15)], fill=GREEN, width=12)
        d.line([(px + 0, y + 5), (px + 95, y + 5)], fill=GREY, width=12)


def _prop_coins(d, px, py):
    for i in range(4):
        y = py + 110 - i * 40
        d.ellipse([px - 110, y - 30, px + 110, y + 30], fill=(190, 130, 20, 255))
        d.ellipse([px - 110, y - 40, px + 110, y + 20], fill=GOLD)
    d.ellipse([px - 60, py - 110, px + 60, py - 70], fill=GOLD)


def _prop_phone(d, px, py):
    d.rounded_rectangle([px - 95, py - 175, px + 95, py + 175], radius=28, fill=DARK)
    d.rounded_rectangle([px - 80, py - 150, px + 80, py + 140], radius=10, fill=(120, 190, 240, 255))
    d.ellipse([px - 30, py - 110, px + 30, py - 50], fill=WHITE)
    d.rectangle([px - 50, py + 0, px + 50, py + 20], fill=WHITE)


def _prop_question(d, px, py):
    d.text((px, py), "?", font=_font(330), fill=YELLOW, anchor="mm")


def _prop_cart(d, px, py):
    d.polygon([(px - 150, py - 90), (px + 150, py - 90), (px + 100, py + 60), (px - 110, py + 60)], fill=CORAL)
    d.line([(px - 170, py - 110), (px - 120, py - 110), (px - 110, py + 60)], fill=GREY, width=14)
    for x in (px - 70, px + 80):
        d.ellipse([x - 28, py + 80, x + 28, py + 136], fill=DARK)


def _prop_clock(d, px, py):
    d.ellipse([px - 150, py - 150, px + 150, py + 150], fill=WHITE, outline=DARK, width=12)
    d.line([(px, py), (px, py - 100)], fill=DARK, width=14)
    d.line([(px, py), (px + 75, py + 30)], fill=DARK, width=12)
    d.ellipse([px - 12, py - 12, px + 12, py + 12], fill=DARK)


def _prop_customer(d, px, py):
    d.ellipse([px - 90, py - 190, px + 90, py - 10], fill=(160, 110, 80, 255))
    d.rounded_rectangle([px - 130, py + 0, px + 130, py + 200], radius=60, fill=CORAL)


def _prop_trophy(d, px, py):
    d.polygon([(px - 130, py - 140), (px + 130, py - 140), (px + 90, py + 20), (px - 90, py + 20)], fill=GOLD)
    d.rectangle([px - 22, py + 20, px + 22, py + 100], fill=GOLD)
    d.rectangle([px - 100, py + 100, px + 100, py + 130], fill=(120, 80, 30, 255))


PROP_FUNCS = {
    "lightbulb": _prop_lightbulb, "chart_up": _prop_chart_up, "checklist": _prop_checklist,
    "coins": _prop_coins, "phone": _prop_phone, "question": _prop_question,
    "cart": _prop_cart, "clock": _prop_clock, "customer": _prop_customer, "trophy": _prop_trophy,
}


def draw_art(pose: str, prop: str) -> Image.Image:
    """Transparent art panel: character (and prop if any). Used on top of the gradient."""
    if pose not in POSES:
        pose = "idle"
    if prop not in PROPS:
        prop = "none"
    img = Image.new("RGBA", (ART_W, ART_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if prop == "none":
        draw_character(d, ART_W // 2, pose)
    else:
        draw_character(d, 330, pose)
        PROP_FUNCS[prop](d, 800, 470)
    return img
