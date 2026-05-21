# T-SEC-3 BUG-SENTINEL-003 upload validation 회귀 테스트
"""
Sprint 25 T-SEC-3 — upload 입력 검증.

배경: Multi-Agent QA 2026-05-21 Sentinel은 upload endpoint에 size/MIME/확장자
검증 부재를 P1로 등재. 사용자/디스크/R2 자원 남용 + 위장 MIME으로 인한
다운스트림 STT/AI 파이프라인 오작동 가능성.

검증 매트릭스:
  - test_upload_rejects_empty_file       → 400 (빈 파일)
  - test_upload_rejects_oversize         → 413 (size 초과)
  - test_upload_rejects_unsupported_mime → 415 (image/png 등 비허용)
  - test_upload_rejects_extension_mismatch → 415 (확장자/MIME 불일치)
  - test_upload_rejects_content_mismatch → 415 (선언 MIME과 실 signature 불일치)
  - test_upload_accepts_valid_audio      → 201 (정상 audio/mp4 + .m4a + ftyp)
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
from src.upload.dependencies import get_upload_validator
from src.upload.service import UploadValidator
from src.workspaces.models import WorkspaceMember

WORKSPACE_ID = uuid.uuid4()

# 1KB 한도 — 테스트용 작은 상한
TEST_MAX_BYTES = 1024

# 정상 audio/mp4 signature (offset 4-8 == "ftyp")
VALID_MP4_BYTES = b"\x00\x00\x00\x20ftypM4A \x00\x00\x00\x00M4A mp42isom\x00\x00\x00\x00" + b"\x00" * 64


@pytest_asyncio.fixture
async def authed_client():
    """인증 + RBAC mock 클라이언트. 검증기는 TEST_MAX_BYTES로 강제."""
    mock_session = AsyncMock()
    mock_user = MagicMock(spec=User)
    mock_user.id = uuid.uuid4()
    mock_member = MagicMock(spec=WorkspaceMember)
    mock_member.role = "member"
    app.dependency_overrides[get_async_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_member] = lambda: mock_member
    app.dependency_overrides[get_upload_validator] = lambda: UploadValidator(
        max_bytes=TEST_MAX_BYTES,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_upload_rejects_empty_file(authed_client):
    """빈 파일(0byte) → 400."""
    response = await authed_client.post(
        f"/api/v1/workspaces/{WORKSPACE_ID}/upload/file",
        files={"file": ("empty.m4a", b"", "audio/mp4")},
    )
    assert response.status_code == 400, response.text
    assert "빈" in response.json().get("detail", "") or "empty" in response.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_upload_rejects_oversize(authed_client):
    """size 초과 → 413."""
    oversized = b"\x00" * (TEST_MAX_BYTES + 1)
    response = await authed_client.post(
        f"/api/v1/workspaces/{WORKSPACE_ID}/upload/file",
        files={"file": ("big.m4a", oversized, "audio/mp4")},
    )
    assert response.status_code == 413, response.text


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_mime(authed_client):
    """비허용 MIME (image/png) → 415."""
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32  # PNG magic
    response = await authed_client.post(
        f"/api/v1/workspaces/{WORKSPACE_ID}/upload/file",
        files={"file": ("photo.png", png_bytes, "image/png")},
    )
    assert response.status_code == 415, response.text


@pytest.mark.asyncio
async def test_upload_rejects_extension_mismatch(authed_client):
    """확장자(.png)와 declared MIME(audio/mp4) 불일치 → 415."""
    # MP4 signature를 가졌어도 확장자가 .png면 reject (사용자 혼동/위장 방지)
    response = await authed_client.post(
        f"/api/v1/workspaces/{WORKSPACE_ID}/upload/file",
        files={"file": ("audio.png", VALID_MP4_BYTES, "audio/mp4")},
    )
    assert response.status_code == 415, response.text


@pytest.mark.asyncio
async def test_upload_rejects_content_mismatch(authed_client):
    """declared MIME(audio/mp4) 인데 실 content는 PDF magic → 415."""
    pdf_bytes = b"%PDF-1.4\n%fake binary data\n" + b"\x00" * 64
    response = await authed_client.post(
        f"/api/v1/workspaces/{WORKSPACE_ID}/upload/file",
        files={"file": ("audio.m4a", pdf_bytes, "audio/mp4")},
    )
    assert response.status_code == 415, response.text


@pytest.mark.asyncio
async def test_upload_accepts_valid_audio(authed_client):
    """정상 audio/mp4 + .m4a 확장자 + ftyp signature → 201."""
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

    assert response.status_code == 201, response.text
    assert response.json()["fileKey"] == expected_file_key


# ── Sprint 25 polish (codex + agy review fix) — 5 추가 회귀 가드 ──


@pytest.mark.asyncio
async def test_presigned_url_rejects_unsupported_mime(authed_client):
    """F1 (agy): /presigned-url 가 unsupported MIME 차단 (이전엔 bypass)."""
    response = await authed_client.post(
        f"/api/v1/workspaces/{WORKSPACE_ID}/upload/presigned-url",
        json={"filename": "photo.png", "contentType": "image/png"},
    )
    assert response.status_code == 415, response.text


@pytest.mark.asyncio
async def test_presigned_url_rejects_extension_mismatch(authed_client):
    """F1 (agy): /presigned-url 확장자/MIME 정합 검증 (이전엔 bypass)."""
    response = await authed_client.post(
        f"/api/v1/workspaces/{WORKSPACE_ID}/upload/presigned-url",
        json={"filename": "audio.png", "contentType": "audio/mp4"},
    )
    assert response.status_code == 415, response.text


@pytest.mark.asyncio
async def test_presigned_url_accepts_valid_request(authed_client):
    """F1 (agy): 정상 filename + MIME → 200 (R2 mock)."""
    fake_url = "https://r2.example.com/presigned-put"
    fake_key = f"uploads/{uuid.uuid4()}/meeting.m4a"
    with patch(
        "src.upload.router.R2Service.get_presigned_upload_url",
        new_callable=AsyncMock,
        return_value={"upload_url": fake_url, "file_key": fake_key, "expires_in": 3600},
    ):
        response = await authed_client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/upload/presigned-url",
            json={"filename": "meeting.m4a", "contentType": "audio/mp4"},
        )
    assert response.status_code == 200, response.text
    assert response.json()["uploadUrl"] == fake_url


@pytest.mark.asyncio
async def test_upload_rejects_unknown_binary_signature(authed_client):
    """F3 (codex+agy): unknown binary signature 는 fail-closed (이전엔 통과).

    declared audio/mp4 + .m4a 확장자지만 ftyp/ID3/RIFF 등 알려진 audio signature
    가 전혀 없는 random bytes → 415. 이전엔 _is_signature_compatible(None, ...)
    가 True 였음.
    """
    random_bytes = b"\xde\xad\xbe\xef" * 32  # 128 byte, no audio magic
    response = await authed_client.post(
        f"/api/v1/workspaces/{WORKSPACE_ID}/upload/file",
        files={"file": ("noise.m4a", random_bytes, "audio/mp4")},
    )
    assert response.status_code == 415, response.text


@pytest.mark.asyncio
async def test_upload_proxy_accepts_valid_video_mp4(authed_client):
    """F-2A v2 (codex+agy 2차): proxy /file 에 실 video/mp4 bytes (ftyp) → 201.

    1차 polish 가 _is_signature_compatible 미수정으로 detected=audio/mp4 vs
    declared=video/mp4 ContentMismatchError → 415 였음. v2 보강으로 호환.
    """
    # VALID_MP4_BYTES 는 ftyp container — audio/mp4 또는 video/mp4 양쪽 호환
    expected_file_key = f"uploads/{uuid.uuid4()}/zoom-recording.mp4"
    with patch(
        "src.upload.router.R2Service.upload_file_bytes",
        new_callable=AsyncMock,
        return_value=expected_file_key,
    ):
        response = await authed_client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/upload/file",
            files={"file": ("zoom-recording.mp4", VALID_MP4_BYTES, "video/mp4")},
        )
    assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_upload_proxy_accepts_valid_video_webm(authed_client):
    """F-2A v2: proxy /file 에 실 video/webm bytes (EBML magic) → 201."""
    valid_webm_bytes = b"\x1a\x45\xdf\xa3" + b"\x00" * 128
    expected_file_key = f"uploads/{uuid.uuid4()}/screen.webm"
    with patch(
        "src.upload.router.R2Service.upload_file_bytes",
        new_callable=AsyncMock,
        return_value=expected_file_key,
    ):
        response = await authed_client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/upload/file",
            files={"file": ("screen.webm", valid_webm_bytes, "video/webm")},
        )
    assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_upload_proxy_accepts_valid_mov(authed_client):
    """F-2A v2: proxy /file 에 .mov (ftypqt) → 201."""
    valid_mov_bytes = b"\x00\x00\x00\x20ftypqt  \x00\x00\x00\x00qt  \x00\x00\x00\x00" + b"\x00" * 64
    expected_file_key = f"uploads/{uuid.uuid4()}/iphone-recording.mov"
    with patch(
        "src.upload.router.R2Service.upload_file_bytes",
        new_callable=AsyncMock,
        return_value=expected_file_key,
    ):
        response = await authed_client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/upload/file",
            files={"file": ("iphone-recording.mov", valid_mov_bytes, "video/quicktime")},
        )
    assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_presigned_url_accepts_video_mp4(authed_client):
    """F-2A (codex 2차): 브라우저가 .mp4 비디오 파일을 video/mp4 MIME 으로 전송.

    FE source-add-modal + new/page 가 video/* accept → 사용자 실 워크플로우
    회복. 이전 polish v1 에서 audio/* 만 화이트리스트 → 415 regression.
    """
    fake_url = "https://r2.example.com/presigned-video"
    fake_key = f"uploads/{uuid.uuid4()}/zoom-recording.mp4"
    with patch(
        "src.upload.router.R2Service.get_presigned_upload_url",
        new_callable=AsyncMock,
        return_value={"upload_url": fake_url, "file_key": fake_key, "expires_in": 3600},
    ):
        response = await authed_client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/upload/presigned-url",
            json={"filename": "zoom-recording.mp4", "contentType": "video/mp4"},
        )
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_presigned_url_accepts_video_webm(authed_client):
    """F-2A (codex 2차): .webm 파일은 video/webm 으로 종종 전송."""
    fake_key = f"uploads/{uuid.uuid4()}/screen.webm"
    with patch(
        "src.upload.router.R2Service.get_presigned_upload_url",
        new_callable=AsyncMock,
        return_value={"upload_url": "https://r2/x", "file_key": fake_key, "expires_in": 3600},
    ):
        response = await authed_client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/upload/presigned-url",
            json={"filename": "screen.webm", "contentType": "video/webm"},
        )
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_upload_rejects_heic_renamed_as_video_mp4(authed_client):
    """F-2A v3 (codex 3차 P2 fix): HEIC 이미지 (ftypheic) 가 .mp4 + video/mp4 로
    위장해도 brand allowlist 가 차단 (이전 v2 는 통과 bypass).

    HEIC 는 ftyp 박스 공유 (ISO-BMFF). v2 의 collapse 가 모든 non-qt ftyp 를
    audio/mp4 로 mapping → audio/mp4 ↔ video/mp4 container parity 통과 → bypass.
    v3 는 MP4 brand allowlist 로 image brand (heic/heix/mif1/avif/avis 등) 제외.
    """
    # HEIC 매직: ftypheic + mif1heic compatible brands
    heic_bytes = b"\x00\x00\x00\x20ftypheic\x00\x00\x00\x00mif1heic\x00\x00\x00\x00" + b"\x00" * 64
    response = await authed_client.post(
        f"/api/v1/workspaces/{WORKSPACE_ID}/upload/file",
        files={"file": ("photo.mp4", heic_bytes, "video/mp4")},
    )
    assert response.status_code == 415, response.text


@pytest.mark.asyncio
async def test_upload_rejects_avif_renamed_as_video_mp4(authed_client):
    """F-2A v3: AVIF (ftypavif) 도 동일 차단."""
    avif_bytes = b"\x00\x00\x00\x20ftypavif\x00\x00\x00\x00avifmif1\x00\x00\x00\x00" + b"\x00" * 64
    response = await authed_client.post(
        f"/api/v1/workspaces/{WORKSPACE_ID}/upload/file",
        files={"file": ("photo.mp4", avif_bytes, "video/mp4")},
    )
    assert response.status_code == 415, response.text


@pytest.mark.asyncio
async def test_upload_accepts_csv_as_text_plain(authed_client):
    """F4 (agy): text/* family 는 확장자 자유 (.csv/.json/.rtf 등). 이전엔 415."""
    csv_bytes = b"name,age\nAlice,30\nBob,25\n"
    expected_file_key = f"uploads/{uuid.uuid4()}/data.csv"
    with patch(
        "src.upload.router.R2Service.upload_file_bytes",
        new_callable=AsyncMock,
        return_value=expected_file_key,
    ):
        response = await authed_client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/upload/file",
            files={"file": ("data.csv", csv_bytes, "text/plain")},
        )
    assert response.status_code == 201, response.text
    assert response.json()["fileKey"] == expected_file_key
