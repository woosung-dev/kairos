# backend/tests/test_upload_proxy.py
"""업로드 프록시 엔드포인트 테스트 — R2 CORS 우회.

Regression: ISSUE-R2-CORS-001 — 브라우저 직접 R2 PUT이 CORS로 차단됨.
Found by /qa on 2026-05-12.
Fix: POST /workspaces/{wid}/upload/file 로 백엔드 경유 업로드.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.auth.rbac import require_member
from src.common.database import get_async_session
from src.main import app
from src.workspaces.models import WorkspaceMember

ALLOWED_ORIGIN = "http://localhost:3000"
WORKSPACE_ID = uuid.uuid4()

# Sprint 25 polish (F3 fix): T-SEC-3 binary signature fail-closed 로 인해
# fake bytes 는 415. 정합 ftyp 헤더 (audio/mp4 magic) 로 교체.
VALID_MP4_BYTES = b"\x00\x00\x00\x20ftypM4A \x00\x00\x00\x00M4A mp42isom\x00\x00\x00\x00" + b"\x00" * 64


@pytest_asyncio.fixture
async def authed_client():
    mock_session = AsyncMock()
    mock_user = MagicMock(spec=User)
    mock_user.id = uuid.uuid4()
    mock_member = MagicMock(spec=WorkspaceMember)
    mock_member.role = "member"
    app.dependency_overrides[get_async_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_member] = lambda: mock_member
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_upload_file_proxy_endpoint_exists(authed_client):
    """POST /workspaces/{wid}/upload/file 엔드포인트가 존재해야 한다.

    Regression: ISSUE-R2-CORS-001 — 브라우저 CORS 차단 우회용 프록시.
    """
    with patch(
        "src.upload.router.R2Service.upload_file_bytes",
        new_callable=AsyncMock,
        return_value=f"uploads/{uuid.uuid4()}/test.m4a",
    ):
        response = await authed_client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/upload/file",
            files={"file": ("test.m4a", VALID_MP4_BYTES, "audio/mp4")},
            headers={"Origin": ALLOWED_ORIGIN},
        )

    # 404가 아닌 응답이 와야 함 (엔드포인트 존재 확인)
    assert response.status_code != 404, (
        "POST /upload/file 엔드포인트가 없습니다. "
        "R2 CORS 문제 우회를 위해 백엔드 프록시 업로드 엔드포인트를 추가해야 합니다."
    )
    assert response.status_code == 201
    data = response.json()
    assert "fileKey" in data, f"fileKey가 응답에 없음: {data}"


@pytest.mark.asyncio
async def test_upload_file_proxy_returns_file_key(authed_client):
    """프록시 업로드 성공 시 file_key를 반환해야 한다."""
    expected_file_key = f"uploads/{uuid.uuid4()}/meeting.m4a"
    with patch(
        "src.upload.router.R2Service.upload_file_bytes",
        new_callable=AsyncMock,
        return_value=expected_file_key,
    ):
        response = await authed_client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/upload/file",
            files={"file": ("meeting.m4a", VALID_MP4_BYTES, "audio/mp4")},
        )

    assert response.status_code == 201
    assert response.json()["fileKey"] == expected_file_key


@pytest.mark.asyncio
async def test_upload_file_proxy_requires_file(authed_client):
    """파일 없이 요청 시 422를 반환해야 한다."""
    response = await authed_client.post(
        f"/api/v1/workspaces/{WORKSPACE_ID}/upload/file",
        # 파일 없음
    )
    assert response.status_code == 422
