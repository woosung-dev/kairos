# Sprint 15 R-CRON — Memory 도메인 admin endpoint (R2 30일 cleanup)
"""Memory admin router — founder/Cloud Scheduler only.

본 라우터는 Clerk JWT 인증 대신 cron secret token 헤더로 보호.
GCP Cloud Scheduler에서 매일 호출. 30일 이상 경과한 voice 메모의 R2 객체 삭제.
"""
from fastapi import APIRouter, Depends, Header, HTTPException

from src.core.config import get_settings
from src.memory.dependencies import get_memory_service
from src.memory.service import MemoryService

admin_router = APIRouter(prefix="/api/v1/admin/memory", tags=["memory-admin"])


async def verify_cron_token(x_cron_token: str = Header(default="")) -> None:
    """Cron secret token 검증 — Clerk JWT 우회 경로."""
    settings = get_settings()
    expected = settings.cron_secret_token.get_secret_value()
    if not x_cron_token or x_cron_token != expected:
        raise HTTPException(status_code=403, detail="invalid cron token")


@admin_router.post("/r2-cleanup", dependencies=[Depends(verify_cron_token)])
async def r2_cleanup(
    days: int = 30,
    service: MemoryService = Depends(get_memory_service),
) -> dict:
    """R2 30일 TTL cleanup — Cloud Scheduler에서 daily invoke. O-E lock-in."""
    if days < 1 or days > 365:
        raise HTTPException(status_code=422, detail="days는 1~365 범위")
    deleted = await service.cleanup_expired_r2_audio(days=days)
    return {"deleted_count": deleted, "ttl_days": days}
