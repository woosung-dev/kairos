# apps/api/src/workspaces/schemas.py
"""Workspace 스키마."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class CreateWorkspaceRequest(BaseModel):
    name: str


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    # Sprint 15 R6: 'personal' | 'team'. legacy row 보호용 default 'team' (DB type 컬럼 NULL 방어).
    type: str = "team"
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
    default_project_visibility: str = Field(
        default="public",
        pattern=r"^(public|draft|private)$",
        alias="defaultProjectVisibility",
    )
    max_uses: int | None = Field(default=None, ge=1, alias="maxUses")
    expires_in_days: int | None = Field(default=7, ge=1, le=30, alias="expiresInDays")

    model_config = {"populate_by_name": True}


class InviteResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    code: str
    role: str
    default_project_visibility: str = "public"
    invite_url: str
    max_uses: int | None
    use_count: int
    expires_at: datetime | None
    is_active: bool
    created_at: datetime


class UpdateWorkspaceSettingsRequest(BaseModel):
    """PATCH settings 본문 — 부분 갱신. 전달된 필드만 반영한다."""
    inbox_threshold: float | None = Field(
        default=None, ge=0.5, le=1.0, alias="inboxThreshold"
    )
    name: str | None = Field(default=None, min_length=1, max_length=60)

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def _validate_partial_update(self) -> "UpdateWorkspaceSettingsRequest":
        # 공백만 있는 이름은 min_length 를 통과하므로 strip 후 다시 검사한다.
        if self.name is not None:
            stripped = self.name.strip()
            if not stripped:
                raise ValueError("name must not be blank")
            self.name = stripped
        # 빈 PATCH 는 updated_at 만 건드리는 무의미한 쓰기라 422 로 막는다.
        if self.inbox_threshold is None and self.name is None:
            raise ValueError("at least one of inboxThreshold or name is required")
        return self


class InviteInfoResponse(BaseModel):
    """초대 링크 공개 정보 (인증 불필요)."""
    workspace_name: str
    inviter_name: str | None
    role: str
    is_valid: bool
    reason: str | None = None  # 무효 시 사유
