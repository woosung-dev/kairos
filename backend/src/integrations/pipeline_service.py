"""Google Drive 외부 문서 동기화 오케스트레이터."""
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from src.embeddings.repository import EmbeddingRepository
from src.embeddings.service import EmbeddingService
from src.integrations.drive_client import GoogleDriveClient, is_supported_mime_type
from src.integrations.exceptions import (
    DriveClientError,
    DrivePermissionRevokedError,
    DriveReauthenticationRequiredError,
    DriveSourceMissingError,
    DriveTemporaryError,
    DriveUnsupportedMimeTypeError,
)
from src.integrations.models import ExternalDocument
from src.integrations.repository import IntegrationRepository
from src.integrations.service import IntegrationService

_PURGE_ALLOWED_ERRORS = (
    DriveSourceMissingError,
    DrivePermissionRevokedError,
)

DriveClientFactory = Callable[[], GoogleDriveClient]


class GoogleDriveSyncPipelineService:
    """Drive 읽기·외부 원본 상태·임베딩을 조율한다."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        drive_client_factory: DriveClientFactory,
        google_oauth_client_id: str,
        google_oauth_client_secret: str,
    ) -> None:
        self._session_factory = session_factory
        self._drive_client_factory = drive_client_factory
        self._google_oauth_client_id = google_oauth_client_id
        self._google_oauth_client_secret = google_oauth_client_secret

    async def import_documents(
        self,
        sync_run_id: uuid.UUID,
        workspace_id: uuid.UUID,
        connection_id: uuid.UUID,
        file_ids: list[str],
        project_id: uuid.UUID | None,
    ) -> None:
        """선택된 Drive 문서를 최초 수집한다."""
        async with self._session_factory() as session:
            repository = IntegrationRepository(session)
            integration_service = IntegrationService(repository)
            embedding_repository = EmbeddingRepository(session)
            embedding_service = EmbeddingService(embedding_repository)
            drive_client = self._drive_client_factory()
            try:
                sync_run = await repository.find_sync_run_by_id(sync_run_id, workspace_id)
                if sync_run is None:
                    return
                if sync_run.connection_id != connection_id:
                    await self._finish_sync_run(
                        repository,
                        sync_run_id,
                        workspace_id,
                        status="failed",
                    )
                    return

                await repository.update_sync_run_status(
                    sync_run_id,
                    workspace_id,
                    status="processing",
                )
                await repository.commit()

                try:
                    refresh_token = await integration_service.get_decrypted_refresh_token(
                        connection_id,
                        workspace_id,
                    )
                    access_token = await drive_client.refresh_access_token(
                        refresh_token,
                        client_id=self._google_oauth_client_id,
                        client_secret=self._google_oauth_client_secret,
                    )
                except DriveClientError:
                    await self._finish_sync_run(
                        repository,
                        sync_run_id,
                        workspace_id,
                        status="failed",
                    )
                    return
                except Exception:
                    await self._finish_sync_run(
                        repository,
                        sync_run_id,
                        workspace_id,
                        status="failed",
                    )
                    return

                has_document_failure = False
                for file_id in file_ids:
                    failed = await self._process_document_with_safety(
                        repository=repository,
                        embedding_repository=embedding_repository,
                        embedding_service=embedding_service,
                        drive_client=drive_client,
                        access_token=access_token,
                        workspace_id=workspace_id,
                        connection_id=connection_id,
                        file_id=file_id,
                        project_id=project_id,
                        sync_run_id=sync_run_id,
                        document=None,
                    )
                    has_document_failure = has_document_failure or failed

                await self._finish_sync_run(
                    repository,
                    sync_run_id,
                    workspace_id,
                    status="completed",
                    has_document_failure=has_document_failure,
                )
            finally:
                await drive_client.aclose()

    async def resync_document(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> None:
        """단일 문서를 사용자 트리거로 재동기화한다."""
        async with self._session_factory() as session:
            repository = IntegrationRepository(session)
            integration_service = IntegrationService(repository)
            embedding_repository = EmbeddingRepository(session)
            embedding_service = EmbeddingService(embedding_repository)
            drive_client = self._drive_client_factory()
            try:
                document = await repository.find_document_by_id(document_id, workspace_id)
                if document is None:
                    return

                try:
                    refresh_token = await integration_service.get_decrypted_refresh_token(
                        document.connection_id,
                        workspace_id,
                    )
                    access_token = await drive_client.refresh_access_token(
                        refresh_token,
                        client_id=self._google_oauth_client_id,
                        client_secret=self._google_oauth_client_secret,
                    )
                except DriveClientError as exc:
                    await self._preserve_document_for_drive_error(
                        repository,
                        document,
                        workspace_id,
                        exc,
                        sync_run_id=None,
                    )
                    return
                except Exception:
                    await self._mark_document_failed(
                        repository,
                        document,
                        workspace_id,
                        sync_run_id=None,
                    )
                    return

                await self._process_document_with_safety(
                    repository=repository,
                    embedding_repository=embedding_repository,
                    embedding_service=embedding_service,
                    drive_client=drive_client,
                    access_token=access_token,
                    workspace_id=workspace_id,
                    connection_id=document.connection_id,
                    file_id=document.drive_file_id,
                    project_id=document.project_id,
                    sync_run_id=None,
                    document=document,
                )
            finally:
                await drive_client.aclose()

    async def unpublish_document(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> None:
        """사용자 요청 발행 취소와 파생 데이터 정리를 수행한다."""
        async with self._session_factory() as session:
            repository = IntegrationRepository(session)
            embedding_repository = EmbeddingRepository(session)
            document = await repository.find_document_by_id(document_id, workspace_id)
            if document is None:
                return

            # 사전 무효화는 이후 실패·취소에도 기존 본문이 노출될 창을 닫는다.
            await self._invalidate_document_caches(embedding_repository, workspace_id)
            await embedding_repository.delete_by_source("external_document", document.id)
            # 사후 무효화는 삭제 사이 도착한 캐시행을 덮는다. 중복이 아니므로 하나를
            # 제거하면 이번 권한 회수 캐시 누출 회귀가 다시 발생한다.
            await self._invalidate_document_caches(embedding_repository, workspace_id)
            await repository.delete_document(document.id, workspace_id)
            await repository.commit()

    async def _process_document_with_safety(
        self,
        *,
        repository: IntegrationRepository,
        embedding_repository: EmbeddingRepository,
        embedding_service: EmbeddingService,
        drive_client: GoogleDriveClient,
        access_token: str,
        workspace_id: uuid.UUID,
        connection_id: uuid.UUID,
        file_id: str,
        project_id: uuid.UUID | None,
        sync_run_id: uuid.UUID | None,
        document: ExternalDocument | None,
    ) -> bool:
        """문서 하나를 fail-closed 규칙으로 처리하고 실패 여부를 반환한다."""
        try:
            await self._sync_document(
                repository=repository,
                embedding_repository=embedding_repository,
                embedding_service=embedding_service,
                drive_client=drive_client,
                access_token=access_token,
                workspace_id=workspace_id,
                connection_id=connection_id,
                file_id=file_id,
                project_id=project_id,
                sync_run_id=sync_run_id,
                document=document,
            )
            return False
        except _PURGE_ALLOWED_ERRORS as exc:
            document = document or await self._find_document_for_file(
                repository,
                connection_id,
                workspace_id,
                file_id,
            )
            await self._purge_document(
                repository,
                embedding_repository,
                document,
                workspace_id,
                exc,
                sync_run_id,
            )
            return True
        except DriveClientError as exc:
            document = document or await self._find_document_for_file(
                repository,
                connection_id,
                workspace_id,
                file_id,
            )
            if document is not None:
                await self._preserve_document_for_drive_error(
                    repository,
                    document,
                    workspace_id,
                    exc,
                    sync_run_id,
                )
            return True
        except Exception:
            document = document or await self._find_document_for_file(
                repository,
                connection_id,
                workspace_id,
                file_id,
            )
            if document is not None:
                await self._mark_document_failed(
                    repository,
                    document,
                    workspace_id,
                    sync_run_id,
                )
            return True

    async def _sync_document(
        self,
        *,
        repository: IntegrationRepository,
        embedding_repository: EmbeddingRepository,
        embedding_service: EmbeddingService,
        drive_client: GoogleDriveClient,
        access_token: str,
        workspace_id: uuid.UUID,
        connection_id: uuid.UUID,
        file_id: str,
        project_id: uuid.UUID | None,
        sync_run_id: uuid.UUID | None,
        document: ExternalDocument | None,
    ) -> None:
        if document is None:
            document = await self._find_document_for_file(
                repository,
                connection_id,
                workspace_id,
                file_id,
            )

        if document is not None and document.project_id is None:
            existing_chunk_project_ids = await embedding_repository.find_chunk_project_ids(
                "external_document",
                document.id,
            )
            if existing_chunk_project_ids:
                # 미지정 문서의 청크 0개는 Drive metadata·본문 변화와 무관한 DB 불변식이다.
                # metadata/export 실패와 조기 반환 이전에 cache를 삭제 전후로 무효화해
                # anti-join fail-open으로 레거시 본문이 남지 않게 한다.
                await self._invalidate_document_caches(
                    embedding_repository,
                    document.workspace_id,
                )
                await embedding_repository.delete_by_source(
                    "external_document",
                    document.id,
                )
                await self._invalidate_document_caches(
                    embedding_repository,
                    document.workspace_id,
                )

        metadata = await drive_client.get_file_metadata(access_token, file_id)
        is_supported_mime = is_supported_mime_type(metadata.mime_type)
        origin_url = (
            f"https://docs.google.com/document/d/{metadata.file_id}/edit"
            if is_supported_mime
            else f"https://drive.google.com/open?id={metadata.file_id}"
        )
        if not is_supported_mime:
            if document is None:
                document = ExternalDocument(
                    workspace_id=workspace_id,
                    connection_id=connection_id,
                    project_id=project_id,
                    sync_run_id=sync_run_id,
                    drive_file_id=metadata.file_id,
                    title=metadata.title,
                    mime_type=metadata.mime_type,
                    origin_url=origin_url,
                    revision_id=metadata.revision_id,
                    content_hash="",
                    plain_text="",
                    sync_status="processing",
                )
                await repository.create_document(document, workspace_id)
                await repository.commit()
            raise DriveUnsupportedMimeTypeError()

        # 동일 revision의 export 생략은 completed 문서에만 적용해 실패 상태의 복구 경로를 보존한다.
        if (
            document is not None
            and document.revision_id == metadata.revision_id
            and document.sync_status == "completed"
        ):
            await self._update_document_status(
                repository,
                document,
                workspace_id,
                sync_status="completed",
                sync_run_id=sync_run_id,
            )
            return

        # Drive revision은 문서를 되돌려도 새 상위 revision이 생기는 단조 값이다.
        # 더 작은 숫자 revision은 stale read이므로 상태와 무관하게 최신 본문을 덮어쓰지 않는다.
        if document is not None:
            try:
                stored_revision = int(document.revision_id)
                incoming_revision = int(metadata.revision_id)
            except ValueError:
                # Drive revision은 불투명 문자열일 수 있으므로 비교하지 못하면 갱신을 진행한다.
                pass
            else:
                if incoming_revision < stored_revision:
                    await self._update_document_status(
                        repository,
                        document,
                        workspace_id,
                        sync_status=document.sync_status,
                        sync_run_id=sync_run_id,
                    )
                    return

        exported = await drive_client.export_plain_text(
            access_token,
            file_id,
            metadata.mime_type,
        )
        last_synced_at = datetime.now(UTC).replace(tzinfo=None)

        if (
            document is not None
            and document.content_hash == exported.content_hash
            and document.sync_status == "completed"
        ):
            await self._update_document(
                repository,
                document,
                workspace_id,
                title=metadata.title,
                mime_type=metadata.mime_type,
                origin_url=origin_url,
                revision_id=metadata.revision_id,
                content_hash=exported.content_hash,
                plain_text=exported.plain_text,
                sync_status="completed",
                last_synced_at=last_synced_at,
                sync_run_id=sync_run_id,
            )
            return

        if document is None:
            document = ExternalDocument(
                workspace_id=workspace_id,
                connection_id=connection_id,
                project_id=project_id,
                sync_run_id=sync_run_id,
                drive_file_id=metadata.file_id,
                title=metadata.title,
                mime_type=metadata.mime_type,
                origin_url=origin_url,
                revision_id=metadata.revision_id,
                content_hash=exported.content_hash,
                plain_text=exported.plain_text,
                sync_status="processing",
            )
            await repository.create_document(document, workspace_id)
            await repository.commit()
        else:
            await self._update_document(
                repository,
                document,
                workspace_id,
                title=metadata.title,
                mime_type=metadata.mime_type,
                origin_url=origin_url,
                revision_id=metadata.revision_id,
                content_hash=exported.content_hash,
                plain_text=exported.plain_text,
                sync_status="processing",
                last_synced_at=None,
                sync_run_id=sync_run_id,
            )

        if document.project_id is not None:
            # 같은 세션의 실패 상태 commit이 미완료 청크 DELETE를 확정할 수 있으므로,
            # 청크 변형 전 cache를 먼저 비우고 commit해 노출 창을 닫는다.
            await self._invalidate_document_caches(
                embedding_repository,
                document.workspace_id,
            )
            await embedding_service.embed_external_document(
                document_id=document.id,
                workspace_id=workspace_id,
                source_workspace_id=document.workspace_id,
                project_id=document.project_id,
                title=metadata.title,
                origin_url=origin_url,
                plain_text=exported.plain_text,
            )
            # 동기화 중 생성된 cache도 옛 청크를 참조할 수 있어 사후 무효화도 유지한다.
            await self._invalidate_document_caches(
                embedding_repository,
                document.workspace_id,
            )
        await self._update_document_status(
            repository,
            document,
            workspace_id,
            sync_status="completed",
            sync_run_id=sync_run_id,
        )

    async def _purge_document(
        self,
        repository: IntegrationRepository,
        embedding_repository: EmbeddingRepository,
        document: ExternalDocument | None,
        workspace_id: uuid.UUID,
        exc: DriveClientError,
        sync_run_id: uuid.UUID | None,
    ) -> None:
        assert exc.allows_purge
        if document is None:
            return

        # 사전 무효화는 이후 실패·취소에도 기존 본문이 노출될 창을 닫는다.
        await self._invalidate_document_caches(embedding_repository, workspace_id)
        await embedding_repository.delete_by_source("external_document", document.id)
        # 사후 무효화는 삭제 사이 도착한 캐시행을 덮는다. 중복이 아니므로 하나를
        # 제거하면 이번 권한 회수 캐시 누출 회귀가 다시 발생한다.
        await self._invalidate_document_caches(embedding_repository, workspace_id)
        await embedding_repository.commit()
        if sync_run_id is None:
            await repository.purge_document_content(
                document.id,
                workspace_id,
                last_synced_at=datetime.now(UTC).replace(tzinfo=None),
            )
        else:
            await repository.purge_document_content(
                document.id,
                workspace_id,
                last_synced_at=datetime.now(UTC).replace(tzinfo=None),
                sync_run_id=sync_run_id,
            )
        await repository.commit()

    async def _preserve_document_for_drive_error(
        self,
        repository: IntegrationRepository,
        document: ExternalDocument,
        workspace_id: uuid.UUID,
        exc: DriveClientError,
        sync_run_id: uuid.UUID | None,
    ) -> None:
        if isinstance(exc, DriveReauthenticationRequiredError):
            sync_status = "reauth_required"
        elif isinstance(exc, DriveTemporaryError):
            sync_status = "stale"
        elif isinstance(exc, DriveUnsupportedMimeTypeError):
            sync_status = "failed"
        else:
            sync_status = "failed"
        await self._update_document_status(
            repository,
            document,
            workspace_id,
            sync_status=sync_status,
            sync_run_id=sync_run_id,
        )

    async def _mark_document_failed(
        self,
        repository: IntegrationRepository,
        document: ExternalDocument,
        workspace_id: uuid.UUID,
        sync_run_id: uuid.UUID | None,
    ) -> None:
        await self._update_document_status(
            repository,
            document,
            workspace_id,
            sync_status="failed",
            sync_run_id=sync_run_id,
        )

    async def _update_document_status(
        self,
        repository: IntegrationRepository,
        document: ExternalDocument,
        workspace_id: uuid.UUID,
        *,
        sync_status: str,
        sync_run_id: uuid.UUID | None,
    ) -> None:
        if sync_run_id is None:
            await repository.update_document_sync_status(
                document.id,
                workspace_id,
                sync_status=sync_status,
                last_synced_at=datetime.now(UTC).replace(tzinfo=None),
            )
        else:
            await repository.update_document_sync_status(
                document.id,
                workspace_id,
                sync_status=sync_status,
                last_synced_at=datetime.now(UTC).replace(tzinfo=None),
                sync_run_id=sync_run_id,
            )
        await repository.commit()

    async def _update_document(
        self,
        repository: IntegrationRepository,
        document: ExternalDocument,
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
        sync_run_id: uuid.UUID | None,
    ) -> None:
        if sync_run_id is None:
            await repository.update_document(
                document.id,
                workspace_id,
                title=title,
                mime_type=mime_type,
                origin_url=origin_url,
                revision_id=revision_id,
                content_hash=content_hash,
                plain_text=plain_text,
                sync_status=sync_status,
                last_synced_at=last_synced_at,
            )
        else:
            await repository.update_document(
                document.id,
                workspace_id,
                title=title,
                mime_type=mime_type,
                origin_url=origin_url,
                revision_id=revision_id,
                content_hash=content_hash,
                plain_text=plain_text,
                sync_status=sync_status,
                last_synced_at=last_synced_at,
                sync_run_id=sync_run_id,
            )
        await repository.commit()

    async def _invalidate_document_caches(
        self,
        embedding_repository: EmbeddingRepository,
        workspace_id: uuid.UUID,
    ) -> None:
        # ADR-026 D8의 사용자 요청 동기화는 저빈도이므로 캐시 효율보다 본문 교체와
        # 권한 회수의 정확성을 우선해 workspace 캐시를 전량 무효화한다.
        await embedding_repository.delete_caches(workspace_id, None)
        await embedding_repository.commit()

    async def _find_document_for_file(
        self,
        repository: IntegrationRepository,
        connection_id: uuid.UUID,
        workspace_id: uuid.UUID,
        file_id: str,
    ) -> ExternalDocument | None:
        document_id = await repository.find_document_id_by_drive_file_id(
            connection_id,
            workspace_id,
            file_id,
        )
        if document_id is None:
            return None
        return await repository.find_document_by_id(document_id, workspace_id)

    async def _finish_sync_run(
        self,
        repository: IntegrationRepository,
        sync_run_id: uuid.UUID,
        workspace_id: uuid.UUID,
        *,
        status: str,
        has_document_failure: bool = False,
    ) -> None:
        await repository.update_sync_run_status(
            sync_run_id,
            workspace_id,
            status=status,
            completed_at=datetime.now(UTC).replace(tzinfo=None),
            error_summary=(
                "일부 문서를 동기화하지 못했습니다."
                if has_document_failure
                else "동기화를 시작할 수 없습니다." if status == "failed" else None
            ),
        )
        await repository.commit()
