"""Draw a simple cartoon business character as a transparent PNG.

Usage: python scripts/make_character.py out.png
"""

import sys

from PIL import Image, ImageDraw

SIZE = 800
SKIN = (255, 204, 153, 255)
HAIR = (60, 40, 30, 255)
SUIT = (38, 70, 110, 255)
SHIRT = (255, 255, 255, 255)
TIE = (220, 50, 60, 255)
DARK = (30, 30, 40, 255)
CASE = (140, 90, 50, 255)
BLUSH = (255, 140, 140, 255)


def draw(out: str) -> None:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Body (suit) with shirt and tie
    d.rounded_rectangle([200, 470, 600, 800], radius=60, fill=SUIT)
    d.polygon([(340, 470), (460, 470), (400, 600)], fill=SHIRT)
    d.polygon([(385, 490), (415, 490), (425, 560), (400, 600), (375, 560)], fill=TIE)

    # Arm holding briefcase (right side of image)
    d.rounded_rectangle([560, 540, 630, 700], radius=30, fill=SUIT)
    d.rounded_rectangle([540, 660, 680, 760], radius=14, fill=CASE)
    d.rectangle([590, 630, 630, 650], outline=DARK, width=8)
    d.line([(600, 620), (600, 650)], fill=DARK, width=0)

    # Neck
    d.rectangle([360, 430, 440, 490], fill=SKIN)

    # Head
    d.ellipse([220, 130, 580, 470], fill=SKIN)
    # Hair
    d.chord([215, 110, 585, 330], start=180, end=360, fill=HAIR)
    d.ellipse([215, 150, 260, 260], fill=HAIR)
    d.ellipse([540, 150, 585, 260], fill=HAIR)

    # Glasses
    d.ellipse([295, 260, 375, 340], outline=DARK, width=8)
    d.ellipse([425, 260, 505, 340], outline=DARK, width=8)
    d.line([(375, 298), (425, 298)], fill=DARK, width=8)

    # Eyes
    d.ellipse([320, 280, 350, 316], fill=DARK)
    d.ellipse([450, 280, 480, 316], fill=DARK)
    d.ellipse([327, 285, 336, 294], fill=(255, 255, 255, 255))
    d.ellipse([457, 285, 466, 294], fill=(255, 255, 255, 255))

    # Cheeks and smile
    d.ellipse([280, 345, 320, 370], fill=BLUSH)
    d.ellipse([480, 345, 520, 370], fill=BLUSH)
    d.arc([330, 340, 470, 420], start=20, end=160, fill=DARK, width=10)

    img.save(out)


if __name__ == "__main__":
    draw(sys.argv[1] if len(sys.argv) > 1 else "character.png")
