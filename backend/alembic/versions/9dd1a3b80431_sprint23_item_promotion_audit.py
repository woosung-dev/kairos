"""sprint23_item_promotion_audit

Revision ID: 9dd1a3b80431
Revises: d8623df0adab
Create Date: 2026-05-19

Sprint 23 cozy-crystal D4 — generic cross-workspace promote audit 테이블 신설.
memory.PromotionAudit 와 별개 (memory_id FK 강제 회피).
Option B 사용자 lock-in (2026-05-19).

scope:
- item_promotion_audit 테이블 신설
- 4 FK (source/target workspaces.id × 2, users.id × 1)
- CHECK constraint: item_type ∈ {'meeting','note','inbox','action'}
- 5 index (item_type, source_item_id, source_workspace_id, target_workspace_id, created_at)

도메인별 source_item_id → meetings/notes/inbox_items/action_items.id 는 soft reference
(item_type generic 으로 composite FK 강제 불가, BL-050 적용 도메인 model 만).
"""
# alembic revision 9dd1a3b80431 (sprint23_item_promotion_audit)
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9dd1a3b80431'
down_revision: Union[str, Sequence[str], None] = 'd8623df0adab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """item_promotion_audit 테이블 + FK + CHECK + 5 index 신설."""
    op.create_table(
        "item_promotion_audit",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("item_type", sa.String(), nullable=False),
        sa.Column("source_item_id", sa.Uuid(), nullable=False),
        sa.Column("new_item_id", sa.Uuid(), nullable=False),
        sa.Column("source_workspace_id", sa.Uuid(), nullable=False),
        sa.Column("target_workspace_id", sa.Uuid(), nullable=False),
        sa.Column("promoted_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "embedding_status",
            sa.String(),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_workspace_id"],
            ["workspaces.id"],
            name="fk_item_promotion_audit_source_workspace_id_workspaces",
        ),
        sa.ForeignKeyConstraint(
            ["target_workspace_id"],
            ["workspaces.id"],
            name="fk_item_promotion_audit_target_workspace_id_workspaces",
        ),
        sa.ForeignKeyConstraint(
            ["promoted_by_user_id"],
            ["users.id"],
            name="fk_item_promotion_audit_promoted_by_user_id_users",
        ),
        sa.CheckConstraint(
            "item_type IN ('meeting', 'note', 'inbox', 'action')",
            name="ck_item_promotion_audit_item_type",
        ),
    )
    op.create_index(
        "ix_item_promotion_audit_item_type",
        "item_promotion_audit",
        ["item_type"],
    )
    op.create_index(
        "ix_item_promotion_audit_source_item_id",
        "item_promotion_audit",
        ["source_item_id"],
    )
    op.create_index(
        "ix_item_promotion_audit_source_workspace_id",
        "item_promotion_audit",
        ["source_workspace_id"],
    )
    op.create_index(
        "ix_item_promotion_audit_target_workspace_id",
        "item_promotion_audit",
        ["target_workspace_id"],
    )
    op.create_index(
        "ix_item_promotion_audit_created_at",
        "item_promotion_audit",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_item_promotion_audit_created_at", table_name="item_promotion_audit"
    )
    op.drop_index(
        "ix_item_promotion_audit_target_workspace_id",
        table_name="item_promotion_audit",
    )
    op.drop_index(
        "ix_item_promotion_audit_source_workspace_id",
        table_name="item_promotion_audit",
    )
    op.drop_index(
        "ix_item_promotion_audit_source_item_id",
        table_name="item_promotion_audit",
    )
    op.drop_index(
        "ix_item_promotion_audit_item_type", table_name="item_promotion_audit"
    )
    op.drop_table("item_promotion_audit")
