"""ADR-026 integrations HTTP 경계 회귀 테스트."""
import asyncio
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import parse_qs, urlparse

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.models import User
from src.auth.rbac import require_owner, require_viewer
from src.common import crypto
from src.common.database import get_async_session
from src.common.exceptions import (
    EncryptionConfigurationError,
    EncryptionDecryptionError,
    EncryptionError,
)
from src.integrations import router as integration_router
from src.integrations.dependencies import (
    get_google_drive_client,
    get_google_drive_sync_pipeline_service,
    get_integration_project_repository,
    get_integration_repository,
    get_integration_service,
)
from src.integrations.drive_client import GoogleAuthorizationCodeToken
from src.integrations.models import (
    ExternalDocument,
    IntegrationConnection,
    IntegrationOAuthState,
)
from src.integrations.repository import IntegrationRepository
from src.main import app
from src.workspaces.models import Workspace, WorkspaceMember


@dataclass
class _CryptoSettings:
    integrations_encryption_key: SecretStr


@dataclass
class _OAuthSettings:
    frontend_url: str = "https://app.kairos.test"
    google_oauth_client_id: str | None = "google-client-id"
    google_oauth_client_secret: SecretStr | None = SecretStr("google-client-secret")
    google_oauth_redirect_uri: str = (
        "https://api.kairos.test/api/v1/integrations/google-drive/callback"
    )


@pytest.fixture(autouse=True)
def _clear_dependency_overrides() -> None:
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def oauth_settings(monkeypatch: pytest.MonkeyPatch) -> _OAuthSettings:
    key = Fernet.generate_key().decode()
    settings = _OAuthSettings()
    monkeypatch.setattr(
        crypto,
        "get_settings",
        lambda: _CryptoSettings(integrations_encryption_key=SecretStr(key)),
    )
    monkeypatch.setattr(integration_router, "get_settings", lambda: settings)
    crypto._get_fernet.cache_clear()
    yield settings
    crypto._get_fernet.cache_clear()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


def _member(workspace_id: uuid.UUID, role: str = "owner") -> WorkspaceMember:
    return WorkspaceMember(
        workspace_id=workspace_id,
        user_id=uuid.uuid4(),
        role=role,
    )


def _external_document(
    workspace_id: uuid.UUID,
    project_id: uuid.UUID | None,
) -> ExternalDocument:
    return ExternalDocument(
        workspace_id=workspace_id,
        connection_id=uuid.uuid4(),
        project_id=project_id,
        drive_file_id="drive-document-id",
        title="외부 회의록",
        mime_type="application/vnd.google-apps.document",
        origin_url="https://docs.google.com/document/d/drive-document-id",
        revision_id="revision-1",
        content_hash="content-hash",
        plain_text="외부 문서 본문",
        sync_status="completed",
    )


def _install_callback_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    member: WorkspaceMember | None,
) -> tuple[AsyncMock, AsyncMock]:
    connect = AsyncMock()
    exchange = AsyncMock(
        return_value=GoogleAuthorizationCodeToken(
            refresh_token="refresh-token-from-google",
            expires_in=3600,
        )
    )
    workspace_repository = SimpleNamespace(find_member=AsyncMock(return_value=member))
    app.dependency_overrides[get_async_session] = lambda: object()
    app.dependency_overrides[get_integration_service] = lambda: SimpleNamespace(
        connect_or_reauthorize=connect,
    )
    app.dependency_overrides[get_integration_repository] = lambda: SimpleNamespace(
        consume_oauth_state=AsyncMock(return_value=True),
        commit=AsyncMock(),
    )
    app.dependency_overrides[get_google_drive_client] = lambda: SimpleNamespace(
        exchange_authorization_code=exchange,
    )
    monkeypatch.setattr(
        integration_router,
        "WorkspaceRepository",
        lambda _session: workspace_repository,
    )
    return connect, exchange


def _expired_state(workspace_id: uuid.UUID, requester_user_id: uuid.UUID) -> str:
    return crypto.encrypt_string(
        json.dumps(
            {
                "workspace_id": str(workspace_id),
                "requester_user_id": str(requester_user_id),
                "nonce": "test-nonce",
                "code_verifier": "test-code-verifier",
                "exp": int((datetime.now(UTC) - timedelta(seconds=1)).timestamp()),
            }
        )
    )


async def _seed_callback_owner(
    session: AsyncSession,
    tag: str,
) -> tuple[User, Workspace, WorkspaceMember]:
    suffix = uuid.uuid4().hex[:8]
    user = User(
        auth_user_id=f"ba_oauth_{tag}_{suffix}",
        display_name=f"OAuth {tag}",
        email=f"oauth_{tag}_{suffix}@k.test",
    )
    session.add(user)
    await session.flush()
    workspace = Workspace(name=f"OAuth {tag}", owner_id=user.id)
    session.add(workspace)
    await session.flush()
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role="owner",
    )
    session.add(member)
    await session.commit()
    return user, workspace, member


def test_integration_route_paths_match_endpoint_contract() -> None:
    routes = {
        (method, route.path)
        for route in (*integration_router.router.routes, *integration_router.public_router.routes)
        for method in route.methods or set()
    }
    workspace_prefix = "/api/v1/workspaces/{workspace_id}"

    assert {
        ("POST", f"{workspace_prefix}/integrations/google-drive/authorize"),
        ("GET", "/api/v1/integrations/google-drive/callback"),
        ("GET", f"{workspace_prefix}/integrations/google-drive"),
        ("POST", f"{workspace_prefix}/integrations/google-drive/documents"),
        ("GET", f"{workspace_prefix}/integrations/sync-runs/{{sync_run_id}}"),
        (
            "POST",
            f"{workspace_prefix}/integrations/google-drive/documents/{{document_id}}/sync",
        ),
        (
            "DELETE",
            f"{workspace_prefix}/integrations/google-drive/documents/{{document_id}}",
        ),
        ("GET", f"{workspace_prefix}/external-documents/{{document_id}}"),
    } <= routes


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("post", "/integrations/google-drive/authorize", None),
        ("get", "/integrations/google-drive", None),
        ("post", "/integrations/google-drive/documents", {"fileIds": ["file-1"]}),
        ("get", "/integrations/sync-runs/{resource_id}", None),
        (
            "post",
            "/integrations/google-drive/documents/{resource_id}/sync",
            None,
        ),
        ("delete", "/integrations/google-drive/documents/{resource_id}", None),
    ],
)
async def test_workspace_owner_endpoints_reject_non_owner(
    client: AsyncClient,
    method: str,
    path: str,
    payload: dict[str, object] | None,
) -> None:
    workspace_id = uuid.uuid4()

    async def reject_owner() -> WorkspaceMember:
        raise HTTPException(status_code=403, detail="owner only")

    app.dependency_overrides[require_owner] = reject_owner
    resource_id = uuid.uuid4()
    response = await client.request(
        method.upper(),
        f"/api/v1/workspaces/{workspace_id}{path.format(resource_id=resource_id)}",
        json=payload,
    )

    assert response.status_code == 403


async def test_import_returns_sync_run_and_passes_workspace_to_background_task(
    client: AsyncClient,
) -> None:
    workspace_id = uuid.uuid4()
    owner = _member(workspace_id)
    connection = SimpleNamespace(id=uuid.uuid4())
    service = SimpleNamespace(
        get_connection_by_provider=AsyncMock(return_value=connection),
    )
    repository = SimpleNamespace(
        create_sync_run=AsyncMock(),
        commit=AsyncMock(),
    )
    pipeline = SimpleNamespace(import_documents=AsyncMock())

    app.dependency_overrides[require_owner] = lambda: owner
    app.dependency_overrides[get_integration_service] = lambda: service
    app.dependency_overrides[get_integration_repository] = lambda: repository
    app.dependency_overrides[get_integration_project_repository] = lambda: SimpleNamespace()
    app.dependency_overrides[get_google_drive_sync_pipeline_service] = lambda: pipeline

    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/integrations/google-drive/documents",
        json={"fileIds": ["drive-file-1", "drive-file-2"]},
    )

    assert response.status_code == 202
    assert set(response.json()) == {"syncRunId"}
    sync_run_id = uuid.UUID(response.json()["syncRunId"])
    assert repository.create_sync_run.await_args.args[1] == workspace_id
    assert pipeline.import_documents.await_args.args == (
        sync_run_id,
        workspace_id,
        connection.id,
        ["drive-file-1", "drive-file-2"],
        None,
    )


async def test_sync_run_polling_returns_document_statuses(
    client: AsyncClient,
) -> None:
    workspace_id = uuid.uuid4()
    sync_run_id = uuid.uuid4()
    document = _external_document(workspace_id, None)
    sync_run = SimpleNamespace(
        id=sync_run_id,
        status="completed",
        started_at=datetime.now(UTC).replace(tzinfo=None),
        completed_at=datetime.now(UTC).replace(tzinfo=None),
        error_summary=None,
    )
    service = SimpleNamespace(
        get_sync_run=AsyncMock(return_value=sync_run),
        list_documents_by_sync_run=AsyncMock(return_value=[document]),
    )
    app.dependency_overrides[require_owner] = lambda: _member(workspace_id)
    app.dependency_overrides[get_integration_service] = lambda: service

    response = await client.get(
        f"/api/v1/workspaces/{workspace_id}/integrations/sync-runs/{sync_run_id}",
    )

    assert response.status_code == 200
    assert response.json()["documents"] == [
        {
            "id": str(document.id),
            "projectId": None,
            "driveFileId": "drive-document-id",
            "title": "외부 회의록",
            "mimeType": "application/vnd.google-apps.document",
            "originUrl": "https://docs.google.com/document/d/drive-document-id",
            "revisionId": "revision-1",
            "syncStatus": "completed",
            "lastSyncedAt": None,
        }
    ]
    assert service.get_sync_run.await_args.args == (sync_run_id, workspace_id)


async def test_manual_resync_is_background_task_with_workspace_id(
    client: AsyncClient,
) -> None:
    workspace_id = uuid.uuid4()
    document_id = uuid.uuid4()
    pipeline = SimpleNamespace(resync_document=AsyncMock())
    app.dependency_overrides[require_owner] = lambda: _member(workspace_id)
    app.dependency_overrides[get_integration_service] = lambda: SimpleNamespace(
        get_document=AsyncMock(return_value=SimpleNamespace(id=document_id)),
    )
    app.dependency_overrides[get_google_drive_sync_pipeline_service] = lambda: pipeline

    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/integrations/google-drive/documents/{document_id}/sync",
    )

    assert response.status_code == 202
    assert response.content == b""
    assert pipeline.resync_document.await_args.args == (document_id, workspace_id)


async def test_unpublish_is_inline_cleanup_and_returns_no_content(
    client: AsyncClient,
) -> None:
    workspace_id = uuid.uuid4()
    document_id = uuid.uuid4()
    pipeline = SimpleNamespace(unpublish_document=AsyncMock())
    app.dependency_overrides[require_owner] = lambda: _member(workspace_id)
    app.dependency_overrides[get_integration_service] = lambda: SimpleNamespace(
        get_document=AsyncMock(return_value=SimpleNamespace(id=document_id)),
    )
    app.dependency_overrides[get_google_drive_sync_pipeline_service] = lambda: pipeline

    response = await client.delete(
        f"/api/v1/workspaces/{workspace_id}/integrations/google-drive/documents/{document_id}",
    )

    assert response.status_code == 204
    assert response.content == b""
    assert pipeline.unpublish_document.await_args.args == (document_id, workspace_id)


@pytest.mark.parametrize(
    ("visibility", "is_project_member"),
    [("private", False), ("draft", False)],
)
async def test_private_and_draft_external_documents_hide_from_non_members(
    client: AsyncClient,
    visibility: str,
    is_project_member: bool,
) -> None:
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()
    member = _member(workspace_id, "member")
    document = _external_document(workspace_id, project_id)
    project = SimpleNamespace(visibility=visibility, created_by_id=uuid.uuid4())
    project_repository = SimpleNamespace(
        find_by_id=AsyncMock(return_value=project),
        is_member=AsyncMock(return_value=is_project_member),
    )
    app.dependency_overrides[require_viewer] = lambda: member
    app.dependency_overrides[get_integration_service] = lambda: SimpleNamespace(
        get_document=AsyncMock(return_value=document),
    )
    app.dependency_overrides[get_integration_project_repository] = lambda: project_repository

    response = await client.get(
        f"/api/v1/workspaces/{workspace_id}/external-documents/{document.id}",
    )

    assert response.status_code == 404


async def test_project_member_can_read_private_external_document(
    client: AsyncClient,
) -> None:
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()
    document = _external_document(workspace_id, project_id)
    app.dependency_overrides[require_viewer] = lambda: _member(workspace_id, "member")
    app.dependency_overrides[get_integration_service] = lambda: SimpleNamespace(
        get_document=AsyncMock(return_value=document),
    )
    app.dependency_overrides[get_integration_project_repository] = lambda: SimpleNamespace(
        find_by_id=AsyncMock(
            return_value=SimpleNamespace(
                visibility="private",
                created_by_id=uuid.uuid4(),
            )
        ),
        is_member=AsyncMock(return_value=True),
    )

    response = await client.get(
        f"/api/v1/workspaces/{workspace_id}/external-documents/{document.id}",
    )

    assert response.status_code == 200
    assert response.json()["plainText"] == "외부 문서 본문"


async def test_authorize_uses_encrypted_state_without_plaintext_secrets(
    client: AsyncClient,
    oauth_settings: _OAuthSettings,
) -> None:
    workspace_id = uuid.uuid4()
    owner = _member(workspace_id)
    app.dependency_overrides[require_owner] = lambda: owner
    app.dependency_overrides[get_integration_repository] = lambda: SimpleNamespace(
        delete_expired_oauth_states=AsyncMock(),
        create_oauth_state=AsyncMock(),
        commit=AsyncMock(),
    )

    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/integrations/google-drive/authorize",
        headers={"Host": "evil.example.com"},
    )

    assert response.status_code == 200
    assert set(response.json()) == {"authorizationUrl"}
    query = parse_qs(urlparse(response.json()["authorizationUrl"]).query)
    state = query["state"][0]
    decoded_state = integration_router._decode_oauth_state(state)
    assert query["code_challenge_method"] == ["S256"]
    assert query["redirect_uri"] == [oauth_settings.google_oauth_redirect_uri]
    assert decoded_state.workspace_id == workspace_id
    assert decoded_state.requester_user_id == owner.user_id
    assert decoded_state.code_verifier not in response.text
    assert "workspace_id" not in response.text
    assert "refresh-token" not in response.text
    assert "access-token" not in response.text
    assert "nonce" not in response.text


async def test_authorize_returns_503_when_state_encryption_fails(
    client: AsyncClient,
    oauth_settings: _OAuthSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid.uuid4()

    def raise_encryption_error(_: str) -> str:
        raise EncryptionError()

    app.dependency_overrides[require_owner] = lambda: _member(workspace_id)
    app.dependency_overrides[get_integration_repository] = lambda: SimpleNamespace(
        delete_expired_oauth_states=AsyncMock(),
        create_oauth_state=AsyncMock(),
        commit=AsyncMock(),
    )
    monkeypatch.setattr(integration_router, "encrypt_string", raise_encryption_error)

    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/integrations/google-drive/authorize",
    )

    assert response.status_code == 503
    assert "암호화" not in response.text


async def test_callback_consumes_state_once_before_google_exchange(
    client: AsyncClient,
    integration_session: AsyncSession,
    oauth_settings: _OAuthSettings,
) -> None:
    """정상 callback은 한 번만 Google 교환으로 진행하고 자기 workspace stale nonce만 정리한다."""
    user, workspace, owner = await _seed_callback_owner(
        integration_session,
        "single-use",
    )
    other_user, other_workspace, _ = await _seed_callback_owner(
        integration_session,
        "other-workspace",
    )
    expired_nonce = "expired-authorize-nonce"
    other_expired_nonce = "other-expired-authorize-nonce"
    integration_session.add(
        IntegrationOAuthState(
            nonce=expired_nonce,
            workspace_id=workspace.id,
            requester_user_id=user.id,
            expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1),
        )
    )
    integration_session.add(
        IntegrationOAuthState(
            nonce=other_expired_nonce,
            workspace_id=other_workspace.id,
            requester_user_id=other_user.id,
            expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1),
        )
    )
    await integration_session.commit()

    exchange = AsyncMock(
        return_value=GoogleAuthorizationCodeToken(
            refresh_token="single-use-refresh-token",
            expires_in=3600,
        )
    )
    app.dependency_overrides[require_owner] = lambda: owner
    app.dependency_overrides[get_async_session] = lambda: integration_session
    app.dependency_overrides[get_google_drive_client] = lambda: SimpleNamespace(
        exchange_authorization_code=exchange,
    )

    authorize_response = await client.post(
        f"/api/v1/workspaces/{workspace.id}/integrations/google-drive/authorize",
    )
    assert authorize_response.status_code == 200
    state = parse_qs(
        urlparse(authorize_response.json()["authorizationUrl"]).query
    )["state"][0]
    assert (await integration_session.exec(
        select(IntegrationOAuthState).where(
            IntegrationOAuthState.nonce == expired_nonce
        )
    )).one_or_none() is None
    assert (await integration_session.exec(
        select(IntegrationOAuthState).where(
            IntegrationOAuthState.nonce == other_expired_nonce
        )
    )).one_or_none() is not None

    first_response = await client.get(
        "/api/v1/integrations/google-drive/callback",
        params={"code": "first-authorization-code", "state": state},
        follow_redirects=False,
    )
    second_response = await client.get(
        "/api/v1/integrations/google-drive/callback",
        params={"code": "second-authorization-code", "state": state},
        follow_redirects=False,
    )

    assert first_response.status_code == 302
    assert second_response.status_code == 400
    assert second_response.json()["detail"] == "유효하지 않거나 만료된 OAuth state입니다"
    assert exchange.await_count == 1


async def test_consume_oauth_state_executes_single_delete_returning_statement(
    integration_session: AsyncSession,
) -> None:
    """nonce 소비는 pre-check 없이 단일 DELETE ... RETURNING SQL이어야 한다."""
    user, workspace, _ = await _seed_callback_owner(
        integration_session,
        "statement-shape",
    )
    nonce = "statement-shape-nonce"
    integration_session.add(
        IntegrationOAuthState(
            nonce=nonce,
            workspace_id=workspace.id,
            requester_user_id=user.id,
            expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5),
        )
    )
    await integration_session.commit()
    statements: list[str] = []
    bind = integration_session.bind
    assert bind is not None

    def capture_statement(
        _connection,
        _cursor,
        statement,
        _parameters,
        _context,
        _executemany,
    ) -> None:
        if "integration_oauth_states" in statement:
            statements.append(statement)

    event.listen(bind.sync_engine, "before_cursor_execute", capture_statement)
    try:
        consumed = await IntegrationRepository(integration_session).consume_oauth_state(
            nonce=nonce,
            workspace_id=workspace.id,
            now=datetime.now(UTC).replace(tzinfo=None),
        )
        await integration_session.commit()
    finally:
        event.remove(bind.sync_engine, "before_cursor_execute", capture_statement)

    assert consumed is True
    assert len(statements) == 1
    statement = " ".join(statements[0].upper().split())
    assert statement.startswith("DELETE FROM INTEGRATION_OAUTH_STATES")
    assert "RETURNING INTEGRATION_OAUTH_STATES.NONCE" in statement


async def test_callback_keeps_expired_nonce_unconsumed(
    client: AsyncClient,
    integration_session: AsyncSession,
    oauth_settings: _OAuthSettings,
) -> None:
    user, workspace, _ = await _seed_callback_owner(
        integration_session,
        "expired",
    )
    nonce = "expired-callback-nonce"
    state = integration_router._encode_oauth_state(
        workspace.id,
        user.id,
        "expired-callback-verifier",
        nonce=nonce,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    integration_session.add(
        IntegrationOAuthState(
            nonce=nonce,
            workspace_id=workspace.id,
            requester_user_id=user.id,
            expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1),
        )
    )
    await integration_session.commit()
    exchange = AsyncMock()
    app.dependency_overrides[get_async_session] = lambda: integration_session
    app.dependency_overrides[get_google_drive_client] = lambda: SimpleNamespace(
        exchange_authorization_code=exchange,
    )

    response = await client.get(
        "/api/v1/integrations/google-drive/callback",
        params={"code": "expired-authorization-code", "state": state},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert exchange.await_count == 0
    assert (await integration_session.exec(
        select(IntegrationOAuthState).where(IntegrationOAuthState.nonce == nonce)
    )).one_or_none() is not None


async def test_callback_revalidates_state_owner_and_hides_tokens(
    client: AsyncClient,
    oauth_settings: _OAuthSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid.uuid4()
    owner = _member(workspace_id)
    connect, exchange = _install_callback_dependencies(monkeypatch, owner)
    state = integration_router._encode_oauth_state(
        workspace_id,
        owner.user_id,
        "callback-code-verifier",
    )

    response = await client.get(
        "/api/v1/integrations/google-drive/callback",
        params={"code": "authorization-code", "state": state},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "https://app.kairos.test/settings?tab=integrations"
    assert response.text == ""
    assert "refresh-token-from-google" not in response.text
    assert "authorization-code" not in response.text
    assert "callback-code-verifier" not in response.text
    assert state not in response.text
    assert exchange.await_args.args[:2] == (
        "authorization-code",
        "callback-code-verifier",
    )
    assert exchange.await_args.args[2] == oauth_settings.google_oauth_redirect_uri
    assert connect.await_args.kwargs["workspace_id"] == workspace_id
    assert connect.await_args.kwargs["authorized_by_id"] == owner.user_id
    assert connect.await_args.kwargs["refresh_token"] == "refresh-token-from-google"


@pytest.mark.parametrize("state_kind", ["expired", "tampered"])
async def test_callback_rejects_expired_and_tampered_state(
    client: AsyncClient,
    oauth_settings: _OAuthSettings,
    monkeypatch: pytest.MonkeyPatch,
    state_kind: str,
) -> None:
    workspace_id = uuid.uuid4()
    owner = _member(workspace_id)
    _install_callback_dependencies(monkeypatch, owner)
    state = (
        _expired_state(workspace_id, owner.user_id)
        if state_kind == "expired"
        else "tampered-state"
    )

    response = await client.get(
        "/api/v1/integrations/google-drive/callback",
        params={"code": "authorization-code", "state": state},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert state not in response.text


@pytest.mark.parametrize("encryption_key", [None, "invalid-fernet-key"])
async def test_callback_returns_503_when_state_decryption_configuration_fails(
    client: AsyncClient,
    oauth_settings: _OAuthSettings,
    monkeypatch: pytest.MonkeyPatch,
    encryption_key: str | None,
) -> None:
    workspace_id = uuid.uuid4()
    owner = _member(workspace_id)
    _install_callback_dependencies(monkeypatch, owner)
    state = integration_router._encode_oauth_state(
        workspace_id,
        owner.user_id,
        "configuration-failure-verifier",
    )
    monkeypatch.setattr(
        crypto,
        "get_settings",
        lambda: SimpleNamespace(
            integrations_encryption_key=(
                SecretStr(encryption_key) if encryption_key is not None else None
            )
        ),
    )
    response = await client.get(
        "/api/v1/integrations/google-drive/callback",
        params={"code": "authorization-code", "state": state},
        follow_redirects=False,
    )

    assert response.status_code == 503
    assert state not in response.text
    assert "authorization-code" not in response.text


@pytest.mark.parametrize(
    ("error_type", "expected_status"),
    [
        (EncryptionDecryptionError, 400),
        (EncryptionConfigurationError, 503),
    ],
)
def test_callback_encryption_error_mapping_does_not_depend_on_message(
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[EncryptionError],
    expected_status: int,
) -> None:
    def raise_error(_: str) -> str:
        raise error_type("메시지를 바꿔도 HTTP 의미는 유지된다")

    monkeypatch.setattr(integration_router, "decrypt_string", raise_error)

    with pytest.raises(HTTPException) as exc_info:
        integration_router._decode_oauth_state("state")

    assert exc_info.value.status_code == expected_status


@pytest.mark.parametrize(
    "payload",
    [
        {
            "workspace_id": str(uuid.uuid4()),
            "nonce": "nonce",
            "code_verifier": "code-verifier",
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        },
        {
            "workspace_id": "not-a-uuid",
            "requester_user_id": str(uuid.uuid4()),
            "nonce": "nonce",
            "code_verifier": "code-verifier",
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        },
        {
            "workspace_id": 1,
            "requester_user_id": [],
            "nonce": "nonce",
            "code_verifier": "code-verifier",
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        },
    ],
)
def test_decode_oauth_state_rejects_invalid_payload_shape(
    oauth_settings: _OAuthSettings,
    payload: dict[str, object],
) -> None:
    state = crypto.encrypt_string(json.dumps(payload))

    with pytest.raises(HTTPException) as exc_info:
        integration_router._decode_oauth_state(state)

    assert exc_info.value.status_code == 400


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("post", "/integrations/google-drive/documents", {"fileIds": ["file-1"]}),
        (
            "post",
            "/integrations/google-drive/documents/{document_id}/sync",
            None,
        ),
        ("delete", "/integrations/google-drive/documents/{document_id}", None),
    ],
)
async def test_pipeline_endpoints_return_503_when_oauth_settings_are_missing(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    payload: dict[str, object] | None,
) -> None:
    from src.common.database import get_session_factory
    from src.integrations import dependencies as integration_dependencies

    workspace_id = uuid.uuid4()
    document_id = uuid.uuid4()
    settings = SimpleNamespace(
        google_oauth_client_id=None,
        google_oauth_client_secret=None,
    )
    app.dependency_overrides[require_owner] = lambda: _member(workspace_id)
    app.dependency_overrides[get_async_session] = lambda: AsyncMock()
    app.dependency_overrides[get_session_factory] = lambda: MagicMock()
    monkeypatch.setattr(integration_dependencies, "get_settings", lambda: settings)

    response = await client.request(
        method.upper(),
        f"/api/v1/workspaces/{workspace_id}{path.format(document_id=document_id)}",
        json=payload,
    )

    assert response.status_code == 503


async def test_callback_rejects_revoked_owner_and_other_workspace_state(
    client: AsyncClient,
    oauth_settings: _OAuthSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid.uuid4()
    requester = _member(workspace_id, "member")
    connect, exchange = _install_callback_dependencies(monkeypatch, requester)
    state = integration_router._encode_oauth_state(
        workspace_id,
        requester.user_id,
        "revoked-owner-verifier",
    )

    revoked_response = await client.get(
        "/api/v1/integrations/google-drive/callback",
        params={"code": "authorization-code", "state": state},
        follow_redirects=False,
    )

    assert revoked_response.status_code == 403
    assert exchange.await_count == 0
    assert connect.await_count == 0

    app.dependency_overrides.clear()
    other_workspace_state = integration_router._encode_oauth_state(
        uuid.uuid4(),
        requester.user_id,
        "other-workspace-verifier",
    )
    connect, exchange = _install_callback_dependencies(monkeypatch, None)
    manipulated_response = await client.get(
        "/api/v1/integrations/google-drive/callback",
        params={"code": "authorization-code", "state": other_workspace_state},
        follow_redirects=False,
    )

    assert manipulated_response.status_code == 403
    assert exchange.await_count == 0
    assert connect.await_count == 0


async def test_concurrent_callbacks_upsert_one_connection_without_500(
    client: AsyncClient,
    integration_session: AsyncSession,
    oauth_settings: _OAuthSettings,
) -> None:
    user = User(
        auth_user_id=f"ba_callback_concurrent_{uuid.uuid4().hex[:8]}",
        display_name="Concurrent Callback Owner",
        email=f"callback_concurrent_{uuid.uuid4().hex[:8]}@k.test",
    )
    integration_session.add(user)
    await integration_session.flush()
    workspace = Workspace(name="Concurrent Callback", owner_id=user.id)
    integration_session.add(workspace)
    await integration_session.flush()
    integration_session.add(
        WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role="owner",
        )
    )
    await integration_session.commit()
    session_factory = async_sessionmaker(
        integration_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def request_session():
        async with session_factory() as session:
            yield session

    barrier = asyncio.Barrier(2)

    async def exchange_authorization_code(*_args, **_kwargs):
        await barrier.wait()
        return GoogleAuthorizationCodeToken(
            refresh_token="concurrent-callback-refresh-token",
            expires_in=3600,
        )

    exchange = AsyncMock(side_effect=exchange_authorization_code)
    app.dependency_overrides[get_async_session] = request_session
    app.dependency_overrides[get_google_drive_client] = lambda: SimpleNamespace(
        exchange_authorization_code=exchange,
    )
    first_state = integration_router._encode_oauth_state(
        workspace.id,
        user.id,
        "concurrent-callback-verifier-a",
    )
    second_state = integration_router._encode_oauth_state(
        workspace.id,
        user.id,
        "concurrent-callback-verifier-b",
    )
    for state in (first_state, second_state):
        oauth_state = integration_router._decode_oauth_state(state)
        integration_session.add(
            IntegrationOAuthState(
                nonce=oauth_state.nonce,
                workspace_id=workspace.id,
                requester_user_id=user.id,
                expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5),
            )
        )
    await integration_session.commit()

    first, second = await asyncio.gather(
        client.get(
            "/api/v1/integrations/google-drive/callback",
            params={"code": "authorization-code-a", "state": first_state},
            follow_redirects=False,
        ),
        client.get(
            "/api/v1/integrations/google-drive/callback",
            params={"code": "authorization-code-b", "state": second_state},
            follow_redirects=False,
        ),
    )

    async with session_factory() as verification_session:
        connections = list((await verification_session.exec(
            select(IntegrationConnection).where(
                IntegrationConnection.workspace_id == workspace.id,
                IntegrationConnection.provider == "google_drive",
            )
        )).all())

    assert first.status_code == 302
    assert second.status_code == 302
    assert len(connections) == 1
    assert exchange.await_count == 2


async def test_concurrent_callbacks_consume_same_nonce_once(
    client: AsyncClient,
    integration_session: AsyncSession,
    oauth_settings: _OAuthSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """동시에 같은 callback state를 보내도 한 요청만 Google 교환까지 진행한다."""
    user, workspace, _ = await _seed_callback_owner(
        integration_session,
        "same-nonce",
    )
    nonce = "concurrent-callback-nonce"
    state = integration_router._encode_oauth_state(
        workspace.id,
        user.id,
        "concurrent-callback-verifier",
        nonce=nonce,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    integration_session.add(
        IntegrationOAuthState(
            nonce=nonce,
            workspace_id=workspace.id,
            requester_user_id=user.id,
            expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5),
        )
    )
    await integration_session.commit()
    session_factory = async_sessionmaker(
        integration_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def request_session():
        async with session_factory() as session:
            yield session

    consume_barrier = asyncio.Barrier(2)
    consume_oauth_state = IntegrationRepository.consume_oauth_state

    async def synchronized_consume(
        repository: IntegrationRepository,
        **kwargs: object,
    ) -> bool:
        await consume_barrier.wait()
        return await consume_oauth_state(repository, **kwargs)

    exchange = AsyncMock(
        return_value=GoogleAuthorizationCodeToken(
            refresh_token="same-nonce-refresh-token",
            expires_in=3600,
        )
    )
    monkeypatch.setattr(
        IntegrationRepository,
        "consume_oauth_state",
        synchronized_consume,
    )
    app.dependency_overrides[get_async_session] = request_session
    app.dependency_overrides[get_google_drive_client] = lambda: SimpleNamespace(
        exchange_authorization_code=exchange,
    )

    first, second = await asyncio.gather(
        client.get(
            "/api/v1/integrations/google-drive/callback",
            params={"code": "same-nonce-code-a", "state": state},
            follow_redirects=False,
        ),
        client.get(
            "/api/v1/integrations/google-drive/callback",
            params={"code": "same-nonce-code-b", "state": state},
            follow_redirects=False,
        ),
    )

    assert sorted((first.status_code, second.status_code)) == [302, 400]
    assert exchange.await_count == 1
