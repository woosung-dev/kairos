# backend/src/workspaces/models.py
"""Workspace 모델."""
import uuid
from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Workspace(SQLModel, table=True):
    __tablename__ = "workspaces"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    owner_id: uuid.UUID = Field(foreign_key="users.id")
    # Sprint 15: 'personal' | 'team' (default 'team' — 기존 row 호환)
    type: str = Field(default="team", nullable=False)
    inbox_threshold: float = Field(default=0.9)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WorkspaceMember(SQLModel, table=True):
    __tablename__ = "workspace_members"
    # BUG-WS-MEMBER-UNIQUE (S28b): (workspace_id, user_id) DB UNIQUE backstop.
    # lazy-seed/invite-accept 의 app-level NOT EXISTS 가드는 멀티워커(Cloud Run >1
    # 인스턴스) interleave 에 backstop 없음 → 중복 멤버십 row 가능. DB 제약으로 차단.
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id")
    user_id: uuid.UUID = Field(foreign_key="users.id")
    role: str = "member"  # owner | admin | member | viewer
    # W-5: 초대 수락 시 invite.default_project_visibility 복사 — 이 멤버가 프로젝트
    # 생성 시 visibility 미지정이면 적용되는 기본값 (null = 워크스페이스 기본 public)
    default_project_visibility: str | None = Field(default=None)


class WorkspaceInvite(SQLModel, table=True):
    """워크스페이스 초대 링크 (Sprint 6 L-8: default_project_visibility 추가)."""
    __tablename__ = "workspace_invites"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id")
    code: str = Field(index=True, unique=True)  # nanoid 12자리
    role: str = "member"  # 초대 시 부여할 역할
    default_project_visibility: str = "public"  # public | draft | private (Sprint 6 L-8)
    created_by_id: uuid.UUID = Field(foreign_key="users.id")
    max_uses: int | None = None  # null = 무제한
    use_count: int = 0
    expires_at: datetime | None = None  # null = 만료 없음
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
