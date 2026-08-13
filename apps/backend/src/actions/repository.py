# apps/backend/src/actions/repository.py
"""ActionItem Repository — AsyncSession 유일 보유자."""
import uuid

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import func, select, update

from src.actions.models import ActionItem
from src.common.promote_models import ItemPromotionAudit
from src.common.visibility import RequesterContext, apply_fk_project_visibility


def _action_visibility_filter(
    stmt,
    requester_user_id: uuid.UUID | None,
    requester_role: str | None,
):
    """F1 (2026-06-23 fullsweep): action LIST 에 project visibility 게이트 적용.

    규칙 정의는 common/visibility.py SSOT — FK-상관 어댑터 위임
    (notes._note_visibility_filter 와 동일 계보, project_id IS NULL 통과 /
    role=None 내부호출 skip / admin·owner 우회 / CAND-B flatten EXISTS).
    """
    return apply_fk_project_visibility(
        stmt, ActionItem.project_id, RequesterContext(requester_user_id, requester_role)
    )


class ActionItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(
        self, action_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> ActionItem | None:
        """헌법 I-9 (Codex F-1): action_id + workspace_id 동시 필터."""
        return (await self.session.exec(
            select(ActionItem).where(
                ActionItem.id == action_id,
                ActionItem.workspace_id == workspace_id,
            )
        )).one_or_none()

    async def find_by_workspace(
        self,
        workspace_id: uuid.UUID,
        status: str | None = None,
        priority: str | None = None,
        project_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 20,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> list[ActionItem]:
        stmt = select(ActionItem).where(ActionItem.workspace_id == workspace_id)
        if status:
            stmt = stmt.where(ActionItem.status == status)
        if priority:
            stmt = stmt.where(ActionItem.priority == priority)
        if project_id:
            stmt = stmt.where(ActionItem.project_id == project_id)
        # F1: project visibility 게이트 (비-멤버 private/draft 액션 누출 차단).
        stmt = _action_visibility_filter(stmt, requester_user_id, requester_role)
        stmt = stmt.order_by(ActionItem.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)
        return list((await self.session.exec(stmt)).all())

    async def count_by_workspace(
        self,
        workspace_id: uuid.UUID,
        status: str | None = None,
        priority: str | None = None,
        project_id: uuid.UUID | None = None,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> int:
        """count 는 find_by_workspace 와 동일 필터 계약 (PR-2 c1 — 이전엔
        priority/project_id 를 못 받아 필터된 list 와 total/hasNext 가 불일치)."""
        stmt = (
            select(func.count())
            .select_from(ActionItem)
            .where(ActionItem.workspace_id == workspace_id)
        )
        if status:
            stmt = stmt.where(ActionItem.status == status)
        if priority:
            stmt = stmt.where(ActionItem.priority == priority)
        if project_id:
            stmt = stmt.where(ActionItem.project_id == project_id)
        # F1: total 도 필터된 집합 기준 (pagination 정합).
        stmt = _action_visibility_filter(stmt, requester_user_id, requester_role)
        return (await self.session.exec(stmt)).one()

    async def find_by_meeting(self, meeting_id: uuid.UUID) -> list[ActionItem]:
        """회의에서 추출된 액션 아이템 조회."""
        stmt = (
            select(ActionItem)
            .where(ActionItem.meeting_id == meeting_id)
            .order_by(ActionItem.created_at.desc())
        )
        return list((await self.session.exec(stmt)).all())

    async def cancel_todo_by_project(self, project_id: uuid.UUID) -> int:
        """프로젝트 archive 시 todo 상태 액션을 cancelled로 변경.

        BL-054 manifest G3-keep: rowcount contract preservation 을 위해 session.execute() 유지.
        SQLModel exec(UpdateBase) 가 반환하는 result 의 type 이 SQLModel 0.0.37 시점
        dialect/version 에 따라 CursorResult / ScalarResult 모호 — DML result 의
        rowcount 접근을 SA Result 의 표준 패턴으로 명시적으로 유지한다
        (Codex 2차 review BL-054 F3 MINOR 수락).
        """
        result = await self.session.execute(
            update(ActionItem)
            .where(
                ActionItem.project_id == project_id,
                ActionItem.status == "todo",
            )
            .values(status="cancelled")
        )
        await self.session.flush()
        return result.rowcount  # type: ignore[return-value]

    async def save(self, item: ActionItem) -> ActionItem:
        self.session.add(item)
        await self.session.flush()
        return item

    async def commit(self) -> None:
        await self.session.commit()

    # ── Sprint 23 D4 Task 2 Step 2.5: promote 지원 메서드 ──

    async def save_promoted_action_item(self, item: ActionItem) -> ActionItem:
        """promote 복제본 ActionItem INSERT — workspace_id 는 호출자가 target 으로 설정.

        save() 와 시그니처 동일하지만, promote 흐름에서 명시적으로 호출 출처 분리.
        I-9 검증은 호출자 (service.promote) 가 사전에 target workspace 멤버십을 확인.
        """
        self.session.add(item)
        await self.session.flush()
        return item

    async def save_item_promotion_audit(
        self, audit: ItemPromotionAudit
    ) -> ItemPromotionAudit:
        """4 도메인 공통 ItemPromotionAudit INSERT — commit 은 호출자."""
        self.session.add(audit)
        await self.session.flush()
        return audit
