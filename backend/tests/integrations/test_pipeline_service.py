"""Google Drive sync pipeline의 fail-closed 계약 테스트."""
import gc
import json
import uuid
import weakref
from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import sentry_sdk
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.models import User
from src.common.exceptions import EncryptionError
from src.embeddings.models import EmbeddingChunk, SemanticCache
from src.embeddings.repository import EmbeddingRepository
from src.embeddings.service import EmbeddingService
from src.integrations import pipeline_service as pipeline_module
from src.integrations import service as integration_service_module
from src.integrations.drive_client import DriveExport, DriveFileMetadata
from src.integrations.exceptions import (
    DriveClientError,
    DrivePermissionRevokedError,
    DriveReauthenticationRequiredError,
    DriveSourceMissingError,
    DriveTemporaryError,
    DriveUnsupportedMimeTypeError,
    IntegrationEncryptionError,
)
from src.integrations.models import ExternalDocument, IntegrationConnection
from src.integrations.pipeline_service import (
    GoogleDriveSyncPipelineService,
    _PURGE_ALLOWED_ERRORS,
)
from src.integrations.service import IntegrationService
from src.main import _scrub_pii_hook
from src.projects.models import Project
from src.workspaces.models import Workspace


@dataclass
class _PipelineState:
    workspace_id: uuid.UUID = field(default_factory=uuid.uuid4)
    connection_id: uuid.UUID = field(default_factory=uuid.uuid4)
    project_id: uuid.UUID = field(default_factory=uuid.uuid4)
    documents: dict[uuid.UUID, SimpleNamespace] = field(default_factory=dict)
    sync_run: SimpleNamespace | None = None
    deleted_sources: list[tuple[str, uuid.UUID]] = field(default_factory=list)
    deleted_caches: list[tuple[uuid.UUID, uuid.UUID | None]] = field(default_factory=list)
    embedded_documents: list[dict[str, object]] = field(default_factory=list)
    generated_chunk_count: int = 0
    chunk_project_ids: set[uuid.UUID | None] = field(default_factory=set)
    commits: int = 0


class _FakeSession:
    def __init__(self, state: _PipelineState) -> None:
        self.state = state

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class _FakeSessionFactory:
    def __init__(self, state: _PipelineState) -> None:
        self.state = state
        self.calls = 0

    def __call__(self) -> _FakeSession:
        self.calls += 1
        return _FakeSession(self.state)


class _FakeIntegrationRepository:
    def __init__(self, session: _FakeSession) -> None:
        self.state = session.state

    async def find_document_by_id(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> SimpleNamespace | None:
        document = self.state.documents.get(document_id)
        if document is None or document.workspace_id != workspace_id:
            return None
        return document

    async def find_document_id_by_drive_file_id(
        self,
        connection_id: uuid.UUID,
        workspace_id: uuid.UUID,
        drive_file_id: str,
    ) -> uuid.UUID | None:
        for document in self.state.documents.values():
            if (
                document.connection_id == connection_id
                and document.workspace_id == workspace_id
                and document.drive_file_id == drive_file_id
            ):
                return document.id
        return None

    async def create_document(
        self,
        document: SimpleNamespace,
        workspace_id: uuid.UUID,
    ) -> SimpleNamespace:
        assert document.workspace_id == workspace_id
        self.state.documents[document.id] = document
        return document

    async def update_document(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
        **values: object,
    ) -> None:
        document = await self.find_document_by_id(document_id, workspace_id)
        if document is not None:
            for key, value in values.items():
                setattr(document, key, value)

    async def update_document_sync_status(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
        sync_status: str,
        last_synced_at: object,
        **values: object,
    ) -> None:
        await self.update_document(
            document_id,
            workspace_id,
            sync_status=sync_status,
            last_synced_at=last_synced_at,
            **values,
        )

    async def purge_document_content(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
        **values: object,
    ) -> None:
        await self.update_document(
            document_id,
            workspace_id,
            plain_text="",
            content_hash="",
            sync_status="purged",
            **values,
        )

    async def delete_document(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> None:
        document = await self.find_document_by_id(document_id, workspace_id)
        if document is not None:
            del self.state.documents[document_id]

    async def find_sync_run_by_id(
        self,
        sync_run_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> SimpleNamespace | None:
        if (
            self.state.sync_run is None
            or self.state.sync_run.id != sync_run_id
            or self.state.sync_run.workspace_id != workspace_id
        ):
            return None
        return self.state.sync_run

    async def update_sync_run_status(
        self,
        sync_run_id: uuid.UUID,
        workspace_id: uuid.UUID,
        **values: object,
    ) -> None:
        sync_run = await self.find_sync_run_by_id(sync_run_id, workspace_id)
        if sync_run is not None:
            for key, value in values.items():
                setattr(sync_run, key, value)

    async def commit(self) -> None:
        self.state.commits += 1


class _FakeIntegrationService:
    def __init__(self, repository: _FakeIntegrationRepository) -> None:
        self.repository = repository

    async def get_decrypted_refresh_token(
        self,
        connection_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> str:
        assert connection_id == self.repository.state.connection_id
        assert workspace_id == self.repository.state.workspace_id
        return "refresh-token"


class _FakeEmbeddingRepository:
    def __init__(self, session: _FakeSession) -> None:
        self.state = session.state

    async def find_chunk_project_ids(
        self,
        source_type: str,
        source_id: uuid.UUID,
    ) -> set[uuid.UUID | None]:
        assert source_type == "external_document"
        return set(self.state.chunk_project_ids)

    async def delete_by_source(
        self,
        source_type: str,
        source_id: uuid.UUID,
    ) -> None:
        self.state.deleted_sources.append((source_type, source_id))

    async def delete_caches(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None,
    ) -> None:
        self.state.deleted_caches.append((workspace_id, project_id))

    async def commit(self) -> None:
        self.state.commits += 1


class _FakeEmbeddingService:
    def __init__(self, repository: _FakeEmbeddingRepository) -> None:
        self.repository = repository

    async def embed_external_document(self, **kwargs: object) -> int:
        self.repository.state.embedded_documents.append(kwargs)
        return 2


class _FakeDriveClient:
    def __init__(self) -> None:
        self.refresh_calls = 0
        self.metadata_calls: list[str] = []
        self.export_calls: list[str] = []
        self.metadata: dict[str, DriveFileMetadata | Exception] = {}
        self.exports: dict[str, DriveExport | Exception] = {}
        self.refresh_error: Exception | None = None

    async def refresh_access_token(self, *args: object, **kwargs: object) -> str:
        self.refresh_calls += 1
        if self.refresh_error is not None:
            raise self.refresh_error
        return "access-token"

    async def get_file_metadata(
        self,
        access_token: str,
        file_id: str,
    ) -> DriveFileMetadata:
        assert access_token == "access-token"
        self.metadata_calls.append(file_id)
        result = self.metadata[file_id]
        if isinstance(result, Exception):
            raise result
        return result

    async def export_plain_text(
        self,
        access_token: str,
        file_id: str,
        mime_type: str,
    ) -> DriveExport:
        assert access_token == "access-token"
        self.export_calls.append(file_id)
        result = self.exports[file_id]
        if isinstance(result, Exception):
            raise result
        return result


def _make_document(
    state: _PipelineState,
    *,
    file_id: str = "document-1",
    revision_id: str = "revision-1",
    content_hash: str = "content-hash-1",
    plain_text: str = "기존 본문",
) -> SimpleNamespace:
    document = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=state.workspace_id,
        connection_id=state.connection_id,
        project_id=state.project_id,
        drive_file_id=file_id,
        title="기존 제목",
        mime_type="application/vnd.google-apps.document",
        origin_url=f"https://docs.google.com/document/d/{file_id}/edit",
        revision_id=revision_id,
        content_hash=content_hash,
        plain_text=plain_text,
        sync_status="completed",
        sync_run_id=None,
        last_synced_at=None,
    )
    state.documents[document.id] = document
    return document


def _metadata(file_id: str, revision_id: str) -> DriveFileMetadata:
    return DriveFileMetadata(
        file_id=file_id,
        title="Drive 제목",
        mime_type="application/vnd.google-apps.document",
        revision_id=revision_id,
    )


@pytest.fixture
def pipeline_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[_PipelineState, GoogleDriveSyncPipelineService, _FakeDriveClient, _FakeSessionFactory]:
    state = _PipelineState()
    drive_client = _FakeDriveClient()
    session_factory = _FakeSessionFactory(state)
    monkeypatch.setattr(
        pipeline_module,
        "IntegrationRepository",
        _FakeIntegrationRepository,
    )
    monkeypatch.setattr(
        pipeline_module,
        "IntegrationService",
        _FakeIntegrationService,
    )
    monkeypatch.setattr(
        pipeline_module,
        "EmbeddingRepository",
        _FakeEmbeddingRepository,
    )
    monkeypatch.setattr(
        pipeline_module,
        "EmbeddingService",
        _FakeEmbeddingService,
    )
    pipeline = GoogleDriveSyncPipelineService(
        session_factory=session_factory,
        drive_client_factory=lambda: drive_client,
        google_oauth_client_id="client-id",
        google_oauth_client_secret="client-secret",
    )
    return state, pipeline, drive_client, session_factory


@pytest.mark.parametrize(
    "drive_error",
    [DriveSourceMissingError(), DrivePermissionRevokedError()],
    ids=("source-missing", "permission-revoked"),
)
async def test_confirmed_source_errors_purge_document_content(
    pipeline_environment: tuple[_PipelineState, GoogleDriveSyncPipelineService, _FakeDriveClient, _FakeSessionFactory],
    drive_error: DriveClientError,
) -> None:
    state, pipeline, drive_client, _ = pipeline_environment
    document = _make_document(state)
    drive_client.metadata[document.drive_file_id] = drive_error

    await pipeline.resync_document(document.id, state.workspace_id)

    assert state.deleted_sources == [("external_document", document.id)]
    assert document.plain_text == ""
    assert document.content_hash == ""
    assert document.sync_status == "purged"
    assert document.revision_id == "revision-1"


@pytest.mark.parametrize(
    ("drive_error", "expected_status"),
    [
        (DriveReauthenticationRequiredError(), "reauth_required"),
        (DriveTemporaryError(), "stale"),
        (DriveUnsupportedMimeTypeError(), "failed"),
    ],
    ids=("reauth", "temporary", "unsupported"),
)
async def test_non_purge_drive_errors_preserve_document_content(
    pipeline_environment: tuple[_PipelineState, GoogleDriveSyncPipelineService, _FakeDriveClient, _FakeSessionFactory],
    drive_error: DriveClientError,
    expected_status: str,
) -> None:
    state, pipeline, drive_client, _ = pipeline_environment
    document = _make_document(state)
    drive_client.metadata[document.drive_file_id] = drive_error

    await pipeline.resync_document(document.id, state.workspace_id)

    assert state.deleted_sources == []
    assert document.plain_text == "기존 본문"
    assert document.sync_status == expected_status


@pytest.mark.parametrize(
    "raw_error",
    [ValueError("raw value error"), RuntimeError("raw runtime error")],
    ids=("value-error", "runtime-error"),
)
async def test_unclassified_errors_never_purge_document_content(
    pipeline_environment: tuple[_PipelineState, GoogleDriveSyncPipelineService, _FakeDriveClient, _FakeSessionFactory],
    raw_error: Exception,
) -> None:
    state, pipeline, drive_client, _ = pipeline_environment
    document = _make_document(state)
    drive_client.metadata[document.drive_file_id] = raw_error

    await pipeline.resync_document(document.id, state.workspace_id)

    assert state.deleted_sources == []
    assert document.plain_text == "기존 본문"
    assert document.sync_status == "failed"


def _recursive_drive_error_subclasses(
    error_class: type[DriveClientError],
) -> set[type[DriveClientError]]:
    direct_subclasses = set(error_class.__subclasses__())
    return direct_subclasses | {
        descendant
        for subclass in direct_subclasses
        for descendant in _recursive_drive_error_subclasses(subclass)
    }


def test_purge_allowed_error_set_matches_exception_capability() -> None:
    allowed_error_classes = {
        error_class
        for error_class in _recursive_drive_error_subclasses(DriveClientError)
        if error_class.allows_purge
    }

    assert allowed_error_classes == set(_PURGE_ALLOWED_ERRORS)


def test_purge_allowed_error_guard_detects_grandchild() -> None:
    class _FuturePurgeAllowedError(DriveTemporaryError):
        allows_purge = True

    future_error_ref = weakref.ref(_FuturePurgeAllowedError)
    try:
        allowed_error_classes = {
            error_class
            for error_class in _recursive_drive_error_subclasses(DriveClientError)
            if error_class.allows_purge
        }

        assert _FuturePurgeAllowedError in allowed_error_classes
        assert allowed_error_classes != set(_PURGE_ALLOWED_ERRORS)
    finally:
        del allowed_error_classes
        del _FuturePurgeAllowedError
        gc.collect()

    assert future_error_ref() is None


async def test_same_revision_skips_export_and_updates_sync_timestamp(
    pipeline_environment: tuple[_PipelineState, GoogleDriveSyncPipelineService, _FakeDriveClient, _FakeSessionFactory],
) -> None:
    state, pipeline, drive_client, _ = pipeline_environment
    document = _make_document(state)
    drive_client.metadata[document.drive_file_id] = _metadata(
        document.drive_file_id,
        document.revision_id,
    )

    await pipeline.resync_document(document.id, state.workspace_id)

    assert drive_client.export_calls == []
    assert document.sync_status == "completed"
    assert document.last_synced_at is not None


async def test_changed_revision_updates_content_and_reembeds(
    pipeline_environment: tuple[_PipelineState, GoogleDriveSyncPipelineService, _FakeDriveClient, _FakeSessionFactory],
) -> None:
    state, pipeline, drive_client, _ = pipeline_environment
    document = _make_document(state)
    drive_client.metadata[document.drive_file_id] = _metadata(
        document.drive_file_id,
        "revision-2",
    )
    drive_client.exports[document.drive_file_id] = DriveExport(
        plain_text="갱신 본문",
        content_hash="content-hash-2",
    )

    await pipeline.resync_document(document.id, state.workspace_id)

    assert drive_client.export_calls == [document.drive_file_id]
    assert document.revision_id == "revision-2"
    assert document.content_hash == "content-hash-2"
    assert document.plain_text == "갱신 본문"
    assert len(state.embedded_documents) == 1
    assert state.embedded_documents[0]["workspace_id"] == state.workspace_id
    assert state.embedded_documents[0]["source_workspace_id"] == document.workspace_id
    assert document.sync_status == "completed"


async def test_failed_embedding_retries_on_same_revision(
    pipeline_environment: tuple[_PipelineState, GoogleDriveSyncPipelineService, _FakeDriveClient, _FakeSessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FailOnceEmbeddingService:
        attempts = 0

        def __init__(self, repository: _FakeEmbeddingRepository) -> None:
            self.repository = repository

        async def embed_external_document(self, **kwargs: object) -> int:
            type(self).attempts += 1
            if type(self).attempts == 1:
                raise RuntimeError("embedding unavailable")
            self.repository.state.embedded_documents.append(kwargs)
            self.repository.state.generated_chunk_count += 2
            return 2

    monkeypatch.setattr(
        pipeline_module,
        "EmbeddingService",
        _FailOnceEmbeddingService,
    )
    state, pipeline, drive_client, _ = pipeline_environment
    document = _make_document(state)
    drive_client.metadata[document.drive_file_id] = _metadata(
        document.drive_file_id,
        "revision-2",
    )
    drive_client.exports[document.drive_file_id] = DriveExport(
        plain_text="갱신 본문",
        content_hash="content-hash-2",
    )

    await pipeline.resync_document(document.id, state.workspace_id)

    assert document.sync_status == "failed"
    assert drive_client.export_calls == [document.drive_file_id]
    assert state.embedded_documents == []

    await pipeline.resync_document(document.id, state.workspace_id)

    assert document.sync_status == "completed"
    assert drive_client.export_calls == [document.drive_file_id, document.drive_file_id]
    assert len(state.embedded_documents) == 1
    assert state.generated_chunk_count == 2


@pytest.mark.parametrize(
    "has_project_id",
    [False, True],
    ids=("workspace-scope", "project-scope"),
)
async def test_reembedding_invalidates_only_document_project_cache_scope(
    pipeline_environment: tuple[_PipelineState, GoogleDriveSyncPipelineService, _FakeDriveClient, _FakeSessionFactory],
    has_project_id: bool,
) -> None:
    state, pipeline, drive_client, _ = pipeline_environment
    project_id = uuid.uuid4() if has_project_id else None
    document = _make_document(state)
    document.project_id = project_id
    state.chunk_project_ids = {project_id}
    drive_client.metadata[document.drive_file_id] = _metadata(
        document.drive_file_id,
        "revision-2",
    )
    drive_client.exports[document.drive_file_id] = DriveExport(
        plain_text="갱신 본문",
        content_hash="content-hash-2",
    )

    await pipeline.resync_document(document.id, state.workspace_id)

    assert state.embedded_documents[0]["project_id"] == project_id
    assert state.deleted_caches == [(state.workspace_id, project_id)]


async def test_purge_invalidates_workspace_cache_while_sync_keeps_other_project_cache(
    integration_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _StaticIntegrationService:
        def __init__(self, repository: object) -> None:
            self.repository = repository

        async def get_decrypted_refresh_token(
            self,
            connection_id: uuid.UUID,
            workspace_id: uuid.UUID,
        ) -> str:
            return "refresh-token"

    class _NoopEmbeddingService:
        def __init__(self, repository: EmbeddingRepository) -> None:
            self.repository = repository

        async def embed_external_document(self, **kwargs: object) -> int:
            return 0

    engine = integration_session.bind
    assert engine is not None
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    user = User(
        clerk_id=f"drive-cache-user-{uuid.uuid4().hex}",
        display_name="Drive Cache Tester",
        email=f"drive-cache-{uuid.uuid4().hex}@kairos.test",
    )
    workspace = Workspace(name="Drive Cache Workspace", owner_id=user.id)
    document_project = Project(
        workspace_id=workspace.id,
        title="Document Project",
        created_by_id=user.id,
        visibility="private",
    )
    other_project = Project(
        workspace_id=workspace.id,
        title="Other Project",
        created_by_id=user.id,
    )
    connection = IntegrationConnection(
        workspace_id=workspace.id,
        authorized_by_id=user.id,
        encrypted_refresh_token="encrypted-refresh-token",
        scope="drive.file",
    )
    document = ExternalDocument(
        workspace_id=workspace.id,
        connection_id=connection.id,
        project_id=document_project.id,
        drive_file_id="document-1",
        title="Drive document",
        mime_type="application/vnd.google-apps.document",
        origin_url="https://docs.google.com/document/d/document-1/edit",
        revision_id="revision-1",
        content_hash="content-hash-1",
        plain_text="private source text",
        sync_status="completed",
    )
    chunk = EmbeddingChunk(
        workspace_id=workspace.id,
        project_id=document_project.id,
        source_id=document.id,
        source_type="external_document",
        chunk_text="private source text",
        chunk_level=2,
    )
    global_cache = SemanticCache(
        workspace_id=workspace.id,
        question="global question",
        answer="private source text",
        sources=[str(chunk.id)],
        max_visibility="private",
    )
    document_cache = SemanticCache(
        workspace_id=workspace.id,
        project_id=document_project.id,
        question="project question",
        answer="private source text",
        sources=[str(chunk.id)],
        max_visibility="private",
    )
    other_project_cache = SemanticCache(
        workspace_id=workspace.id,
        project_id=other_project.id,
        question="other project question",
        answer="other project answer",
        sources=[],
    )
    integration_session.add(user)
    await integration_session.commit()
    integration_session.add(workspace)
    await integration_session.commit()
    integration_session.add_all([document_project, other_project, connection])
    await integration_session.commit()
    integration_session.add(document)
    await integration_session.commit()
    integration_session.add_all(
        [chunk, global_cache, document_cache, other_project_cache]
    )
    await integration_session.commit()

    monkeypatch.setattr(
        pipeline_module,
        "IntegrationService",
        _StaticIntegrationService,
    )
    monkeypatch.setattr(
        pipeline_module,
        "EmbeddingService",
        _NoopEmbeddingService,
    )
    drive_client = _FakeDriveClient()
    pipeline = GoogleDriveSyncPipelineService(
        session_factory=session_factory,
        drive_client_factory=lambda: drive_client,
        google_oauth_client_id="client-id",
        google_oauth_client_secret="client-secret",
    )
    drive_client.metadata[document.drive_file_id] = _metadata(
        document.drive_file_id,
        "revision-2",
    )
    drive_client.exports[document.drive_file_id] = DriveExport(
        plain_text="updated private source text",
        content_hash="content-hash-2",
    )

    await pipeline.resync_document(document.id, workspace.id)

    async with session_factory() as verification_session:
        remaining_caches = (await verification_session.exec(
            select(SemanticCache).where(SemanticCache.workspace_id == workspace.id)
        )).all()
    assert {cache.project_id for cache in remaining_caches} == {
        None,
        other_project.id,
    }

    async with session_factory() as cache_session:
        cache_session.add(
            SemanticCache(
                workspace_id=workspace.id,
                project_id=document_project.id,
                question="project question after sync",
                answer="updated private source text",
                sources=[str(chunk.id)],
                max_visibility="private",
            )
        )
        await cache_session.commit()

    drive_client.metadata[document.drive_file_id] = DriveSourceMissingError()
    await pipeline.resync_document(document.id, workspace.id)

    async with session_factory() as verification_session:
        remaining_caches = (await verification_session.exec(
            select(SemanticCache).where(SemanticCache.workspace_id == workspace.id)
        )).all()
        remaining_chunks = (await verification_session.exec(
            select(EmbeddingChunk).where(EmbeddingChunk.source_id == document.id)
        )).all()
        purged_document = (await verification_session.exec(
            select(ExternalDocument).where(ExternalDocument.id == document.id)
        )).one()
    assert remaining_caches == []
    assert remaining_chunks == []
    assert purged_document.sync_status == "purged"


async def test_import_continues_after_document_failure_and_closes_sync_run(
    pipeline_environment: tuple[_PipelineState, GoogleDriveSyncPipelineService, _FakeDriveClient, _FakeSessionFactory],
) -> None:
    state, pipeline, drive_client, _ = pipeline_environment
    failed_document = _make_document(state, file_id="failed-document")
    sync_run_id = uuid.uuid4()
    state.sync_run = SimpleNamespace(
        id=sync_run_id,
        workspace_id=state.workspace_id,
        connection_id=state.connection_id,
        status="pending",
        completed_at=None,
        error_summary=None,
    )
    drive_client.metadata[failed_document.drive_file_id] = DriveTemporaryError()
    drive_client.metadata["successful-document"] = _metadata(
        "successful-document",
        "revision-1",
    )
    drive_client.exports["successful-document"] = DriveExport(
        plain_text="새 문서 본문",
        content_hash="new-content-hash",
    )

    await pipeline.import_documents(
        sync_run_id,
        state.workspace_id,
        state.connection_id,
        [failed_document.drive_file_id, "successful-document"],
        state.project_id,
    )

    assert drive_client.refresh_calls == 1
    assert failed_document.sync_status == "stale"
    successful_document = next(
        document
        for document in state.documents.values()
        if document.drive_file_id == "successful-document"
    )
    assert successful_document.sync_status == "completed"
    assert successful_document.sync_run_id == sync_run_id
    assert state.sync_run.status == "completed"
    assert state.sync_run.completed_at is not None
    assert state.sync_run.error_summary is not None


async def test_refresh_failure_closes_sync_run_as_failed(
    pipeline_environment: tuple[_PipelineState, GoogleDriveSyncPipelineService, _FakeDriveClient, _FakeSessionFactory],
) -> None:
    state, pipeline, drive_client, _ = pipeline_environment
    sync_run_id = uuid.uuid4()
    state.sync_run = SimpleNamespace(
        id=sync_run_id,
        workspace_id=state.workspace_id,
        connection_id=state.connection_id,
        status="pending",
        completed_at=None,
        error_summary=None,
    )
    drive_client.refresh_error = DriveTemporaryError()

    await pipeline.import_documents(
        sync_run_id,
        state.workspace_id,
        state.connection_id,
        ["document-1"],
        state.project_id,
    )

    assert state.sync_run.status == "failed"
    assert state.sync_run.completed_at is not None
    assert state.sync_run.error_summary is not None


async def test_cross_workspace_document_is_not_processed(
    pipeline_environment: tuple[_PipelineState, GoogleDriveSyncPipelineService, _FakeDriveClient, _FakeSessionFactory],
) -> None:
    state, pipeline, drive_client, _ = pipeline_environment
    document = _make_document(state)

    await pipeline.resync_document(document.id, uuid.uuid4())

    assert drive_client.metadata_calls == []
    assert document.plain_text == "기존 본문"


@pytest.mark.parametrize(
    "has_project_id",
    [False, True],
    ids=("workspace-scope", "project-scope"),
)
async def test_external_document_embedding_uses_save_chunk_for_l1_and_l2(
    has_project_id: bool,
) -> None:
    class _SaveChunkRepository:
        def __init__(self) -> None:
            self.deleted_sources: list[tuple[str, uuid.UUID]] = []
            self.saved_chunks: list[SimpleNamespace] = []
            self.committed = False

        async def delete_by_source(
            self,
            source_type: str,
            source_id: uuid.UUID,
        ) -> None:
            self.deleted_sources.append((source_type, source_id))

        async def save_chunk(self, **kwargs: object) -> SimpleNamespace:
            chunk = SimpleNamespace(id=uuid.uuid4(), **kwargs)
            self.saved_chunks.append(chunk)
            return chunk

        async def commit(self) -> None:
            self.committed = True

    repository = _SaveChunkRepository()
    service = EmbeddingService.__new__(EmbeddingService)
    service.repo = repository
    document_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4() if has_project_id else None
    plain_text = "가나다라마바사" * 100
    paragraphs = service._chunk_text(plain_text)
    service.generate_embeddings = AsyncMock(
        return_value=[[0.1] for _ in range(len(paragraphs) + 1)]
    )

    await service.embed_external_document(
        document_id=document_id,
        workspace_id=workspace_id,
        source_workspace_id=workspace_id,
        project_id=project_id,
        title="외부 문서 제목",
        origin_url="https://docs.google.com/document/d/document-1/edit",
        plain_text=plain_text,
    )

    assert repository.deleted_sources == [("external_document", document_id)]
    assert {chunk.source_type for chunk in repository.saved_chunks} == {
        "external_document"
    }
    assert {chunk.chunk_level for chunk in repository.saved_chunks} == {1, 2}
    assert all(chunk.workspace_id == workspace_id for chunk in repository.saved_chunks)
    assert all(chunk.source_workspace_id == workspace_id for chunk in repository.saved_chunks)
    assert all(chunk.project_id == project_id for chunk in repository.saved_chunks)
    assert all(
        chunk.metadata_json["title"] == "외부 문서 제목"
        and "originUrl" in chunk.metadata_json
        for chunk in repository.saved_chunks
    )
    assert repository.committed is True


async def test_external_document_embedding_rejects_source_workspace_mismatch() -> None:
    class _SourceWorkspaceGuardRepository:
        async def delete_by_source(
            self,
            source_type: str,
            source_id: uuid.UUID,
        ) -> None:
            return None

        async def save_chunk(self, **kwargs: object) -> SimpleNamespace:
            return await EmbeddingRepository(SimpleNamespace()).save_chunk(**kwargs)

    service = EmbeddingService.__new__(EmbeddingService)
    service.repo = _SourceWorkspaceGuardRepository()
    plain_text = "불일치 본문"
    paragraphs = service._chunk_text(plain_text)
    service.generate_embeddings = AsyncMock(
        return_value=[[0.1] for _ in range(len(paragraphs) + 1)]
    )

    with pytest.raises(AssertionError, match="I-9 4-C violation"):
        await service.embed_external_document(
            document_id=uuid.uuid4(),
            workspace_id=uuid.uuid4(),
            source_workspace_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            title="외부 문서 제목",
            origin_url="https://docs.google.com/document/d/document-1/edit",
            plain_text=plain_text,
        )


async def test_encrypt_failure_captures_sentry_without_refresh_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _EncryptionRepository:
        async def find_connection_by_workspace(
            self,
            workspace_id: uuid.UUID,
            provider: str,
        ) -> None:
            return None

    captured: list[Exception] = []

    def raise_encryption_error(_: str) -> str:
        raise EncryptionError("암호화 실패")

    monkeypatch.setattr(integration_service_module, "encrypt_string", raise_encryption_error)
    monkeypatch.setattr(
        integration_service_module.sentry_sdk,
        "capture_exception",
        captured.append,
    )
    refresh_token = "refresh-token-secret"

    with pytest.raises(IntegrationEncryptionError):
        await IntegrationService(_EncryptionRepository()).connect_or_reauthorize(
            workspace_id=uuid.uuid4(),
            authorized_by_id=uuid.uuid4(),
            refresh_token=refresh_token,
            scope="drive.file",
        )

    assert len(captured) == 1
    assert refresh_token not in str(captured)


async def test_decrypt_failure_captures_sentry_without_refresh_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _EncryptionRepository:
        async def find_connection_by_id(
            self,
            connection_id: uuid.UUID,
            workspace_id: uuid.UUID,
        ) -> SimpleNamespace:
            return SimpleNamespace(encrypted_refresh_token="encrypted-token")

    captured: list[Exception] = []

    def raise_encryption_error(_: str) -> str:
        raise EncryptionError("복호화 실패")

    monkeypatch.setattr(integration_service_module, "decrypt_string", raise_encryption_error)
    monkeypatch.setattr(
        integration_service_module.sentry_sdk,
        "capture_exception",
        captured.append,
    )
    refresh_token = "refresh-token-secret"

    with pytest.raises(IntegrationEncryptionError):
        await IntegrationService(_EncryptionRepository()).get_decrypted_refresh_token(
            uuid.uuid4(),
            uuid.uuid4(),
        )

    assert len(captured) == 1
    assert refresh_token not in str(captured)


def test_scrub_pii_hook_redacts_exception_and_thread_frame_vars() -> None:
    refresh_token = "frame-refresh-token"
    event = {
        "request": {
            "data": {
                "transcript": "remove",
                "email": "remove@example.test",
                "password": "remove",
                "audio_url": "remove",
                "keep": "request context",
            }
        },
        "user": {"email": "remove@example.test", "ip_address": "127.0.0.1"},
        "exception": {
            "values": [
                {
                    "stacktrace": {
                        "frames": [
                            {
                                "vars": {
                                    "refresh_token": refresh_token,
                                    "safe_context": {
                                        "apiKey": refresh_token,
                                        "label": "keep",
                                    },
                                }
                            }
                        ]
                    }
                }
            ]
        },
        "threads": {
            "values": [
                {
                    "stacktrace": {
                        "frames": [
                            {
                                "vars": {
                                    "authorization": refresh_token,
                                    "safe_thread_context": "keep",
                                }
                            }
                        ]
                    }
                }
            ]
        },
    }

    scrubbed_event = _scrub_pii_hook(event, None)

    assert refresh_token not in json.dumps(scrubbed_event)
    assert scrubbed_event["request"]["data"] == {"keep": "request context"}
    assert scrubbed_event["user"] == {}
    exception_vars = scrubbed_event["exception"]["values"][0]["stacktrace"][
        "frames"
    ][0]["vars"]
    thread_vars = scrubbed_event["threads"]["values"][0]["stacktrace"]["frames"][0][
        "vars"
    ]
    assert exception_vars["refresh_token"] == "[redacted]"
    assert exception_vars["safe_context"]["apiKey"] == "[redacted]"
    assert exception_vars["safe_context"]["label"] == "keep"
    assert thread_vars["authorization"] == "[redacted]"
    assert thread_vars["safe_thread_context"] == "keep"


@pytest.mark.parametrize("operation", ("encrypt", "decrypt"))
async def test_sentry_scrub_removes_refresh_token_from_captured_event(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    class _EncryptionRepository:
        async def find_connection_by_workspace(
            self,
            workspace_id: uuid.UUID,
            provider: str,
        ) -> None:
            return None

        async def find_connection_by_id(
            self,
            connection_id: uuid.UUID,
            workspace_id: uuid.UUID,
        ) -> SimpleNamespace:
            return SimpleNamespace(encrypted_refresh_token="encrypted-token")

    refresh_token = f"refresh-token-{operation}-{uuid.uuid4().hex}"
    captured_events: list[dict] = []

    def transport(event: dict) -> None:
        captured_events.append(event)

    if operation == "encrypt":
        def encrypt_string(plaintext: str) -> str:
            raise EncryptionError("암호화 실패")

        monkeypatch.setattr(integration_service_module, "encrypt_string", encrypt_string)
    else:
        def decrypt_string(ciphertext: str) -> str:
            plaintext = refresh_token
            raise EncryptionError("복호화 실패")

        monkeypatch.setattr(integration_service_module, "decrypt_string", decrypt_string)

    previous_client = sentry_sdk.get_client()
    sentry_sdk.init(
        dsn="http://public@example.invalid/1",
        transport=transport,
        send_default_pii=False,
        before_send=_scrub_pii_hook,
    )
    try:
        with pytest.raises(IntegrationEncryptionError):
            if operation == "encrypt":
                await IntegrationService(_EncryptionRepository()).connect_or_reauthorize(
                    workspace_id=uuid.uuid4(),
                    authorized_by_id=uuid.uuid4(),
                    refresh_token=refresh_token,
                    scope="drive.file",
                )
            else:
                await IntegrationService(_EncryptionRepository()).get_decrypted_refresh_token(
                    uuid.uuid4(),
                    uuid.uuid4(),
                )
        sentry_sdk.flush()
    finally:
        sentry_sdk.get_global_scope().set_client(previous_client)

    assert captured_events
    serialized_events = json.dumps(captured_events, default=str)
    assert refresh_token not in serialized_events
    assert "[redacted]" in serialized_events
