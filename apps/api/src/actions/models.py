# apps/api/src/actions/models.py
"""ActionItem 관련 모델."""
import uuid
from datetime import date, datetime

from sqlmodel import Field, ForeignKeyConstraint, SQLModel


class ActionItem(SQLModel, table=True):
    __tablename__ = "action_items"
    __table_args__ = (
        # Sprint 19 PR #2 D4 (BUG-C01-EXT-FK / 헌법 I-9 (9)): cross-workspace project_id insert 차단.
        # 기존 single-FK (workspace_id → workspaces.id, project_id → projects.id) 유지 — defense-in-depth.
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="fk_action_items_project_workspace",
        ),
        # Sprint 21 BL-050 Simple 4: cross-workspace meeting_id insert 차단.
        # 기존 single-FK (meeting_id → meetings.id) 유지 — defense-in-depth.
        # meetings(id, workspace_id) UNIQUE 는 PR #2 alembic revision
        # e5f6g7h8i9ja (sprint19_pr2_composite_fk) 에서 신설됨.
        # nullable FK → MATCH SIMPLE NULL row 면제.
        ForeignKeyConstraint(
            ["workspace_id", "meeting_id"],
            ["meetings.workspace_id", "meetings.id"],
            name="fk_action_items_meeting_workspace",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # Sprint 28 PERF-2 — index=True (alembic be0e82ab810c, ix_action_items_workspace_id 정합).
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", index=True)
    meeting_id: uuid.UUID | None = Field(default=None, foreign_key="meetings.id")
    project_id: uuid.UUID | None = Field(default=None, foreign_key="projects.id")
    title: str
    description: str | None = None
    assignee_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    due_date: date | None = None
    priority: str = "medium"  # high | medium | low
    status: str = "todo"  # todo | in_progress | done | cancelled
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
