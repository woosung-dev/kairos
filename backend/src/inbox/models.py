# backend/src/inbox/models.py
"""InboxItem 관련 모델."""
import uuid
from datetime import datetime

from sqlalchemy import JSON
from sqlmodel import Field, SQLModel


class InboxItem(SQLModel, table=True):
    __tablename__ = "inbox_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id")
    title: str
    summary: str | None = None
    source_type: str  # meeting | note | attachment
    source_id: uuid.UUID
    ai_suggested_project_id: uuid.UUID | None = Field(
        default=None, foreign_key="projects.id"
    )
    ai_suggested_project_title: str | None = None
    ai_suggested_tags: list[str] = Field(default_factory=list, sa_type=JSON)
    ai_confidence: float = 0.0
    is_processed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
