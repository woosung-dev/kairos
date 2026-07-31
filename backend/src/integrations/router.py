"""Google Drive integrations HTTP 경계."""
import base64
import hashlib
import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Response,
)
from fastapi.responses import RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.rbac import require_owner, require_viewer
from src.common.crypto import decrypt_string, encrypt_string
from src.common.database import get_async_session
from src.common.exceptions import EncryptionDecryptionError, EncryptionError
from src.common.visibility import ADMIN_BYPASS_ROLES, Access, decide_project_access
from src.core.config import get_settings
from src.integrations.dependencies import (
    get_google_drive_client,
    get_google_drive_sync_pipeline_service,
    get_integration_project_repository,
    get_integration_repository,
    get_integration_service,
)
from src.integrations.drive_client import GoogleDriveClient
from src.integrations.exceptions import (
    DriveClientError,
    ExternalDocumentNotFoundError,
    IntegrationConnectionNotFoundError,
    IntegrationEncryptionError,
    IntegrationSyncRunNotFoundError,
)
from src.integrations.models import IntegrationSyncRun
from src.integrations.pipeline_service import GoogleDriveSyncPipelineService
from src.integrations.repository import IntegrationRepository
from src.integrations.schemas import (
    AuthorizationUrlResponse,
    ExternalDocumentDetailResponse,
    ImportExternalDocumentsRequest,
    IntegrationConnectionResponse,
    IntegrationSyncRunResponse,
    SyncRunCreatedResponse,
)
from src.integrations.service import IntegrationService
from src.projects.exceptions import ProjectNotFoundError
from src.projects.repository import ProjectRepository
from src.workspaces.models import WorkspaceMember
from src.workspaces.repository import WorkspaceRepository

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}",
    tags=["integrations"],
)
public_router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])

_GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"
_OAUTH_STATE_TTL = timedelta(minutes=10)


@dataclass(frozen=True)
class _OAuthState:
    workspace_id: uuid.UUID
    requester_user_id: uuid.UUID
    nonce: str
    code_verifier: str


def _create_code_verifier() -> str:
    return secrets.token_urlsafe(48)


def _code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def _encode_oauth_state(
    workspace_id: uuid.UUID,
    requester_user_id: uuid.UUID,
    code_verifier: str,
) -> str:
    payload = {
        "workspace_id": str(workspace_id),
        "requester_user_id": str(requester_user_id),
        "nonce": secrets.token_urlsafe(24),
        "code_verifier": code_verifier,
        "exp": int((datetime.now(UTC) + _OAUTH_STATE_TTL).timestamp()),
    }
    try:
        return encrypt_string(json.dumps(payload, separators=(",", ":")))
    except EncryptionError as exc:
        raise IntegrationEncryptionError() from exc


def _invalid_oauth_state() -> HTTPException:
    return HTTPException(status_code=400, detail="유효하지 않거나 만료된 OAuth state입니다")


def _decode_oauth_state(state: str) -> _OAuthState:
    try:
        payload = json.loads(decrypt_string(state))
        if not isinstance(payload, dict):
            raise ValueError
        exp = payload["exp"]
        nonce = payload["nonce"]
        code_verifier = payload["code_verifier"]
        workspace_id = payload["workspace_id"]
        requester_user_id = payload["requester_user_id"]
        if (
            not isinstance(exp, int)
            or isinstance(exp, bool)
            or exp <= int(datetime.now(UTC).timestamp())
            or not isinstance(nonce, str)
            or not nonce
            or not isinstance(code_verifier, str)
            or not code_verifier
            or not isinstance(workspace_id, str)
            or not isinstance(requester_user_id, str)
        ):
            raise ValueError
        return _OAuthState(
            workspace_id=uuid.UUID(workspace_id),
            requester_user_id=uuid.UUID(requester_user_id),
            nonce=nonce,
            code_verifier=code_verifier,
        )
    except EncryptionDecryptionError as exc:
        # Fernet은 키 회전과 변조를 모두 InvalidToken으로만 알려 구분할 수 없다.
        # callback state는 둘 다 유효하지 않은 state(400)로 처리한다.
        raise _invalid_oauth_state() from exc
    except EncryptionError as exc:
        raise IntegrationEncryptionError() from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise _invalid_oauth_state() from exc


def _oauth_credentials() -> tuple[str, str]:
    settings = get_settings()
    client_id = settings.google_oauth_client_id
    client_secret = settings.google_oauth_client_secret
    if client_id is None or client_secret is None:
        raise HTTPException(status_code=503, detail="Google OAuth 설정이 필요합니다")
    return client_id, client_secret.get_secret_value()


async def _verify_external_document_visibility(
    *,
    document_project_id: uuid.UUID | None,
    workspace_id: uuid.UUID,
    member: WorkspaceMember,
    project_repository: ProjectRepository,
) -> None:
    if document_project_id is None or member.role in ADMIN_BYPASS_ROLES:
        return
    project = await project_repository.find_by_id(document_project_id, workspace_id)
    if project is None:
        raise ExternalDocumentNotFoundError()
    decision = decide_project_access(project, member.user_id)
    if decision is Access.DENY:
        raise ExternalDocumentNotFoundError()
    if decision is Access.NEED_MEMBERSHIP and not await project_repository.is_member(
        document_project_id,
        member.user_id,
        workspace_id,
    ):
        raise ExternalDocumentNotFoundError()


@router.post(
    "/integrations/google-drive/authorize",
    response_model=AuthorizationUrlResponse,
)
async def authorize_google_drive(
    workspace_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_owner),
) -> AuthorizationUrlResponse:
    client_id, _ = _oauth_credentials()
    settings = get_settings()
    code_verifier = _create_code_verifier()
    state = _encode_oauth_state(workspace_id, member.user_id, code_verifier)
    authorization_url = f"{_GOOGLE_AUTHORIZE_URL}?{urlencode({
        'client_id': client_id,
        'redirect_uri': settings.google_oauth_redirect_uri,
        'response_type': 'code',
        'scope': _GOOGLE_DRIVE_SCOPE,
        'state': state,
        'code_challenge': _code_challenge(code_verifier),
        'code_challenge_method': 'S256',
        'access_type': 'offline',
        'prompt': 'consent',
    })}"
    return AuthorizationUrlResponse(authorization_url=authorization_url)


@public_router.get("/google-drive/callback", name="google_drive_callback")
async def google_drive_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    service: IntegrationService = Depends(get_integration_service),
    drive_client: GoogleDriveClient = Depends(get_google_drive_client),
) -> RedirectResponse:
    if not code or not state:
        raise _invalid_oauth_state()
    oauth_state = _decode_oauth_state(state)
    workspace_repository = WorkspaceRepository(session)
    member = await workspace_repository.find_member(
        oauth_state.workspace_id,
        oauth_state.requester_user_id,
    )
    if member is None or member.role != "owner":
        raise HTTPException(status_code=403, detail="워크스페이스 owner 권한이 필요합니다")

    client_id, client_secret = _oauth_credentials()
    try:
        token = await drive_client.exchange_authorization_code(
            code,
            oauth_state.code_verifier,
            get_settings().google_oauth_redirect_uri,
            client_id=client_id,
            client_secret=client_secret,
        )
    except DriveClientError as exc:
        raise HTTPException(
            status_code=400,
            detail="Google OAuth 인증을 완료할 수 없습니다",
        ) from exc

    token_expires_at = (
        datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=token.expires_in)
        if token.expires_in is not None
        else None
    )
    await service.connect_or_reauthorize(
        workspace_id=oauth_state.workspace_id,
        authorized_by_id=oauth_state.requester_user_id,
        refresh_token=token.refresh_token,
        scope=_GOOGLE_DRIVE_SCOPE,
        token_expires_at=token_expires_at,
    )
    settings = get_settings()
    return RedirectResponse(
        url=f"{settings.frontend_url.rstrip('/')}/settings?tab=integrations",
        status_code=302,
    )


@router.get(
    "/integrations/google-drive",
    response_model=IntegrationConnectionResponse | None,
)
async def get_google_drive_connection(
    workspace_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_owner),
    service: IntegrationService = Depends(get_integration_service),
) -> IntegrationConnectionResponse | None:
    connection = await service.get_connection_by_provider(workspace_id, "google_drive")
    if connection is None:
        return None
    return IntegrationConnectionResponse.model_validate(connection)


@router.post(
    "/integrations/google-drive/documents",
    response_model=SyncRunCreatedResponse,
    status_code=202,
)
async def import_google_drive_documents(
    workspace_id: uuid.UUID,
    data: ImportExternalDocumentsRequest,
    background_tasks: BackgroundTasks,
    member: WorkspaceMember = Depends(require_owner),
    service: IntegrationService = Depends(get_integration_service),
    repository: IntegrationRepository = Depends(get_integration_repository),
    project_repository: ProjectRepository = Depends(get_integration_project_repository),
    pipeline: GoogleDriveSyncPipelineService = Depends(
        get_google_drive_sync_pipeline_service
    ),
) -> SyncRunCreatedResponse:
    connection = await service.get_connection_by_provider(workspace_id, "google_drive")
    if connection is None:
        raise IntegrationConnectionNotFoundError()
    if data.project_id is not None and await project_repository.find_by_id(
        data.project_id,
        workspace_id,
    ) is None:
        raise ProjectNotFoundError()

    sync_run = IntegrationSyncRun(
        workspace_id=workspace_id,
        connection_id=connection.id,
        requested_by_id=member.user_id,
    )
    await repository.create_sync_run(sync_run, workspace_id)
    await repository.commit()
    background_tasks.add_task(
        pipeline.import_documents,
        sync_run.id,
        workspace_id,
        connection.id,
        data.file_ids,
        data.project_id,
    )
    return SyncRunCreatedResponse(sync_run_id=sync_run.id)


@router.get(
    "/integrations/sync-runs/{sync_run_id}",
    response_model=IntegrationSyncRunResponse,
)
async def get_integration_sync_run(
    workspace_id: uuid.UUID,
    sync_run_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_owner),
    service: IntegrationService = Depends(get_integration_service),
) -> IntegrationSyncRunResponse:
    sync_run = await service.get_sync_run(sync_run_id, workspace_id)
    if sync_run is None:
        raise IntegrationSyncRunNotFoundError()
    documents = await service.list_documents_by_sync_run(sync_run_id, workspace_id)
    return IntegrationSyncRunResponse(
        id=sync_run.id,
        status=sync_run.status,
        started_at=sync_run.started_at,
        completed_at=sync_run.completed_at,
        error_summary=sync_run.error_summary,
        documents=documents,
    )


@router.post(
    "/integrations/google-drive/documents/{document_id}/sync",
    status_code=202,
)
async def resync_google_drive_document(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    member: WorkspaceMember = Depends(require_owner),
    service: IntegrationService = Depends(get_integration_service),
    pipeline: GoogleDriveSyncPipelineService = Depends(
        get_google_drive_sync_pipeline_service
    ),
) -> Response:
    if await service.get_document(document_id, workspace_id) is None:
        raise ExternalDocumentNotFoundError()
    background_tasks.add_task(pipeline.resync_document, document_id, workspace_id)
    return Response(status_code=202)


@router.delete("/integrations/google-drive/documents/{document_id}", status_code=204)
async def unpublish_google_drive_document(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_owner),
    service: IntegrationService = Depends(get_integration_service),
    pipeline: GoogleDriveSyncPipelineService = Depends(
        get_google_drive_sync_pipeline_service
    ),
) -> None:
    if await service.get_document(document_id, workspace_id) is None:
        raise ExternalDocumentNotFoundError()
    await pipeline.unpublish_document(document_id, workspace_id)


@router.get(
    "/external-documents/{document_id}",
    response_model=ExternalDocumentDetailResponse,
)
async def get_external_document(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_viewer),
    service: IntegrationService = Depends(get_integration_service),
    project_repository: ProjectRepository = Depends(get_integration_project_repository),
) -> ExternalDocumentDetailResponse:
    document = await service.get_document(document_id, workspace_id)
    if document is None:
        raise ExternalDocumentNotFoundError()
    await _verify_external_document_visibility(
        document_project_id=document.project_id,
        workspace_id=workspace_id,
        member=member,
        project_repository=project_repository,
    )
    return ExternalDocumentDetailResponse.model_validate(document)
