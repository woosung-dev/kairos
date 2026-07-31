"""add integration oauth states

Revision ID: 7f6b8c9d0e1f
Revises: a48095872e14
Create Date: 2026-08-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "7f6b8c9d0e1f"
down_revision: Union[str, Sequence[str], None] = "a48095872e14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """OAuth callback의 일회성 nonce 저장소를 생성한다."""
    op.create_table(
        "integration_oauth_states",
        sa.Column("nonce", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("requester_user_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["requester_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("nonce"),
    )
    op.create_index(
        "ix_integration_oauth_states_workspace_id",
        "integration_oauth_states",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_integration_oauth_states_expires_at",
        "integration_oauth_states",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    """OAuth callback nonce 저장소를 제거한다."""
    op.drop_index(
        "ix_integration_oauth_states_expires_at",
        table_name="integration_oauth_states",
    )
    op.drop_index(
        "ix_integration_oauth_states_workspace_id",
        table_name="integration_oauth_states",
    )
    op.drop_table("integration_oauth_states")
