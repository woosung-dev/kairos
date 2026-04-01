# backend/src/upload/router.py
"""Upload 라우터 — R2 presigned URL 발급."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.common.r2 import R2Service

router = APIRouter(prefix="/api/v1/upload", tags=["upload"])


class PresignedUrlRequest(BaseModel):
    filename: str
    content_type: str


@router.post("/presigned-url")
async def get_presigned_url(
    data: PresignedUrlRequest,
    current_user: User = Depends(get_current_user),
):
    r2 = R2Service()
    result = await r2.get_presigned_upload_url(data.filename, data.content_type)
    return {
        "uploadUrl": result["upload_url"],
        "fileKey": result["file_key"],
        "expiresIn": result["expires_in"],
    }
