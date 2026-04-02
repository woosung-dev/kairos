# backend/src/projects/models.py
"""Project 관련 모델."""
import uuid
from datetime import datetime

from sqlalchemy import JSON, UniqueConstraint
from sqlmodel import Field, SQLModel


class Project(SQLModel, table=True):
    __tablename__ = "projects"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id")
    title: str
    description: str | None = None
    status: str = "active"  # active | completed | archived
    tags: list[str] = Field(default_factory=list, sa_type=JSON)
    sort_order: int = 0
    created_by_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MeetingProjectLink(SQLModel, table=True):
    __tablename__ = "meeting_project_links"
    __table_args__ = (
        UniqueConstraint("meeting_id", "project_id", name="uq_meeting_project"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    meeting_id: uuid.UUID = Field(foreign_key="meetings.id")
    project_id: uuid.UUID = Field(foreign_key="projects.id")
