"""ADR-026 integrations API 스키마 — Pydantic V2 camelCase alias."""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ConnectionStatus = Literal["active", "disabled", "reauth_required"]
DocumentSyncStatus = Literal[
    "pending",
    "processing",
    "completed",
    "failed",
    "stale",
    "reauth_required",
    "purged",
]
SyncRunStatus = Literal["pending", "processing", "completed", "failed"]


class AuthorizationUrlResponse(BaseModel):
    authorization_url: str = Field(alias="authorizationUrl")

    model_config = {"populate_by_name": True}


class IntegrationConnectionResponse(BaseModel):
    id: uuid.UUID
    provider: str
    status: ConnectionStatus
    last_synced_at: datetime | None = Field(default=None, alias="lastSyncedAt")

    model_config = {"from_attributes": True, "populate_by_name": True}


class ImportExternalDocumentsRequest(BaseModel):
    file_ids: list[str] = Field(min_length=1, alias="fileIds")
    project_id: uuid.UUID | None = Field(default=None, alias="projectId")

    model_config = {"populate_by_name": True}


class SyncRunCreatedResponse(BaseModel):
    sync_run_id: uuid.UUID = Field(alias="syncRunId")

    model_config = {"populate_by_name": True}


class ExternalDocumentResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID | None = Field(alias="projectId")
    drive_file_id: str = Field(alias="driveFileId")
    title: str
    mime_type: str = Field(alias="mimeType")
    origin_url: str = Field(alias="originUrl")
    revision_id: str = Field(alias="revisionId")
    sync_status: DocumentSyncStatus = Field(alias="syncStatus")
    last_synced_at: datetime | None = Field(default=None, alias="lastSyncedAt")

    model_config = {"from_attributes": True, "populate_by_name": True}


class ExternalDocumentDetailResponse(ExternalDocumentResponse):
    plain_text: str = Field(alias="plainText")


class IntegrationSyncRunResponse(BaseModel):
    id: uuid.UUID
    status: SyncRunStatus
    started_at: datetime = Field(alias="startedAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")
    error_summary: str | None = Field(default=None, alias="errorSummary")
    documents: list[ExternalDocumentResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True, "populate_by_name": True}
