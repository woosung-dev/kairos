# 4 도메인 (meeting / note / inbox / action) cross-workspace promote audit 모델
"""ItemPromotionAudit — Sprint 23 D4 (cozy-crystal) generic promote audit.

memory 도메인의 PromotionAudit 와 별개 — 그쪽은 `memory_id` FK 강제로 도메인 재사용 불가.
헌법 I-18 (Promotion = 복제 + tombstone, 이동 금지) 강제 — 적용 도메인 4 추가:
meeting / note / inbox / action. Option B 사용자 lock-in (2026-05-19).

설계 사유 (FK soft reference):
- item_type generic — 도메인별 (workspace_id, item_id) → (workspace_id, id) composite FK 강제 불가.
- BL-050 composite FK 패턴은 도메인 model 만 적용. 본 audit 테이블은 item_type 으로 분기 soft FK 유지.
- CHECK constraint 로 item_type 허용값 강제 (ck_item_promotion_audit_item_type).
- source_workspace_id / target_workspace_id / promoted_by_user_id 만 FK (cross-workspace 격리).
"""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel


# 4 도메인 promote 허용 item_type literal (CHECK constraint 와 정합)
PROMOTABLE_ITEM_TYPES: tuple[str, ...] = ("meeting", "note", "inbox", "action")


class ItemPromotionAudit(SQLModel, table=True):
    """4 도메인 (meeting / note / inbox / action) cross-workspace promote audit.

    1 row per promote event. source_item_id (보존된 원본) + new_item_id (target 복제본) 추적.
    embedding_status: 'pending' / 'processing' / 'completed' / 'failed' / 'n/a' (도메인별 다름).
    """

    __tablename__ = "item_promotion_audit"
    __table_args__ = (
        CheckConstraint(
            "item_type IN ('meeting', 'note', 'inbox', 'action')",
            name="ck_item_promotion_audit_item_type",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    item_type: str = Field(nullable=False, index=True)
    source_item_id: uuid.UUID = Field(nullable=False, index=True)
    new_item_id: uuid.UUID = Field(nullable=False)
    source_workspace_id: uuid.UUID = Field(
        foreign_key="workspaces.id", nullable=False, index=True
    )
    target_workspace_id: uuid.UUID = Field(
        foreign_key="workspaces.id", nullable=False, index=True
    )
    promoted_by_user_id: uuid.UUID = Field(
        foreign_key="users.id", nullable=False
    )
    embedding_status: str = Field(default="pending", nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
