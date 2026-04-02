"""add sprint3 tables embedding_chunks semantic_caches notes

Revision ID: e2c3782ab9c6
Revises: 300102db250d
Create Date: 2026-04-02 13:47:51.911771

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'e2c3782ab9c6'
down_revision: Union[str, Sequence[str], None] = '300102db250d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # PostgreSQL 확장 활성화
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # embedding_chunks 테이블
    op.create_table('embedding_chunks',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=True),
        sa.Column('source_id', sa.Uuid(), nullable=False),
        sa.Column('source_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('chunk_level', sa.Integer(), nullable=False),
        sa.Column('parent_chunk_id', sa.Uuid(), nullable=True),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['parent_chunk_id'], ['embedding_chunks.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_embedding_chunks_parent_chunk_id'), 'embedding_chunks', ['parent_chunk_id'], unique=False)
    op.create_index(op.f('ix_embedding_chunks_project_id'), 'embedding_chunks', ['project_id'], unique=False)
    op.create_index(op.f('ix_embedding_chunks_workspace_id'), 'embedding_chunks', ['workspace_id'], unique=False)

    # 수동 인덱스: pgvector ivfflat + pg_trgm gin
    op.execute("""
        CREATE INDEX idx_chunks_source ON embedding_chunks (source_type, source_id)
    """)
    op.execute("""
        CREATE INDEX idx_chunks_vector ON embedding_chunks
        USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
    """)
    op.execute("""
        CREATE INDEX idx_chunks_trgm ON embedding_chunks
        USING gin (chunk_text gin_trgm_ops)
    """)

    # notes 테이블
    op.create_table('notes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=True),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('content', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('plain_text', sa.Text(), server_default='', nullable=True),
        sa.Column('created_by_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notes_created_by_id'), 'notes', ['created_by_id'], unique=False)
    op.create_index(op.f('ix_notes_project_id'), 'notes', ['project_id'], unique=False)
    op.create_index(op.f('ix_notes_workspace_id'), 'notes', ['workspace_id'], unique=False)

    # semantic_caches 테이블
    op.create_table('semantic_caches',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=True),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('question_embedding', Vector(1536), nullable=True),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('sources', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('hit_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_semantic_caches_workspace_id'), 'semantic_caches', ['workspace_id'], unique=False)
    op.execute("""
        CREATE INDEX idx_cache_vector ON semantic_caches
        USING ivfflat (question_embedding vector_cosine_ops)
    """)
    op.execute("""
        CREATE INDEX idx_cache_expires ON semantic_caches (expires_at)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_cache_expires', table_name='semantic_caches')
    op.drop_index('idx_cache_vector', table_name='semantic_caches')
    op.drop_index(op.f('ix_semantic_caches_workspace_id'), table_name='semantic_caches')
    op.drop_table('semantic_caches')

    op.drop_index(op.f('ix_notes_workspace_id'), table_name='notes')
    op.drop_index(op.f('ix_notes_project_id'), table_name='notes')
    op.drop_index(op.f('ix_notes_created_by_id'), table_name='notes')
    op.drop_table('notes')

    op.drop_index('idx_chunks_trgm', table_name='embedding_chunks')
    op.drop_index('idx_chunks_vector', table_name='embedding_chunks')
    op.drop_index('idx_chunks_source', table_name='embedding_chunks')
    op.drop_index(op.f('ix_embedding_chunks_workspace_id'), table_name='embedding_chunks')
    op.drop_index(op.f('ix_embedding_chunks_project_id'), table_name='embedding_chunks')
    op.drop_index(op.f('ix_embedding_chunks_parent_chunk_id'), table_name='embedding_chunks')
    op.drop_table('embedding_chunks')

    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS vector")
