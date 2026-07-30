"""ADR-026 integrations 저장소 — 모든 조회·변경에 workspace 범위를 강제한다."""
import uuid
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import defer
from sqlmodel import delete, select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from src.integrations.models import (
    ExternalDocument,
    IntegrationConnection,
    IntegrationSyncRun,
)


class _SyncRunIdUnchanged:
    """update_document 호출에서 sync run 연결 유지 sentinel."""


_SYNC_RUN_ID_UNCHANGED = _SyncRunIdUnchanged()


class IntegrationRepository:
    """Integrations 모델의 workspace-scoped 데이터 접근."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_connection_by_id(
        self,
        connection_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> IntegrationConnection | None:
        return (await self.session.exec(
            select(IntegrationConnection).where(
                IntegrationConnection.id == connection_id,
                IntegrationConnection.workspace_id == workspace_id,
            )
        )).one_or_none()

    async def find_connection_by_workspace(
        self,
        workspace_id: uuid.UUID,
        provider: str,
    ) -> IntegrationConnection | None:
        return (await self.session.exec(
            select(IntegrationConnection).where(
                IntegrationConnection.workspace_id == workspace_id,
                IntegrationConnection.provider == provider,
            )
        )).one_or_none()

    async def upsert_connection(
        self,
        *,
        workspace_id: uuid.UUID,
        provider: str,
        authorized_by_id: uuid.UUID,
        encrypted_refresh_token: str,
        scope: str,
        token_expires_at: datetime | None,
    ) -> IntegrationConnection:
        """OAuth callback 경쟁을 원자적으로 연결·재승인한다."""
        stmt = (
            pg_insert(IntegrationConnection.__table__)
            .values(
                workspace_id=workspace_id,
                provider=provider,
                authorized_by_id=authorized_by_id,
                encrypted_refresh_token=encrypted_refresh_token,
                scope=scope,
                token_expires_at=token_expires_at,
                status="active",
            )
            .on_conflict_do_update(
                index_elements=["workspace_id", "provider"],
                set_={
                    "authorized_by_id": authorized_by_id,
                    "encrypted_refresh_token": encrypted_refresh_token,
                    "scope": scope,
                    "token_expires_at": token_expires_at,
                    "status": "active",
                },
            )
            .returning(IntegrationConnection.id)
        )
        connection_id = (await self.session.execute(stmt)).scalar_one()
        connection = await self.find_connection_by_id(connection_id, workspace_id)
        if connection is None:
            raise RuntimeError("upsert된 연동 연결을 다시 조회할 수 없습니다")
        return connection

    async def update_connection_status(
        self,
        connection_id: uuid.UUID,
        workspace_id: uuid.UUID,
        status: str,
        clear_refresh_token: bool = False,
    ) -> None:
        stmt = update(IntegrationConnection).where(
            IntegrationConnection.id == connection_id,
            IntegrationConnection.workspace_id == workspace_id,
        )
        if clear_refresh_token:
            stmt = stmt.values(
                status=status,
                encrypted_refresh_token=None,
            )
        else:
            stmt = stmt.values(status=status)
        await self.session.exec(stmt)

    async def find_document_by_id(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> ExternalDocument | None:
        return (await self.session.exec(
            select(ExternalDocument).where(
                ExternalDocument.id == document_id,
                ExternalDocument.workspace_id == workspace_id,
            )
        )).one_or_none()

    async def find_document_id_by_drive_file_id(
        self,
        connection_id: uuid.UUID,
        workspace_id: uuid.UUID,
        drive_file_id: str,
    ) -> uuid.UUID | None:
        return (await self.session.exec(
            select(ExternalDocument.id).where(
                ExternalDocument.connection_id == connection_id,
                ExternalDocument.workspace_id == workspace_id,
                ExternalDocument.drive_file_id == drive_file_id,
            )
        )).one_or_none()

    async def find_documents_by_workspace(
        self,
        workspace_id: uuid.UUID,
    ) -> list[ExternalDocument]:
        """본문을 defer한 목록. 본문이 필요하면 find_document_by_id를 사용한다."""
        stmt = (
            select(ExternalDocument)
            .where(ExternalDocument.workspace_id == workspace_id)
            .options(defer(ExternalDocument.plain_text))
            .order_by(ExternalDocument.last_synced_at.desc().nulls_last())
        )
        return list((await self.session.exec(stmt)).all())

    async def find_documents_by_sync_run(
        self,
        sync_run_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> list[ExternalDocument]:
        """본문을 defer한 sync run 목록. 본문이 필요하면 find_document_by_id를 사용한다."""
        stmt = (
            select(ExternalDocument)
            .where(
                ExternalDocument.workspace_id == workspace_id,
                ExternalDocument.sync_run_id == sync_run_id,
            )
            .options(defer(ExternalDocument.plain_text))
            .order_by(ExternalDocument.last_synced_at.desc().nulls_last())
        )
        return list((await self.session.exec(stmt)).all())

    async def create_document(
        self,
        document: ExternalDocument,
        workspace_id: uuid.UUID,
    ) -> ExternalDocument:
        if document.workspace_id != workspace_id:
            raise ValueError("document workspace_id가 일치하지 않습니다")
        self.session.add(document)
        await self.session.flush()
        return document

    async def update_document(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
        *,
        title: str,
        mime_type: str,
        origin_url: str,
        revision_id: str,
        content_hash: str,
        plain_text: str,
        sync_status: str,
        last_synced_at: datetime | None,
        sync_run_id: uuid.UUID | None | _SyncRunIdUnchanged = (
            _SYNC_RUN_ID_UNCHANGED
        ),
    ) -> None:
        stmt = update(ExternalDocument).where(
            ExternalDocument.id == document_id,
            ExternalDocument.workspace_id == workspace_id,
        )
        values = {
            "title": title,
            "mime_type": mime_type,
            "origin_url": origin_url,
            "revision_id": revision_id,
            "content_hash": content_hash,
            "plain_text": plain_text,
            "sync_status": sync_status,
            "last_synced_at": last_synced_at,
        }
        if sync_run_id is not _SYNC_RUN_ID_UNCHANGED:
            values["sync_run_id"] = sync_run_id
        await self.session.exec(stmt.values(**values))

    async def update_document_sync_status(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
        sync_status: str,
        last_synced_at: datetime | None,
        sync_run_id: uuid.UUID | None | _SyncRunIdUnchanged = (
            _SYNC_RUN_ID_UNCHANGED
        ),
    ) -> None:
        values = {
            "sync_status": sync_status,
            "last_synced_at": last_synced_at,
        }
        if sync_run_id is not _SYNC_RUN_ID_UNCHANGED:
            values["sync_run_id"] = sync_run_id
        await self.session.exec(
            update(ExternalDocument)
            .where(
                ExternalDocument.id == document_id,
                ExternalDocument.workspace_id == workspace_id,
            )
            .values(**values)
        )

    async def purge_document_content(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
        *,
        last_synced_at: datetime,
        sync_run_id: uuid.UUID | None | _SyncRunIdUnchanged = (
            _SYNC_RUN_ID_UNCHANGED
        ),
    ) -> None:
        """외부 원본 소실 확정 시 본문만 purge하고 이력 행은 보존한다."""
        values = {
            "plain_text": "",
            "content_hash": "",
            "sync_status": "purged",
            "last_synced_at": last_synced_at,
        }
        if sync_run_id is not _SYNC_RUN_ID_UNCHANGED:
            values["sync_run_id"] = sync_run_id
        await self.session.exec(
            update(ExternalDocument)
            .where(
                ExternalDocument.id == document_id,
                ExternalDocument.workspace_id == workspace_id,
            )
            .values(**values)
        )

    async def delete_document(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> None:
        await self.session.exec(
            delete(ExternalDocument).where(
                ExternalDocument.id == document_id,
                ExternalDocument.workspace_id == workspace_id,
            )
        )
        await self.session.flush()

    async def create_sync_run(
        self,
        sync_run: IntegrationSyncRun,
        workspace_id: uuid.UUID,
    ) -> IntegrationSyncRun:
        if sync_run.workspace_id != workspace_id:
            raise ValueError("sync run workspace_id가 일치하지 않습니다")
        self.session.add(sync_run)
        await self.session.flush()
        return sync_run

    async def find_sync_run_by_id(
        self,
        sync_run_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> IntegrationSyncRun | None:
        return (await self.session.exec(
            select(IntegrationSyncRun).where(
                IntegrationSyncRun.id == sync_run_id,
                IntegrationSyncRun.workspace_id == workspace_id,
            )
        )).one_or_none()

    async def update_sync_run_status(
        self,
        sync_run_id: uuid.UUID,
        workspace_id: uuid.UUID,
        status: str,
        completed_at: datetime | None = None,
        error_summary: str | None = None,
    ) -> None:
        await self.session.exec(
            update(IntegrationSyncRun)
            .where(
                IntegrationSyncRun.id == sync_run_id,
                IntegrationSyncRun.workspace_id == workspace_id,
            )
            .values(
                status=status,
                completed_at=completed_at,
                error_summary=error_summary,
            )
        )

    async def commit(self) -> None:
        await self.session.commit()
