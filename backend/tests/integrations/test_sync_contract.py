"""HTTP에서 Drive 동기화 파이프라인까지 관통하는 실 DB 계약 테스트."""
import hashlib
import uuid
from dataclasses import dataclass

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient, MockTransport, Response
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.models import User
from src.auth.rbac import require_owner, require_viewer
from src.common.database import get_async_session
from src.embeddings.models import EmbeddingChunk, SemanticCache
from src.embeddings.repository import EmbeddingRepository
from src.embeddings.service import EmbeddingService
from src.integrations.dependencies import get_google_drive_sync_pipeline_service
from src.integrations.drive_client import (
    GOOGLE_DOC_MIME_TYPE,
    DriveExport,
    DriveFileMetadata,
    GoogleDriveClient,
)
from src.integrations.exceptions import (
    DrivePermissionRevokedError,
    DriveReauthenticationRequiredError,
    DriveSourceMissingError,
    DriveTemporaryError,
    DriveUnsupportedMimeTypeError,
)
from src.integrations.models import ExternalDocument, IntegrationConnection
from src.integrations.pipeline_service import GoogleDriveSyncPipelineService
from src.integrations.service import IntegrationService
from src.main import app
from src.projects.models import Project
from src.services.ai_resilience import drive_breaker, reset_breakers_for_test
from src.workspaces.models import Workspace, WorkspaceMember

pytestmark = pytest.mark.integration

_VECTOR = [1.0, *([0.0] * 1535)]


class _StubDriveClient:
    """실제 HTTP 없이 pipeline에 Drive 응답·오류를 주입한다."""

    def __init__(self) -> None:
        self.metadata_calls: list[str] = []
        self.export_calls: list[str] = []
        self.metadata: dict[str, DriveFileMetadata | Exception] = {}
        self.exports: dict[str, DriveExport | Exception] = {}

    async def refresh_access_token(self, *_args: object, **_kwargs: object) -> str:
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
        if mime_type != GOOGLE_DOC_MIME_TYPE:
            raise DriveUnsupportedMimeTypeError()
        result = self.exports[file_id]
        if isinstance(result, Exception):
            raise result
        return result


@dataclass
class _ContractEnvironment:
    client: AsyncClient
    session_factory: async_sessionmaker[AsyncSession]
    workspace: Workspace
    owner: User
    viewer: User
    project: Project
    connection: IntegrationConnection
    drive: _StubDriveClient
    pipeline: GoogleDriveSyncPipelineService


def _metadata(file_id: str, revision_id: str, *, mime_type: str = GOOGLE_DOC_MIME_TYPE) -> DriveFileMetadata:
    return DriveFileMetadata(
        file_id=file_id,
        title="Drive 계약 문서",
        mime_type=mime_type,
        revision_id=revision_id,
    )


def _export(plain_text: str) -> DriveExport:
    return DriveExport(
        plain_text=plain_text,
        content_hash=hashlib.sha256(plain_text.encode()).hexdigest(),
    )


def _cache_source(chunk: EmbeddingChunk, document: ExternalDocument) -> dict[str, object]:
    """RagService._format_sources가 저장하는 production sources 형태."""
    return {
        "id": str(chunk.id),
        "sourceId": str(document.id),
        "text": chunk.chunk_text[:200],
        "source": document.title,
        "sourceType": chunk.source_type,
        "date": "",
        "speaker": None,
        "score": 1.0,
        "freshness": "recent",
    }


async def _fixed_embeddings(_service: EmbeddingService, texts: list[str]) -> list[list[float]]:
    return [list(_VECTOR) for _ in texts]


async def _decrypted_refresh_token(
    _service: IntegrationService,
    _connection_id: uuid.UUID,
    _workspace_id: uuid.UUID,
) -> str:
    return "refresh-token"


@pytest_asyncio.fixture
async def sync_contract(
    integration_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> _ContractEnvironment:
    engine = integration_session.bind
    assert engine is not None
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    owner = User(
        clerk_id=f"drive-contract-owner-{uuid.uuid4().hex}",
        display_name="Drive Contract Owner",
        email=f"drive-owner-{uuid.uuid4().hex}@kairos.test",
    )
    viewer = User(
        clerk_id=f"drive-contract-viewer-{uuid.uuid4().hex}",
        display_name="Drive Contract Viewer",
        email=f"drive-viewer-{uuid.uuid4().hex}@kairos.test",
    )
    integration_session.add_all([owner, viewer])
    await integration_session.flush()
    workspace = Workspace(name="Drive Contract Workspace", owner_id=owner.id)
    integration_session.add(workspace)
    await integration_session.flush()
    project = Project(
        workspace_id=workspace.id,
        title="Drive Contract Project",
        created_by_id=owner.id,
    )
    connection = IntegrationConnection(
        workspace_id=workspace.id,
        authorized_by_id=owner.id,
        encrypted_refresh_token="test-encrypted-refresh-token",
        scope="drive.file",
    )
    integration_session.add_all([project, connection])
    await integration_session.flush()
    integration_session.add_all(
        [
            WorkspaceMember(workspace_id=workspace.id, user_id=owner.id, role="owner"),
            WorkspaceMember(workspace_id=workspace.id, user_id=viewer.id, role="member"),
        ]
    )
    await integration_session.commit()

    drive = _StubDriveClient()
    pipeline = GoogleDriveSyncPipelineService(
        session_factory=session_factory,
        drive_client_factory=lambda: drive,
        google_oauth_client_id="test-client-id",
        google_oauth_client_secret="test-client-secret",
    )
    monkeypatch.setattr(EmbeddingService, "generate_embeddings", _fixed_embeddings)
    monkeypatch.setattr(
        IntegrationService,
        "get_decrypted_refresh_token",
        _decrypted_refresh_token,
    )
    owner_member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=owner.id,
        role="owner",
    )
    app.dependency_overrides[get_async_session] = lambda: integration_session
    app.dependency_overrides[require_owner] = lambda: owner_member
    app.dependency_overrides[require_viewer] = lambda: owner_member
    app.dependency_overrides[get_google_drive_sync_pipeline_service] = lambda: pipeline
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield _ContractEnvironment(
            client=client,
            session_factory=session_factory,
            workspace=workspace,
            owner=owner,
            viewer=viewer,
            project=project,
            connection=connection,
            drive=drive,
            pipeline=pipeline,
        )
    app.dependency_overrides.clear()


async def _import_document(
    environment: _ContractEnvironment,
    *,
    file_id: str = "drive-document-1",
    revision_id: str = "revision-1",
    plain_text: str = "외부 문서의 최초 본문",
) -> tuple[uuid.UUID, ExternalDocument]:
    environment.drive.metadata[file_id] = _metadata(file_id, revision_id)
    environment.drive.exports[file_id] = _export(plain_text)
    response = await environment.client.post(
        f"/api/v1/workspaces/{environment.workspace.id}/integrations/google-drive/documents",
        json={"fileIds": [file_id], "projectId": str(environment.project.id)},
    )
    assert response.status_code == 202
    sync_run_id = uuid.UUID(response.json()["syncRunId"])
    async with environment.session_factory() as session:
        document = (await session.exec(
            select(ExternalDocument).where(
                ExternalDocument.workspace_id == environment.workspace.id,
                ExternalDocument.drive_file_id == file_id,
            )
        )).one()
    return sync_run_id, document


async def _document(
    environment: _ContractEnvironment,
    document_id: uuid.UUID,
) -> ExternalDocument | None:
    async with environment.session_factory() as session:
        return (await session.exec(
            select(ExternalDocument).where(ExternalDocument.id == document_id)
        )).one_or_none()


async def _document_chunks(
    environment: _ContractEnvironment,
    document_id: uuid.UUID,
) -> list[EmbeddingChunk]:
    async with environment.session_factory() as session:
        return list((await session.exec(
            select(EmbeddingChunk).where(
                EmbeddingChunk.source_type == "external_document",
                EmbeddingChunk.source_id == document_id,
            )
        )).all())


async def _seed_private_cache(
    environment: _ContractEnvironment,
    document: ExternalDocument,
) -> None:
    async with environment.session_factory() as session:
        chunk = (await session.exec(
            select(EmbeddingChunk).where(
                EmbeddingChunk.source_id == document.id,
                EmbeddingChunk.chunk_level == 2,
            )
        )).one()
        session.add(
            SemanticCache(
                workspace_id=environment.workspace.id,
                project_id=environment.project.id,
                question="private Drive cache question",
                question_embedding=list(_VECTOR),
                answer="private Drive cache answer",
                sources=[_cache_source(chunk, document)],
                max_visibility="private",
            )
        )
        await session.commit()


async def _cache_probe(
    environment: _ContractEnvironment,
    user: User,
    role: str,
) -> dict | None:
    async with environment.session_factory() as session:
        return await EmbeddingRepository(session).find_similar_cache(
            question_embedding=list(_VECTOR),
            workspace_id=environment.workspace.id,
            requester_user_id=user.id,
            requester_role=role,
        )


async def _workspace_cache_rows(environment: _ContractEnvironment) -> list[SemanticCache]:
    async with environment.session_factory() as session:
        return list((await session.exec(
            select(SemanticCache).where(
                SemanticCache.workspace_id == environment.workspace.id
            )
        )).all())


async def _set_project_visibility(
    environment: _ContractEnvironment,
    visibility: str,
) -> None:
    async with environment.session_factory() as session:
        project = (await session.exec(
            select(Project).where(Project.id == environment.project.id)
        )).one()
        project.visibility = visibility
        session.add(project)
        await session.commit()


async def _resync(
    environment: _ContractEnvironment,
    document_id: uuid.UUID,
) -> None:
    response = await environment.client.post(
        f"/api/v1/workspaces/{environment.workspace.id}/integrations/google-drive/"
        f"documents/{document_id}/sync",
    )
    assert response.status_code == 202


async def test_http_import_persists_chunks_polling_and_project_search(
    sync_contract: _ContractEnvironment,
) -> None:
    sync_run_id, document = await _import_document(sync_contract)

    polling = await sync_contract.client.get(
        f"/api/v1/workspaces/{sync_contract.workspace.id}/integrations/sync-runs/{sync_run_id}"
    )
    assert polling.status_code == 200
    assert polling.json()["status"] == "completed"
    assert polling.json()["documents"][0]["syncStatus"] == "completed"
    stored_document = await _document(sync_contract, document.id)
    assert stored_document is not None
    assert stored_document.plain_text == "외부 문서의 최초 본문"
    chunks = await _document_chunks(sync_contract, document.id)
    assert {chunk.chunk_level for chunk in chunks} == {1, 2}

    async with sync_contract.session_factory() as session:
        results = await EmbeddingRepository(session).vector_search(
            query_embedding=list(_VECTOR),
            workspace_id=sync_contract.workspace.id,
            requester_user_id=sync_contract.owner.id,
            requester_role="owner",
            project_id=sync_contract.project.id,
            source_type="external_document",
        )
    assert any(result["source_id"] == document.id for result in results)


async def test_http_resync_same_revision_skips_export_and_reuses_chunks(
    sync_contract: _ContractEnvironment,
) -> None:
    _, document = await _import_document(sync_contract)
    original_chunks = await _document_chunks(sync_contract, document.id)
    before_resync = await _document(sync_contract, document.id)
    assert before_resync is not None
    before_last_synced_at = before_resync.last_synced_at
    assert before_last_synced_at is not None
    sync_contract.drive.export_calls.clear()

    await _resync(sync_contract, document.id)

    stored_document = await _document(sync_contract, document.id)
    assert stored_document is not None
    assert stored_document.sync_status == "completed"
    assert stored_document.last_synced_at > before_last_synced_at
    assert sync_contract.drive.export_calls == []
    assert {chunk.id for chunk in await _document_chunks(sync_contract, document.id)} == {
        chunk.id for chunk in original_chunks
    }


async def test_http_resync_changed_revision_replaces_chunks_invalidates_cache_and_closes_nonmember_probe(
    sync_contract: _ContractEnvironment,
) -> None:
    await _set_project_visibility(sync_contract, "private")
    _, document = await _import_document(sync_contract)
    original_chunk_ids = {chunk.id for chunk in await _document_chunks(sync_contract, document.id)}
    await _seed_private_cache(sync_contract, document)
    assert await _cache_probe(sync_contract, sync_contract.owner, "owner") is not None
    assert await _cache_probe(sync_contract, sync_contract.viewer, "member") is None
    sync_contract.drive.metadata[document.drive_file_id] = _metadata(
        document.drive_file_id,
        "revision-2",
    )
    updated_plain_text = "가" * 600
    sync_contract.drive.exports[document.drive_file_id] = _export(updated_plain_text)

    await _resync(sync_contract, document.id)

    stored_document = await _document(sync_contract, document.id)
    assert stored_document is not None
    assert stored_document.revision_id == "revision-2"
    assert stored_document.plain_text == updated_plain_text
    assert stored_document.content_hash == _export(updated_plain_text).content_hash
    replacement_chunks = await _document_chunks(sync_contract, document.id)
    replacement_chunk_ids = {chunk.id for chunk in replacement_chunks}
    assert replacement_chunk_ids
    assert replacement_chunk_ids.isdisjoint(original_chunk_ids)
    assert {chunk.chunk_level for chunk in replacement_chunks} == {1, 2}
    assert len(replacement_chunks) == 3
    assert sum(chunk.chunk_level == 2 for chunk in replacement_chunks) == 2
    assert await _cache_probe(sync_contract, sync_contract.viewer, "member") is None
    assert await _workspace_cache_rows(sync_contract) == []


@pytest.mark.parametrize(
    ("error_kind", "metadata_result", "expected_status", "should_purge"),
    [
        pytest.param(
            "source-missing-error",
            DriveSourceMissingError(),
            "purged",
            True,
            id="source-missing-error",
        ),
        pytest.param(
            "permission-revoked-error",
            DrivePermissionRevokedError(),
            "purged",
            True,
            id="permission-revoked-error",
        ),
        pytest.param(
            "temporary-drive-error",
            DriveTemporaryError(),
            "stale",
            False,
            id="temporary-drive-error",
        ),
        pytest.param(
            "reauthentication-required-error",
            DriveReauthenticationRequiredError(),
            "reauth_required",
            False,
            id="reauthentication-required-error",
        ),
        pytest.param(
            "unclassified-value-error",
            ValueError("unclassified"),
            "failed",
            False,
            id="unclassified-value-error",
        ),
    ],
)
async def test_http_resync_fail_closed_lifecycle_contract(
    sync_contract: _ContractEnvironment,
    error_kind: str,
    metadata_result: Exception,
    expected_status: str,
    should_purge: bool,
) -> None:
    """파이프라인에 주입된 예외별 수명주기를 검증한다.

    HTTP 429·5xx·판별 불가 403의 Drive 예외 분류는 W6이 담당한다.
    """
    await _set_project_visibility(sync_contract, "private")
    _, document = await _import_document(sync_contract, file_id=f"{error_kind}-document")
    original_text = document.plain_text
    original_hash = document.content_hash
    original_revision = document.revision_id
    await _seed_private_cache(sync_contract, document)
    sync_contract.drive.metadata[document.drive_file_id] = metadata_result

    await _resync(sync_contract, document.id)

    stored_document = await _document(sync_contract, document.id)
    assert stored_document is not None
    assert stored_document.sync_status == expected_status
    if should_purge:
        assert stored_document.plain_text == ""
        assert stored_document.content_hash == ""
        assert stored_document.revision_id == original_revision
        assert await _document_chunks(sync_contract, document.id) == []
        assert await _cache_probe(sync_contract, sync_contract.viewer, "member") is None
        assert await _workspace_cache_rows(sync_contract) == []
    else:
        assert stored_document.plain_text == original_text
        assert stored_document.content_hash == original_hash
        assert stored_document.revision_id == original_revision
        assert await _document_chunks(sync_contract, document.id)
        assert await _workspace_cache_rows(sync_contract)


async def test_http_resync_open_breaker_preserves_document(
    sync_contract: _ContractEnvironment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """실제 Drive breaker가 열린 뒤 HTTP 재동기화가 본문을 보존하는지 검증한다."""
    await _set_project_visibility(sync_contract, "private")
    _, document = await _import_document(sync_contract, file_id="open-breaker-document")
    original_text = document.plain_text
    original_hash = document.content_hash
    original_revision = document.revision_id
    await _seed_private_cache(sync_contract, document)
    request_count = 0

    def _server_error_handler(request: object) -> Response:
        nonlocal request_count
        request_count += 1
        return Response(503, request=request)

    reset_breakers_for_test()
    try:
        async with AsyncClient(transport=MockTransport(_server_error_handler)) as http_client:
            drive_client = GoogleDriveClient(http_client)
            for _ in range(drive_breaker.failure_threshold):
                with pytest.raises(DriveTemporaryError):
                    await drive_client.get_file_metadata("access-token", document.drive_file_id)
            monkeypatch.setattr(
                sync_contract.pipeline,
                "_drive_client_factory",
                lambda: drive_client,
            )
            await _resync(sync_contract, document.id)
    finally:
        reset_breakers_for_test()

    stored_document = await _document(sync_contract, document.id)
    assert stored_document is not None
    assert request_count == drive_breaker.failure_threshold
    assert stored_document.sync_status == "stale"
    assert stored_document.plain_text == original_text
    assert stored_document.content_hash == original_hash
    assert stored_document.revision_id == original_revision
    assert await _document_chunks(sync_contract, document.id)
    assert await _workspace_cache_rows(sync_contract)


async def test_http_resync_unsupported_mime_marks_failed_without_purge(
    sync_contract: _ContractEnvironment,
) -> None:
    await _set_project_visibility(sync_contract, "private")
    _, document = await _import_document(sync_contract, file_id="unsupported-mime-document")
    await _seed_private_cache(sync_contract, document)
    sync_contract.drive.metadata[document.drive_file_id] = _metadata(
        document.drive_file_id,
        "revision-2",
        mime_type="application/pdf",
    )

    await _resync(sync_contract, document.id)

    stored_document = await _document(sync_contract, document.id)
    assert stored_document is not None
    assert stored_document.sync_status == "failed"
    assert stored_document.plain_text == document.plain_text
    assert await _document_chunks(sync_contract, document.id)
    assert await _workspace_cache_rows(sync_contract)


@pytest.mark.parametrize("visibility", ["private", "draft"])
async def test_private_and_draft_external_document_are_hidden_from_nonmember_but_project_search_keeps_owner_access(
    sync_contract: _ContractEnvironment,
    visibility: str,
) -> None:
    await _set_project_visibility(sync_contract, visibility)
    _, document = await _import_document(sync_contract, file_id=f"{visibility}-document")

    async with sync_contract.session_factory() as session:
        repository = EmbeddingRepository(session)
        owner_results = await repository.vector_search(
            query_embedding=list(_VECTOR),
            workspace_id=sync_contract.workspace.id,
            requester_user_id=sync_contract.owner.id,
            requester_role="owner",
            project_id=sync_contract.project.id,
            source_type="external_document",
        )
        viewer_results = await repository.vector_search(
            query_embedding=list(_VECTOR),
            workspace_id=sync_contract.workspace.id,
            requester_user_id=sync_contract.viewer.id,
            requester_role="member",
            source_type="external_document",
        )
    assert any(result["source_id"] == document.id for result in owner_results)
    assert not any(result["source_id"] == document.id for result in viewer_results)


async def test_http_unpublish_removes_document_chunks_caches_and_followup_detail(
    sync_contract: _ContractEnvironment,
) -> None:
    await _set_project_visibility(sync_contract, "private")
    _, document = await _import_document(sync_contract)
    await _seed_private_cache(sync_contract, document)

    response = await sync_contract.client.delete(
        f"/api/v1/workspaces/{sync_contract.workspace.id}/integrations/google-drive/"
        f"documents/{document.id}",
    )

    assert response.status_code == 204
    assert await _document(sync_contract, document.id) is None
    assert await _document_chunks(sync_contract, document.id) == []
    assert await _cache_probe(sync_contract, sync_contract.viewer, "member") is None
    assert await _workspace_cache_rows(sync_contract) == []
    detail = await sync_contract.client.get(
        f"/api/v1/workspaces/{sync_contract.workspace.id}/external-documents/{document.id}"
    )
    assert detail.status_code == 404


async def test_same_document_revision_request_keeps_document_and_chunk_identity(
    sync_contract: _ContractEnvironment,
) -> None:
    _, document = await _import_document(sync_contract)
    original_chunk_ids = {chunk.id for chunk in await _document_chunks(sync_contract, document.id)}
    before_resync = await _document(sync_contract, document.id)
    assert before_resync is not None
    before_last_synced_at = before_resync.last_synced_at
    assert before_last_synced_at is not None
    sync_contract.drive.export_calls.clear()

    await _resync(sync_contract, document.id)

    assert sync_contract.drive.export_calls == []
    assert {chunk.id for chunk in await _document_chunks(sync_contract, document.id)} == original_chunk_ids
    stored_document = await _document(sync_contract, document.id)
    assert stored_document is not None
    assert stored_document.id == document.id
    assert stored_document.last_synced_at > before_last_synced_at


async def test_characterization_revision_monotonic_guard_is_currently_absent(
    sync_contract: _ContractEnvironment,
) -> None:
    """알려진 BL-EXT-REVISION-1 결함의 현재 동작을 기록한다.

    단조성 guard가 추가되면 이 characterization 테스트는 보존 계약으로 갱신해야 한다.
    """
    _, document = await _import_document(sync_contract)
    sync_contract.drive.metadata[document.drive_file_id] = _metadata(document.drive_file_id, "revision-2")
    sync_contract.drive.exports[document.drive_file_id] = _export("newer content")
    await _resync(sync_contract, document.id)
    sync_contract.drive.metadata[document.drive_file_id] = _metadata(document.drive_file_id, "revision-1")
    sync_contract.drive.exports[document.drive_file_id] = _export("older content")

    await _resync(sync_contract, document.id)

    stored_document = await _document(sync_contract, document.id)
    assert stored_document is not None
    assert stored_document.revision_id == "revision-1"
    assert stored_document.plain_text == "older content"
