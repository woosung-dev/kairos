"""Google Drive API의 읽기 전용 저수준 클라이언트."""
import asyncio
import hashlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import quote

import httpx

from src.integrations.exceptions import (
    DrivePermissionRevokedError,
    DriveReauthenticationRequiredError,
    DriveSourceMissingError,
    DriveTemporaryError,
    DriveUnsupportedMimeTypeError,
)
from src.services.ai_resilience import (
    CircuitBreakerOpen,
    DRIVE_TIMEOUT_SEC,
    drive_breaker,
    with_drive_timeout,
)

GOOGLE_DOC_MIME_TYPE = "application/vnd.google-apps.document"

_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
_RATE_LIMIT_REASONS = frozenset({"rateLimitExceeded", "userRateLimitExceeded"})
_PERMISSION_REVOKED_REASONS = frozenset({"insufficientFilePermissions"})

RequestFactory = Callable[[], Awaitable[httpx.Response]]


@dataclass(frozen=True)
class DriveFileMetadata:
    """동기화 변경 감지에 필요한 Drive 파일 메타데이터."""

    file_id: str
    title: str
    mime_type: str
    revision_id: str


@dataclass(frozen=True)
class DriveExport:
    """Google Docs 평문 export와 그 내용 해시."""

    plain_text: str
    content_hash: str


@dataclass(frozen=True)
class GoogleAuthorizationCodeToken:
    """인가 코드 교환 뒤 연결 저장에 필요한 최소 토큰 정보."""

    refresh_token: str
    expires_in: int | None


class _TransientDriveResponse(Exception):
    """breaker에 기록해야 할 HTTP 응답을 내부적으로 전달한다."""

    def __init__(self, response: httpx.Response) -> None:
        self.response = response


class GoogleDriveClient:
    """주입된 ``httpx.AsyncClient``로만 Google Drive를 호출한다.

    호출자는 transport를 포함한 ``AsyncClient`` 수명주기를 관리한다. 이 경계는
    자동 재시도를 하지 않고, 원본 purge가 가능한 오류만 명시적으로 구분한다.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        timeout_sec: float = DRIVE_TIMEOUT_SEC,
    ) -> None:
        self._client = client
        self._timeout_sec = timeout_sec

    async def refresh_access_token(
        self,
        refresh_token: str,
        *,
        client_id: str,
        client_secret: str,
    ) -> str:
        """OAuth refresh token으로 새 access token을 얻는다."""

        response = await self._request(
            lambda: self._client.post(
                _GOOGLE_TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            ),
            is_token_refresh=True,
        )
        payload = self._response_object(response)
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise DriveReauthenticationRequiredError()
        return access_token

    async def exchange_authorization_code(
        self,
        code: str,
        code_verifier: str,
        redirect_uri: str,
        *,
        client_id: str,
        client_secret: str,
    ) -> GoogleAuthorizationCodeToken:
        """PKCE authorization code를 연결용 refresh token으로 교환한다."""

        response = await self._request(
            lambda: self._client.post(
                _GOOGLE_TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "code_verifier": code_verifier,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            ),
            is_token_refresh=True,
        )
        payload = self._response_object(response)
        refresh_token = payload.get("refresh_token")
        expires_in = payload.get("expires_in")
        if not isinstance(refresh_token, str) or not refresh_token:
            raise DriveReauthenticationRequiredError()
        if not isinstance(expires_in, int) or isinstance(expires_in, bool):
            expires_in = None
        return GoogleAuthorizationCodeToken(
            refresh_token=refresh_token,
            expires_in=expires_in,
        )

    async def get_file_metadata(
        self,
        access_token: str,
        file_id: str,
    ) -> DriveFileMetadata:
        """파일의 제목, MIME, revision을 조회한다."""

        response = await self._request(
            lambda: self._client.get(
                self._file_url(file_id),
                headers=self._authorization_headers(access_token),
                params={"fields": "id,name,mimeType,headRevisionId,version,trashed"},
            ),
        )
        payload = self._response_object(response)
        if payload.get("trashed") is True:
            raise DriveSourceMissingError()

        response_file_id = payload.get("id")
        title = payload.get("name")
        mime_type = payload.get("mimeType")
        revision = payload.get("headRevisionId") or payload.get("version")
        if (
            not isinstance(response_file_id, str)
            or not response_file_id
            or not isinstance(title, str)
            or not isinstance(mime_type, str)
            or not isinstance(revision, (str, int))
        ):
            raise DriveTemporaryError()

        return DriveFileMetadata(
            file_id=response_file_id,
            title=title,
            mime_type=mime_type,
            revision_id=str(revision),
        )

    async def export_plain_text(
        self,
        access_token: str,
        file_id: str,
        mime_type: str,
    ) -> DriveExport:
        """Google Docs 원본만 ``text/plain`` 형식으로 export한다."""

        if mime_type != GOOGLE_DOC_MIME_TYPE:
            raise DriveUnsupportedMimeTypeError()

        response = await self._request(
            lambda: self._client.get(
                f"{self._file_url(file_id)}/export",
                headers=self._authorization_headers(access_token),
                params={"mimeType": "text/plain"},
            ),
        )
        plain_text = response.text
        return DriveExport(
            plain_text=plain_text,
            content_hash=hashlib.sha256(plain_text.encode()).hexdigest(),
        )

    async def _request(
        self,
        request_factory: RequestFactory,
        *,
        is_token_refresh: bool = False,
    ) -> httpx.Response:
        try:
            # breaker가 열린 경우 coroutine을 만들기 전에 차단한다.
            drive_breaker.check()
            response = await with_drive_timeout(
                self._send_with_breaker(request_factory),
                timeout_sec=self._timeout_sec,
            )
        except CircuitBreakerOpen as exc:
            raise DriveTemporaryError() from exc
        except _TransientDriveResponse as exc:
            raise self._classify_error(
                exc.response,
                is_token_refresh=is_token_refresh,
            ) from exc
        except (asyncio.TimeoutError, httpx.RequestError) as exc:
            raise DriveTemporaryError() from exc

        if response.is_error:
            raise self._classify_error(response, is_token_refresh=is_token_refresh)
        return response

    async def _send_with_breaker(
        self,
        request_factory: RequestFactory,
    ) -> httpx.Response:
        response = await request_factory()
        if self._is_transient_response(response):
            raise _TransientDriveResponse(response)
        return response

    @staticmethod
    def _authorization_headers(access_token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {access_token}"}

    @staticmethod
    def _file_url(file_id: str) -> str:
        return f"{_DRIVE_FILES_URL}/{quote(file_id, safe='')}"

    @staticmethod
    def _response_object(response: httpx.Response) -> dict[str, object]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise DriveTemporaryError() from exc
        if not isinstance(payload, dict):
            raise DriveTemporaryError()
        return payload

    @classmethod
    def _is_transient_response(cls, response: httpx.Response) -> bool:
        return (
            response.status_code == 429
            or response.status_code >= 500
            or (
                response.status_code == 403
                and bool(_RATE_LIMIT_REASONS & cls._google_error_reasons(response))
            )
        )

    @classmethod
    def _classify_error(
        cls,
        response: httpx.Response,
        *,
        is_token_refresh: bool,
    ) -> Exception:
        if is_token_refresh:
            # OAuth endpoint는 Drive 원본을 식별하지 못하므로 purge 가능 예외를 만들지 않는다.
            if (
                response.status_code == 429
                or response.status_code >= 500
                or (
                    response.status_code == 403
                    and bool(
                        _RATE_LIMIT_REASONS
                        & cls._google_error_reasons(response)
                    )
                )
            ):
                return DriveTemporaryError()
            return DriveReauthenticationRequiredError()
        if response.status_code == 404:
            return DriveSourceMissingError()
        if response.status_code == 401:
            return DriveReauthenticationRequiredError()
        if response.status_code == 403:
            reasons = cls._google_error_reasons(response)
            if _RATE_LIMIT_REASONS & reasons:
                return DriveTemporaryError()
            if _PERMISSION_REVOKED_REASONS & reasons:
                return DrivePermissionRevokedError()
            return DriveReauthenticationRequiredError()
        return DriveTemporaryError()

    @staticmethod
    def _google_error_reasons(response: httpx.Response) -> frozenset[str]:
        try:
            payload = response.json()
        except ValueError:
            return frozenset()
        if not isinstance(payload, dict):
            return frozenset()

        error = payload.get("error")
        if not isinstance(error, dict):
            return frozenset()
        errors = error.get("errors")
        if not isinstance(errors, list):
            return frozenset()

        return frozenset(
            reason
            for item in errors
            if isinstance(item, dict)
            and isinstance(reason := item.get("reason"), str)
        )
