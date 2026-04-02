# backend/src/notes/models.py
"""노트 모델. project_id nullable — CODE 철학(마찰 최소화)."""
import uuid
from datetime import datetime

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


class Note(SQLModel, table=True):
    __tablename__ = "notes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", index=True)
    project_id: uuid.UUID | None = Field(
        default=None, foreign_key="projects.id", index=True
    )
    title: str = Field(default="")
    content: dict = Field(default_factory=dict, sa_type="JSON")
    plain_text: str = Field(default="", sa_column=Column(Text, server_default=""))
    created_by_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
