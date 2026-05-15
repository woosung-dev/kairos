# Sprint 17 BL-034 — DB pool config 회귀 가드 (asyncpg "connection is closed" 방지)
"""init_engine 이 생성하는 AsyncEngine 의 pool config 가 BL-034 fix 와 일치하는지 검증.

Neon 의 idle connection timeout (기본 5분) 대응 — pool_pre_ping=True 와 짧은
pool_recycle 이 누락되면 asyncpg.InterfaceError "connection is closed"
intermittent 회귀. fix 회귀 시 본 spec 이 즉시 검출.
"""

import src.common.database as database_module
from src.common.database import init_engine


def test_init_engine_applies_pool_pre_ping_and_recycle():
    """BL-034: init_engine 호출 후 _engine 의 pool config 확인.

    - pool_pre_ping=True : 매 checkout 시 SELECT 1 health check
    - pool_recycle <= 240 초 : Neon 5분 idle timeout 보다 짧게
    """
    # asyncpg dialect — 실제 connect 시점까지 lazy. URL 만 검증용으로 OK.
    init_engine("postgresql+asyncpg://fake:fake@localhost/fakedb")
    engine = database_module._engine
    assert engine is not None

    # pool_pre_ping (BL-034 핵심)
    assert engine.pool._pre_ping is True, (
        "BL-034 회귀: pool_pre_ping 가 활성화되지 않음. "
        "Neon idle connection 회복 메커니즘 누락 위험."
    )

    # pool_recycle — 240 초 이하 (Neon 5분 timeout 보다 짧게)
    recycle = engine.pool._recycle
    assert 0 < recycle <= 240, (
        f"BL-034 회귀: pool_recycle={recycle}. 4분 (240s) 이하여야 "
        f"Neon idle timeout 보다 선제적으로 connection 교체."
    )

    # cleanup
    database_module._engine = None
    database_module._async_session_factory = None
