"""Data contracts for projects and briefs."""

from __future__ import annotations

from typing import Literal

from .illustrate import POSES, PROPS

from pydantic import BaseModel, Field


class ProjectIn(BaseModel):
    product_name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    language: Literal["vi", "en"] = "vi"
    target_seconds: int = Field(default=20, ge=5, le=60)
    tone: str = Field(default="friendly", max_length=40)
    use_voice: bool = True


class Visual(BaseModel):
    pose: str = "idle"  # one of illustrate.POSES
    prop: str = "none"  # one of illustrate.PROPS

    def sanitized(self) -> "Visual":
        return Visual(
            pose=self.pose if self.pose in POSES else "idle",
            prop=self.prop if self.prop in PROPS else "none",
        )


class Beat(BaseModel):
    on_screen: str = Field(min_length=1, max_length=120)
    voiceover: str = Field(default="", max_length=400)
    visual: Visual = Field(default_factory=Visual)


class Brief(BaseModel):
    story: str = Field(default="problem_idea_action_result", max_length=60)
    hook: str = Field(min_length=1, max_length=200)
    beats: list[Beat] = Field(min_length=1, max_length=8)
    cta: str = Field(min_length=1, max_length=120)
    caption: str = Field(default="", max_length=2200)
    hashtags: list[str] = Field(default_factory=list, max_length=15)
    background: str = Field(default="#1f2a44", pattern=r"^#[0-9a-fA-F]{6}$")
    accent: str = Field(default="#ffb703", pattern=r"^#[0-9a-fA-F]{6}$")
    ai_disclosure: bool = True
    character: bool = True
    claims_flags: list[str] = Field(default_factory=list)


class Project(BaseModel):
    id: str
    input: ProjectIn
    brief: Brief | None = None
    brief_source: Literal["llm", "template", "user"] | None = None
    image: str | None = None
    video: str | None = None
    qa: list[dict] | None = None
    created_at: str
