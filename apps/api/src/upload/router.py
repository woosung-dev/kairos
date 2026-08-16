# Upload 라우터 — R2 presigned URL 발급 + 프록시 업로드 (size/MIME/확장자/signature 검증)
"""Sprint 25 T-SEC-3 (BUG-SENTINEL-003) — UploadValidator wire. HTTP 4xx 매핑만."""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from src.auth.rbac import require_member
from src.common.r2 import R2Service, get_r2_service
from src.upload.dependencies import get_upload_validator
from src.upload.exceptions import (
    ContentMismatchError,
    EmptyFileError,
    FileTooLargeError,
    MimeExtensionMismatchError,
    UnsupportedMimeError,
)
from src.upload.service import UploadValidator
from src.workspaces.models import WorkspaceMember

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/upload",
    tags=["upload"],
)


class PresignedUrlRequest(BaseModel):
    filename: str
    content_type: str | None = None
    contentType: str | None = None  # FE camelCase 호환

    def get_content_type(self) -> str:
        return self.content_type or self.contentType or "application/octet-stream"


@router.post("/presigned-url")
async def get_presigned_url(
    workspace_id: uuid.UUID,
    data: PresignedUrlRequest,
    member: WorkspaceMember = Depends(require_member),
    validator: UploadValidator = Depends(get_upload_validator),
):
    """R2 presigned PUT URL 발급.

    F1 fix (Sprint 25 polish, agy review): /presigned-url 가 T-SEC-3 검증
    bypass 던 critical 결손 해소 — filename + declared MIME 1차 검증 적용.
    size + signature 는 파일 미존재 시점이라 검증 불가 (BL carry — post-upload
    R2 event trigger 또는 proxy 단일화).
    """
    declared_mime = data.get_content_type()
    try:
        validator.validate_pre_upload(data.filename, declared_mime)
    except UnsupportedMimeError as e:
        raise HTTPException(status_code=415, detail=str(e))
    except MimeExtensionMismatchError as e:
        raise HTTPException(status_code=415, detail=str(e))

    r2 = get_r2_service()
    result = await r2.get_presigned_upload_url(data.filename, declared_mime)
    return {
        "uploadUrl": result["upload_url"],
        "fileKey": result["file_key"],
        "expiresIn": result["expires_in"],
    }


@router.post("/file", status_code=201)
async def upload_file_proxy(
    workspace_id: uuid.UUID,
    file: UploadFile = File(...),
    member: WorkspaceMember = Depends(require_member),
    validator: UploadValidator = Depends(get_upload_validator),
):
    """브라우저 CORS 우회용 백엔드 프록시 업로드.

    FE → BE → R2 경로. T-SEC-3로 size/MIME/확장자/content signature 4계층 검증.
    F2 fix (Sprint 25 polish, agy review): file.size (UploadFile spool 메타데이터)
    로 사전 size 차단 → 500MB 페이로드를 RAM 적재 전 reject (DoS 완화).
    """
    content_type = file.content_type or "application/octet-stream"
    filename = file.filename or "upload"

    # F2: pre-read size 차단 — file.read() 호출 전 OOM 회피.
    # FastAPI UploadFile.size 는 multipart 파싱 시점에 설정 (None 가능 — fallback 은 read 후 검증).
    if file.size is not None and file.size > validator.max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"파일 크기 {file.size}바이트가 한도 {validator.max_bytes}바이트를 초과합니다",
        )

    file_bytes = await file.read()
    try:
        validator.validate(filename, content_type, file_bytes)
    except EmptyFileError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileTooLargeError as e:
        raise HTTPException(status_code=413, detail=str(e))
    except (UnsupportedMimeError, MimeExtensionMismatchError, ContentMismatchError) as e:
        raise HTTPException(status_code=415, detail=str(e))

    r2 = get_r2_service()
    file_key = await r2.upload_file_bytes(filename, content_type, file_bytes)
    return {"fileKey": file_key}
