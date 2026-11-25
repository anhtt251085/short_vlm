"""Brief Agent: turns product info into a structured short-video brief.

Uses an LLM when ANTHROPIC_API_KEY is set; otherwise falls back to a
deterministic template so the app works offline.
"""

from __future__ import annotations

import json
import os
import re

import httpx

from .schemas import Brief, Beat, ProjectIn

# Words that commonly create legal risk in product advertising.
RISKY_TERMS = [
    "best", "guaranteed", "guarantee", "cure", "miracle", "100%", "free forever",
    "tốt nhất", "đảm bảo", "chữa", "chữa khỏi", "số 1", "hiệu quả 100%", "cam kết",
]


def find_claims(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({t for t in RISKY_TERMS if t in lowered})


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [p.strip(" -•") for p in parts if p.strip(" -•")]


def template_brief(data: ProjectIn) -> Brief:
    name = data.product_name
    feats = _sentences(data.description)[:3]
    if data.language == "vi":
        hook = f"Bạn đã biết về {name} chưa?"
        beats = [Beat(on_screen=hook, voiceover=hook)]
        for f in feats or [f"{name} là lựa chọn đáng thử."]:
            beats.append(Beat(on_screen=f[:60], voiceover=f))
        cta = "Nhấn follow để xem thêm!"
        hashtags = ["#review", "#muasamonline", "#xuhuong"]
    else:
        hook = f"Meet {name}"
        beats = [Beat(on_screen=hook, voiceover=hook)]
        for f in feats or [f"{name} is worth a try."]:
            beats.append(Beat(on_screen=f[:60], voiceover=f))
        cta = "Follow for more!"
        hashtags = ["#review", "#shopping", "#fyp"]
    text_all = " ".join([data.product_name, data.description])
    caption = " ".join(b.voiceover for b in beats)[:300]
    return Brief(
        hook=hook,
        beats=beats,
        cta=cta,
        caption=caption,
        hashtags=hashtags,
        claims_flags=find_claims(text_all),
    )


PROMPT = """You write short vertical product videos (9:16).
Return ONLY a JSON object with keys:
hook (string), beats (list of {{"on_screen": string <=60 chars, "voiceover": string}}, 3 to 5 items),
cta (string), caption (string), hashtags (list of strings starting with #), background (hex color), accent (hex color).
Language for all text: {lang_name}. Tone: {tone}. Target length: about {seconds} seconds.
Avoid absolute or unverifiable claims (best, guaranteed, cures, 100%).

Product: {name}
Details: {desc}
"""


def llm_brief(data: ProjectIn) -> Brief:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("no LLM key")
    base = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
    model = os.environ.get("BRIEF_MODEL", "claude-haiku-5-5")
    prompt = PROMPT.format(
        lang_name="Vietnamese" if data.language == "vi" else "English",
        tone=data.tone,
        seconds=data.target_seconds,
        name=data.product_name,
        desc=data.description or "(none provided)",
    )
    resp = httpx.post(
        f"{base}/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
        json={
            "model": model,
            "max_tokens": 1200,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    text = "".join(b.get("text", "") for b in resp.json()["content"] if b.get("type") == "text")
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("no JSON in model output")
    raw = json.loads(match.group(0))
    brief = Brief.model_validate(raw)
    brief.claims_flags = find_claims(
        " ".join([brief.hook, brief.caption] + [b.voiceover for b in brief.beats])
    )
    return brief


def make_brief(data: ProjectIn) -> tuple[Brief, str]:
    """Return (brief, source). Falls back to the template if the LLM fails."""
    try:
        return llm_brief(data), "llm"
    except Exception:
        return template_brief(data), "template"
