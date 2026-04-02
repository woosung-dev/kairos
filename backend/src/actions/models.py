# backend/src/actions/models.py
"""ActionItem 관련 모델."""
import uuid
from datetime import date, datetime

from sqlmodel import Field, SQLModel


class ActionItem(SQLModel, table=True):
    __tablename__ = "action_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id")
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
