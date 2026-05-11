# backend/src/common/database.py
"""비동기 DB 엔진 및 세션 관리."""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# 전역 변수 — lifespan에서 초기화
_engine = None
_async_session_factory = None


def init_engine(database_url: str) -> None:
    """비동기 엔진과 세션 팩토리를 초기화한다. lifespan에서 호출."""
    global _engine, _async_session_factory
    _engine = create_async_engine(
        database_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
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
