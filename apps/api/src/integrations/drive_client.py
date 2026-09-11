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
_GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
_RATE_LIMIT_REASONS = frozenset({"rateLimitExceeded", "userRateLimitExceeded"})
_PERMISSION_REVOKED_REASONS = frozenset({"insufficientFilePermissions"})

RequestFactory = Callable[[], Awaitable[httpx.Response]]


def is_supported_mime_type(mime_type: str) -> bool:
    """Google Docs plain-text export 지원 여부를 반환한다."""
    return mime_type == GOOGLE_DOC_MIME_TYPE


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

    async def aclose(self) -> None:
        """주입받은 HTTP transport를 닫는다."""
        await self._client.aclose()

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

    async def revoke_refresh_token(self, refresh_token: str) -> bool:
        """Google 에서 refresh token 을 폐기하고 성공 여부를 반환한다.

        연결 해제의 **best-effort 원격 단계**다. 예외를 던지지 않고 ``False`` 를
        반환한다 — Google 장애가 Kairos 연결 해제를 막으면, 권한 회수가 가장
        급한 순간에 그것을 못 하게 된다.

        ★circuit breaker 를 경유하지 않는다. Drive 원본 조회 실패로 열린 breaker
        때문에 권한 회수까지 차단되면 같은 문제가 생기므로, 여기서는
        ``with_drive_timeout`` (내부에서 ``drive_breaker.check()`` 를 한다) 대신
        timeout 만 직접 건다. 폐기 결과도 breaker 에 기록하지 않는다.
        """
        try:
            response = await asyncio.wait_for(
                self._client.post(
                    _GOOGLE_REVOKE_URL,
                    data={"token": refresh_token},
                ),
                timeout=self._timeout_sec,
            )
        except (asyncio.TimeoutError, httpx.RequestError):
            return False
        if response.is_success:
            return True
        # 이미 폐기·만료된 토큰에 Google 은 400 invalid_token 을 준다. 목표 상태가
        # 이미 달성돼 있으므로 성공으로 취급한다 (멱등).
        return (
            response.status_code == 400
            and self._oauth_error_code(response) == "invalid_token"
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
                params={"fields": "id,name,mimeType,version,trashed"},
            ),
        )
        payload = self._response_object(response)
        if payload.get("trashed") is True:
            raise DriveSourceMissingError()

        response_file_id = payload.get("id")
        title = payload.get("name")
        mime_type = payload.get("mimeType")
        # v0 지원 타입의 revision guard에는 version만 사용한다.
        # 근거 — Drive API v3 File 리소스 문서 (2026-07-31 조회):
        #   headRevisionId "is currently only available for files with binary content"
        #     → Google Docs에는 제공되지 않는다.
        #   version "A monotonically increasing version number for the file."
        # 불투명 문자열이 숫자 version을 가리면 단조성 비교가 무력해지므로 fallback을 두지 않는다.
        revision = payload.get("version")
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

        if not is_supported_mime_type(mime_type):
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
    def _oauth_error_code(response: httpx.Response) -> str | None:
        """OAuth 엔드포인트의 **평면** 오류 코드를 읽는다.

        ``{"error": "invalid_token"}`` 형태로, Drive API 의 중첩
        ``{"error": {"errors": [{"reason": ...}]}}`` 와 스키마가 다르다.
        그래서 ``_google_error_reasons`` 와 공유하지 않는다 — 한쪽 파서로
        양쪽을 읽으면 조용히 ``None`` 이 되어 분기가 뭉개진다.
        """
        try:
            payload = response.json()
        except ValueError:
            return None
        if not isinstance(payload, dict):
            return None
        error = payload.get("error")
        return error if isinstance(error, str) else None

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
