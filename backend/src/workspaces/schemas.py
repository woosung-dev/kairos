# backend/src/workspaces/schemas.py
"""Workspace 스키마."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CreateWorkspaceRequest(BaseModel):
    name: str


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class WorkspaceDetailResponse(WorkspaceResponse):
    member_count: int = 0


# --- 멤버 관리 ---


class MemberResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str | None = None
    display_name: str | None = None
    role: str


class UpdateMemberRoleRequest(BaseModel):
    role: str = Field(pattern=r"^(admin|member|viewer)$")


# --- 초대 링크 ---


class CreateInviteRequest(BaseModel):
    role: str = Field(default="member", pattern=r"^(admin|member|viewer)$")
    max_uses: int | None = Field(default=None, ge=1)
    expires_in_days: int | None = Field(default=7, ge=1, le=30)


class InviteResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    code: str
    role: str
    invite_url: str
    max_uses: int | None
    use_count: int
    expires_at: datetime | None
    is_active: bool
    created_at: datetime


class InviteInfoResponse(BaseModel):
    """초대 링크 공개 정보 (인증 불필요)."""
    workspace_name: str
    inviter_name: str | None
    role: str
    is_valid: bool
    reason: str | None = None  # 무효 시 사유
