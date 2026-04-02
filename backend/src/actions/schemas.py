# backend/src/actions/schemas.py
"""ActionItem 스키마 — Pydantic V2, camelCase alias."""
from datetime import date

from pydantic import BaseModel, Field


class CreateActionItemRequest(BaseModel):
    title: str
    description: str | None = None
    meeting_id: str | None = Field(default=None, alias="meetingId")
    project_id: str | None = Field(default=None, alias="projectId")
    assignee_id: str | None = Field(default=None, alias="assigneeId")
    due_date: date | None = Field(default=None, alias="dueDate")
    priority: str = "medium"

    model_config = {"populate_by_name": True}


class UpdateActionItemRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    project_id: str | None = Field(default=None, alias="projectId")
    assignee_id: str | None = Field(default=None, alias="assigneeId")
    due_date: date | None = Field(default=None, alias="dueDate")
    priority: str | None = None
    status: str | None = None

    model_config = {"populate_by_name": True}
