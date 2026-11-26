"""Brief Agent: turns product info into a structured short-video brief.

Uses an LLM when ANTHROPIC_API_KEY is set; otherwise falls back to a
deterministic template so the app works offline.
"""

from __future__ import annotations

import json
import os
import re

import httpx

from .illustrate import POSES, PROPS
from .schemas import Beat, Brief, ProjectIn, Visual

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


# Scene visuals for the story arc: hook (problem) -> idea -> action -> action -> call to action.
ARC_VISUALS = [
    Visual(pose="worried", prop="question"),
    Visual(pose="pointing", prop="lightbulb"),
    Visual(pose="happy", prop="checklist"),
    Visual(pose="happy", prop="chart_up"),
    Visual(pose="celebrate", prop="coins"),
]

TEXTS = {
    "vi": {
        "hook": "Bạn đang muốn kinh doanh?",
        "hook_vo": "Bạn đang muốn bắt đầu kinh doanh? Hãy xem ba bước đơn giản nhé.",
        "cta": "Nhấn follow để xem thêm mẹo kinh doanh!",
        "tags": ["#kinhdoanh", "#khoinghiep", "#meohay"],
        "idea": "Mỗi ý tưởng đều bắt đầu từ một vấn đề có thật.",
        "result": "Theo dõi thu chi mỗi tuần để biết mình lãi hay lỗ.",
        "invite": "Bắt đầu nhỏ, học nhanh, rồi mở rộng.",
    },
    "en": {
        "hook": "Want to start a business?",
        "hook_vo": "Want to start your own business? Here are three simple steps.",
        "cta": "Follow for more business tips!",
        "tags": ["#business", "#startup", "#smallbusiness"],
        "idea": "Every good business starts with a real problem people already have.",
        "result": "Track your money every week, so you know whether you are really making a profit.",
        "invite": "Start small, test fast, then grow.",
    },
}


def template_brief(data: ProjectIn) -> Brief:
    """Rule-based story brief. Works offline; the LLM path writes richer scenes."""
    name = data.product_name
    t = TEXTS[data.language]
    feats = _sentences(data.description)[:2]
    idea_on = f"Idea: {name}" if data.language == "en" else f"Ý tưởng: {name}"
    idea_vo = (f"Our idea is {name}. {t['idea']}" if data.language == "en"
               else f"Ý tưởng của chúng ta là {name}. {t['idea']}")
    middle = [(f[:60], f) for f in feats] or [(t["result"][:60], t["result"])]
    scenes = [(t["hook"], t["hook_vo"]), (idea_on, idea_vo)] + middle + [(t["cta"], t["cta"])]

    beats: list[Beat] = []
    for i, (on, vo) in enumerate(scenes):
        is_last = i == len(scenes) - 1
        visual = ARC_VISUALS[-1] if is_last else ARC_VISUALS[min(i, len(ARC_VISUALS) - 2)]
        beats.append(Beat(on_screen=on, voiceover=vo, visual=visual))

    caption = " ".join(b.voiceover for b in beats)[:300]
    return Brief(
        story="problem_idea_action_result",
        hook=t["hook"],
        beats=beats,
        cta=t["cta"],
        caption=caption,
        hashtags=t["tags"],
        claims_flags=find_claims(" ".join([name, data.description])),
    )


PROMPT = """You write short vertical story videos (9:16) with a cartoon presenter.
Tell a story with this arc: a problem the viewer has, an idea, a concrete action, a result, then an invitation.
Each beat must match its voiceover: the pose and prop must show what is being said.
Return ONLY a JSON object with keys:
story (string), hook (string),
beats (list of 4 to 5 items: {{"on_screen": string <=60 chars, "voiceover": string, "visual": {{"pose": one of {poses}, "prop": one of {props}}}}}),
cta (string), caption (string), hashtags (list of strings starting with #), background (hex color), accent (hex color).
The last beat must be the call to action.
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
        poses=", ".join(POSES),
        props=", ".join(PROPS),
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
    # Replace unknown poses or props with safe defaults instead of failing.
    for beat in raw.get("beats", []):
        vis = Visual.model_validate(beat.get("visual") or {}).sanitized()
        beat["visual"] = vis.model_dump()
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
