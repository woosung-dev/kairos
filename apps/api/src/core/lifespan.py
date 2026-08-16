# apps/backend/src/core/lifespan.py
"""FastAPI lifespan — startup/shutdown 관리."""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.common.database import dispose_engine, init_engine
from src.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """앱 시작 시 DB 엔진 생성, 종료 시 정리."""
    settings = get_settings()
    init_engine(settings.database_url)
    yield
    await dispose_engine()
