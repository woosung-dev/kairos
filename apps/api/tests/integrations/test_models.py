"""ADR-026 integrations 모델 제약 회귀 테스트."""
import uuid
from dataclasses import dataclass

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.models import User
from src.integrations.models import (
    ExternalDocument,
    IntegrationConnection,
    IntegrationSyncRun,
)
from src.projects.models import Project
from src.workspaces.models import Workspace

pytestmark = pytest.mark.integration


@dataclass
class _IntegrationSeed:
    user: User
    workspace: Workspace
    project: Project
    connection: IntegrationConnection


async def _seed_workspace_with_connection(
    session: AsyncSession,
    tag: str,
) -> _IntegrationSeed:
    suffix = uuid.uuid4().hex[:8]
    user = User(
        auth_user_id=f"ba_integrations_{tag}_{suffix}",
        display_name=f"Integrations {tag}",
        email=f"integrations_{tag}_{suffix}@k.test",
    )
    session.add(user)
    await session.flush()

    workspace = Workspace(name=f"Integrations {tag}", owner_id=user.id)
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
        encrypted_refresh_token="test-encrypted-refresh-token",
        scope="https://www.googleapis.com/auth/drive.file",
    )
    session.add_all([project, connection])
    await session.flush()

    return _IntegrationSeed(
        user=user,
        workspace=workspace,
        project=project,
        connection=connection,
    )


def _external_document(
    seed: _IntegrationSeed,
    drive_file_id: str,
    project_id: uuid.UUID | None,
    sync_run_id: uuid.UUID | None = None,
) -> ExternalDocument:
    return ExternalDocument(
        workspace_id=seed.workspace.id,
        connection_id=seed.connection.id,
        project_id=project_id,
        sync_run_id=sync_run_id,
        drive_file_id=drive_file_id,
        title="Drive 문서",
        mime_type="application/vnd.google-apps.document",
        origin_url="https://docs.google.com/document/d/test",
        revision_id="1",
        content_hash="test-content-hash",
        plain_text="외부 문서 본문",
    )


async def _expect_integrity_error(session: AsyncSession) -> None:
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


async def test_integration_models_create_and_query(
    integration_session: AsyncSession,
) -> None:
    """연결·외부 문서·sync run을 생성하고 조회한다."""
    seed = await _seed_workspace_with_connection(integration_session, "basic")
    sync_run = IntegrationSyncRun(
        workspace_id=seed.workspace.id,
        connection_id=seed.connection.id,
        requested_by_id=seed.user.id,
    )
    integration_session.add(sync_run)
    await integration_session.flush()
    document = _external_document(
        seed,
        drive_file_id="drive-basic",
        project_id=seed.project.id,
        sync_run_id=sync_run.id,
    )
    integration_session.add(document)
    await integration_session.commit()

    document_result = await integration_session.exec(
        select(ExternalDocument).where(ExternalDocument.id == document.id)
    )
    sync_run_result = await integration_session.exec(
        select(IntegrationSyncRun).where(IntegrationSyncRun.id == sync_run.id)
    )

    stored_document = document_result.one()

    assert stored_document.connection_id == seed.connection.id
    assert stored_document.sync_run_id == sync_run.id
    assert sync_run_result.one().requested_by_id == seed.user.id


async def test_connection_provider_is_unique_per_workspace(
    integration_session: AsyncSession,
) -> None:
    seed = await _seed_workspace_with_connection(integration_session, "provider-unique")
    integration_session.add(
        IntegrationConnection(
            workspace_id=seed.workspace.id,
            authorized_by_id=seed.user.id,
            encrypted_refresh_token="duplicate-refresh-token",
            scope="https://www.googleapis.com/auth/drive.file",
        )
    )

    await _expect_integrity_error(integration_session)


async def test_external_document_cross_workspace_sync_run_is_blocked(
    integration_session: AsyncSession,
) -> None:
    first = await _seed_workspace_with_connection(integration_session, "sync-first")
    second = await _seed_workspace_with_connection(integration_session, "sync-second")
    other_sync_run = IntegrationSyncRun(
        workspace_id=second.workspace.id,
        connection_id=second.connection.id,
        requested_by_id=second.user.id,
    )
    integration_session.add(other_sync_run)
    await integration_session.flush()
    integration_session.add(
        _external_document(
            first,
            drive_file_id="drive-cross-workspace-sync-run",
            project_id=first.project.id,
            sync_run_id=other_sync_run.id,
        )
    )

    await _expect_integrity_error(integration_session)


async def test_external_document_cross_workspace_project_is_blocked(
    integration_session: AsyncSession,
) -> None:
    """다른 워크스페이스 Project 연결은 복합 FK가 차단한다."""
    first = await _seed_workspace_with_connection(integration_session, "first")
    second = await _seed_workspace_with_connection(integration_session, "second")
    integration_session.add(
        _external_document(
            first,
            drive_file_id="drive-cross-workspace-project",
            project_id=second.project.id,
        )
    )

    await _expect_integrity_error(integration_session)


async def test_external_document_duplicate_drive_file_is_blocked(
    integration_session: AsyncSession,
) -> None:
    """같은 연결에서 같은 Drive 파일을 중복 발행할 수 없다."""
    seed = await _seed_workspace_with_connection(integration_session, "unique")
    integration_session.add(
        _external_document(
            seed,
            drive_file_id="drive-duplicate",
            project_id=seed.project.id,
        )
    )
    await integration_session.commit()

    integration_session.add(
        _external_document(
            seed,
            drive_file_id="drive-duplicate",
            project_id=seed.project.id,
        )
    )

    await _expect_integrity_error(integration_session)


async def test_external_document_without_project_is_allowed(
    integration_session: AsyncSession,
) -> None:
    """Project를 고르지 않은 문서는 MATCH SIMPLE로 허용한다."""
    seed = await _seed_workspace_with_connection(integration_session, "no-project")
    document = _external_document(
        seed,
        drive_file_id="drive-no-project",
        project_id=None,
    )
    integration_session.add(document)
    await integration_session.commit()

    await integration_session.refresh(document)

    assert document.project_id is None
