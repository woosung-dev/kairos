# backend/src/common/r2.py
"""Cloudflare R2 스토리지 서비스. aioboto3 비동기."""
import uuid

import aioboto3

from src.core.config import get_settings


class R2Service:
    """R2 presigned URL 발급 및 파일 관리."""

    def __init__(self) -> None:
        self._session = aioboto3.Session()

    def _get_endpoint_url(self) -> str:
        settings = get_settings()
        account_id = settings.r2_account_id.get_secret_value()
        return f"https://{account_id}.r2.cloudflarestorage.com"

    async def get_presigned_upload_url(
        self, filename: str, content_type: str
    ) -> dict:
        """업로드용 presigned URL 발급."""
        settings = get_settings()
        file_key = f"uploads/{uuid.uuid4()}/{filename}"
        async with self._session.client(
            "s3",
            endpoint_url=self._get_endpoint_url(),
            aws_access_key_id=settings.r2_access_key_id.get_secret_value(),
            aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
            region_name="auto",
        ) as client:
            upload_url = await client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": settings.r2_bucket_name,
                    "Key": file_key,
                    "ContentType": content_type,
                },
                ExpiresIn=3600,
            )
        return {
            "upload_url": upload_url,
            "file_key": file_key,
            "expires_in": 3600,
        }

    async def upload_file_bytes(
        self, filename: str, content_type: str, data: bytes
    ) -> str:
        """파일 바이트를 R2에 직접 업로드 (백엔드 프록시용). file_key 반환."""
        settings = get_settings()
        file_key = f"uploads/{uuid.uuid4()}/{filename}"
        async with self._session.client(
            "s3",
            endpoint_url=self._get_endpoint_url(),
            aws_access_key_id=settings.r2_access_key_id.get_secret_value(),
            aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
            region_name="auto",
        ) as client:
            await client.put_object(
                Bucket=settings.r2_bucket_name,
                Key=file_key,
                Body=data,
                ContentType=content_type,
            )
        return file_key

    async def delete_object(self, file_key: str) -> None:
        """R2 객체 삭제 — Sprint 15 R-CRON 30일 TTL cleanup용."""
        settings = get_settings()
        async with self._session.client(
            "s3",
            endpoint_url=self._get_endpoint_url(),
            aws_access_key_id=settings.r2_access_key_id.get_secret_value(),
            aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
            region_name="auto",
        ) as client:
            await client.delete_object(
                Bucket=settings.r2_bucket_name, Key=file_key,
            )

    async def get_download_url(self, file_key: str) -> str:
        """다운로드용 presigned URL 발급 (파이프라인 내부용)."""
        settings = get_settings()
        async with self._session.client(
            "s3",
            endpoint_url=self._get_endpoint_url(),
            aws_access_key_id=settings.r2_access_key_id.get_secret_value(),
            aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
            region_name="auto",
        ) as client:
            url = await client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": settings.r2_bucket_name,
                    "Key": file_key,
                },
                ExpiresIn=3600,
            )
        return url
