"""FastAPI app: create a project, generate a brief, edit it, render a video."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from . import brief as brief_agent
from . import qa
from .render import render_video
from .schemas import Brief, Project, ProjectIn

DATA = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
PROJECTS = DATA / "projects"
FILES = DATA / "files"
for d in (PROJECTS, FILES):
    d.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Short Video Studio", version="0.1.0")
STATIC = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _load(pid: str) -> Project:
    f = PROJECTS / f"{pid}.json"
    if not f.exists():
        raise HTTPException(404, "project not found")
    return Project.model_validate_json(f.read_text())


def _save(p: Project) -> None:
    (PROJECTS / f"{p.id}.json").write_text(p.model_dump_json(indent=2))


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC / "index.html").read_text(encoding="utf-8")


@app.post("/api/projects", response_model=Project)
def create_project(data: ProjectIn) -> Project:
    p = Project(
        id=uuid.uuid4().hex[:12],
        input=data,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    _save(p)
    return p


@app.get("/api/projects")
def list_projects() -> list[dict]:
    items = [json.loads(f.read_text()) for f in PROJECTS.glob("*.json")]
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return [{"id": i["id"], "name": i["input"]["product_name"], "created_at": i["created_at"],
             "has_video": bool(i.get("video"))} for i in items]


@app.get("/api/projects/{pid}", response_model=Project)
def get_project(pid: str) -> Project:
    return _load(pid)


@app.post("/api/projects/{pid}/brief", response_model=Project)
def generate_brief(pid: str) -> Project:
    p = _load(pid)
    b, source = brief_agent.make_brief(p.input)
    p.brief, p.brief_source = b, source
    p.video, p.qa = None, None
    _save(p)
    return p


@app.put("/api/projects/{pid}/brief", response_model=Project)
def save_brief(pid: str, brief: Brief) -> Project:
    """Human review/approval step: the user edits the brief before rendering."""
    p = _load(pid)
    brief.claims_flags = brief_agent.find_claims(
        " ".join([brief.hook, brief.caption] + [b.voiceover for b in brief.beats])
    )
    p.brief, p.brief_source = brief, "user"
    p.video, p.qa = None, None
    _save(p)
    return p


@app.post("/api/projects/{pid}/image", response_model=Project)
async def upload_image(pid: str, file: UploadFile = File(...)) -> Project:
    p = _load(pid)
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(400, "image must be JPEG, PNG or WebP")
    dest = FILES / f"{pid}_product{Path(file.filename or 'img').suffix or '.jpg'}"
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    p.image = str(dest)
    _save(p)
    return p


@app.post("/api/projects/{pid}/render", response_model=Project)
def render(pid: str) -> Project:
    p = _load(pid)
    if not p.brief:
        raise HTTPException(400, "generate or save a brief first")
    out = FILES / f"{pid}.mp4"
    image = Path(p.image) if p.image else None
    lang = p.input.language
    _, has_voice = render_video(
        p.brief, p.input.product_name, lang,
        work=FILES / f"{pid}_work", out=out,
        target_seconds=p.input.target_seconds, image=image,
        use_voice=p.input.use_voice,
    )
    p.video = str(out)
    p.qa = qa.check_video(out, expect_voice=has_voice)
    _save(p)
    return p


@app.get("/api/projects/{pid}/video")
def get_video(pid: str) -> FileResponse:
    p = _load(pid)
    if not p.video or not Path(p.video).exists():
        raise HTTPException(404, "no video rendered yet")
    return FileResponse(p.video, media_type="video/mp4", filename=f"{pid}.mp4")


@app.get("/api/projects/{pid}/post-text")
def post_text(pid: str) -> dict:
    """Caption and hashtags ready to paste into the platform. You post it yourself."""
    p = _load(pid)
    if not p.brief:
        raise HTTPException(400, "no brief yet")
    b = p.brief
    text = b.caption.strip()
    if b.cta and b.cta not in text:
        text = f"{text}\n{b.cta}".strip()
    if b.ai_disclosure:
        text += "\n\n(Video made with AI assistance)"
    tags = " ".join(h if h.startswith("#") else f"#{h}" for h in b.hashtags)
    return {"text": f"{text}\n\n{tags}".strip(), "claims_flags": b.claims_flags}
