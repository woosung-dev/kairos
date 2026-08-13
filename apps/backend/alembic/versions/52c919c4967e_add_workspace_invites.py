"""add_workspace_invites

Revision ID: 52c919c4967e
Revises: e2c3782ab9c6
Create Date: 2026-04-04 22:05:43.092724

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision: str = '52c919c4967e'
down_revision: Union[str, Sequence[str], None] = 'e2c3782ab9c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """workspace_invites 테이블 생성."""
    op.create_table('workspace_invites',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('workspace_id', sa.Uuid(), nullable=False),
    sa.Column('code', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('role', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_by_id', sa.Uuid(), nullable=False),
    sa.Column('max_uses', sa.Integer(), nullable=True),
    sa.Column('use_count', sa.Integer(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workspace_invites_code'), 'workspace_invites', ['code'], unique=True)
    op.create_index('idx_invites_workspace', 'workspace_invites', ['workspace_id'])


def downgrade() -> None:
    """workspace_invites 테이블 삭제."""
    op.drop_index('idx_invites_workspace', table_name='workspace_invites')
    op.drop_index(op.f('ix_workspace_invites_code'), table_name='workspace_invites')
    op.drop_table('workspace_invites')
