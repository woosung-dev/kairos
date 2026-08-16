# apps/api/src/inbox/models.py
"""InboxItem 관련 모델."""
import uuid
from datetime import datetime

from sqlmodel import JSON, Field, ForeignKeyConstraint, SQLModel


class InboxItem(SQLModel, table=True):
    __tablename__ = "inbox_items"
    __table_args__ = (
        # Sprint 21 BL-050 Simple 4: cross-workspace ai_suggested_project_id 차단.
        # nullable FK → MATCH SIMPLE NULL row 면제 (AI 추천 없는 inbox 정상).
        ForeignKeyConstraint(
            ["workspace_id", "ai_suggested_project_id"],
            ["projects.workspace_id", "projects.id"],
            name="fk_inbox_suggested_project_workspace",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # Sprint 28 PERF-2 — index=True (alembic be0e82ab810c, ix_inbox_items_workspace_id 정합).
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", index=True)
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
