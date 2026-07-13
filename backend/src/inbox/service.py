# backend/src/inbox/service.py
"""Inbox 서비스 — 크로스 레포지토리 (InboxRepo + ProjectRepo + MeetingRepo).

Sprint 19 PR #1 C13a (Codex 2차 F-1): classify 의 source_type='meeting' 시
item.source_id (meeting_id) cross-tenant 검증. fail-closed RuntimeError.

Sprint 23 D4 Task 2 Step 2.4: cross-workspace promote 추가 (4 도메인 중 inbox).
- I-18 (복제 + tombstone): 원본 보존 + target ws InboxItem 복제 + ItemPromotionAudit.
- InboxItem 임베딩 ledger 부재 (source_type='inbox' EmbeddingChunk 실제 인서트 없음 — whitelist 만 존재) →
  BG embedding 복제 task schedule 없이 audit.embedding_status='n/a' 즉시 commit.
- workspace_repo 옵션 주입 — promote 호출 시 필수 (없으면 RuntimeError via validate_promote_target).
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import BackgroundTasks

from src.common.pagination import build_page, to_offset
from src.common.promote_helpers import (
    PromoteValidationError,
    build_item_promotion_audit,
    validate_promote_target,
)
from src.inbox.exceptions import (
    CannotPromoteToPersonalError,
    CannotPromoteToSameWorkspaceError,
    InboxItemNotFoundError,
    TargetWorkspaceInvalidError,
)
from src.inbox.models import InboxItem
from src.inbox.repository import InboxRepository
from src.inbox.schemas import InboxPromoteOut
from src.projects.exceptions import ProjectNotFoundError
from src.projects.repository import ProjectRepository

if TYPE_CHECKING:
    from src.meetings.repository import MeetingRepository
    from src.workspaces.repository import WorkspaceRepository


class InboxService:
    def __init__(
        self,
        inbox_repo: InboxRepository,
        project_repo: ProjectRepository,
        meeting_repo: "MeetingRepository | None" = None,
        workspace_repo: "WorkspaceRepository | None" = None,
    ) -> None:
        self.inbox_repo = inbox_repo
        self.project_repo = project_repo
        # Sprint 19 PR #1 C13a (Codex 2차 F-1): classify 의 meeting source_id 검증용
        self.meeting_repo = meeting_repo
        # Sprint 23 D4 (Task 2 Step 2.4): promote 흐름 필수 의존성.
        # 일반 CRUD (list/classify/dismiss) 흐름은 None 허용 — promote 호출 시점에 fail-closed 검증.
        self.workspace_repo = workspace_repo

    async def list_inbox(
        self,
        workspace_id: uuid.UUID,
        is_processed: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """워크스페이스 Inbox 목록 (페이지네이션)."""
        offset = to_offset(page, page_size)
        items = await self.inbox_repo.find_by_workspace(
            workspace_id, is_processed=is_processed, offset=offset, limit=page_size
        )
        total = await self.inbox_repo.count_by_workspace(
            workspace_id, is_processed=is_processed
        )
        return build_page(
            [self._to_dict(item) for item in items], total, page, page_size
        )

    async def classify(
        self,
        inbox_id: uuid.UUID,
        workspace_id: uuid.UUID,
        project_ids: list[uuid.UUID],
    ) -> dict:
        """Inbox 아이템을 프로젝트에 연결 확정.

        헌법 I-9 (Codex F-1): workspace_id 필수.
        Codex F-2 Critical: project_ids 모두 같은 workspace 내인지 사전 검증.
        """
        item = await self.inbox_repo.find_by_id(inbox_id, workspace_id)
        if item is None:
            raise InboxItemNotFoundError()

        # Codex F-2 Critical: project_ids 모두 같은 workspace 인지 사전 검증
        # (add_meeting_link 가 cross-workspace meeting/project 링크 생성하는 것 차단)
        # Sprint 19 PR #1 C9 (Codex F-1 cascade): find_by_id 시그니처 workspace_id 강제
        verified_projects: list = []
        for project_id in project_ids:
            project = await self.project_repo.find_by_id(project_id, workspace_id)
            if project is None:
                raise ProjectNotFoundError()
            verified_projects.append(project)

        item.is_processed = True
        item.updated_at = datetime.utcnow()
        await self.inbox_repo.save(item)

        # source_type 이 "meeting" 이면 → 각 프로젝트에 회의 연결
        # Sprint 19 PR #1 C9 (Codex F-3): add_meeting_link workspace_id 명시 전달
        # Sprint 19 PR #1 C13a (Codex 2차 F-1): item.source_id (meeting_id) cross-tenant 검증
        # fail-closed: meeting_repo 미주입 시 RuntimeError (silent skip 금지)
        linked_projects: list[dict] = []
        if item.source_type == "meeting":
            if self.meeting_repo is None:
                raise RuntimeError(
                    "meeting_repo 필수 (Codex 2차 F-1 source_id meeting 검증)"
                )
            # source_id (meeting_id) 가 같은 workspace 소속 인지 검증
            from src.meetings.exceptions import MeetingNotFoundError

            meeting = await self.meeting_repo.find_by_id(item.source_id, workspace_id)
            if meeting is None:
                raise MeetingNotFoundError()
            for project in verified_projects:
                await self.project_repo.add_meeting_link(
                    item.source_id, project.id, workspace_id
                )
                linked_projects.append(
                    {"id": str(project.id), "title": project.title}
                )

        # 동일 session 이므로 한 번만 commit
        await self.inbox_repo.commit()

        result = self._to_dict(item)
        result["linkedProjects"] = linked_projects
        return result

    async def dismiss(
        self, inbox_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> dict:
        """Inbox 아이템 무시 처리. 헌법 I-9 workspace_id 필수 (Codex F-1)."""
        item = await self.inbox_repo.find_by_id(inbox_id, workspace_id)
        if item is None:
            raise InboxItemNotFoundError()

        item.is_processed = True
        item.updated_at = datetime.utcnow()
        await self.inbox_repo.save(item)
        await self.inbox_repo.commit()

        return self._to_dict(item)

    # ── Sprint 23 D4 Task 2 Step 2.4: promote 1-button ──

    async def promote(
        self,
        *,
        inbox_id: uuid.UUID,
        source_workspace_id: uuid.UUID,
        target_workspace_id: uuid.UUID,
        promoted_by_user_id: uuid.UUID,
        background_tasks: BackgroundTasks,
    ) -> InboxPromoteOut:
        """1-button promote: 원본 보존 + target ws InboxItem 복제 + audit.

        I-18 (Promotion = 복제 + tombstone, 이동 금지): source InboxItem 변경 없음.
        검증: source != target / target type='team' / promoter 가 target ws 멤버.
        helper: common/promote_helpers.validate_promote_target + build_item_promotion_audit.

        ai_suggested_project_id: target ws orphan — None 으로 reset (composite FK
        fk_inbox_suggested_project_workspace 가 (workspace_id, ai_suggested_project_id) 정합 강제,
        source ws 의 project 는 target ws 에 존재 X).
        source_id: 원본 콘텐츠 (meeting/note) 참조 — cross-workspace transitive 참조 그대로 보존.
          - 사유: source_id 는 InboxItem 자체 모델의 FK 가 아니라 soft reference (워크스페이스 미강제).
          - 후속: 사용자가 target ws 에서 별도 콘텐츠 promote 후 새 inbox 적재 권장. 본 흐름에서는 source 보존.
        is_processed: False 로 reset — target ws 사용자가 분류 작업 다시 수행.

        InboxItem 은 source_type='inbox' EmbeddingChunk 가 실제 인서트되지 않음 (whitelist 만 존재) →
        BG embedding 복제 task schedule 없이 audit.embedding_status='n/a' 즉시 commit.

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
            # PromoteValidationError.code → inbox 도메인 HTTPException 매핑.
            if exc.code == "same_workspace":
                raise CannotPromoteToSameWorkspaceError() from exc
            if exc.code == "target_personal":
                raise CannotPromoteToPersonalError() from exc
            # target_invalid / not_member → 403 (meetings/notes 패턴 정렬)
            raise TargetWorkspaceInvalidError() from exc

        # 2. 원본 InboxItem fetch (I-9 workspace_id 강제)
        source = await self.inbox_repo.find_by_id(inbox_id, source_workspace_id)
        if source is None:
            raise InboxItemNotFoundError()

        # 3. 복제 InboxItem (id 새로 발급, workspace_id=target).
        # I-18: 원본 보존 — source 미변경.
        # ai_suggested_project_id=None: source.ai_suggested_project_id 는 source ws 의 project —
        #   composite FK fk_inbox_suggested_project_workspace 가 (workspace_id, project_id) 정합 강제.
        #   target ws 와 무관 → None reset. 사용자가 target ws 에서 별도 분류 권장.
        # ai_suggested_project_title: 단순 텍스트 메타 — 보존 (사용자 참고용).
        # Sprint 23 Codex 3차 P2 fix: source_type='attachment' + 새 UUID source_id 로 reset.
        #   사유: source.source_type='meeting' 일 때 source.source_id 는 source ws 의 meeting →
        #   target ws 에 존재 X → classify 가 meeting_repo.find_by_id(source_id, target_ws) 실패.
        #   target ws 의 사용자가 classify 불가. attachment 로 reset → meeting verify 분기 회피.
        # is_processed=False: 복제본은 미처리 상태로 reset (사용자 재분류 필요).
        import uuid as _uuid
        new_item = InboxItem(
            workspace_id=target_workspace_id,
            title=source.title,
            summary=source.summary,
            source_type="attachment",
            source_id=_uuid.uuid4(),
            ai_suggested_project_id=None,
            ai_suggested_project_title=source.ai_suggested_project_title,
            ai_suggested_tags=list(source.ai_suggested_tags or []),
            ai_confidence=source.ai_confidence,
            is_processed=False,
        )
        new_item = await self.inbox_repo.save_promoted_inbox_item(new_item)

        # 4. ItemPromotionAudit row (helper).
        # embedding_status='n/a': InboxItem 임베딩 ledger 부재 — BG embedding 복제 없음.
        audit = build_item_promotion_audit(
            item_type="inbox",
            source_item_id=source.id,
            new_item_id=new_item.id,
            source_workspace_id=source_workspace_id,
            target_workspace_id=target_workspace_id,
            promoted_by_user_id=promoted_by_user_id,
            embedding_status="n/a",
        )
        await self.inbox_repo.save_item_promotion_audit(audit)

        await self.inbox_repo.commit()

        # 5. BG embedding 복제 task 없음 — InboxItem 은 직접 임베딩 안 됨.
        # (notes/meetings 와 시그니처 정렬 위해 background_tasks 인자 유지.)

        return InboxPromoteOut(
            new_inbox_id=new_item.id,
            audit_id=audit.id,
            status="completed",
        )

    @staticmethod
    def _to_dict(item: InboxItem) -> dict:
        """InboxItem → camelCase dict 변환."""
        return {
            "id": str(item.id),
            "workspaceId": str(item.workspace_id),
            "title": item.title,
            "summary": item.summary,
            "sourceType": item.source_type,
            "sourceId": str(item.source_id),
            "aiSuggestedProjectId": (
                str(item.ai_suggested_project_id)
                if item.ai_suggested_project_id
                else None
            ),
            "aiSuggestedProjectTitle": item.ai_suggested_project_title,
            "aiSuggestedTags": item.ai_suggested_tags,
            "aiConfidence": item.ai_confidence,
            "isProcessed": item.is_processed,
            "createdAt": item.created_at.isoformat(),
            "updatedAt": item.updated_at.isoformat(),
        }
