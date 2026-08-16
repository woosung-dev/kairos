# apps/backend/src/notes/models.py
"""노트 모델. project_id nullable — CODE 철학(마찰 최소화)."""
import uuid
from datetime import datetime

from sqlmodel import JSON, Column, Field, ForeignKeyConstraint, SQLModel, Text


class Note(SQLModel, table=True):
    __tablename__ = "notes"
    __table_args__ = (
        # Sprint 19 PR #2 D5 (BUG-C01-EXT-FK / 헌법 I-9 (9)): cross-workspace project_id insert 차단.
        # project_id nullable — PostgreSQL MATCH SIMPLE (default) 동작으로 project_id IS NULL 시 FK 면제 (의도).
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="fk_notes_project_workspace",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", index=True)
    project_id: uuid.UUID | None = Field(
        default=None, foreign_key="projects.id", index=True
    )
    title: str = Field(default="")
    content: dict = Field(default_factory=dict, sa_type=JSON)
    plain_text: str = Field(default="", sa_column=Column(Text, server_default=""))
    created_by_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
