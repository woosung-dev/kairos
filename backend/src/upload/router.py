# backend/src/upload/router.py
"""Upload 라우터 — R2 presigned URL 발급 + 프록시 업로드 (CORS 우회)."""
import uuid

from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel

from src.auth.rbac import require_member
from src.common.r2 import R2Service
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
):
    """브라우저 CORS 우회용 백엔드 프록시 업로드.

    FE → BE → R2 경로로 업로드하여 R2 직접 PUT의 CORS 문제를 해결한다.
    """
    content_type = file.content_type or "application/octet-stream"
    file_bytes = await file.read()
    r2 = R2Service()
    file_key = await r2.upload_file_bytes(file.filename or "upload", content_type, file_bytes)
    return {"fileKey": file_key}
