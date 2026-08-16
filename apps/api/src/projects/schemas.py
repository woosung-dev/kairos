# apps/api/src/projects/schemas.py
"""Project 스키마 — Pydantic V2, camelCase alias."""
from typing import Literal

from pydantic import BaseModel, Field

VisibilityLiteral = Literal["public", "draft", "private"]


class CreateProjectRequest(BaseModel):
    title: str
    description: str | None = None
    # None = 미지정 → 멤버의 default_project_visibility 시드(W-5), 없으면 public
    visibility: VisibilityLiteral | None = None
    tags: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class UpdateProjectRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    visibility: VisibilityLiteral | None = None
    tags: list[str] | None = None

    model_config = {"populate_by_name": True}


class AddMeetingProjectRequest(BaseModel):
    project_id: str = Field(alias="projectId")

    model_config = {"populate_by_name": True}
