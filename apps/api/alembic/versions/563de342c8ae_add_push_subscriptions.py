"""add push_subscriptions (웹 푸시 구독, ENT-001)

Revision ID: 563de342c8ae
Revises: b3d5f8a1c2e4
Create Date: 2026-10-02 00:00:00.000000

PWA PR-2 웹 푸시 (docs/requirements/pwa.md §5.1). 사용자 단위 리소스라 workspace_id 가 없다.

- 새 테이블 1개 + FK 1 (users.id ON DELETE CASCADE) + UNIQUE(endpoint) + index(user_id).
- **가산형** — 기존 테이블 변경 0. deploy-rollback 은 migrate 를 건너뛰므로(구 이미지는 이 테이블을
  모른다) 롤백 뒤에도 남은 테이블이 구 코드에 영향을 주지 않는다 (C-20).
- 제약 이름은 전부 명시한다 (모델 `src/push/models.py` 와 같은 이름).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "563de342c8ae"
down_revision: Union[str, Sequence[str], None] = "b3d5f8a1c2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """push_subscriptions 테이블 + FK(CASCADE) + UNIQUE(endpoint) + index(user_id)."""
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.Text(), nullable=False),
        sa.Column("auth", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="push_subscriptions_pkey"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_push_subscriptions_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("endpoint", name="uq_push_subscriptions_endpoint"),
    )
    op.create_index(
        "ix_push_subscriptions_user_id",
        "push_subscriptions",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_push_subscriptions_user_id", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
