"""add project visibility

Revision ID: c4c5709a4ab4
Revises: 8df4cabf213d
Create Date: 2026-05-11 12:15:12.107353

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4c5709a4ab4'
down_revision: Union[str, Sequence[str], None] = '8df4cabf213d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'projects',
        sa.Column('visibility', sa.String(), nullable=False, server_default='public'),
    )
    op.create_index(
        op.f('ix_projects_visibility'),
        'projects',
        ['visibility'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_projects_visibility'), table_name='projects')
    op.drop_column('projects', 'visibility')
