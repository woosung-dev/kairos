"""add_meeting_source

Revision ID: 5f9a2b7ee3a4
Revises: 7ebd009f89a4
Create Date: 2026-05-11 22:49:17.677418

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f9a2b7ee3a4'
down_revision: Union[str, Sequence[str], None] = '7ebd009f89a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('meetings', sa.Column('source', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('meetings', 'source')
