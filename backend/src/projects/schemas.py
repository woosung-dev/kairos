# backend/src/projects/schemas.py
"""Project 스키마 — Pydantic V2, camelCase alias."""
from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    title: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class UpdateProjectRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    tags: list[str] | None = None

    model_config = {"populate_by_name": True}


class AddMeetingProjectRequest(BaseModel):
    project_id: str = Field(alias="projectId")

    model_config = {"populate_by_name": True}
