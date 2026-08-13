"""sprint28_wave1_feedback_entries

Revision ID: f3a8c1d29b04
Revises: c7e9f1a2b3d4
Create Date: 2026-05-29

Sprint 28 Wave 1 — dogfooding 사용자 피드백 수집 테이블 신설.
user-level 피드백(워크스페이스 비종속) — workspace_id 는 작성 시점 컨텍스트로 nullable.

scope:
- feedback_entries 테이블 신설
- 2 FK (users.id, workspaces.id nullable)
- 3 index (user_id, workspace_id, created_at)
"""
# alembic revision f3a8c1d29b04 (sprint28_wave1_feedback_entries)
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3a8c1d29b04"
down_revision: Union[str, Sequence[str], None] = "c7e9f1a2b3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """feedback_entries 테이블 + 2 FK + 3 index 신설."""
    op.create_table(
        "feedback_entries",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "is_anonymous",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("page_url", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_feedback_entries_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_feedback_entries_workspace_id_workspaces",
        ),
    )
    op.create_index(
        "ix_feedback_entries_user_id", "feedback_entries", ["user_id"]
    )
    op.create_index(
        "ix_feedback_entries_workspace_id", "feedback_entries", ["workspace_id"]
    )
    op.create_index(
        "ix_feedback_entries_created_at", "feedback_entries", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_feedback_entries_created_at", table_name="feedback_entries")
    op.drop_index("ix_feedback_entries_workspace_id", table_name="feedback_entries")
    op.drop_index("ix_feedback_entries_user_id", table_name="feedback_entries")
    op.drop_table("feedback_entries")
