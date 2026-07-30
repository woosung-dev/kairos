"""add integrations tables

Revision ID: a48095872e14
Revises: 5933c7261107
Create Date: 2026-07-30 16:55:26.360695

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a48095872e14'
down_revision: Union[str, Sequence[str], None] = '5933c7261107'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """외부 소스 ingest 테이블과 workspace 복합 FK를 생성한다."""
    op.create_table(
        "integration_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("authorized_by_id", sa.Uuid(), nullable=False),
        sa.Column(
            "encrypted_refresh_token",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
        ),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("scope", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["authorized_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "workspace_id",
            name="uq_integration_connections_id_workspace_id",
        ),
    )
    op.create_index(
        "ix_integration_connections_workspace_id",
        "integration_connections",
        ["workspace_id"],
        unique=False,
    )

    op.create_table(
        "external_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("drive_file_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("mime_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("origin_url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("revision_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("content_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("plain_text", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("sync_status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["connection_id"], ["integration_connections.id"]),
        sa.ForeignKeyConstraint(
            ["workspace_id", "connection_id"],
            ["integration_connections.workspace_id", "integration_connections.id"],
            name="fk_external_documents_connection_workspace",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="fk_external_documents_project_workspace",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "workspace_id",
            name="uq_external_documents_id_workspace_id",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "connection_id",
            "drive_file_id",
            name="uq_external_documents_workspace_connection_drive_file",
        ),
    )
    op.create_index(
        "ix_external_documents_workspace_id",
        "external_documents",
        ["workspace_id"],
        unique=False,
    )

    op.create_table(
        "integration_sync_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("requested_by_id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_summary", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(["connection_id"], ["integration_connections.id"]),
        sa.ForeignKeyConstraint(
            ["workspace_id", "connection_id"],
            ["integration_connections.workspace_id", "integration_connections.id"],
            name="fk_integration_sync_runs_connection_workspace",
        ),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "workspace_id",
            name="uq_integration_sync_runs_id_workspace_id",
        ),
    )
    op.create_index(
        "ix_integration_sync_runs_workspace_id",
        "integration_sync_runs",
        ["workspace_id"],
        unique=False,
    )


def downgrade() -> None:
    """자식 테이블부터 역순으로 제거한다."""
    op.drop_index(
        "ix_integration_sync_runs_workspace_id",
        table_name="integration_sync_runs",
    )
    op.drop_table("integration_sync_runs")
    op.drop_index(
        "ix_external_documents_workspace_id",
        table_name="external_documents",
    )
    op.drop_table("external_documents")
    op.drop_index(
        "ix_integration_connections_workspace_id",
        table_name="integration_connections",
    )
    op.drop_table("integration_connections")
