"""add_inbox_threshold

Revision ID: 8df4cabf213d
Revises: 52c919c4967e
Create Date: 2026-04-04 23:57:58.824615

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8df4cabf213d'
down_revision: Union[str, Sequence[str], None] = '52c919c4967e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('workspaces', sa.Column('inbox_threshold', sa.Float(), nullable=False, server_default='0.9'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('workspaces', 'inbox_threshold')
