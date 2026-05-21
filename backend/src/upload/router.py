# Upload 라우터 — R2 presigned URL 발급 + 프록시 업로드 (size/MIME/확장자/signature 검증)
"""Sprint 25 T-SEC-3 (BUG-SENTINEL-003) — UploadValidator wire. HTTP 4xx 매핑만."""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from src.auth.rbac import require_member
from src.common.r2 import R2Service
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
):
    r2 = R2Service()
    result = await r2.get_presigned_upload_url(data.filename, data.get_content_type())
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

    FE → BE → R2 경로. T-SEC-3로 size/MIME/확장자/content signature 4계층 검증 추가.
    """
    content_type = file.content_type or "application/octet-stream"
    file_bytes = await file.read()
    filename = file.filename or "upload"

    try:
        validator.validate(filename, content_type, file_bytes)
    except EmptyFileError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileTooLargeError as e:
        raise HTTPException(status_code=413, detail=str(e))
    except (UnsupportedMimeError, MimeExtensionMismatchError, ContentMismatchError) as e:
        raise HTTPException(status_code=415, detail=str(e))

    r2 = R2Service()
    file_key = await r2.upload_file_bytes(filename, content_type, file_bytes)
    return {"fileKey": file_key}
