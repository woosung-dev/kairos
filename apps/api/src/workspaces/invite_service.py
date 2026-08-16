# apps/api/src/workspaces/invite_service.py
"""초대/멤버 관리 서비스 — AsyncSession import 금지."""
import secrets
import string
import uuid
from datetime import datetime, timedelta

from src.auth.repository import UserRepository
from src.core.config import get_settings
from src.workspaces.exceptions import (
    CannotModifyOwnerError,
    InviteExpiredError,
    InviteNotFoundError,
    MemberAlreadyExistsError,
    MemberNotFoundError,
    PersonalWorkspaceProtected,
    WorkspaceNotFoundError,
)
from src.workspaces.models import WorkspaceInvite, WorkspaceMember
from src.workspaces.repository import WorkspaceRepository


def _generate_invite_code(length: int = 12) -> str:
    """URL-safe 초대 코드 생성 (12자리)."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class InviteService:
    """초대 링크 + 멤버 관리 비즈니스 로직."""

    def __init__(
        self,
        repo: WorkspaceRepository,
        user_repo: UserRepository,
    ) -> None:
        self.repo = repo
        self.user_repo = user_repo

    # --- 초대 링크 ---

    async def create_invite(
        self,
        workspace_id: uuid.UUID,
        created_by_id: uuid.UUID,
        role: str = "member",
        default_project_visibility: str = "public",
        max_uses: int | None = None,
        expires_in_days: int | None = 7,
    ) -> dict:
        """초대 링크 생성. Admin 이상만 호출 가능 (라우터에서 검증).

        Sprint 6 L-8: default_project_visibility (public|draft|private) 저장.
        실제 첫 project 생성 시 적용은 향후 FE 안내 또는 다음 sprint+ 확장.
        """
        workspace = await self.repo.find_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError()
        # I-19: personal workspace는 1인 격리 — 초대 발급 불가
        if getattr(workspace, "type", "team") == "personal":
            raise PersonalWorkspaceProtected("초대")

        expires_at = None
        if expires_in_days is not None:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        invite = WorkspaceInvite(
            workspace_id=workspace_id,
            code=_generate_invite_code(),
            role=role,
            default_project_visibility=default_project_visibility,
            created_by_id=created_by_id,
            max_uses=max_uses,
            expires_at=expires_at,
        )
        invite = await self.repo.save_invite(invite)
        await self.repo.commit()

        settings = get_settings()
        base_url = settings.frontend_url.rstrip("/")

        return {
            "id": str(invite.id),
            "workspaceId": str(invite.workspace_id),
            "code": invite.code,
            "role": invite.role,
            "defaultProjectVisibility": invite.default_project_visibility,
            "inviteUrl": f"{base_url}/invite/{invite.code}",
            "maxUses": invite.max_uses,
            "useCount": invite.use_count,
            "expiresAt": invite.expires_at.isoformat() if invite.expires_at else None,
            "isActive": invite.is_active,
            "createdAt": invite.created_at.isoformat(),
        }

    async def list_invites(self, workspace_id: uuid.UUID) -> list[dict]:
        """활성 초대 링크 목록."""
        invites = await self.repo.list_invites(workspace_id)
        settings = get_settings()
        base_url = settings.frontend_url.rstrip("/")

        return [
            {
                "id": str(inv.id),
                "workspaceId": str(inv.workspace_id),
                "code": inv.code,
                "role": inv.role,
                "defaultProjectVisibility": inv.default_project_visibility,
                "inviteUrl": f"{base_url}/invite/{inv.code}",
                "maxUses": inv.max_uses,
                "useCount": inv.use_count,
                "expiresAt": inv.expires_at.isoformat() if inv.expires_at else None,
                "isActive": inv.is_active,
                "createdAt": inv.created_at.isoformat(),
            }
            for inv in invites
        ]

    async def deactivate_invite(
        self, workspace_id: uuid.UUID, invite_id: uuid.UUID
    ) -> None:
        """초대 링크 비활성화 (Sprint 19 PR #1 C12 Codex F-1/F-5: workspace_id WHERE 강제)."""
        invite = await self.repo.find_invite_by_id(invite_id, workspace_id)
        if invite is None:
            raise InviteNotFoundError()
        await self.repo.deactivate_invite(invite_id, workspace_id)
        await self.repo.commit()

    async def get_invite_info(self, code: str) -> dict:
        """초대 링크 공개 정보 조회 (인증 불필요)."""
        invite = await self.repo.find_invite_by_code(code)
        if invite is None:
            return {
                "workspaceName": "",
                "inviterName": None,
                "role": "",
                "isValid": False,
                "reason": "존재하지 않는 초대 링크입니다",
            }

        workspace = await self.repo.find_by_id(invite.workspace_id)
        workspace_name = workspace.name if workspace else ""

        # 유효성 검증
        is_valid, reason = self._validate_invite(invite)

        # 초대 생성자 이름
        inviter = await self.user_repo.find_by_id(invite.created_by_id)
        inviter_name = inviter.display_name if inviter else None

        return {
            "workspaceName": workspace_name,
            "inviterName": inviter_name,
            "role": invite.role,
            "isValid": is_valid,
            "reason": reason,
        }

    async def accept_invite(
        self, code: str, user_id: uuid.UUID
    ) -> dict:
        """초대 수락 → 멤버 추가."""
        invite = await self.repo.find_invite_by_code(code)
        if invite is None:
            raise InviteNotFoundError()

        is_valid, reason = self._validate_invite(invite)
        if not is_valid:
            raise InviteExpiredError(reason or "초대 링크를 사용할 수 없습니다")

        # I-19: personal workspace 멤버 추가 금지 (만약 기존 invite가 발급되어 있었다면 차단)
        workspace = await self.repo.find_by_id(invite.workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError()
        if getattr(workspace, "type", "team") == "personal":
            raise PersonalWorkspaceProtected("멤버 추가")

        # 이미 멤버인지 확인
        existing = await self.repo.find_member(invite.workspace_id, user_id)
        if existing is not None:
            raise MemberAlreadyExistsError()

        # 멤버 추가 (race-safe: ON CONFLICT DO NOTHING).
        # 사전체크(find_member)는 fast path — 동시 수락 race 는 add_member 가 backstop.
        # None 반환 = 동시 수락 중 다른 쪽이 먼저 INSERT (이미 멤버) → 사전체크와
        # 동일 semantics 로 409 (MemberAlreadyExistsError). NEVER 500/IntegrityError.
        member = WorkspaceMember(
            workspace_id=invite.workspace_id,
            user_id=user_id,
            role=invite.role,
            # W-5: 신규 멤버의 프로젝트 생성 기본 visibility 시드
            default_project_visibility=invite.default_project_visibility,
        )
        inserted = await self.repo.add_member(member)
        if inserted is None:
            raise MemberAlreadyExistsError()
        member = inserted

        # CAND-B fix (codex P1): 사전 잔재 ProjectMember 정리.
        # accept 가 여기까지 도달했다면 user 는 직전까지 *비-멤버*였다(위 find_member None).
        # 따라서 이 워크스페이스에 남아 있는 user 의 ProjectMember 행은 모두 stale 잔재다
        # (과거 제거 시 정리 로직이 없던 시절의 orphan 포함). re-invite 로 WorkspaceMember
        # 가 재생성되면 visibility 가드가 다시 참이 되어 private 접근이 복원되므로,
        # 새 멤버는 명시적 재추가 전까지 private project 매핑이 없어야 한다.
        await self.repo.delete_project_members_for_user(invite.workspace_id, user_id)

        # 사용 횟수 증가 (Sprint 19 PR #1 C12: invite.workspace_id 명시 전달)
        await self.repo.increment_invite_use_count(invite.id, invite.workspace_id)

        # max_uses 도달 시 자동 비활성화
        if invite.max_uses is not None and invite.use_count + 1 >= invite.max_uses:
            await self.repo.deactivate_invite(invite.id, invite.workspace_id)

        await self.repo.commit()

        return {
            "workspaceId": str(invite.workspace_id),
            "memberId": str(member.id),
            "role": member.role,
        }

    # --- 멤버 관리 ---

    async def list_members(self, workspace_id: uuid.UUID) -> list[dict]:
        """워크스페이스 멤버 목록 (이메일, 이름 포함). 단일 JOIN 쿼리 (N+1 제거)."""
        rows = await self.repo.list_members_with_users(workspace_id)
        return [
            {
                "id": str(m.id),
                # ADR-031: 외부 인증 공급자 ID(`clerkId`)를 응답에서 제거했다.
                # FE 의 role 판정이 그 값에 문자열 매칭으로 결합돼 있었고, 그게 이번 전환에서
                # 터진 지점이다. `userId`(내부 UUID)는 인증 공급자가 또 바뀌어도 불변이다.
                "userId": str(m.user_id),
                "email": user.email if user else None,
                "displayName": user.display_name if user else None,
                "role": m.role,
            }
            for m, user in rows
        ]

    async def update_member_role(
        self,
        workspace_id: uuid.UUID,
        member_id: uuid.UUID,
        new_role: str,
    ) -> dict:
        """멤버 역할 변경. Owner는 변경 불가.

        Sprint 19 PR #1 C12 (Codex F-1/F-5): workspace_id WHERE 강제.
        """
        member = await self.repo.find_member_by_id(member_id, workspace_id)
        if member is None:
            raise MemberNotFoundError()
        if member.role == "owner":
            raise CannotModifyOwnerError()

        await self.repo.update_member_role(member_id, workspace_id, new_role)
        await self.repo.commit()

        # BUG-RBAC-CACHE-STALE fix: 권한 강등 즉시 반영 — RBAC in-process 캐시 무효화
        # (없으면 RoleChecker 가 최대 60s 동안 옛 role 로 통과).
        from src.auth.rbac import invalidate_member_cache

        invalidate_member_cache(workspace_id, member.user_id)

        return {
            "id": str(member.id),
            "userId": str(member.user_id),
            "role": new_role,
        }

    async def remove_member(
        self, workspace_id: uuid.UUID, member_id: uuid.UUID
    ) -> None:
        """멤버 제거. Owner는 제거 불가.

        Sprint 19 PR #1 C12 (Codex F-1/F-5): workspace_id WHERE 강제.
        """
        member = await self.repo.find_member_by_id(member_id, workspace_id)
        if member is None:
            raise MemberNotFoundError()
        if member.role == "owner":
            raise CannotModifyOwnerError()

        await self.repo.remove_member(member_id, workspace_id)
        # CAND-B fix: 워크스페이스 제거 시 해당 유저의 private project 매핑(ProjectMember)도
        # revoke. 잔재 행이 남으면 re-invite 된 plain member 가 private project 접근/RAG 를
        # 되찾는 privilege residue 가 발생한다 (PROBE-SENTINEL-03).
        await self.repo.delete_project_members_for_user(workspace_id, member.user_id)
        await self.repo.commit()

        # BUG-RBAC-CACHE-STALE fix: 멤버 제거 즉시 반영 — RBAC in-process 캐시 무효화.
        from src.auth.rbac import invalidate_member_cache

        invalidate_member_cache(workspace_id, member.user_id)

    # --- 내부 헬퍼 ---

    @staticmethod
    def _validate_invite(invite: WorkspaceInvite) -> tuple[bool, str | None]:
        """초대 링크 유효성 검증."""
        if not invite.is_active:
            return False, "비활성화된 초대 링크입니다"
        if invite.expires_at is not None and datetime.utcnow() > invite.expires_at:
            return False, "만료된 초대 링크입니다"
        if invite.max_uses is not None and invite.use_count >= invite.max_uses:
            return False, "사용 한도에 도달한 초대 링크입니다"
        return True, None
