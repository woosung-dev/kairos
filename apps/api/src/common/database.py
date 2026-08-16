# apps/api/src/common/database.py
"""비동기 DB 엔진 및 세션 관리."""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

# 전역 변수 — lifespan에서 초기화
_engine = None
_async_session_factory = None


def init_engine(database_url: str) -> None:
    """비동기 엔진과 세션 팩토리를 초기화한다. lifespan에서 호출."""
    global _engine, _async_session_factory
    # BL-034: Neon Postgres 의 idle connection timeout (기본 5분) 이후 pool 에
    # 남은 connection 을 재사용하면 asyncpg.InterfaceError "connection is closed".
    # pool_pre_ping=True 는 매 체크아웃마다 가벼운 SELECT 1 으로 health check,
    # pool_recycle=240 은 4분 (Neon timeout 보다 짧게) 마다 connection 재생성.
    # PERF-r2-5: pool 크기 env 조정 가능 (DB_POOL_SIZE / DB_MAX_OVERFLOW, 기본 5+10)
    from src.core.config import get_settings
    settings = get_settings()
    _engine = create_async_engine(
        database_url,
        echo=False,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        pool_recycle=240,
    )
    _async_session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def dispose_engine() -> None:
    """엔진을 정리한다. lifespan shutdown에서 호출."""
    global _engine
    if _engine:
        await _engine.dispose()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends용 세션 제너레이터."""
    if _async_session_factory is None:
        raise RuntimeError("DB 엔진이 초기화되지 않았습니다. lifespan을 확인하세요.")
    async with _async_session_factory() as session:
        yield session


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """BackgroundTasks용 세션 팩토리 반환. Depends()로 주입 가능."""
    if _async_session_factory is None:
        raise RuntimeError("DB 엔진이 초기화되지 않았습니다. lifespan을 확인하세요.")
    return _async_session_factory
