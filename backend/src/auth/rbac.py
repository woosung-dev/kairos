# backend/src/auth/rbac.py
"""역할 기반 접근 제어 (RBAC). Depends()로 라우터에 주입."""
import uuid

from fastapi import Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.common.database import get_async_session
from src.workspaces.models import WorkspaceMember
from src.workspaces.repository import WorkspaceRepository

# 역할 레벨: 숫자가 높을수록 강한 권한
ROLE_LEVEL: dict[str, int] = {
    "viewer": 1,
    "member": 2,
    "admin": 3,
    "owner": 4,
}


class RoleChecker:
    """최소 역할 요구 검증. Depends()로 사용.

    Usage:
        @router.post("")
        async def create(
            workspace_id: uuid.UUID,
            member: WorkspaceMember = Depends(require_member),
        ):
            ...
    """

    def __init__(self, min_role: str) -> None:
        if min_role not in ROLE_LEVEL:
            raise ValueError(f"유효하지 않은 역할: {min_role}")
        self.min_role = min_role

    async def __call__(
        self,
        workspace_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session),
    ) -> WorkspaceMember:
        repo = WorkspaceRepository(session)
        member = await repo.find_member(workspace_id, current_user.id)
        if member is None:
            raise HTTPException(
                status_code=403, detail="워크스페이스 멤버가 아닙니다"
            )
        member_level = ROLE_LEVEL.get(member.role, 0)
        if member_level < ROLE_LEVEL[self.min_role]:
            raise HTTPException(
                status_code=403,
                detail=f"{self.min_role} 이상 권한이 필요합니다",
            )
        return member


# 사전 정의 의존성 — 라우터에서 Depends(require_member) 형태로 사용
require_viewer = RoleChecker("viewer")
require_member = RoleChecker("member")
require_admin = RoleChecker("admin")
require_owner = RoleChecker("owner")
