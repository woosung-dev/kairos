"""member_default_project_visibility

Revision ID: 5933c7261107
Revises: f3a8c1d29b04
Create Date: 2026-07-05

W-5 연결 — 초대 수락 시 invite.default_project_visibility 를 멤버로 복사해
이후 프로젝트 생성 기본 visibility 로 적용하기 위한 컬럼.

scope:
- workspace_members.default_project_visibility 컬럼 추가 (nullable, additive)
"""
# alembic revision 5933c7261107 (member_default_project_visibility)
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5933c7261107"
down_revision: Union[str, Sequence[str], None] = "f3a8c1d29b04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """workspace_members 에 default_project_visibility nullable 컬럼 추가."""
    op.add_column(
        "workspace_members",
        sa.Column("default_project_visibility", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workspace_members", "default_project_visibility")
