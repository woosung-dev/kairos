"""Integrations 단일 도메인 서비스 — Router와 pipeline의 중간 경계."""
import logging
import uuid
from datetime import datetime

from src.common.crypto import decrypt_string, encrypt_string
from src.common.exceptions import EncryptionError
from src.integrations.exceptions import (
    ExternalDocumentNotFoundError,
    IntegrationConnectionNotFoundError,
    IntegrationEncryptionError,
)
from src.integrations.models import (
    ExternalDocument,
    IntegrationConnection,
    IntegrationSyncRun,
)
from src.integrations.repository import IntegrationRepository

logger = logging.getLogger(__name__)


class IntegrationService:
    """Workspace-scoped integrations CRUD와 refresh token 암호화."""

    def __init__(self, repo: IntegrationRepository) -> None:
        self.repo = repo

    async def get_connection(
        self,
        connection_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> IntegrationConnection | None:
        return await self.repo.find_connection_by_id(connection_id, workspace_id)

    async def get_connection_by_provider(
        self,
        workspace_id: uuid.UUID,
        provider: str,
    ) -> IntegrationConnection | None:
        return await self.repo.find_connection_by_workspace(workspace_id, provider)

    async def connect_or_reauthorize(
        self,
        workspace_id: uuid.UUID,
        authorized_by_id: uuid.UUID,
        refresh_token: str,
        scope: str,
        token_expires_at: datetime | None = None,
        provider: str = "google_drive",
    ) -> IntegrationConnection:
        try:
            encrypted_refresh_token = encrypt_string(refresh_token)
        except EncryptionError as exc:
            # ADR-028: Sentry 제거 후 stdout 로그가 유일한 관측 경로다.
            logger.exception("integration_encryption_failed", exc_info=exc)
            raise IntegrationEncryptionError() from exc

        connection = await self.repo.upsert_connection(
            workspace_id=workspace_id,
            provider=provider,
            authorized_by_id=authorized_by_id,
            encrypted_refresh_token=encrypted_refresh_token,
            scope=scope,
            token_expires_at=token_expires_at,
        )
        await self.repo.commit()
        return connection

    async def disable_connection(
        self,
        connection_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> None:
        """연결만 비활성화하고 저장된 토큰을 지운다.

        ★**이것은 "연결 해제" 가 아니다.** 발행된 `ExternalDocument` 와 그
        임베딩 청크·SemanticCache 를 그대로 남기므로, 이것만 부르면 "토큰은
        지웠는데 문서는 계속 검색되는" 상태가 된다 — ADR-026 회수 전략이
        없애려는 바로 그 상태다.

        사용자향 연결 해제는 `GoogleDriveSyncPipelineService.disconnect_connection`
        하나뿐이다 (문서 전량 회수 + Google 폐기 포함). 이 메서드는 토큰 수명만
        다루는 저수준 조각이며, 이름으로 그 차이를 드러내려고 `disconnect_` 접두사를
        쓰지 않는다.
        """
        connection = await self.repo.find_connection_by_id(connection_id, workspace_id)
        if connection is None:
            raise IntegrationConnectionNotFoundError()
        await self.repo.update_connection_status(
            connection_id,
            workspace_id,
            status="disabled",
            clear_refresh_token=True,
        )
        await self.repo.commit()

    async def get_decrypted_refresh_token(
        self,
        connection_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> str:
        connection = await self.repo.find_connection_by_id(connection_id, workspace_id)
        if connection is None:
            raise IntegrationConnectionNotFoundError()
        if connection.encrypted_refresh_token is None:
            raise IntegrationEncryptionError()
        try:
            return decrypt_string(connection.encrypted_refresh_token)
        except EncryptionError as exc:
            # ADR-028: Sentry 제거 후 stdout 로그가 유일한 관측 경로다.
            logger.exception("integration_encryption_failed", exc_info=exc)
            raise IntegrationEncryptionError() from exc

    async def get_document(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> ExternalDocument | None:
        return await self.repo.find_document_by_id(document_id, workspace_id)

    async def list_documents_by_connection(
        self,
        connection_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> list[ExternalDocument]:
        return await self.repo.find_documents_by_connection(
            connection_id,
            workspace_id,
        )

    async def list_documents_by_sync_run(
        self,
        sync_run_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> list[ExternalDocument]:
        return await self.repo.find_documents_by_sync_run(sync_run_id, workspace_id)

    async def delete_document(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> None:
        document = await self.repo.find_document_by_id(document_id, workspace_id)
        if document is None:
            raise ExternalDocumentNotFoundError()
        await self.repo.delete_document(document_id, workspace_id)
        await self.repo.commit()

    async def get_sync_run(
        self,
        sync_run_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> IntegrationSyncRun | None:
        return await self.repo.find_sync_run_by_id(sync_run_id, workspace_id)
