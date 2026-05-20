# Sprint 24 Wave 2 T-AUDIT-VIEW (BUG-POW-008) — ItemPromotionAudit 조회 전용 repository
"""ItemPromotionAudit read-only 조회 — Settings Audit 탭 (admin) 용.

Sprint 23 D4 의 inbox/notes/meetings/actions repository 가 보유한 save_*_audit
는 INSERT 전용. 본 repository 는 cross-domain 일관 조회 (workspace_id 기준) 를
하나의 위치에 둔다. router 의 단일 endpoint 가 본 클래스에 의존.

도메인 직접 import 금지 (헌법 §4): common/promote_models 의 generic SQLModel 만 사용.
"""
import uuid

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.common.promote_models import (
    PROMOTABLE_ITEM_TYPES,
    ItemPromotionAudit,
)


class ItemPromotionAuditRepository:
    """ItemPromotionAudit cross-domain 조회 — read only."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_workspace(
        self,
        workspace_id: uuid.UUID,
        item_type: str | None = None,
        limit: int = 50,
        before_created_at: str | None = None,
    ) -> list[ItemPromotionAudit]:
        """target_workspace_id 기준 audit 목록 (최신 → 과거 순).

        Args:
            workspace_id: target workspace (요청 admin 의 ws).
            item_type: 4 종 (meeting/note/inbox/action) 중 1 또는 None.
                None → 모두. 화이트리스트 외 값 → 빈 결과 (fail-safe).
            limit: 페이지 크기 (1..200 — router 에서 clamp).
            before_created_at: cursor (created_at ISO string) — 이 시각 이전 audit 만.
                None 이면 가장 최신부터.

        Returns:
            target_workspace_id == workspace_id 인 audit. created_at desc.
            cross-workspace 격리: source_workspace_id 외 검색 금지 (I-9).
        """
        stmt = select(ItemPromotionAudit).where(
            ItemPromotionAudit.target_workspace_id == workspace_id
        )
        if item_type is not None:
            # 화이트리스트 외 값 → 빈 결과 (SQL 통과 안 시킴 — fail-safe).
            if item_type not in PROMOTABLE_ITEM_TYPES:
                return []
            stmt = stmt.where(ItemPromotionAudit.item_type == item_type)

        if before_created_at is not None:
            from datetime import datetime
            try:
                cursor_dt = datetime.fromisoformat(before_created_at)
            except ValueError:
                # 잘못된 cursor → 빈 결과 (404 보단 빈 페이지 — Codex F-1 fail-safe).
                return []
            stmt = stmt.where(ItemPromotionAudit.created_at < cursor_dt)

        stmt = stmt.order_by(ItemPromotionAudit.created_at.desc()).limit(limit)
        return list((await self.session.exec(stmt)).all())
