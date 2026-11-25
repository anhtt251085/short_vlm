# Short Video Studio

A small web app that turns a product or topic into a 9:16 short video with captions and optional Vietnamese or English voiceover, plus caption text to post yourself.

## What it does

1. **Product:** enter a name, description, language, tone, and optional product photo.
2. **Brief:** a Brief Agent writes the hook, beats, call to action, caption, and hashtags. It uses an LLM if `ANTHROPIC_API_KEY` is set, otherwise a built-in template. You can edit everything.
3. **Render:** builds a 1080x1920 MP4 with ffmpeg, with voiceover (gTTS) if enabled.
4. **Check:** automatic QA (aspect ratio, duration, audio track, file size).
5. **Post text:** caption and hashtags to paste into TikTok, YouTube Shorts, or Reels. The app does not post for you.

Risky advertising words ("best", "guaranteed", "cures", and Vietnamese equivalents) are flagged for review.

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

## Tests

```bash
python -m pytest -q tests
```

## Layout

```
app/
  main.py      FastAPI routes
  brief.py     Brief Agent (LLM with template fallback, claims check)
  render.py    Cards (Pillow), segments and audio (ffmpeg), voiceover (gTTS)
  qa.py        Technical checks via ffprobe
  schemas.py   Pydantic models
static/index.html   Single-page UI
tests/              API and render tests
docs/product-feasibility-plan.md   Feasibility, business, architecture, and implementation plan
```

## Known limits (MVP)

- Visuals are text cards with a product photo; no motion or AI-generated footage yet.
- With voiceover, the video length follows the voice, so it may be shorter than the target length.
- No frame-level AI check yet; QA is technical only.
- Voiceover uses Google's TTS service through gTTS, which needs internet access and is not a commercial-grade voice.
- Single user, no login, local file storage.
- Posting is manual. Automatic posting needs platform API approval first (see the plan document).
