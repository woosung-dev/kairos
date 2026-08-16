# apps/backend/src/workspaces/invite_router.py
"""초대 링크 엔드포인트."""
import uuid

from fastapi import APIRouter, Depends, HTTPException

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.auth.rbac import require_admin
from src.workspaces.dependencies import get_invite_service
from src.workspaces.exceptions import (
    InviteExpiredError,
    InviteNotFoundError,
    MemberAlreadyExistsError,
)
from src.workspaces.invite_service import InviteService
from src.workspaces.models import WorkspaceMember
from src.workspaces.schemas import CreateInviteRequest

# 워크스페이스 내 초대 관리 (Admin 이상)
router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/invites",
    tags=["invites"],
)

# 공개 초대 링크 (인증 필요/불필요 혼합)
public_router = APIRouter(
    prefix="/api/v1/invites",
    tags=["invites"],
)


@router.post("", status_code=201)
async def create_invite(
    workspace_id: uuid.UUID,
    data: CreateInviteRequest,
    member: WorkspaceMember = Depends(require_admin),
    service: InviteService = Depends(get_invite_service),
):
    """초대 링크 생성. Admin 이상만."""
    return await service.create_invite(
        workspace_id=workspace_id,
        created_by_id=member.user_id,
        role=data.role,
        default_project_visibility=data.default_project_visibility,
        max_uses=data.max_uses,
        expires_in_days=data.expires_in_days,
    )


@router.get("")
async def list_invites(
    workspace_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_admin),
    service: InviteService = Depends(get_invite_service),
):
    """활성 초대 링크 목록. Admin 이상만."""
    return await service.list_invites(workspace_id)


@router.delete("/{invite_id}", status_code=204)
async def deactivate_invite(
    workspace_id: uuid.UUID,
    invite_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_admin),
    service: InviteService = Depends(get_invite_service),
):
    """초대 링크 비활성화. Admin 이상만."""
    await service.deactivate_invite(workspace_id, invite_id)


# --- 공개 엔드포인트 ---


@public_router.get("/{code}")
async def get_invite_info(
    code: str,
    service: InviteService = Depends(get_invite_service),
):
    """초대 링크 정보 조회 (인증 불필요)."""
    return await service.get_invite_info(code)


@public_router.post("/{code}/accept")
async def accept_invite(
    code: str,
    current_user: User = Depends(get_current_user),
    service: InviteService = Depends(get_invite_service),
):
    """초대 수락 → 멤버 추가 (인증 필요)."""
    try:
        return await service.accept_invite(code, current_user.id)
    except InviteNotFoundError:
        raise HTTPException(404, "존재하지 않는 초대 링크입니다")
    except InviteExpiredError as e:
        raise HTTPException(410, str(e.reason))
    except MemberAlreadyExistsError:
        raise HTTPException(409, "이미 워크스페이스 멤버입니다")
