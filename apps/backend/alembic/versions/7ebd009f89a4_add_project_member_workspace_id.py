"""add project_member workspace_id

Revision ID: 7ebd009f89a4
Revises: 2d128def6779
Create Date: 2026-05-11 20:20:08.767132

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ebd009f89a4'
down_revision: Union[str, Sequence[str], None] = '2d128def6779'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """ProjectMember에 workspace_id NOT NULL 컬럼 추가 + composite FK (BE-T13)."""
    # 1. workspace_id 컬럼 추가 (nullable=True로 시작)
    op.add_column('project_members', sa.Column('workspace_id', sa.Uuid(), nullable=True))
    op.create_index(op.f('ix_project_members_workspace_id'), 'project_members', ['workspace_id'], unique=False)

    # 2. 기존 row backfill (project_members에 workspace_id 채우기)
    op.execute("""
        UPDATE project_members pm
        SET workspace_id = p.workspace_id
        FROM projects p
        WHERE pm.project_id = p.id
    """)

    # 3. NOT NULL 제약 적용
    op.alter_column('project_members', 'workspace_id', nullable=False)

    # 4. projects 테이블에 UNIQUE(id, workspace_id) 추가 (composite FK 선행 조건)
    op.create_unique_constraint('uq_projects_id_workspace_id', 'projects', ['id', 'workspace_id'])

    # 5. composite FK 추가
    op.create_foreign_key(
        'fk_project_members_project_workspace',
        'project_members', 'projects',
        ['project_id', 'workspace_id'], ['id', 'workspace_id'],
    )

    # 6. uq_project_member_ws UNIQUE 추가 (models.py에 추가한 것)
    op.create_unique_constraint('uq_project_member_ws', 'project_members', ['id', 'workspace_id'])

    # 7. workspaces 단순 FK 추가
    op.create_foreign_key(
        'fk_project_members_workspace',
        'project_members', 'workspaces',
        ['workspace_id'], ['id'],
    )


def downgrade() -> None:
    """workspace_id 컬럼 및 관련 제약 제거."""
    op.drop_constraint('fk_project_members_workspace', 'project_members', type_='foreignkey')
    op.drop_constraint('uq_project_member_ws', 'project_members', type_='unique')
    op.drop_constraint('fk_project_members_project_workspace', 'project_members', type_='foreignkey')
    op.drop_constraint('uq_projects_id_workspace_id', 'projects', type_='unique')
    op.drop_index(op.f('ix_project_members_workspace_id'), table_name='project_members')
    op.drop_column('project_members', 'workspace_id')
