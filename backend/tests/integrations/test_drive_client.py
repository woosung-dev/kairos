"""Google Drive 저수준 클라이언트의 MockTransport 계약 테스트."""
import asyncio
from collections.abc import Awaitable, Callable, Iterator

import httpx
import pytest

from src.integrations.drive_client import (
    GOOGLE_DOC_MIME_TYPE,
    GoogleDriveClient,
)
from src.integrations.exceptions import (
    DriveClientError,
    DrivePermissionRevokedError,
    DriveReauthenticationRequiredError,
    DriveSourceMissingError,
    DriveTemporaryError,
    DriveUnsupportedMimeTypeError,
)
from src.services.ai_resilience import drive_breaker, reset_breakers_for_test


@pytest.fixture(autouse=True)
def _reset_drive_breaker() -> Iterator[None]:
    reset_breakers_for_test()
    yield
    reset_breakers_for_test()


def _metadata_response(
    request: httpx.Request,
    *,
    revision_id: str = "revision-1",
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "document-1",
            "name": "회의록",
            "mimeType": GOOGLE_DOC_MIME_TYPE,
            "headRevisionId": revision_id,
        },
        request=request,
    )


def _client(
    handler: (
        Callable[[httpx.Request], httpx.Response]
        | Callable[[httpx.Request], Awaitable[httpx.Response]]
    ),
) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_refresh_access_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/token"
        assert request.content == (
            b"client_id=client-id&client_secret=client-secret&grant_type=refresh_token"
            b"&refresh_token=refresh-token"
        )
        return httpx.Response(
            200,
            json={"access_token": "new-access-token"},
            request=request,
        )

    async with _client(handler) as http_client:
        client = GoogleDriveClient(http_client)
        access_token = await client.refresh_access_token(
            "refresh-token",
            client_id="client-id",
            client_secret="client-secret",
        )

    assert access_token == "new-access-token"


@pytest.mark.parametrize(
    ("status_code", "payload", "expected_error"),
    [
        (400, {"error": {}}, DriveReauthenticationRequiredError),
        (401, {"error": {}}, DriveReauthenticationRequiredError),
        (404, {"error": {}}, DriveReauthenticationRequiredError),
        (
            403,
            {"error": {"errors": [{"reason": "insufficientFilePermissions"}]}},
            DriveReauthenticationRequiredError,
        ),
        (429, {"error": {}}, DriveTemporaryError),
        (503, {"error": {}}, DriveTemporaryError),
    ],
    ids=("400", "401", "404", "permission-revoked-403", "429", "5xx"),
)
async def test_refresh_errors_never_allow_purge(
    status_code: int,
    payload: dict[str, object],
    expected_error: type[DriveClientError],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/token"
        return httpx.Response(status_code, json=payload, request=request)

    async with _client(handler) as http_client:
        client = GoogleDriveClient(http_client)
        with pytest.raises(expected_error) as exc_info:
            await client.refresh_access_token(
                "refresh-token",
                client_id="client-id",
                client_secret="client-secret",
            )

    assert exc_info.value.allows_purge is False


async def test_refresh_network_error_is_temporary_without_purge() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        raise httpx.ConnectError("mock connection failure", request=request)

    async with _client(handler) as http_client:
        client = GoogleDriveClient(http_client)
        with pytest.raises(DriveTemporaryError) as exc_info:
            await client.refresh_access_token(
                "refresh-token",
                client_id="client-id",
                client_secret="client-secret",
            )

    assert exc_info.value.allows_purge is False
    assert request_count == 1


async def test_get_metadata_and_export_google_doc_plain_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer access-token"
        if request.url.path == "/drive/v3/files/document-1":
            return _metadata_response(request)
        if request.url.path == "/drive/v3/files/document-1/export":
            assert request.url.params["mimeType"] == "text/plain"
            return httpx.Response(200, text="회의록 본문", request=request)
        raise AssertionError(f"예상하지 못한 요청: {request.url.path}")

    async with _client(handler) as http_client:
        client = GoogleDriveClient(http_client)
        metadata = await client.get_file_metadata("access-token", "document-1")
        exported = await client.export_plain_text(
            "access-token",
            "document-1",
            metadata.mime_type,
        )

    assert metadata.revision_id == "revision-1"
    assert exported.plain_text == "회의록 본문"
    assert exported.content_hash == "a62fd36dc1ae40459825a13cc0dccb964d00b774658b0fdfac81eee03c054b49"


async def test_unchanged_revision_and_content_hash_are_stable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/drive/v3/files/document-1":
            return _metadata_response(request, revision_id="revision-1")
        return httpx.Response(200, text="변경 없음", request=request)

    async with _client(handler) as http_client:
        client = GoogleDriveClient(http_client)
        first_metadata = await client.get_file_metadata("access-token", "document-1")
        first_export = await client.export_plain_text(
            "access-token",
            "document-1",
            first_metadata.mime_type,
        )
        second_metadata = await client.get_file_metadata("access-token", "document-1")
        second_export = await client.export_plain_text(
            "access-token",
            "document-1",
            second_metadata.mime_type,
        )

    assert second_metadata.revision_id == first_metadata.revision_id
    assert second_export.content_hash == first_export.content_hash


async def test_changed_revision_and_content_hash_are_detectable() -> None:
    metadata_requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal metadata_requests
        if request.url.path == "/drive/v3/files/document-1":
            metadata_requests += 1
            return _metadata_response(
                request,
                revision_id=f"revision-{metadata_requests}",
            )
        return httpx.Response(
            200,
            text=f"본문 {metadata_requests}",
            request=request,
        )

    async with _client(handler) as http_client:
        client = GoogleDriveClient(http_client)
        first_metadata = await client.get_file_metadata("access-token", "document-1")
        first_export = await client.export_plain_text(
            "access-token",
            "document-1",
            first_metadata.mime_type,
        )
        second_metadata = await client.get_file_metadata("access-token", "document-1")
        second_export = await client.export_plain_text(
            "access-token",
            "document-1",
            second_metadata.mime_type,
        )

    assert second_metadata.revision_id != first_metadata.revision_id
    assert second_export.content_hash != first_export.content_hash


async def test_404_is_confirmed_source_missing_and_allows_purge() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": {}}, request=request)

    async with _client(handler) as http_client:
        client = GoogleDriveClient(http_client)
        with pytest.raises(DriveSourceMissingError) as exc_info:
            await client.get_file_metadata("access-token", "document-1")

    assert exc_info.value.allows_purge is True


async def test_trashed_file_is_confirmed_source_missing_and_allows_purge() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"trashed": True},
            request=request,
        )

    async with _client(handler) as http_client:
        client = GoogleDriveClient(http_client)
        with pytest.raises(DriveSourceMissingError) as exc_info:
            await client.get_file_metadata("access-token", "document-1")

    assert exc_info.value.allows_purge is True


async def test_permission_revocation_reason_allows_purge() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "error": {
                    "errors": [{"reason": "insufficientFilePermissions"}],
                },
            },
            request=request,
        )

    async with _client(handler) as http_client:
        client = GoogleDriveClient(http_client)
        with pytest.raises(DrivePermissionRevokedError) as exc_info:
            await client.get_file_metadata("access-token", "document-1")

    assert exc_info.value.allows_purge is True


async def test_http_rate_limit_is_temporary() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {}}, request=request)

    async with _client(handler) as http_client:
        client = GoogleDriveClient(http_client)
        with pytest.raises(DriveTemporaryError) as exc_info:
            await client.get_file_metadata("access-token", "document-1")

    assert exc_info.value.allows_purge is False


@pytest.mark.parametrize("reason", ["rateLimitExceeded", "userRateLimitExceeded"])
async def test_403_rate_limit_reason_is_temporary(reason: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "error": {
                    "errors": [{"reason": reason}],
                },
            },
            request=request,
        )

    async with _client(handler) as http_client:
        client = GoogleDriveClient(http_client)
        with pytest.raises(DriveTemporaryError) as exc_info:
            await client.get_file_metadata("access-token", "document-1")

    assert exc_info.value.allows_purge is False


async def test_5xx_is_temporary() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="upstream unavailable", request=request)

    async with _client(handler) as http_client:
        client = GoogleDriveClient(http_client)
        with pytest.raises(DriveTemporaryError) as exc_info:
            await client.get_file_metadata("access-token", "document-1")

    assert exc_info.value.allows_purge is False


async def test_network_error_is_temporary_without_automatic_retry() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        raise httpx.ConnectError("mock connection failure", request=request)

    async with _client(handler) as http_client:
        client = GoogleDriveClient(http_client)
        with pytest.raises(DriveTemporaryError) as exc_info:
            await client.get_file_metadata("access-token", "document-1")

    assert exc_info.value.allows_purge is False
    assert request_count == 1


async def test_timeout_is_temporary() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.01)
        return _metadata_response(request)

    async with _client(handler) as http_client:
        client = GoogleDriveClient(http_client, timeout_sec=0.001)
        with pytest.raises(DriveTemporaryError) as exc_info:
            await client.get_file_metadata("access-token", "document-1")

    assert exc_info.value.allows_purge is False


async def test_401_requires_reauthentication_without_purge() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {}}, request=request)

    async with _client(handler) as http_client:
        client = GoogleDriveClient(http_client)
        with pytest.raises(DriveReauthenticationRequiredError) as exc_info:
            await client.get_file_metadata("access-token", "document-1")

    assert exc_info.value.allows_purge is False


async def test_unsupported_mime_type_is_permanent_but_not_purgeable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("지원하지 않는 MIME은 HTTP 요청을 보내면 안 됩니다.")

    async with _client(handler) as http_client:
        client = GoogleDriveClient(http_client)
        with pytest.raises(DriveUnsupportedMimeTypeError) as exc_info:
            await client.export_plain_text(
                "access-token",
                "document-1",
                "application/pdf",
            )

    assert exc_info.value.allows_purge is False


async def test_open_breaker_is_temporary_and_does_not_send_request() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(503, request=request)

    async with _client(handler) as http_client:
        client = GoogleDriveClient(http_client)
        for _ in range(drive_breaker.failure_threshold):
            with pytest.raises(DriveTemporaryError):
                await client.get_file_metadata("access-token", "document-1")

        with pytest.raises(DriveTemporaryError) as exc_info:
            await client.get_file_metadata("access-token", "document-1")

    assert exc_info.value.allows_purge is False
    assert request_count == drive_breaker.failure_threshold


async def test_unknown_403_fails_closed_with_reauthentication() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={"error": {"errors": [{"reason": "unknownReason"}]}},
            request=request,
        )

    async with _client(handler) as http_client:
        client = GoogleDriveClient(http_client)
        with pytest.raises(DriveReauthenticationRequiredError) as exc_info:
            await client.get_file_metadata("access-token", "document-1")

    assert exc_info.value.allows_purge is False


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {"message": "error key 없음"},
        {"error": {"errors": []}},
        {"error": {"errors": "not-a-list"}},
        {"error": {"errors": [{"reason": 123}]}},
    ],
    ids=("non-json", "error-key-missing", "empty-errors", "errors-not-list", "reason-not-string"),
)
async def test_malformed_403_body_fails_closed_without_purge(
    payload: dict[str, object] | None,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if payload is None:
            return httpx.Response(403, text="<html>forbidden</html>", request=request)
        return httpx.Response(403, json=payload, request=request)

    async with _client(handler) as http_client:
        client = GoogleDriveClient(http_client)
        with pytest.raises(DriveReauthenticationRequiredError) as exc_info:
            await client.get_file_metadata("access-token", "document-1")

    assert exc_info.value.allows_purge is False


async def test_error_messages_exclude_tokens_and_document_body() -> None:
    access_token = "access-token-secret"
    refresh_token = "refresh-token-secret"
    document_body = "document-body-secret"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/token":
            return httpx.Response(
                400,
                json={"error": {"message": refresh_token}},
                request=request,
            )
        return httpx.Response(503, text=document_body, request=request)

    async with _client(handler) as http_client:
        client = GoogleDriveClient(http_client)
        with pytest.raises(DriveTemporaryError) as document_exc_info:
            await client.get_file_metadata(access_token, "document-1")
        with pytest.raises(DriveReauthenticationRequiredError) as token_exc_info:
            await client.refresh_access_token(
                refresh_token,
                client_id="client-id-secret",
                client_secret="client-secret-secret",
            )

    message = f"{document_exc_info.value} {token_exc_info.value}"
    assert access_token not in message
    assert refresh_token not in message
    assert document_body not in message
