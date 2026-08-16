# apps/api/src/projects/models.py
"""Project 관련 모델."""
import uuid
from datetime import datetime

from sqlmodel import JSON, Field, ForeignKeyConstraint, SQLModel, UniqueConstraint


class Project(SQLModel, table=True):
    __tablename__ = "projects"
    __table_args__ = (
        # Sprint 19 PR #2 D3a (Codex v2 F-2): alembic 7ebd009f89a4 의 DB UQ 와 model 정합성
        # composite FK target 선행 조건 (action_items / notes / mpl / project_members 가 모두 참조)
        UniqueConstraint("id", "workspace_id", name="uq_projects_id_workspace_id"),
    )

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
        # Sprint 19 PR #2 D6 (BUG-C01-EXT-FK / 헌법 I-9 (9)(10)):
        # workspace_id 컬럼 신설 + 양쪽 composite FK (project + meeting) = cross-workspace 링크 차단.
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="fk_mpl_project_workspace",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "meeting_id"],
            ["meetings.workspace_id", "meetings.id"],
            name="fk_mpl_meeting_workspace",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", index=True)
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
        UniqueConstraint("id", "workspace_id", name="uq_project_member_ws"),
        # Sprint 19 PR #2 D7 (column 순서는 alembic 7ebd009f89a4 정의 그대로 — (project_id, workspace_id) → (id, workspace_id))
        # DB-level composite FK 는 이미 존재 — alembic 변경 X, model 만 sync, schema drift 방지
        ForeignKeyConstraint(
            ["project_id", "workspace_id"],
            ["projects.id", "projects.workspace_id"],
            name="fk_project_members_project_workspace",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", index=True)
    role: str = "member"  # Sprint 6: member 단일. Sprint 7+: project_admin 등 확장 (AD-27)
    created_at: datetime = Field(default_factory=datetime.utcnow)
