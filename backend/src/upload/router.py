# backend/src/upload/router.py
"""Upload 라우터 — R2 presigned URL 발급."""
import uuid

from fastapi import APIRouter, Depends
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
