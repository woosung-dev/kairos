"""ADR-026 integrations service 회귀 테스트."""
import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.models import User
from src.common import crypto
from src.common.exceptions import EncryptionError
from src.integrations import service as integration_service_module
from src.integrations.exceptions import IntegrationEncryptionError
from src.integrations.models import (
    ExternalDocument,
    IntegrationConnection,
    IntegrationSyncRun,
)
from src.integrations.repository import IntegrationRepository
from src.integrations.schemas import IntegrationConnectionResponse
from src.integrations.service import IntegrationService
from src.projects.models import Project
from src.workspaces.models import Workspace

pytestmark = pytest.mark.integration


@dataclass
class _CryptoSettings:
    integrations_encryption_key: SecretStr


@dataclass
class _ServiceSeed:
    user: User
    workspace: Workspace
    project: Project
    connection: IntegrationConnection


async def _seed_service_workspace(
    session: AsyncSession,
    tag: str,
) -> _ServiceSeed:
    suffix = uuid.uuid4().hex[:8]
    user = User(
        auth_user_id=f"ba_service_{tag}_{suffix}",
        display_name=f"Service {tag}",
        email=f"service_{tag}_{suffix}@k.test",
    )
    session.add(user)
    await session.flush()

    workspace = Workspace(name=f"Service {tag}", owner_id=user.id)
    session.add(workspace)
    await session.flush()

    project = Project(
        workspace_id=workspace.id,
        title=f"Project {tag}",
        created_by_id=user.id,
    )
    connection = IntegrationConnection(
        workspace_id=workspace.id,
        authorized_by_id=user.id,
        encrypted_refresh_token="unused",
        scope="https://www.googleapis.com/auth/drive.file",
    )
    session.add_all([project, connection])
    await session.commit()

    return _ServiceSeed(
        user=user,
        workspace=workspace,
        project=project,
        connection=connection,
    )


def _service(session: AsyncSession) -> IntegrationService:
    return IntegrationService(IntegrationRepository(session))


def _set_fernet_key(monkeypatch: pytest.MonkeyPatch) -> None:
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(
        crypto,
        "get_settings",
        lambda: _CryptoSettings(integrations_encryption_key=SecretStr(key)),
    )
    crypto._get_fernet.cache_clear()


async def test_connection_lookup_is_workspace_scoped(
    integration_session: AsyncSession,
) -> None:
    first = await _seed_service_workspace(integration_session, "first")
    second = await _seed_service_workspace(integration_session, "second")

    connection = await _service(integration_session).get_connection(
        first.connection.id,
        second.workspace.id,
    )

    assert connection is None


async def test_connection_lookup_by_provider_is_workspace_scoped(
    integration_session: AsyncSession,
) -> None:
    first = await _seed_service_workspace(integration_session, "provider-first")
    second = await _seed_service_workspace(integration_session, "provider-second")
    service = _service(integration_session)

    connection = await service.get_connection_by_provider(
        first.workspace.id,
        "google_drive",
    )

    assert connection is not None
    assert connection.id == first.connection.id
    assert connection.id != second.connection.id


async def test_connection_response_exposes_last_synced_at(
    integration_session: AsyncSession,
) -> None:
    seed = await _seed_service_workspace(integration_session, "last-synced")
    last_synced_at = datetime.now(UTC).replace(tzinfo=None)
    seed.connection.last_synced_at = last_synced_at
    await integration_session.commit()

    response = IntegrationConnectionResponse.model_validate(seed.connection)

    assert response.last_synced_at == last_synced_at


async def test_refresh_token_is_encrypted_and_decrypted(
    integration_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_fernet_key(monkeypatch)
    seed = await _seed_service_workspace(integration_session, "crypto")
    service = _service(integration_session)
    await integration_session.delete(seed.connection)
    await integration_session.commit()

    connection = await service.connect_or_reauthorize(
        workspace_id=seed.workspace.id,
        authorized_by_id=seed.user.id,
        refresh_token="refresh-token-value",
        scope="https://www.googleapis.com/auth/drive.file",
    )

    assert connection.encrypted_refresh_token != "refresh-token-value"
    assert await service.get_decrypted_refresh_token(
        connection.id,
        seed.workspace.id,
    ) == "refresh-token-value"


async def test_connect_disconnect_reauthorize_reuses_connection(
    integration_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_fernet_key(monkeypatch)
    seed = await _seed_service_workspace(integration_session, "reconnect")
    await integration_session.delete(seed.connection)
    await integration_session.commit()
    service = _service(integration_session)
    first = await service.connect_or_reauthorize(
        workspace_id=seed.workspace.id,
        authorized_by_id=seed.user.id,
        refresh_token="first-refresh-token",
        scope="scope-first",
    )
    first_ciphertext = first.encrypted_refresh_token

    await service.disconnect_connection(first.id, seed.workspace.id)
    token_expires_at = datetime.now(UTC).replace(tzinfo=None)
    reauthorizing_user = User(
        auth_user_id=f"ba_service_reauthorize_{uuid.uuid4().hex[:8]}",
        display_name="Reauthorize User",
        email=f"reauthorize_{uuid.uuid4().hex[:8]}@k.test",
    )
    integration_session.add(reauthorizing_user)
    await integration_session.flush()
    reconnected = await service.connect_or_reauthorize(
        workspace_id=seed.workspace.id,
        authorized_by_id=reauthorizing_user.id,
        refresh_token="second-refresh-token",
        scope="scope-second",
        token_expires_at=token_expires_at,
    )
    await integration_session.refresh(reconnected)
    connections = list((await integration_session.exec(
        select(IntegrationConnection).where(
            IntegrationConnection.workspace_id == seed.workspace.id,
            IntegrationConnection.provider == "google_drive",
        )
    )).all())

    assert reconnected.id == first.id
    assert len(connections) == 1
    assert reconnected.encrypted_refresh_token != first_ciphertext
    assert reconnected.scope == "scope-second"
    assert reconnected.token_expires_at == token_expires_at
    assert reconnected.status == "active"
    assert reconnected.authorized_by_id == reauthorizing_user.id
    assert await service.get_decrypted_refresh_token(
        reconnected.id,
        seed.workspace.id,
    ) == "second-refresh-token"


async def test_concurrent_reauthorize_upserts_single_connection(
    integration_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_fernet_key(monkeypatch)
    seed = await _seed_service_workspace(integration_session, "concurrent-upsert")
    await integration_session.delete(seed.connection)
    await integration_session.commit()
    session_factory = async_sessionmaker(
        integration_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    barrier = asyncio.Barrier(2)
    precheck_barrier = asyncio.Barrier(2)
    original_upsert_connection = IntegrationRepository.upsert_connection
    original_find_connection = IntegrationRepository.find_connection_by_workspace

    async def upsert_with_barrier(
        repository: IntegrationRepository,
        **kwargs,
    ) -> IntegrationConnection:
        await barrier.wait()
        return await original_upsert_connection(repository, **kwargs)

    async def find_connection_with_barrier(
        repository: IntegrationRepository,
        workspace_id: uuid.UUID,
        provider: str,
    ) -> IntegrationConnection | None:
        connection = await original_find_connection(repository, workspace_id, provider)
        await precheck_barrier.wait()
        return connection

    monkeypatch.setattr(
        IntegrationRepository,
        "upsert_connection",
        upsert_with_barrier,
    )
    monkeypatch.setattr(
        IntegrationRepository,
        "find_connection_by_workspace",
        find_connection_with_barrier,
    )

    async def reauthorize(refresh_token: str) -> IntegrationConnection:
        async with session_factory() as session:
            return await _service(session).connect_or_reauthorize(
                workspace_id=seed.workspace.id,
                authorized_by_id=seed.user.id,
                refresh_token=refresh_token,
                scope="https://www.googleapis.com/auth/drive.file",
            )

    first, second = await asyncio.gather(
        reauthorize("concurrent-refresh-token-a"),
        reauthorize("concurrent-refresh-token-b"),
    )

    async with session_factory() as verification_session:
        connections = list((await verification_session.exec(
            select(IntegrationConnection).where(
                IntegrationConnection.workspace_id == seed.workspace.id,
                IntegrationConnection.provider == "google_drive",
            )
        )).all())

    assert first.id == second.id
    assert len(connections) == 1


async def test_upsert_connection_raises_when_returning_row_cannot_be_reloaded() -> None:
    session = AsyncMock()
    session.execute.return_value = SimpleNamespace(scalar_one=lambda: uuid.uuid4())
    repository = IntegrationRepository(session)
    repository.find_connection_by_id = AsyncMock(return_value=None)

    with pytest.raises(RuntimeError, match="다시 조회"):
        await repository.upsert_connection(
            workspace_id=uuid.uuid4(),
            provider="google_drive",
            authorized_by_id=uuid.uuid4(),
            encrypted_refresh_token="encrypted-token",
            scope="scope",
            token_expires_at=None,
        )


async def test_decryption_error_is_converted_to_domain_error(
    integration_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed = await _seed_service_workspace(integration_session, "decrypt-error")
    service = _service(integration_session)

    def _raise_encryption_error(_: str) -> str:
        raise EncryptionError()

    monkeypatch.setattr(
        integration_service_module,
        "decrypt_string",
        _raise_encryption_error,
    )

    with pytest.raises(IntegrationEncryptionError):
        await service.get_decrypted_refresh_token(
            seed.connection.id,
            seed.workspace.id,
        )


async def test_corrupted_ciphertext_is_converted_to_domain_error(
    integration_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_fernet_key(monkeypatch)
    seed = await _seed_service_workspace(integration_session, "corrupted-ciphertext")

    with pytest.raises(IntegrationEncryptionError):
        await _service(integration_session).get_decrypted_refresh_token(
            seed.connection.id,
            seed.workspace.id,
        )


async def test_disconnect_clears_encrypted_refresh_token(
    integration_session: AsyncSession,
) -> None:
    seed = await _seed_service_workspace(integration_session, "disconnect")

    await _service(integration_session).disconnect_connection(
        seed.connection.id,
        seed.workspace.id,
    )
    await integration_session.refresh(seed.connection)

    assert seed.connection.status == "disabled"
    assert seed.connection.encrypted_refresh_token is None


async def test_delete_document_unpublishes_workspace_document(
    integration_session: AsyncSession,
) -> None:
    seed = await _seed_service_workspace(integration_session, "delete-document")
    document = ExternalDocument(
        workspace_id=seed.workspace.id,
        connection_id=seed.connection.id,
        project_id=seed.project.id,
        drive_file_id="drive-delete-document",
        title="삭제할 외부 문서",
        mime_type="application/vnd.google-apps.document",
        origin_url="https://docs.google.com/document/d/delete-document",
        revision_id="1",
        content_hash="delete-document-hash",
        plain_text="삭제할 본문",
    )
    integration_session.add(document)
    await integration_session.commit()
    service = _service(integration_session)

    await service.delete_document(document.id, seed.workspace.id)

    assert await service.get_document(document.id, seed.workspace.id) is None


async def test_document_and_sync_run_cross_workspace_mutations_are_ignored(
    integration_session: AsyncSession,
) -> None:
    first = await _seed_service_workspace(integration_session, "mutation-first")
    second = await _seed_service_workspace(integration_session, "mutation-second")
    sync_run = IntegrationSyncRun(
        workspace_id=first.workspace.id,
        connection_id=first.connection.id,
        requested_by_id=first.user.id,
    )
    integration_session.add(sync_run)
    await integration_session.flush()
    document = ExternalDocument(
        workspace_id=first.workspace.id,
        connection_id=first.connection.id,
        project_id=first.project.id,
        sync_run_id=sync_run.id,
        drive_file_id="drive-cross-workspace-mutation",
        title="격리 문서",
        mime_type="application/vnd.google-apps.document",
        origin_url="https://docs.google.com/document/d/cross-workspace-mutation",
        revision_id="1",
        content_hash="cross-workspace-mutation-hash",
        plain_text="격리 본문",
    )
    integration_session.add(document)
    await integration_session.commit()
    repo = IntegrationRepository(integration_session)

    assert await repo.find_document_by_id(document.id, second.workspace.id) is None
    assert await repo.find_sync_run_by_id(sync_run.id, second.workspace.id) is None
    assert await repo.find_documents_by_sync_run(
        sync_run.id,
        second.workspace.id,
    ) == []

    await repo.update_document_sync_status(
        document.id,
        second.workspace.id,
        sync_status="failed",
        last_synced_at=None,
    )
    await repo.update_sync_run_status(
        sync_run.id,
        second.workspace.id,
        status="failed",
    )
    await repo.delete_document(document.id, second.workspace.id)
    await repo.commit()
    await integration_session.refresh(document)
    await integration_session.refresh(sync_run)

    assert document.sync_status == "pending"
    assert sync_run.status == "pending"
    assert await repo.find_document_by_id(document.id, first.workspace.id) is not None


async def test_update_document_omits_sync_run_id(
    integration_session: AsyncSession,
) -> None:
    seed = await _seed_service_workspace(integration_session, "update-document")
    sync_run = IntegrationSyncRun(
        workspace_id=seed.workspace.id,
        connection_id=seed.connection.id,
        requested_by_id=seed.user.id,
    )
    integration_session.add(sync_run)
    await integration_session.flush()
    document = ExternalDocument(
        workspace_id=seed.workspace.id,
        connection_id=seed.connection.id,
        project_id=seed.project.id,
        sync_run_id=sync_run.id,
        drive_file_id="drive-update-document",
        title="갱신 전 문서",
        mime_type="application/vnd.google-apps.document",
        origin_url="https://docs.google.com/document/d/update-document",
        revision_id="1",
        content_hash="update-document-hash",
        plain_text="갱신 전 본문",
    )
    integration_session.add(document)
    await integration_session.commit()
    repo = IntegrationRepository(integration_session)

    await repo.update_document(
        document.id,
        seed.workspace.id,
        title="갱신 후 문서",
        mime_type=document.mime_type,
        origin_url=document.origin_url,
        revision_id="2",
        content_hash="updated-document-hash",
        plain_text="갱신 후 본문",
        sync_status="completed",
        last_synced_at=None,
    )
    await repo.commit()
    await integration_session.refresh(document)

    assert document.sync_run_id == sync_run.id
    assert document.title == "갱신 후 문서"
