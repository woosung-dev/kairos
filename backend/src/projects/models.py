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
    visibility: str = Field(default="public", index=True)  # public | draft | private
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


class ProjectMember(SQLModel, table=True):
    """visibility=Private일 때 명시적으로 매핑된 Project 멤버 (Sprint 6 L-6, AD-27).

    workspace_id 강제 필터(헌법 I-9) — 멤버 추가 시 동일 워크스페이스 검증은 service 책임.
    role은 향후 Sprint 7+ 확장 여지로 두되 1차는 'member' 단일 사용 (AD-27).
    """
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_member"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    role: str = "member"  # Sprint 6: member 단일. Sprint 7+: project_admin 등 확장 (AD-27)
    created_at: datetime = Field(default_factory=datetime.utcnow)
