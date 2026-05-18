"""sprint22_user_onboarding

Revision ID: d8623df0adab
Revises: cf903ab3dd37
Create Date: 2026-05-18 23:38:29.156916

"""
# alembic revision d8623df0adab (sprint22_user_onboarding)
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8623df0adab'
down_revision: Union[str, Sequence[str], None] = 'cf903ab3dd37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """User 에 onboarding_step + onboarded_at 추가 + 기존 row backfill step=4."""
    op.add_column(
        "users",
        sa.Column("onboarding_step", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("onboarded_at", sa.DateTime(timezone=True), nullable=True),
    )
    # D7 lock-in: 기존 user 는 이미 active → step=4 + onboarded_at=created_at
    op.execute(
        "UPDATE users "
        "SET onboarding_step = 4, onboarded_at = created_at "
        "WHERE onboarding_step = 0"
    )


def downgrade() -> None:
    op.drop_column("users", "onboarded_at")
    op.drop_column("users", "onboarding_step")
