"""add invite default project visibility

Revision ID: 2d128def6779
Revises: 754f571d5544
Create Date: 2026-05-11 12:30:15.189869

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d128def6779'
down_revision: Union[str, Sequence[str], None] = '754f571d5544'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'workspace_invites',
        sa.Column('default_project_visibility', sa.String(), nullable=False, server_default='public'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('workspace_invites', 'default_project_visibility')
