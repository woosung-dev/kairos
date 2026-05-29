# backend/src/auth/rbac.py
"""역할 기반 접근 제어 (RBAC). Depends()로 라우터에 주입."""
import time
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

# Sprint 28 BUG-S28-PERF-RT-1 fix — WorkspaceMember in-process TTL cache.
# Round B 측정: dashboard 4 endpoint × RBAC SELECT × Neon RTT (1-2s) 가 fanout critical path
# 의 큰 부분. JWT cache + User cache 와 동일 60s TTL 패턴. cache hit 시 SELECT 0.
# role 변경/제거 → invite_service 가 invalidate_member_cache() 호출로 즉시 반영
# (BUG-RBAC-CACHE-STALE fix). 그 외 경로는 60s TTL 내 자연 만료.
_MEMBER_CACHE: dict[tuple[uuid.UUID, uuid.UUID], tuple[WorkspaceMember, float]] = {}
_MEMBER_CACHE_TTL_SEC = 60.0
_MEMBER_CACHE_MAX_SIZE = 2000


def _member_cache_get(
    workspace_id: uuid.UUID, user_id: uuid.UUID
) -> WorkspaceMember | None:
    key = (workspace_id, user_id)
    entry = _MEMBER_CACHE.get(key)
    if entry is None:
        return None
    member, expires_at = entry
    if time.time() >= expires_at:
        _MEMBER_CACHE.pop(key, None)
        return None
    return member


def _member_cache_set(
    workspace_id: uuid.UUID, user_id: uuid.UUID, member: WorkspaceMember
) -> None:
    now = time.time()
    if len(_MEMBER_CACHE) >= _MEMBER_CACHE_MAX_SIZE:
        expired = [k for k, (_, exp) in _MEMBER_CACHE.items() if exp <= now]
        for k in expired:
            _MEMBER_CACHE.pop(k, None)
        if len(_MEMBER_CACHE) >= _MEMBER_CACHE_MAX_SIZE:
            oldest = next(iter(_MEMBER_CACHE))
            _MEMBER_CACHE.pop(oldest, None)
    _MEMBER_CACHE[(workspace_id, user_id)] = (member, now + _MEMBER_CACHE_TTL_SEC)


def invalidate_member_cache(workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """role 변경 / member remove 직후 호출 권고 (60s 지연 회피)."""
    _MEMBER_CACHE.pop((workspace_id, user_id), None)


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
        # Sprint 28 BUG-S28-PERF-RT-1 — cache hit 시 SELECT 0.
        member = _member_cache_get(workspace_id, current_user.id)
        if member is None:
            repo = WorkspaceRepository(session)
            member = await repo.find_member(workspace_id, current_user.id)
            if member is None:
                raise HTTPException(
                    status_code=403, detail="워크스페이스 멤버가 아닙니다"
                )
            _member_cache_set(workspace_id, current_user.id, member)
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
