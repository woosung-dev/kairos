# backend/src/notes/schemas.py
"""노트 요청/응답 스키마."""
from pydantic import BaseModel, Field


class CreateNoteRequest(BaseModel):
    title: str = ""
    content: dict = Field(default_factory=dict)
    project_id: str | None = Field(default=None, alias="projectId")

    model_config = {"populate_by_name": True}


class UpdateNoteRequest(BaseModel):
    title: str | None = None
    content: dict | None = None
    project_id: str | None = Field(default=None, alias="projectId")

    model_config = {"populate_by_name": True}
