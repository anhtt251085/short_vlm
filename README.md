# Short Video Studio

A small web app that turns a topic or product into a 9:16 story video. A cartoon presenter poses and holds a prop that matches each line of narration, with optional Vietnamese or English voiceover and a slow camera move. The app also writes caption text to post yourself.

## What it does

1. **Topic:** enter a name, description, language, tone, and optional product photo.
2. **Story brief:** the Brief Agent writes a story with five scenes: problem, idea, action, result, and call to action. Each scene has a presenter pose and a prop. It uses an LLM if `ANTHROPIC_API_KEY` is set, otherwise a rule-based template. Everything can be edited.
3. **Render:** draws each scene with Pillow, adds a slow zoom with ffmpeg, joins the scenes, and adds a voiceover (gTTS) if enabled. Output is a 1080×1920 MP4.
4. **Check:** technical QA (aspect ratio, duration, audio track, file size).
5. **Post text:** caption and hashtags to paste into TikTok, YouTube Shorts, or Reels. The app does not post for you.

Risky advertising words ("best", "guaranteed", "cures", and Vietnamese equivalents) are flagged for review.

**Not yet built:** generated (text-to-video) clips and a VLM check of clips against the narration. See `docs/product-feasibility-plan.md`.

## Run locally

Requirements: Python 3.10+, ffmpeg (with ffprobe) on PATH, internet access for voiceover.

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000.

Optional environment variables:

| Variable | Purpose | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Enables the LLM brief | unset (template brief) |
| `BRIEF_MODEL` | Model for the brief | `claude-haiku-5-5` |
| `ANTHROPIC_BASE_URL` | API base URL | `https://api.anthropic.com` |
| `DATA_DIR` | Where projects and videos are stored | `./data` |

## Presenter poses and props

- **Poses:** idle, thinking, pointing, happy, worried, celebrate
- **Props:** none, lightbulb, chart_up, checklist, coins, phone, question, cart, clock, customer, trophy

Add a prop by writing a function in `app/illustrate.py` and registering it in `PROP_FUNCS`.

To draw a fresh presenter image, run:

```bash
python scripts/make_character.py character.png
```

## Tests

```bash
python -m pytest -q tests
```

## Layout

```
app/
  main.py        FastAPI routes
  brief.py       Brief Agent (story template, LLM with fallback, claims check)
  illustrate.py  Presenter poses and props (Pillow)
  render.py      Scenes, camera move, voiceover (gTTS), MP4 assembly (ffmpeg)
  qa.py          Technical checks via ffprobe
  schemas.py     Pydantic models
static/index.html    Single-page UI
scripts/make_character.py   Draws the default presenter as a PNG
tests/                API and render tests
docs/product-feasibility-plan.md   Feasibility, business plan, architecture, implementation plan (rev. 2)
model_lab/          Separate project: fine-tuning our own video, speech, and voice models
```

## Known limits

- Visuals are simple drawn shapes. The presenter style is basic.
- Only one presenter design; poses and props are limited to the lists above.
- Voiceover uses gTTS, which needs internet and is not a commercial-grade voice.
- With voiceover, the video length follows the narration, so it can be shorter than the target length.
- No generated video clips yet. A text-to-video adapter is planned.
- No frame-level AI check yet; QA is technical only.
- Single user, no login, local file storage.
- Posting is manual. Automatic posting needs platform API approval first.
