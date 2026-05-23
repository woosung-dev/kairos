# Sprint 5: RBAC + 초대 시스템 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 워크스페이스 RBAC 역할 검증 + 초대 링크 시스템 구현. 내부 팀 5명이 역할별로 사용 가능.

**Architecture:** 기존 `get_current_user()` 위에 `RoleChecker` 레이어 추가. 모든 기존 라우터에 최소 역할 의존성 주입. 초대는 `WorkspaceInvite` 모델 + nanoid 코드 기반.

**Tech Stack:** FastAPI + SQLModel + Alembic + Clerk JWT (기존 스택)

---

## File Map

### 새로 생성
| 파일 | 역할 |
|------|------|
| `backend/src/workspaces/models.py` | `WorkspaceInvite` 모델 추가 (기존 파일에 append) |
| `backend/src/auth/rbac.py` | `RoleChecker`, `ROLE_LEVEL`, `require_*` 의존성 |
| `backend/src/workspaces/invite_service.py` | 초대 링크 생성/수락 비즈니스 로직 |
| `backend/src/workspaces/invite_router.py` | 초대 관련 엔드포인트 |
| `backend/src/workspaces/member_router.py` | 멤버 관리 엔드포인트 (목록/역할변경/제거) |
| `backend/alembic/versions/*_add_workspace_invites.py` | 마이그레이션 |
| `backend/tests/auth/test_rbac.py` | RoleChecker 단위 테스트 |
| `backend/tests/workspaces/test_invite.py` | 초대 flow 테스트 |
| `frontend/src/features/members/types.ts` | Member/Invite 타입 |
| `frontend/src/features/members/api.ts` | API 호출 + Query Key |
| `frontend/src/features/members/hooks.ts` | React Query 훅 |
| `frontend/src/features/members/components/member-list.tsx` | 멤버 목록 컴포넌트 |
| `frontend/src/features/members/components/invite-manager.tsx` | 초대 링크 관리 |
| `frontend/src/app/(app)/settings/members/page.tsx` | 설정 페이지 |
| `frontend/src/app/(public)/invite/[code]/page.tsx` | 초대 수락 페이지 |
| `frontend/src/store/auth.ts` | 인증+역할 상태 |

### 수정
| 파일 | 변경 |
|------|------|
| `backend/src/workspaces/repository.py` | `find_member`, `update_member_role`, `remove_member`, invite CRUD 추가 |
| `backend/src/workspaces/schemas.py` | 멤버/초대 스키마 추가 |
| `backend/src/workspaces/exceptions.py` | 새 예외 추가 |
| `backend/src/main.py` | invite_router, member_router 등록 |
| `backend/src/meetings/router.py` | `get_current_user` → `require_member`/`require_viewer` |
| `backend/src/projects/router.py` | 역할 검증 추가 |
| `backend/src/inbox/router.py` | 역할 검증 추가 |
| `backend/src/notes/router.py` | 역할 검증 추가 |
| `backend/src/actions/router.py` | 역할 검증 추가 |
| `backend/src/rag/router.py` | `require_viewer` 추가 |
| `backend/src/upload/router.py` | `require_member` 추가 |
| `frontend/src/components/layout/sidebar.tsx` | 설정 링크 추가 |

---

## Task 1: RoleChecker 미들웨어

**Files:**
- Create: `backend/src/auth/rbac.py`
- Modify: `backend/src/workspaces/repository.py`
- Test: `backend/tests/auth/test_rbac.py`

- [ ] **Step 1: WorkspaceRepository에 find_by_workspace_and_user 추가**

```python
# backend/src/workspaces/repository.py — 기존 find_member를 활용하되 명확한 이름 추가

    async def find_by_workspace_and_user(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkspaceMember | None:
        """워크스페이스-유저 조합으로 멤버 조회. RBAC 검증용."""
        return await self.find_member(workspace_id, user_id)
```

- [ ] **Step 2: RoleChecker 구현**

```python
# backend/src/auth/rbac.py
"""역할 기반 접근 제어 (RBAC). Depends()로 라우터에 주입."""
import uuid

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

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
        member = await repo.find_by_workspace_and_user(
            workspace_id, current_user.id
        )
        if member is None:
            raise HTTPException(
                status_code=403, detail="워크스페이스 멤버가 아닙니다"
            )
        if ROLE_LEVEL[member.role] < ROLE_LEVEL[self.min_role]:
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
```

- [ ] **Step 3: 테스트 작성**

```python
# backend/tests/auth/test_rbac.py
"""RoleChecker 단위 테스트."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.auth.rbac import ROLE_LEVEL, RoleChecker


def test_role_level_ordering():
    """역할 레벨 순서: viewer < member < admin < owner."""
    assert ROLE_LEVEL["viewer"] < ROLE_LEVEL["member"]
    assert ROLE_LEVEL["member"] < ROLE_LEVEL["admin"]
    assert ROLE_LEVEL["admin"] < ROLE_LEVEL["owner"]


def test_invalid_role_raises():
    """존재하지 않는 역할로 RoleChecker 생성 시 ValueError."""
    with pytest.raises(ValueError, match="유효하지 않은 역할"):
        RoleChecker("superadmin")
```

- [ ] **Step 4: 테스트 실행**

Run: `cd backend && python -m pytest tests/auth/test_rbac.py -v`
Expected: 2 PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/src/auth/rbac.py backend/src/workspaces/repository.py backend/tests/auth/test_rbac.py
git commit -m "feat: RoleChecker RBAC 미들웨어 구현"
```

---

## Task 2: 기존 라우터에 역할 검증 적용

**Files:**
- Modify: `backend/src/meetings/router.py`
- Modify: `backend/src/projects/router.py`
- Modify: `backend/src/inbox/router.py`
- Modify: `backend/src/notes/router.py`
- Modify: `backend/src/actions/router.py`
- Modify: `backend/src/rag/router.py`
- Modify: `backend/src/upload/router.py`

- [ ] **Step 1: meetings/router.py — require_member (쓰기), require_viewer (읽기)**

각 엔드포인트의 `current_user: User = Depends(get_current_user)` 파라미터를 역할 의존성으로 교체:

```python
# backend/src/meetings/router.py
# import 변경:
# - from src.auth.dependencies import get_current_user 제거 (더 이상 직접 사용 안 함)
# - from src.auth.models import User 제거
# + 추가:
from src.auth.rbac import require_member, require_viewer
from src.workspaces.models import WorkspaceMember

# create_meeting: current_user → member
@router.post("", status_code=202)
async def create_meeting(
    workspace_id: uuid.UUID,
    data: CreateMeetingRequest,
    background_tasks: BackgroundTasks,
    member: WorkspaceMember = Depends(require_member),  # Member 이상
    service: MeetingService = Depends(get_meeting_service),
    pipeline: MeetingPipelineService = Depends(get_pipeline_service),
):
    result = await service.create_meeting(
        workspace_id=workspace_id,
        title=data.title,
        file_key=data.file_key,
        created_by_id=member.user_id,  # current_user.id → member.user_id
        recorded_at=data.recorded_at,
    )
    background_tasks.add_task(pipeline.process_meeting, uuid.UUID(result["id"]))
    return result

# list_meetings, get_meeting, get_meeting_status: → require_viewer
@router.get("")
async def list_meetings(
    workspace_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    member: WorkspaceMember = Depends(require_viewer),  # Viewer 이상
    service: MeetingService = Depends(get_meeting_service),
):
    return await service.list_meetings(workspace_id, page, page_size)

# get_meeting, get_meeting_status도 동일하게 require_viewer 적용
```

- [ ] **Step 2: projects/router.py — GET은 require_viewer, POST/PATCH는 require_member, DELETE/archive는 require_admin**

```python
# import 변경
from src.auth.rbac import require_admin, require_member, require_viewer
from src.workspaces.models import WorkspaceMember

# list_projects, get_project: require_viewer
# create_project: require_member (member.user_id를 created_by_id로)
# update_project: require_member
# delete_project, archive_project: require_admin
# meeting-project link: require_member
```

- [ ] **Step 3: inbox/router.py — GET은 require_viewer, classify/dismiss는 require_member**

```python
from src.auth.rbac import require_member, require_viewer
from src.workspaces.models import WorkspaceMember
```

- [ ] **Step 4: notes/router.py — GET은 require_viewer, POST/PATCH/DELETE는 require_member**

```python
from src.auth.rbac import require_member, require_viewer
from src.workspaces.models import WorkspaceMember
# create_note: member.user_id를 created_by_id로
```

- [ ] **Step 5: actions/router.py — GET은 require_viewer, POST/PATCH는 require_member**

```python
from src.auth.rbac import require_member, require_viewer
from src.workspaces.models import WorkspaceMember
```

- [ ] **Step 6: rag/router.py — require_viewer**

```python
from src.auth.rbac import require_viewer
from src.workspaces.models import WorkspaceMember

@router.post("/ask")
async def ask_rag(
    workspace_id: uuid.UUID,
    data: RagAskRequest,
    member: WorkspaceMember = Depends(require_viewer),  # Viewer 이상
    service: RagService = Depends(get_rag_service),
):
    ...
```

- [ ] **Step 7: upload/router.py — require_member**

주의: upload 라우터는 `/api/v1/upload/presigned-url` 경로로 `workspace_id`가 없다.
workspace_id를 쿼리 파라미터나 body에 추가하거나, 인증만 유지.
→ **현실적 결정:** upload은 인증만 유지 (workspace 미참조). 업로드 후 meeting 생성 시 역할 검증됨.

```python
# upload/router.py — 변경 없음 (get_current_user 유지)
```

- [ ] **Step 8: 타입 체크**

Run: `cd backend && python -m pytest tests/ -v --ignore=tests/meetings/test_pipeline.py -x 2>&1 | head -30`
Expected: 기존 테스트 통과 (파이프라인 테스트는 mock 구조상 별도)

- [ ] **Step 9: 커밋**

```bash
git add backend/src/meetings/router.py backend/src/projects/router.py backend/src/inbox/router.py backend/src/notes/router.py backend/src/actions/router.py backend/src/rag/router.py
git commit -m "feat: 모든 라우터에 RBAC 역할 검증 적용"
```

---

## Task 3: WorkspaceInvite 모델 + 마이그레이션

**Files:**
- Modify: `backend/src/workspaces/models.py`
- Create: `backend/alembic/versions/*_add_workspace_invites.py`

- [ ] **Step 1: WorkspaceInvite 모델 추가**

```python
# backend/src/workspaces/models.py — 하단에 추가
import secrets
import string

def _generate_invite_code() -> str:
    """12자리 URL-safe 초대 코드 생성."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(12))


class WorkspaceInvite(SQLModel, table=True):
    __tablename__ = "workspace_invites"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id")
    code: str = Field(default_factory=_generate_invite_code, index=True, sa_column_kwargs={"unique": True})
    role: str = "member"
    created_by_id: uuid.UUID = Field(foreign_key="users.id")
    max_uses: int | None = None
    use_count: int = 0
    expires_at: datetime | None = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Step 2: Alembic 마이그레이션 생성**

Run: `cd backend && alembic revision --autogenerate -m "add_workspace_invites"`

- [ ] **Step 3: 마이그레이션 파일 검토**

생성된 파일 확인: `workspace_invites` 테이블, `code` 유니크 인덱스, FK 제약조건.

- [ ] **Step 4: 마이그레이션 적용 (로컬)**

Run: `cd backend && alembic upgrade head`

- [ ] **Step 5: 커밋**

```bash
git add backend/src/workspaces/models.py backend/alembic/versions/
git commit -m "feat: WorkspaceInvite 모델 + 마이그레이션"
```

---

## Task 4: 초대 링크 서비스 + 라우터

**Files:**
- Modify: `backend/src/workspaces/repository.py` (invite CRUD)
- Modify: `backend/src/workspaces/schemas.py` (invite 스키마)
- Modify: `backend/src/workspaces/exceptions.py` (새 예외)
- Create: `backend/src/workspaces/invite_service.py`
- Create: `backend/src/workspaces/invite_router.py`
- Create: `backend/src/workspaces/member_router.py`
- Modify: `backend/src/main.py` (라우터 등록)
- Test: `backend/tests/workspaces/test_invite.py`

- [ ] **Step 1: Repository에 invite + member 관리 메서드 추가**

```python
# backend/src/workspaces/repository.py — 추가 메서드

    # --- Invite ---

    async def save_invite(self, invite: "WorkspaceInvite") -> "WorkspaceInvite":
        self.session.add(invite)
        await self.session.flush()
        return invite

    async def find_invite_by_code(self, code: str) -> "WorkspaceInvite | None":
        from src.workspaces.models import WorkspaceInvite
        result = await self.session.execute(
            select(WorkspaceInvite).where(
                WorkspaceInvite.code == code,
                WorkspaceInvite.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def find_invites_by_workspace(
        self, workspace_id: uuid.UUID
    ) -> list["WorkspaceInvite"]:
        from src.workspaces.models import WorkspaceInvite
        result = await self.session.execute(
            select(WorkspaceInvite)
            .where(WorkspaceInvite.workspace_id == workspace_id)
            .order_by(WorkspaceInvite.created_at.desc())
        )
        return list(result.scalars().all())

    async def deactivate_invite(self, invite_id: uuid.UUID) -> None:
        from src.workspaces.models import WorkspaceInvite
        result = await self.session.execute(
            select(WorkspaceInvite).where(WorkspaceInvite.id == invite_id)
        )
        invite = result.scalar_one_or_none()
        if invite:
            invite.is_active = False

    # --- Member 관리 ---

    async def list_members(
        self, workspace_id: uuid.UUID
    ) -> list[WorkspaceMember]:
        result = await self.session.execute(
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
        )
        return list(result.scalars().all())

    async def find_member_by_id(
        self, member_id: uuid.UUID
    ) -> WorkspaceMember | None:
        result = await self.session.execute(
            select(WorkspaceMember).where(WorkspaceMember.id == member_id)
        )
        return result.scalar_one_or_none()

    async def remove_member(self, member_id: uuid.UUID) -> None:
        member = await self.find_member_by_id(member_id)
        if member:
            await self.session.delete(member)
```

- [ ] **Step 2: 스키마 추가**

```python
# backend/src/workspaces/schemas.py — 추가

class CreateInviteRequest(BaseModel):
    role: str = "member"
    max_uses: int | None = None

class InviteResponse(BaseModel):
    id: uuid.UUID
    code: str
    role: str
    invite_url: str
    max_uses: int | None
    use_count: int
    is_active: bool
    created_at: str

class UpdateMemberRoleRequest(BaseModel):
    role: str

class MemberDetailResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str
    email: str
    role: str

class InviteInfoResponse(BaseModel):
    workspace_name: str
    role: str
    inviter_name: str
```

- [ ] **Step 3: 예외 추가**

```python
# backend/src/workspaces/exceptions.py — 추가
class InviteNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("초대 링크")

class InviteExpiredError(Exception):
    pass

class InviteMaxUsesReachedError(Exception):
    pass
```

- [ ] **Step 4: InviteService 구현**

```python
# backend/src/workspaces/invite_service.py
"""초대 링크 생성/수락 서비스."""
import uuid
from datetime import datetime

from src.auth.repository import UserRepository
from src.common.exceptions import NotFoundError
from src.workspaces.exceptions import (
    InviteExpiredError,
    InviteMaxUsesReachedError,
    InviteNotFoundError,
    MemberAlreadyExistsError,
    WorkspaceNotFoundError,
)
from src.workspaces.models import WorkspaceInvite, WorkspaceMember
from src.workspaces.repository import WorkspaceRepository


class InviteService:
    def __init__(
        self,
        repo: WorkspaceRepository,
        user_repo: UserRepository,
    ) -> None:
        self.repo = repo
        self.user_repo = user_repo

    async def create_invite(
        self,
        workspace_id: uuid.UUID,
        created_by_id: uuid.UUID,
        role: str = "member",
        max_uses: int | None = None,
    ) -> dict:
        workspace = await self.repo.find_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError()

        invite = WorkspaceInvite(
            workspace_id=workspace_id,
            role=role,
            created_by_id=created_by_id,
            max_uses=max_uses,
        )
        invite = await self.repo.save_invite(invite)
        await self.repo.commit()

        return {
            "id": str(invite.id),
            "code": invite.code,
            "role": invite.role,
            "inviteUrl": f"/invite/{invite.code}",
            "maxUses": invite.max_uses,
            "useCount": invite.use_count,
            "isActive": invite.is_active,
            "createdAt": invite.created_at.isoformat(),
        }

    async def get_invite_info(self, code: str) -> dict:
        invite = await self.repo.find_invite_by_code(code)
        if invite is None:
            raise InviteNotFoundError()
        workspace = await self.repo.find_by_id(invite.workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError()
        inviter = await self.user_repo.find_by_id(invite.created_by_id)

        return {
            "workspaceName": workspace.name,
            "role": invite.role,
            "inviterName": inviter.display_name if inviter else "알 수 없음",
        }

    async def accept_invite(self, code: str, user_id: uuid.UUID) -> dict:
        invite = await self.repo.find_invite_by_code(code)
        if invite is None:
            raise InviteNotFoundError()

        # 만료 확인
        if invite.expires_at and invite.expires_at < datetime.utcnow():
            raise InviteExpiredError()

        # 사용 횟수 확인
        if invite.max_uses is not None and invite.use_count >= invite.max_uses:
            raise InviteMaxUsesReachedError()

        # 이미 멤버인지 확인
        existing = await self.repo.find_member(invite.workspace_id, user_id)
        if existing is not None:
            raise MemberAlreadyExistsError()

        # 멤버 추가
        member = WorkspaceMember(
            workspace_id=invite.workspace_id,
            user_id=user_id,
            role=invite.role,
        )
        await self.repo.add_member(member)

        # 사용 횟수 증가
        invite.use_count += 1

        await self.repo.commit()

        return {
            "workspaceId": str(invite.workspace_id),
            "role": invite.role,
        }

    async def list_invites(self, workspace_id: uuid.UUID) -> list[dict]:
        invites = await self.repo.find_invites_by_workspace(workspace_id)
        return [
            {
                "id": str(inv.id),
                "code": inv.code,
                "role": inv.role,
                "inviteUrl": f"/invite/{inv.code}",
                "maxUses": inv.max_uses,
                "useCount": inv.use_count,
                "isActive": inv.is_active,
                "createdAt": inv.created_at.isoformat(),
            }
            for inv in invites
        ]

    async def deactivate_invite(
        self, workspace_id: uuid.UUID, invite_id: uuid.UUID
    ) -> None:
        await self.repo.deactivate_invite(invite_id)
        await self.repo.commit()

    async def list_members(self, workspace_id: uuid.UUID) -> list[dict]:
        members = await self.repo.list_members(workspace_id)
        result = []
        for m in members:
            user = await self.user_repo.find_by_id(m.user_id)
            result.append({
                "id": str(m.id),
                "userId": str(m.user_id),
                "displayName": user.display_name if user else "알 수 없음",
                "email": user.email if user else "",
                "role": m.role,
            })
        return result

    async def update_member_role(
        self, member_id: uuid.UUID, role: str
    ) -> dict:
        member = await self.repo.find_member_by_id(member_id)
        if member is None:
            raise NotFoundError("멤버")
        if member.role == "owner":
            raise ValueError("Owner 역할은 변경할 수 없습니다")
        member.role = role
        await self.repo.commit()
        return {"id": str(member.id), "role": member.role}

    async def remove_member(self, member_id: uuid.UUID) -> None:
        member = await self.repo.find_member_by_id(member_id)
        if member is None:
            raise NotFoundError("멤버")
        if member.role == "owner":
            raise ValueError("Owner는 제거할 수 없습니다")
        await self.repo.remove_member(member_id)
        await self.repo.commit()
```

- [ ] **Step 5: 멤버 관리 라우터**

```python
# backend/src/workspaces/member_router.py
"""멤버 관리 엔드포인트."""
import uuid

from fastapi import APIRouter, Depends, HTTPException

from src.auth.rbac import require_admin, require_owner, require_viewer
from src.workspaces.dependencies import get_invite_service
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
    return await service.list_members(workspace_id)


@router.patch("/{member_id}")
async def update_member_role(
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    data: UpdateMemberRoleRequest,
    member: WorkspaceMember = Depends(require_owner),
    service: InviteService = Depends(get_invite_service),
):
    try:
        return await service.update_member_role(member_id, data.role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{member_id}", status_code=204)
async def remove_member(
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_admin),
    service: InviteService = Depends(get_invite_service),
):
    try:
        await service.remove_member(member_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 6: 초대 라우터**

```python
# backend/src/workspaces/invite_router.py
"""초대 링크 엔드포인트."""
import uuid

from fastapi import APIRouter, Depends, HTTPException

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.auth.rbac import require_admin
from src.workspaces.dependencies import get_invite_service
from src.workspaces.exceptions import (
    InviteExpiredError,
    InviteMaxUsesReachedError,
    InviteNotFoundError,
    MemberAlreadyExistsError,
)
from src.workspaces.invite_service import InviteService
from src.workspaces.models import WorkspaceMember
from src.workspaces.schemas import CreateInviteRequest

# 워크스페이스 내 초대 관리 (Admin 이상)
workspace_invite_router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/invites",
    tags=["invites"],
)

# 공개 초대 수락 (인증만 필요, 역할 불필요)
public_invite_router = APIRouter(
    prefix="/api/v1/invites",
    tags=["invites"],
)


@workspace_invite_router.post("", status_code=201)
async def create_invite(
    workspace_id: uuid.UUID,
    data: CreateInviteRequest,
    member: WorkspaceMember = Depends(require_admin),
    service: InviteService = Depends(get_invite_service),
):
    return await service.create_invite(
        workspace_id=workspace_id,
        created_by_id=member.user_id,
        role=data.role,
        max_uses=data.max_uses,
    )


@workspace_invite_router.get("")
async def list_invites(
    workspace_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_admin),
    service: InviteService = Depends(get_invite_service),
):
    return await service.list_invites(workspace_id)


@workspace_invite_router.delete("/{invite_id}", status_code=204)
async def deactivate_invite(
    workspace_id: uuid.UUID,
    invite_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_admin),
    service: InviteService = Depends(get_invite_service),
):
    await service.deactivate_invite(workspace_id, invite_id)


@public_invite_router.get("/{code}")
async def get_invite_info(
    code: str,
    service: InviteService = Depends(get_invite_service),
):
    """초대 정보 조회 (인증 불필요)."""
    try:
        return await service.get_invite_info(code)
    except InviteNotFoundError:
        raise HTTPException(status_code=404, detail="유효하지 않은 초대 링크입니다")


@public_invite_router.post("/{code}/accept")
async def accept_invite(
    code: str,
    current_user: User = Depends(get_current_user),
    service: InviteService = Depends(get_invite_service),
):
    """초대 수락 (인증 필요)."""
    try:
        return await service.accept_invite(code, current_user.id)
    except InviteNotFoundError:
        raise HTTPException(status_code=404, detail="유효하지 않은 초대 링크입니다")
    except InviteExpiredError:
        raise HTTPException(status_code=410, detail="만료된 초대 링크입니다")
    except InviteMaxUsesReachedError:
        raise HTTPException(status_code=410, detail="초대 사용 횟수를 초과했습니다")
    except MemberAlreadyExistsError:
        raise HTTPException(status_code=409, detail="이미 워크스페이스 멤버입니다")
```

- [ ] **Step 7: dependencies.py에 get_invite_service 추가**

```python
# backend/src/workspaces/dependencies.py — 추가

from src.workspaces.invite_service import InviteService

async def get_invite_service(
    session: AsyncSession = Depends(get_async_session),
) -> InviteService:
    return InviteService(
        repo=WorkspaceRepository(session),
        user_repo=UserRepository(session),
    )
```

- [ ] **Step 8: main.py에 라우터 등록**

```python
# backend/src/main.py — import 추가
from src.workspaces.invite_router import public_invite_router, workspace_invite_router
from src.workspaces.member_router import router as member_router

# app.include_router 추가
app.include_router(member_router)
app.include_router(workspace_invite_router)
app.include_router(public_invite_router)
```

- [ ] **Step 9: UserRepository에 find_by_id 확인/추가**

```python
# backend/src/auth/repository.py — find_by_id가 없으면 추가
    async def find_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
```

- [ ] **Step 10: 테스트**

```python
# backend/tests/workspaces/test_invite.py
"""초대 링크 테스트."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.workspaces.invite_service import InviteService
from src.workspaces.exceptions import InviteNotFoundError, MemberAlreadyExistsError
from src.workspaces.models import WorkspaceInvite, WorkspaceMember


@pytest.mark.asyncio
async def test_create_invite():
    """초대 링크 생성 시 12자리 코드가 포함된 응답."""
    repo = AsyncMock()
    user_repo = AsyncMock()

    workspace = MagicMock()
    workspace.id = uuid.uuid4()
    workspace.name = "Test WS"
    repo.find_by_id.return_value = workspace

    invite = MagicMock(spec=WorkspaceInvite)
    invite.id = uuid.uuid4()
    invite.code = "abc123def456"
    invite.role = "member"
    invite.max_uses = None
    invite.use_count = 0
    invite.is_active = True
    invite.created_at = MagicMock()
    invite.created_at.isoformat.return_value = "2026-04-04T00:00:00"
    repo.save_invite.return_value = invite

    service = InviteService(repo=repo, user_repo=user_repo)
    result = await service.create_invite(
        workspace_id=workspace.id,
        created_by_id=uuid.uuid4(),
        role="member",
    )

    assert result["code"] == "abc123def456"
    assert "/invite/" in result["inviteUrl"]
    repo.save_invite.assert_called_once()
    repo.commit.assert_called_once()


@pytest.mark.asyncio
async def test_accept_invite_already_member():
    """이미 멤버인 사용자가 초대 수락 시 에러."""
    repo = AsyncMock()
    user_repo = AsyncMock()

    invite = MagicMock(spec=WorkspaceInvite)
    invite.workspace_id = uuid.uuid4()
    invite.expires_at = None
    invite.max_uses = None
    invite.use_count = 0
    invite.role = "member"
    repo.find_invite_by_code.return_value = invite
    repo.find_member.return_value = MagicMock()  # 이미 멤버

    service = InviteService(repo=repo, user_repo=user_repo)

    with pytest.raises(MemberAlreadyExistsError):
        await service.accept_invite("abc123", uuid.uuid4())
```

- [ ] **Step 11: 테스트 실행**

Run: `cd backend && python -m pytest tests/workspaces/test_invite.py tests/auth/test_rbac.py -v`
Expected: 4 PASS

- [ ] **Step 12: 커밋**

```bash
git add backend/src/workspaces/ backend/src/auth/repository.py backend/src/main.py backend/tests/
git commit -m "feat: 초대 링크 시스템 + 멤버 관리 API"
```

---

## Task 5: 프론트엔드 — 멤버 도메인 모듈 + 설정 페이지

**Files:**
- Create: `frontend/src/features/members/types.ts`
- Create: `frontend/src/features/members/api.ts`
- Create: `frontend/src/features/members/hooks.ts`
- Create: `frontend/src/features/members/components/member-list.tsx`
- Create: `frontend/src/features/members/components/invite-manager.tsx`
- Create: `frontend/src/app/(app)/settings/members/page.tsx`
- Create: `frontend/src/store/auth.ts`
- Modify: `frontend/src/components/layout/sidebar.tsx`

- [ ] **Step 1: types.ts**

```typescript
// frontend/src/features/members/types.ts
export type WorkspaceRole = "owner" | "admin" | "member" | "viewer";

export interface Member {
  id: string;
  userId: string;
  displayName: string;
  email: string;
  role: WorkspaceRole;
}

export interface Invite {
  id: string;
  code: string;
  role: WorkspaceRole;
  inviteUrl: string;
  maxUses: number | null;
  useCount: number;
  isActive: boolean;
  createdAt: string;
}

export interface InviteInfo {
  workspaceName: string;
  role: WorkspaceRole;
  inviterName: string;
}
```

- [ ] **Step 2: api.ts**

```typescript
// frontend/src/features/members/api.ts
import type { Member, Invite, InviteInfo } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchWithAuth(url: string, options: RequestInit = {}) {
  // Clerk 토큰은 proxy.ts에서 처리 — 여기서는 credentials만 설정
  return fetch(url, { ...options, credentials: "include" });
}

export const memberKeys = {
  all: (wsId: string) => ["members", wsId] as const,
  invites: (wsId: string) => ["invites", wsId] as const,
};

export async function fetchMembers(workspaceId: string): Promise<Member[]> {
  const res = await fetchWithAuth(
    `${API_URL}/api/v1/workspaces/${workspaceId}/members`
  );
  if (!res.ok) throw new Error("멤버 목록 조회 실패");
  return res.json();
}

export async function updateMemberRole(
  workspaceId: string,
  memberId: string,
  role: string,
): Promise<void> {
  const res = await fetchWithAuth(
    `${API_URL}/api/v1/workspaces/${workspaceId}/members/${memberId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role }),
    },
  );
  if (!res.ok) throw new Error("역할 변경 실패");
}

export async function removeMember(
  workspaceId: string,
  memberId: string,
): Promise<void> {
  const res = await fetchWithAuth(
    `${API_URL}/api/v1/workspaces/${workspaceId}/members/${memberId}`,
    { method: "DELETE" },
  );
  if (!res.ok) throw new Error("멤버 제거 실패");
}

export async function fetchInvites(workspaceId: string): Promise<Invite[]> {
  const res = await fetchWithAuth(
    `${API_URL}/api/v1/workspaces/${workspaceId}/invites`
  );
  if (!res.ok) throw new Error("초대 목록 조회 실패");
  return res.json();
}

export async function createInvite(
  workspaceId: string,
  role: string = "member",
): Promise<Invite> {
  const res = await fetchWithAuth(
    `${API_URL}/api/v1/workspaces/${workspaceId}/invites`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role }),
    },
  );
  if (!res.ok) throw new Error("초대 생성 실패");
  return res.json();
}

export async function deactivateInvite(
  workspaceId: string,
  inviteId: string,
): Promise<void> {
  const res = await fetchWithAuth(
    `${API_URL}/api/v1/workspaces/${workspaceId}/invites/${inviteId}`,
    { method: "DELETE" },
  );
  if (!res.ok) throw new Error("초대 비활성화 실패");
}

export async function fetchInviteInfo(code: string): Promise<InviteInfo> {
  const res = await fetch(`${API_URL}/api/v1/invites/${code}`);
  if (!res.ok) throw new Error("초대 정보 조회 실패");
  return res.json();
}

export async function acceptInvite(
  code: string,
): Promise<{ workspaceId: string; role: string }> {
  const res = await fetchWithAuth(
    `${API_URL}/api/v1/invites/${code}/accept`,
    { method: "POST" },
  );
  if (!res.ok) throw new Error("초대 수락 실패");
  return res.json();
}
```

- [ ] **Step 3: hooks.ts**

```typescript
// frontend/src/features/members/hooks.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  memberKeys,
  fetchMembers,
  updateMemberRole,
  removeMember,
  fetchInvites,
  createInvite,
  deactivateInvite,
} from "./api";

export function useMembers(workspaceId: string | undefined) {
  return useQuery({
    queryKey: memberKeys.all(workspaceId ?? ""),
    queryFn: () => fetchMembers(workspaceId!),
    enabled: !!workspaceId,
  });
}

export function useInvites(workspaceId: string | undefined) {
  return useQuery({
    queryKey: memberKeys.invites(workspaceId ?? ""),
    queryFn: () => fetchInvites(workspaceId!),
    enabled: !!workspaceId,
  });
}

export function useUpdateMemberRole(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ memberId, role }: { memberId: string; role: string }) =>
      updateMemberRole(workspaceId, memberId, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: memberKeys.all(workspaceId) }),
  });
}

export function useRemoveMember(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (memberId: string) => removeMember(workspaceId, memberId),
    onSuccess: () => qc.invalidateQueries({ queryKey: memberKeys.all(workspaceId) }),
  });
}

export function useCreateInvite(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (role: string) => createInvite(workspaceId, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: memberKeys.invites(workspaceId) }),
  });
}

export function useDeactivateInvite(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (inviteId: string) => deactivateInvite(workspaceId, inviteId),
    onSuccess: () => qc.invalidateQueries({ queryKey: memberKeys.invites(workspaceId) }),
  });
}
```

- [ ] **Step 4: member-list.tsx, invite-manager.tsx 컴포넌트**

(실제 코드는 구현 시 DESIGN.md 참조하여 작성 — Kairos 디자인 시스템 준수)

핵심 구조:
- `MemberList`: 테이블/리스트 → 각 행에 이름, 이메일, 역할 뱃지, 역할 변경 드롭다운(Owner만), 제거 버튼(Admin+)
- `InviteManager`: 생성 버튼 → 링크 복사, 비활성화 버튼

- [ ] **Step 5: /settings/members 페이지**

```typescript
// frontend/src/app/(app)/settings/members/page.tsx
export default function MembersSettingsPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1>멤버 관리</h1>
      <MemberList />
      <InviteManager />
    </div>
  );
}
```

- [ ] **Step 6: 사이드바에 설정 링크 추가**

```typescript
// frontend/src/components/layout/sidebar.tsx
// NAV_BOTTOM에 설정 추가:
import { Settings } from "lucide-react";

const NAV_BOTTOM: NavItem[] = [
  { href: "/notes", label: "빠른 메모", icon: FileText },
  { href: "/new", label: "+ 추가", icon: Plus },
  { href: "/settings/members", label: "설정", icon: Settings },
];
```

- [ ] **Step 7: 빌드 확인**

Run: `cd frontend && pnpm build 2>&1 | tail -5`
Expected: 빌드 성공

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/features/members/ frontend/src/app/(app)/settings/ frontend/src/components/layout/sidebar.tsx frontend/src/store/auth.ts
git commit -m "feat: 멤버 관리 UI + 초대 링크 페이지"
```

---

## Task 6: 초대 수락 공개 페이지

**Files:**
- Create: `frontend/src/app/(public)/invite/[code]/page.tsx`

- [ ] **Step 1: 초대 수락 페이지 구현**

```typescript
// frontend/src/app/(public)/invite/[code]/page.tsx
// 공개 페이지: 초대 정보 표시 + 수락 버튼
// Clerk 미로그인 시 → 로그인 유도
// 로그인 상태 → 수락 API 호출 → / 로 리다이렉트
```

- [ ] **Step 2: 빌드 확인**

Run: `cd frontend && pnpm build 2>&1 | tail -5`

- [ ] **Step 3: 커밋**

```bash
git add frontend/src/app/(public)/invite/
git commit -m "feat: 초대 수락 공개 페이지"
```

---

## Task 7: 문서 업데이트 + 최종 커밋

**Files:**
- Modify: `docs/TODO.md`
- Modify: `docs/requirements/prd.md`
- Create: `docs/adr/007-rbac-pricing-decision.md` (ADR-007)

- [ ] **Step 1: ADR-007 작성**

Sprint 5 설계 문서의 §1 (배경 및 의사결정)을 ADR-007로 추출.

- [ ] **Step 2: TODO.md 업데이트**

Sprint 5 완료 항목 기록, Next Actions 갱신.

- [ ] **Step 3: PRD 섹션 8 업데이트**

현재 Phase를 Sprint 5 완료로 갱신.

- [ ] **Step 4: 커밋**

```bash
git add docs/
git commit -m "docs: ADR-007 RBAC+가격 결정 + Sprint 5 완료 기록"
```
