# apps/backend/src/workspaces/member_router.py
"""멤버 관리 엔드포인트."""
import uuid

from fastapi import APIRouter, Depends, HTTPException

from src.auth.rbac import require_admin, require_owner, require_viewer
from src.workspaces.dependencies import get_invite_service
from src.workspaces.exceptions import CannotModifyOwnerError, MemberNotFoundError
from src.workspaces.invite_service import InviteService
from src.workspaces.models import WorkspaceMember
from src.workspaces.schemas import UpdateMemberRoleRequest

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/members",
    tags=["members"],
)


@router.get("")
async def list_members(
    workspace_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_viewer),
    service: InviteService = Depends(get_invite_service),
):
    """멤버 목록 조회. Viewer 이상."""
    return await service.list_members(workspace_id)


@router.patch("/{member_id}")
async def update_member_role(
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    data: UpdateMemberRoleRequest,
    member: WorkspaceMember = Depends(require_owner),
    service: InviteService = Depends(get_invite_service),
):
    """멤버 역할 변경. Owner만."""
    try:
        return await service.update_member_role(workspace_id, member_id, data.role)
    except MemberNotFoundError:
        raise HTTPException(404, "멤버를 찾을 수 없습니다")
    except CannotModifyOwnerError:
        raise HTTPException(403, "Owner의 역할은 변경할 수 없습니다")


@router.delete("/{member_id}", status_code=204)
async def remove_member(
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_admin),
    service: InviteService = Depends(get_invite_service),
):
    """멤버 제거. Admin 이상."""
    try:
        await service.remove_member(workspace_id, member_id)
    except MemberNotFoundError:
        raise HTTPException(404, "멤버를 찾을 수 없습니다")
    except CannotModifyOwnerError:
        raise HTTPException(403, "Owner는 제거할 수 없습니다")
