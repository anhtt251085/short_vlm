"""Vietnamese text normalisation for speech: numbers, money, dates, times, units, abbreviations.

TTS models read words, not digits, so "1.500.000đ" must become
"một triệu năm trăm nghìn đồng" both in training transcripts and at inference.

Dialect matters for some readings, which also makes accents consistent:
- north: 105 -> "một trăm linh năm", 1000 -> "một nghìn", 24 -> "hai mươi tư"
- south: 105 -> "một trăm lẻ năm",  1000 -> "một ngàn", 24 -> "hai mươi bốn"
"""

from __future__ import annotations

import re

DIGITS = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
DIALECTS = ("north", "south")


def _check_dialect(dialect: str) -> None:
    if dialect not in DIALECTS:
        raise ValueError(f"dialect must be one of {DIALECTS}, got {dialect!r}")


def _read_triple(n: int, full: bool, dialect: str) -> str:
    """Read 0..999. `full` is True for a non-leading group, which keeps 'không trăm' and 'linh'."""
    h, t, u = n // 100, (n // 10) % 10, n % 10
    words: list[str] = []
    if h > 0 or full:
        words += [DIGITS[h], "trăm"]
    if t == 0:
        if u > 0:
            if h > 0 or full:
                words.append("linh" if dialect == "north" else "lẻ")
            words.append(DIGITS[u])
    elif t == 1:
        words.append("mười")
        if u == 5:
            words.append("lăm")
        elif u > 0:
            words.append(DIGITS[u])
    else:
        words += [DIGITS[t], "mươi"]
        if u == 1:
            words.append("mốt")
        elif u == 4:
            words.append("tư" if dialect == "north" else "bốn")
        elif u == 5:
            words.append("lăm")
        elif u > 0:
            words.append(DIGITS[u])
    return " ".join(words)


def _scale(index: int, dialect: str) -> str:
    thousand = "nghìn" if dialect == "north" else "ngàn"
    scales = ["", thousand, "triệu", "tỷ", f"{thousand} tỷ", "triệu tỷ"]
    if index >= len(scales):
        raise ValueError("number too large")
    return scales[index]


def read_number(n: int, dialect: str = "north") -> str:
    """Read a non-negative integer in Vietnamese words."""
    _check_dialect(dialect)
    if n < 0:
        return "âm " + read_number(-n, dialect)
    if n == 0:
        return DIGITS[0]
    groups: list[int] = []
    while n > 0:
        groups.append(n % 1000)
        n //= 1000
    highest = len(groups) - 1
    parts: list[str] = []
    for i in range(highest, -1, -1):
        g = groups[i]
        if g == 0:
            continue  # zero groups are skipped: 1.000.500 -> "một triệu năm trăm"
        words = _read_triple(g, full=i < highest, dialect=dialect)
        scale = _scale(i, dialect)
        parts.append(f"{words} {scale}".strip())
    return " ".join(parts)


def read_digits(s: str) -> str:
    return " ".join(DIGITS[int(c)] for c in s)


def _read_decimal(text: str, dialect: str) -> str:
    """'1.500' (dot thousands) and '12,5' (comma decimal) as used in Vietnamese."""
    int_part, _, frac = text.partition(",")
    words = read_number(int(int_part.replace(".", "")), dialect)
    if frac:
        frac_words = read_digits(frac) if frac.startswith("0") else read_number(int(frac), dialect)
        words += " phẩy " + frac_words
    return words


def _month(m: int, dialect: str) -> str:
    return "tư" if m == 4 else read_number(m, dialect)


ABBREVIATIONS = [
    (re.compile(r"\bTP\.?\s?HCM\b"), "thành phố Hồ Chí Minh"),
    (re.compile(r"\bTP\.?\s?Hồ Chí Minh\b"), "thành phố Hồ Chí Minh"),
    (re.compile(r"\bHN\b"), "Hà Nội"),
    (re.compile(r"\bVN\b"), "Việt Nam"),
    (re.compile(r"v\.v\.?"), "vân vân"),
    (re.compile(r"\s&\s"), " và "),
]

UNITS = {
    "%": "phần trăm",
    "đồng": "đồng", "đ": "đồng", "VNĐ": "đồng", "VND": "đồng", "vnđ": "đồng", "vnd": "đồng",
    "USD": "đô la", "usd": "đô la",
    "kg": "ki lô gam", "km": "ki lô mét", "m2": "mét vuông", "m²": "mét vuông",
    "tr": "triệu", "k": "nghìn", "K": "nghìn",
}
_UNIT_ALT = "|".join(sorted((re.escape(u) for u in UNITS), key=len, reverse=True))
_NUM = r"(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?"

_DATE_FULL = re.compile(r"(?:([Nn])gày\s+)?\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
_DATE_SHORT = re.compile(r"(?:([Nn])gày\s+)?\b(\d{1,2})/(\d{1,2})\b")
_TIME = re.compile(r"\b(\d{1,2}):(\d{2})\b")
_MONTH = re.compile(r"\b([Tt]háng)\s+(\d{1,2})\b(?!\s*/)")
_RANGE = re.compile(rf"\b({_NUM})\s?-\s?({_NUM})\b")
_NUMBER = re.compile(rf"(\$)?({_NUM})\s?({_UNIT_ALT})?(?!\w)")


def _day(d: int, dialect: str) -> str:
    # Days 1..10 are read with "mùng": "ngày mùng một"
    return ("mùng " if d <= 10 else "") + read_number(d, dialect)


def normalize(text: str, dialect: str = "north") -> str:
    """Turn digits, money, dates, times, and common abbreviations into spoken Vietnamese."""
    _check_dialect(dialect)
    out = text
    for pattern, repl in ABBREVIATIONS:
        out = pattern.sub(repl, out)

    def _ngay(m: re.Match) -> str:
        # Keep the capital letter if the text already said "Ngày" before the date.
        return "Ngày" if m.group(1) == "N" else "ngày"

    def full_date(m: re.Match) -> str:
        d, mo, y = int(m.group(2)), int(m.group(3)), int(m.group(4))
        if not (1 <= d <= 31 and 1 <= mo <= 12):
            return m.group(0)
        return f"{_ngay(m)} {_day(d, dialect)} tháng {_month(mo, dialect)} năm {read_number(y, dialect)}"

    def short_date(m: re.Match) -> str:
        d, mo = int(m.group(2)), int(m.group(3))
        if not (1 <= d <= 31 and 1 <= mo <= 12):
            return m.group(0)
        return f"{_ngay(m)} {_day(d, dialect)} tháng {_month(mo, dialect)}"

    def time(m: re.Match) -> str:
        h, mi = int(m.group(1)), int(m.group(2))
        if h > 23 or mi > 59:
            return m.group(0)
        spoken = f"{read_number(h, dialect)} giờ"
        return spoken if mi == 0 else f"{spoken} {read_number(mi, dialect)} phút"

    def number_range(m: re.Match) -> str:
        return f"{_read_decimal(m.group(1), dialect)} đến {_read_decimal(m.group(2), dialect)}"

    def number(m: re.Match) -> str:
        dollar, num, unit = m.group(1), m.group(2), m.group(3)
        words = _read_decimal(num, dialect)
        if unit:
            words += " " + UNITS[unit]
        if dollar:
            words += " đô la"
        return words

    out = _DATE_FULL.sub(full_date, out)
    out = _DATE_SHORT.sub(short_date, out)
    out = _TIME.sub(time, out)
    # "tháng 4" names a month (April) and reads "tháng tư"; "4 tháng" (four months) is left to the number rule.
    out = _MONTH.sub(lambda m: f"{m.group(1)} {_month(int(m.group(2)), dialect)}"
                     if 1 <= int(m.group(2)) <= 12 else m.group(0), out)
    out = _RANGE.sub(number_range, out)
    out = _NUMBER.sub(number, out)
    return re.sub(r"\s+", " ", out).strip()
