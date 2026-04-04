# backend/src/workspaces/models.py
"""Workspace 모델."""
import uuid
from datetime import datetime, UTC

from sqlmodel import Field, SQLModel


class Workspace(SQLModel, table=True):
    __tablename__ = "workspaces"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    owner_id: uuid.UUID = Field(foreign_key="users.id")
    inbox_threshold: float = Field(default=0.9)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkspaceMember(SQLModel, table=True):
    __tablename__ = "workspace_members"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id")
    user_id: uuid.UUID = Field(foreign_key="users.id")
    role: str = "member"  # owner | admin | member | viewer


class WorkspaceInvite(SQLModel, table=True):
    """워크스페이스 초대 링크."""
    __tablename__ = "workspace_invites"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id")
    code: str = Field(index=True, unique=True)  # nanoid 12자리
    role: str = "member"  # 초대 시 부여할 역할
    created_by_id: uuid.UUID = Field(foreign_key="users.id")
    max_uses: int | None = None  # null = 무제한
    use_count: int = 0
    expires_at: datetime | None = None  # null = 만료 없음
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
