# apps/api/src/actions/service.py
"""ActionItem 서비스 — AsyncSession import 금지. 단일 도메인 CRUD.

헌법 I-9 (Sprint 19 PR #1, Codex F-1): 모든 메서드 workspace_id 필수.
Codex F-2 Critical: create / update 시 project_id / meeting_id / assignee_id secondary FK
cross-workspace 거부 (3건 가장 큰 분량).

Sprint 23 D4 Task 2 Step 2.5: cross-workspace promote 추가 (4 도메인 중 action — 마지막 4/4).
- I-18 (복제 + tombstone): 원본 보존 + target ws ActionItem 복제 + ItemPromotionAudit.
- ActionItem 임베딩 ledger 부재 (actions 도메인 임베딩 미적용) → BG embedding 복제 task
  schedule 없이 audit.embedding_status='n/a' 즉시 commit (inbox 와 동일).
- composite FK 강제 (Sprint 21 BL-050): meeting_id / project_id 는 target ws orphan →
  None reset. assignee_id 도 단순화 None reset (cross-workspace 사용자 책임 모호).
- workspace_repo 옵션 주입 — promote 호출 시 필수 (없으면 RuntimeError via validate_promote_target).
"""
import uuid
from datetime import date, datetime

from fastapi import BackgroundTasks

from src.actions.exceptions import (
    ActionItemNotFoundError,
    CannotPromoteToPersonalError,
    CannotPromoteToSameWorkspaceError,
    TargetWorkspaceInvalidError,
)
from src.actions.models import ActionItem
from src.actions.repository import ActionItemRepository
from src.actions.schemas import ActionPromoteOut
from src.common.exceptions import NotFoundError
from src.common.fk_guard import require_in_workspace
from src.common.pagination import build_page, to_offset
from src.common.promote_helpers import (
    PromoteValidationError,
    build_item_promotion_audit,
    validate_promote_target,
)
from src.common.visibility import (
    ADMIN_BYPASS_ROLES,
    Access,
    decide_project_access,
)
from src.meetings.exceptions import MeetingNotFoundError
from src.meetings.repository import MeetingRepository
from src.projects.exceptions import ProjectNotFoundError
from src.projects.repository import ProjectRepository
from src.workspaces.repository import WorkspaceRepository


class ActionItemService:
    def __init__(
        self,
        repo: ActionItemRepository,
        project_repo: ProjectRepository | None = None,
        meeting_repo: MeetingRepository | None = None,
        workspace_repo: WorkspaceRepository | None = None,
    ) -> None:
        self.repo = repo
        # Codex F-2 Critical: 3 secondary FK cross-tenant 검증용
        self.project_repo = project_repo
        self.meeting_repo = meeting_repo
        self.workspace_repo = workspace_repo

    async def _verify_secondary_fks(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None,
        meeting_id: uuid.UUID | None,
        assignee_id: uuid.UUID | None,
    ) -> None:
        """Codex F-2: 3 secondary FK 모두 같은 workspace 인지 검증.

        Codex 2차 Minor 1 (C7): fail-closed — FK 가 들어왔는데 검증 repo 미주입이면
        silent skip 대신 RuntimeError 로 차단 (테스트 사고 방지).
        """
        await require_in_workspace(
            self.project_repo, project_id, workspace_id,
            not_found=ProjectNotFoundError, repo_label="project_repo",
        )
        await require_in_workspace(
            self.meeting_repo, meeting_id, workspace_id,
            not_found=MeetingNotFoundError, repo_label="meeting_repo",
        )
        if assignee_id is not None:
            if self.workspace_repo is None:
                raise RuntimeError("workspace_repo 필수 (F-2 검증)")
            member = await self.workspace_repo.find_member(workspace_id, assignee_id)
            if member is None:
                raise NotFoundError("워크스페이스 멤버")

    async def create_action_item(
        self,
        workspace_id: uuid.UUID,
        title: str,
        description: str | None = None,
        meeting_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        assignee_id: uuid.UUID | None = None,
        due_date: date | None = None,
        priority: str = "medium",
    ) -> dict:
        """액션 아이템 생성. Codex F-2: 3 secondary FK 검증 후 INSERT."""
        await self._verify_secondary_fks(workspace_id, project_id, meeting_id, assignee_id)
        item = ActionItem(
            workspace_id=workspace_id,
            title=title,
            description=description,
            meeting_id=meeting_id,
            project_id=project_id,
            assignee_id=assignee_id,
            due_date=due_date,
            priority=priority,
        )
        item = await self.repo.save(item)
        await self.repo.commit()
        return self._to_dict(item)

    async def list_action_items(
        self,
        workspace_id: uuid.UUID,
        status: str | None = None,
        priority: str | None = None,
        project_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> dict:
        """워크스페이스 액션 아이템 목록 (페이지네이션).

        F1 (2026-06-23 fullsweep): requester visibility 게이트 — 비-ProjectMember 가
        private/draft 프로젝트 액션을 list 로 읽는 read IDOR 차단 (notes CAND-A 정합).
        requester_role 미전달(None) = 내부/파이프라인 호출 → 게이트 skip (하위호환).
        """
        offset = to_offset(page, page_size)
        items = await self.repo.find_by_workspace(
            workspace_id,
            status=status,
            priority=priority,
            project_id=project_id,
            offset=offset,
            limit=page_size,
            requester_user_id=requester_user_id,
            requester_role=requester_role,
        )
        total = await self.repo.count_by_workspace(
            workspace_id,
            status=status,
            priority=priority,
            project_id=project_id,
            requester_user_id=requester_user_id,
            requester_role=requester_role,
        )

        return build_page([self._to_dict(i) for i in items], total, page, page_size)

    async def _verify_action_visibility(
        self,
        item: ActionItem,
        requester_user_id: uuid.UUID | None,
        requester_role: str | None,
    ) -> None:
        """F2 (2026-06-23 fullsweep): action 의 owning project visibility 게이트.

        notes._verify_note_visibility 정합 — 비-ProjectMember 가 private/draft 프로젝트
        액션을 mutate 하는 write IDOR 차단:
        - admin/owner: 우회 / project_id=None: 통과
        - draft: project.created_by_id == requester 만, 그 외 404
        - private: ProjectMember 만, 그 외 404

        requester_role 미전달(None) = 내부/특권 호출 → 게이트 skip (하위호환).
        코어 규칙은 common/visibility.py decide_project_access SSOT.
        """
        if requester_role is None:
            return
        if requester_role in ADMIN_BYPASS_ROLES:
            return
        if item.project_id is None:
            return
        if self.project_repo is None:
            raise RuntimeError("project_repo 필수 (F2 visibility 검증)")
        project = await self.project_repo.find_by_id(item.project_id, item.workspace_id)
        if project is None:
            # cross-tenant 또는 dangling project → fail-closed 404
            raise ActionItemNotFoundError()
        decision = decide_project_access(project, requester_user_id)
        if decision is Access.DENY:
            raise ActionItemNotFoundError()
        if decision is Access.NEED_MEMBERSHIP and (
            requester_user_id is None
            or not await self.project_repo.is_member(
                item.project_id, requester_user_id, item.workspace_id
            )
        ):
            raise ActionItemNotFoundError()

    async def update_action_item(
        self,
        action_id: uuid.UUID,
        workspace_id: uuid.UUID,
        title: str | None = None,
        description: str | None = None,
        project_id: uuid.UUID | None = None,
        assignee_id: uuid.UUID | None = None,
        meeting_id: uuid.UUID | None = None,
        due_date: date | None = None,
        priority: str | None = None,
        status: str | None = None,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> dict:
        """액션 아이템 수정. 헌법 I-9 (Codex F-1) + Codex F-2 Critical 3 secondary FK 검증.

        F2 (2026-06-23 fullsweep): SOURCE 액션의 project visibility 게이트 — 비-멤버가
        private/draft 프로젝트 액션을 mutate 하는 write IDOR 차단 (비-멤버 → 404).
        """
        item = await self.repo.find_by_id(action_id, workspace_id)
        if item is None:
            raise ActionItemNotFoundError()
        await self._verify_action_visibility(item, requester_user_id, requester_role)

        # Codex F-2: 3 secondary FK 변경 요청 시 cross-workspace 거부
        await self._verify_secondary_fks(workspace_id, project_id, meeting_id, assignee_id)

        if title is not None:
            item.title = title
        if description is not None:
            item.description = description
        if project_id is not None:
            item.project_id = project_id
        if assignee_id is not None:
            item.assignee_id = assignee_id
        if meeting_id is not None:
            item.meeting_id = meeting_id
        if due_date is not None:
            item.due_date = due_date
        if priority is not None:
            item.priority = priority
        if status is not None:
            item.status = status

        item.updated_at = datetime.utcnow()
        item = await self.repo.save(item)
        await self.repo.commit()
        return self._to_dict(item)

    # ── Sprint 23 D4 Task 2 Step 2.5: promote 1-button ──

    async def promote(
        self,
        *,
        action_id: uuid.UUID,
        source_workspace_id: uuid.UUID,
        target_workspace_id: uuid.UUID,
        promoted_by_user_id: uuid.UUID,
        background_tasks: BackgroundTasks,
    ) -> ActionPromoteOut:
        """1-button promote: 원본 보존 + target ws ActionItem 복제 + audit.

        I-18 (Promotion = 복제 + tombstone, 이동 금지): source ActionItem 변경 없음.
        검증: source != target / target type='team' / promoter 가 target ws 멤버.
        helper: common/promote_helpers.validate_promote_target + build_item_promotion_audit.

        복제 정책 (composite FK 제약 + 단순화):
        - meeting_id: None reset — Sprint 21 BL-050 composite FK
          fk_action_items_meeting_workspace (workspace_id, meeting_id) → meetings(workspace_id, id)
          강제. source meeting 은 target ws 에 존재 X → None reset.
        - project_id: None reset — Sprint 19 PR #2 composite FK
          fk_action_items_project_workspace (workspace_id, project_id) → projects(workspace_id, id)
          강제. source project 는 target ws 에 존재 X → None reset (사용자가 target ws 에서
          별도 분류 권장).
        - assignee_id: None reset — assignee 는 user FK (workspace 무관). target ws 멤버
          여부 + cross-workspace 사용자 할당 의미가 모호하여 단순화. 사용자가 target ws 에서
          재할당 (헌법 A-3: assignee 는 워크스페이스 멤버만).
        - title / description / priority / status / due_date 는 보존 (history 의미).
        - ActionItem 모델은 created_by_id 필드가 없음 → audit.promoted_by_user_id 로 추적.

        ActionItem 은 임베딩 ledger 부재 → BG embedding 복제 task schedule 없이
        audit.embedding_status='n/a' 즉시 commit.

        background_tasks 인자: notes/meetings 시그니처와 정렬 — 본 도메인은 미사용.
        """
        # 1. promote target 검증 (헬퍼 — 4 도메인 공통 패턴)
        try:
            await validate_promote_target(
                source_workspace_id=source_workspace_id,
                target_workspace_id=target_workspace_id,
                promoted_by_user_id=promoted_by_user_id,
                workspace_repo=self.workspace_repo,
            )
        except PromoteValidationError as exc:
            # PromoteValidationError.code → action 도메인 HTTPException 매핑.
            if exc.code == "same_workspace":
                raise CannotPromoteToSameWorkspaceError() from exc
            if exc.code == "target_personal":
                raise CannotPromoteToPersonalError() from exc
            # target_invalid / not_member → 403 (inbox/notes/meetings 패턴 정렬)
            raise TargetWorkspaceInvalidError() from exc

        # 2. 원본 ActionItem fetch (I-9 workspace_id 강제)
        source = await self.repo.find_by_id(action_id, source_workspace_id)
        if source is None:
            raise ActionItemNotFoundError()

        # 3. 복제 ActionItem (id 새로 발급, workspace_id=target).
        # I-18: 원본 보존 — source 미변경.
        # meeting_id / project_id / assignee_id 모두 None reset (위 docstring 참조).
        new_item = ActionItem(
            workspace_id=target_workspace_id,
            meeting_id=None,
            project_id=None,
            assignee_id=None,
            title=source.title,
            description=source.description,
            due_date=source.due_date,
            priority=source.priority,
            status=source.status,
        )
        new_item = await self.repo.save_promoted_action_item(new_item)

        # 4. ItemPromotionAudit row (helper).
        # embedding_status='n/a': ActionItem 임베딩 ledger 부재 — BG embedding 복제 없음.
        audit = build_item_promotion_audit(
            item_type="action",
            source_item_id=source.id,
            new_item_id=new_item.id,
            source_workspace_id=source_workspace_id,
            target_workspace_id=target_workspace_id,
            promoted_by_user_id=promoted_by_user_id,
            embedding_status="n/a",
        )
        await self.repo.save_item_promotion_audit(audit)

        await self.repo.commit()

        # 5. BG embedding 복제 task 없음 — ActionItem 은 직접 임베딩 안 됨.
        # (notes/meetings 와 시그니처 정렬 위해 background_tasks 인자 유지.)

        return ActionPromoteOut(
            new_action_id=new_item.id,
            audit_id=audit.id,
            status="completed",
        )

    @staticmethod
    def _to_dict(item: ActionItem) -> dict:
        """ActionItem → camelCase dict 변환."""
        return {
            "id": str(item.id),
            "workspaceId": str(item.workspace_id),
            "meetingId": str(item.meeting_id) if item.meeting_id else None,
            "projectId": str(item.project_id) if item.project_id else None,
            "title": item.title,
            "description": item.description,
            "assigneeId": str(item.assignee_id) if item.assignee_id else None,
            "dueDate": item.due_date.isoformat() if item.due_date else None,
            "priority": item.priority,
            "status": item.status,
            "createdAt": item.created_at.isoformat(),
            "updatedAt": item.updated_at.isoformat(),
        }
