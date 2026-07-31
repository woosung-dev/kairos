"""ADR-026 외부 소스 ingest 모델."""
import uuid
from datetime import datetime

from sqlmodel import Field, ForeignKeyConstraint, SQLModel, UniqueConstraint


class IntegrationConnection(SQLModel, table=True):
    """워크스페이스의 Google OAuth 연결."""

    __tablename__ = "integration_connections"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "workspace_id",
            name="uq_integration_connections_id_workspace_id",
        ),
        UniqueConstraint(
            "workspace_id",
            "provider",
            name="uq_integration_connections_workspace_provider",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", index=True)
    provider: str = "google_drive"
    authorized_by_id: uuid.UUID = Field(foreign_key="users.id")
    encrypted_refresh_token: str | None
    status: str = "active"  # active | disabled | reauth_required
    scope: str
    token_expires_at: datetime | None = None
    last_synced_at: datetime | None = None


class IntegrationOAuthState(SQLModel, table=True):
    """한 번만 소비할 수 있는 Google OAuth callback state."""

    __tablename__ = "integration_oauth_states"

    nonce: str = Field(primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", index=True)
    requester_user_id: uuid.UUID = Field(foreign_key="users.id")
    expires_at: datetime = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExternalDocument(SQLModel, table=True):
    """선택한 Drive 문서의 Kairos 내부 원본."""

    __tablename__ = "external_documents"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "workspace_id",
            name="uq_external_documents_id_workspace_id",
        ),
        UniqueConstraint(
            "workspace_id",
            "connection_id",
            "drive_file_id",
            name="uq_external_documents_workspace_connection_drive_file",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "connection_id"],
            ["integration_connections.workspace_id", "integration_connections.id"],
            name="fk_external_documents_connection_workspace",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="fk_external_documents_project_workspace",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "sync_run_id"],
            ["integration_sync_runs.workspace_id", "integration_sync_runs.id"],
            name="fk_external_documents_sync_run_workspace",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", index=True)
    connection_id: uuid.UUID = Field(foreign_key="integration_connections.id")
    project_id: uuid.UUID | None = Field(
        default=None, foreign_key="projects.id"
    )
    sync_run_id: uuid.UUID | None = Field(
        default=None, foreign_key="integration_sync_runs.id"
    )
    drive_file_id: str
    title: str
    mime_type: str
    origin_url: str
    revision_id: str
    content_hash: str
    plain_text: str
    sync_status: str = "pending"  # pending | processing | completed | failed | stale | reauth_required | purged
    last_synced_at: datetime | None = None


class IntegrationSyncRun(SQLModel, table=True):
    """202 polling과 감사를 위한 외부 문서 동기화 실행 기록."""

    __tablename__ = "integration_sync_runs"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "workspace_id",
            name="uq_integration_sync_runs_id_workspace_id",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "connection_id"],
            ["integration_connections.workspace_id", "integration_connections.id"],
            name="fk_integration_sync_runs_connection_workspace",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", index=True)
    connection_id: uuid.UUID = Field(foreign_key="integration_connections.id")
    status: str = "pending"  # pending | processing | completed | failed
    requested_by_id: uuid.UUID = Field(foreign_key="users.id")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    error_summary: str | None = None
