# Sprint 24 Wave 2 T-BE-PERF spike — dashboard 첫 진입 4 API 직렬 호출 profiling
"""T-BE-PERF spike (BUG-MOBILE-005).

배경:
- Multi-Agent QA Mobile 측정 localhost BE API 첫 진입 3015-3865ms.
- 3G 추정 7-10s → cancel 임계.

목적:
- 4 API (workspaces / members / meetings / inbox) 직렬 호출 latency 분해
- Clerk JWT verify cold vs cached 측정 (in-process LRU cache 도입 효과 검증)
- SQLAlchemy event listener 로 Top slow queries
- cProfile 로 Top cumulative
- 결과 JSON dump + report 용 데이터

실행:
  cd backend
  uv run python -m scripts.sprint24_wave2_perf_spike
  # 결과는 stdout + docs/dev-log/sprints/2026-05-20-sprint24-wave2/be-perf-spike.json

전제:
- testcontainers PostgreSQL 사용 (Neon cold start 노이즈 격리)
- pyjwt + RS256 self-signed key 로 verify_clerk_token 흐름 simulate
  (network 없이 JWKS client 측 캐싱 효과 측정 가능)

산출:
- /tmp/perf-spike.json (raw)
- docs/dev-log/sprints/2026-05-20-sprint24-wave2/be-perf-spike.json (committable)
- stdout: API timing 매트릭스 + Top 5 cumulative + Top 5 slow queries

§19 sub-agent: 코드 수정 + 측정 만, commit 0.
"""
from __future__ import annotations

import asyncio
import cProfile
import io
import json
import pstats
import statistics
import sys
import time
import uuid
from pathlib import Path
from typing import Any

# sys.path에 backend/ 추가 — src.* import 가능
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

# 결과 출력 경로 (commit 대상)
REPORT_JSON = BACKEND_DIR.parent / "docs" / "dev-log" / "2026-05-20-sprint24-wave2" / "be-perf-spike.json"


# ---------------------------------------------------------------------------
# Query timing collector — SQLAlchemy event listener
# ---------------------------------------------------------------------------

QUERY_TIMINGS: list[dict[str, Any]] = []
CURRENT_PHASE: dict[str, str] = {"phase": "boot"}


def _install_query_listener(sync_engine) -> None:
    """SQLAlchemy core Engine 에 before/after_cursor_execute listener 부착."""
    from sqlalchemy import event

    @event.listens_for(sync_engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.time()

    @event.listens_for(sync_engine, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):
        elapsed_ms = (time.time() - getattr(context, "_query_start_time", time.time())) * 1000
        # 첫 80 char 만 보관 (long SELECT 도 가독성 위해)
        QUERY_TIMINGS.append(
            {
                "phase": CURRENT_PHASE["phase"],
                "stmt": " ".join(statement.split())[:120],
                "ms": round(elapsed_ms, 2),
            }
        )


# ---------------------------------------------------------------------------
# Clerk JWT verify — local self-signed RS256 simulate
# ---------------------------------------------------------------------------

def _gen_rsa_keypair() -> tuple[Any, Any]:
    """RSA keypair 생성 (한 번만)."""
    from cryptography.hazmat.primitives.asymmetric import rsa

    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key()
    return private, public


def _make_clerk_token(private_key, clerk_user_id: str) -> str:
    """RS256 JWT 생성 — Clerk JWT 흐름 simulate."""
    import jwt as pyjwt

    return pyjwt.encode(
        {
            "sub": clerk_user_id,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        },
        private_key,
        algorithm="RS256",
    )


def _patch_verify_clerk_token(public_key) -> None:
    """src.auth.dependencies.verify_clerk_token 의 jwks_client 를 local public key 로 교체.

    network call (PyJWKClient.get_signing_key_from_jwt) 를 우회하면서도
    실제 jwt.decode 흐름은 그대로 측정 — cache 미적용 시점의 cost 가 명확히 나타남.
    """
    from unittest.mock import MagicMock

    from src.auth import dependencies as deps

    mock_client = MagicMock()
    signing_key_mock = MagicMock()
    signing_key_mock.key = public_key

    def _get_signing_key_from_jwt(token: str):
        # 실제 jwt.PyJWKClient 는 token header 파싱 + JWKS HTTP fetch + RSA 키 매칭.
        # 캐시 미적용 시 매 호출마다 발생 — 여기서는 network 만 제거하고 dict lookup overhead 는 측정.
        return signing_key_mock

    mock_client.get_signing_key_from_jwt.side_effect = _get_signing_key_from_jwt
    deps._jwks_client = mock_client


# ---------------------------------------------------------------------------
# Dashboard 4 API 직렬 호출 simulate
# ---------------------------------------------------------------------------

async def _seed_dashboard_state(session) -> tuple[uuid.UUID, uuid.UUID, str]:
    """user + team workspace + 멤버 + meetings 5건 + inbox items 5건 seed.

    Returns: (user_id, workspace_id, clerk_id)
    """
    from src.auth.models import User
    from src.inbox.models import InboxItem
    from src.meetings.models import Meeting
    from src.workspaces.models import Workspace, WorkspaceMember

    clerk_id = "user_perf_spike_001"
    user = User(
        clerk_id=clerk_id,
        display_name="Perf Spike Tester",
        email="perf@kairos.test",
    )
    session.add(user)
    await session.flush()

    ws = Workspace(name="Perf 팀", owner_id=user.id, type="team")
    session.add(ws)
    await session.flush()

    member = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner")
    session.add(member)
    await session.flush()

    # meetings 5건
    for i in range(5):
        session.add(
            Meeting(
                workspace_id=ws.id,
                title=f"테스트 미팅 {i}",
                file_key=f"key-{i}",
                created_by_id=user.id,
                status="completed",
            )
        )
    # inbox 5건
    for i in range(5):
        session.add(
            InboxItem(
                workspace_id=ws.id,
                source_type="note",
                source_id=uuid.uuid4(),
                title=f"Inbox 아이템 {i}",
                content=f"테스트 노트 {i}",
                created_by_id=user.id,
            )
        )
    await session.commit()
    return user.id, ws.id, clerk_id


async def _make_http_client(integration_engine, user, async_session_factory):
    """ASGI httpx AsyncClient + dependency override (get_current_user / get_async_session).

    실제 router → service → repo 흐름을 그대로 측정.
    """
    from httpx import ASGITransport, AsyncClient

    from src.auth.dependencies import get_current_user
    from src.common.database import get_async_session, get_session_factory
    from src.main import app

    async def _get_session():
        async with async_session_factory() as s:
            yield s

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_async_session] = _get_session
    app.dependency_overrides[get_session_factory] = lambda: async_session_factory
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test"), app


async def simulate_dashboard_first_visit() -> dict[str, Any]:
    """dashboard 첫 진입 4 API 직렬 호출.

    Steps:
      1) testcontainers PostgreSQL up
      2) async engine + listener install
      3) seed state
      4) JWT verify timing (cold / cached x10)
      5) 4 API call (each measured) — first-call + 2nd-call (warm)
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlmodel import SQLModel, text
    from sqlmodel.ext.asyncio.session import AsyncSession
    from testcontainers.postgres import PostgresContainer

    # SQLModel 등록
    import src.actions.models  # noqa: F401
    import src.auth.models  # noqa: F401
    import src.common.promote_models  # noqa: F401
    import src.embeddings.models  # noqa: F401
    import src.inbox.models  # noqa: F401
    import src.meetings.models  # noqa: F401
    import src.memory.models  # noqa: F401
    import src.notes.models  # noqa: F401
    import src.projects.models  # noqa: F401
    import src.workspaces.models  # noqa: F401

    timings: dict[str, Any] = {}

    with PostgresContainer("pgvector/pgvector:pg16") as pg:
        url = pg.get_connection_url().replace("psycopg2", "asyncpg")
        engine = create_async_engine(url, echo=False, pool_size=5, max_overflow=5)
        async_session_factory = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )

        # listener — sync engine 객체 hook
        _install_query_listener(engine.sync_engine)

        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(SQLModel.metadata.create_all)

        # seed
        CURRENT_PHASE["phase"] = "seed"
        async with async_session_factory() as session:
            user_id, workspace_id, clerk_id = await _seed_dashboard_state(session)

        # user 객체 다시 fetch (FastAPI override 에 주입)
        from sqlmodel import select

        from src.auth.models import User

        async with async_session_factory() as session:
            result = await session.exec(select(User).where(User.id == user_id))
            user = result.one()

        # ---- JWT verify timing ----
        # local RS256 setup
        private, public = _gen_rsa_keypair()
        token = _make_clerk_token(private, clerk_id)
        _patch_verify_clerk_token(public)

        from src.auth.dependencies import verify_clerk_token

        CURRENT_PHASE["phase"] = "jwt_cold"
        t0 = time.time()
        await verify_clerk_token(authorization=f"Bearer {token}")
        timings["jwt_verify_cold_ms"] = (time.time() - t0) * 1000

        # 10회 반복 — Top 1 fix 캐시 적용 상태에서 cost (2회차부터 캐시 hit)
        cached_samples = []
        for _ in range(10):
            t0 = time.time()
            await verify_clerk_token(authorization=f"Bearer {token}")
            cached_samples.append((time.time() - t0) * 1000)
        timings["jwt_verify_with_cache_p50_ms"] = round(statistics.median(cached_samples), 2)
        timings["jwt_verify_with_cache_mean_ms"] = round(statistics.fmean(cached_samples), 2)

        # 캐시 무효화 후 재측정 — no-cache 경로 baseline
        from src.auth import dependencies as deps_mod
        deps_mod._JWT_CLAIMS_CACHE.clear()
        nocache_samples = []
        for _ in range(10):
            deps_mod._JWT_CLAIMS_CACHE.clear()  # 매 호출마다 캐시 강제 무효화
            t0 = time.time()
            await verify_clerk_token(authorization=f"Bearer {token}")
            nocache_samples.append((time.time() - t0) * 1000)
        timings["jwt_verify_no_cache_p50_ms"] = round(statistics.median(nocache_samples), 2)
        timings["jwt_verify_no_cache_mean_ms"] = round(statistics.fmean(nocache_samples), 2)
        # 캐시 비워둔 상태에서 다음 API 호출 단계 진입
        deps_mod._JWT_CLAIMS_CACHE.clear()

        # ---- 4 API direct service-layer simulate (가장 정확한 layer 측정) ----
        # router 통과는 별도 HTTPX 호출에서 측정. 우선 layer 분리해서 dependency 비용 확인.
        from src.workspaces.dependencies import (
            get_invite_service,
            get_workspace_service,
        )

        api_timings: dict[str, dict[str, float]] = {}

        # HTTP client setup
        client_ctx, app = await _make_http_client(engine, user, async_session_factory)
        # require_viewer / require_member / require_admin 가 workspace 멤버십 검증 — DB 거치므로 그대로 측정
        try:
            async with client_ctx as client:
                headers = {"Authorization": f"Bearer {token}"}

                async def _measure(label: str, method: str, path: str, n: int = 3) -> None:
                    """N회 호출 — 1st = cold, 2nd+ = warm."""
                    samples = []
                    for i in range(n):
                        CURRENT_PHASE["phase"] = f"{label}_call_{i}"
                        t0 = time.time()
                        r = await client.request(method, path, headers=headers)
                        ms = (time.time() - t0) * 1000
                        samples.append(ms)
                        if r.status_code >= 400:
                            api_timings.setdefault(label, {})["error"] = r.status_code
                    api_timings.setdefault(label, {}).update(
                        {
                            "first_call_ms": round(samples[0], 2),
                            "warm_p50_ms": round(statistics.median(samples[1:]) if len(samples) > 1 else samples[0], 2),
                            "all_samples_ms": [round(s, 2) for s in samples],
                        }
                    )

                # dashboard 4 API
                await _measure("workspaces", "GET", "/api/v1/workspaces")
                await _measure("members", "GET", f"/api/v1/workspaces/{workspace_id}/members")
                await _measure("meetings", "GET", f"/api/v1/workspaces/{workspace_id}/meetings")
                await _measure("inbox", "GET", f"/api/v1/workspaces/{workspace_id}/inbox")

                # 직렬 합계 — 첫 진입 시 사용자 경험
                CURRENT_PHASE["phase"] = "serial_first_visit"
                t0 = time.time()
                await client.get("/api/v1/workspaces", headers=headers)
                await client.get(f"/api/v1/workspaces/{workspace_id}/members", headers=headers)
                await client.get(f"/api/v1/workspaces/{workspace_id}/meetings", headers=headers)
                await client.get(f"/api/v1/workspaces/{workspace_id}/inbox", headers=headers)
                timings["serial_4_api_first_visit_ms"] = (time.time() - t0) * 1000

                # warm 2회차
                CURRENT_PHASE["phase"] = "serial_warm"
                t0 = time.time()
                await client.get("/api/v1/workspaces", headers=headers)
                await client.get(f"/api/v1/workspaces/{workspace_id}/members", headers=headers)
                await client.get(f"/api/v1/workspaces/{workspace_id}/meetings", headers=headers)
                await client.get(f"/api/v1/workspaces/{workspace_id}/inbox", headers=headers)
                timings["serial_4_api_warm_ms"] = (time.time() - t0) * 1000
        finally:
            app.dependency_overrides.clear()
            await engine.dispose()

        return {
            "timings": timings,
            "api_timings": api_timings,
            "queries_total": len(QUERY_TIMINGS),
        }


# ---------------------------------------------------------------------------
# 캐시 적용 후 재측정 — Top 1 fix 효과 검증
# ---------------------------------------------------------------------------

async def measure_jwt_with_cache() -> dict[str, float]:
    """verify_clerk_token 의 jwks_client.get_signing_key_from_jwt 결과를 module-level dict 로 1회 캐싱.

    Top 1 fix simulate — 실제 fix 는 dependencies.py 에 반영. 여기서는 fix 적용 전후 비교용
    no-cache 와 with-cache 두 가지 모두 측정.
    """
    from cryptography.hazmat.primitives.asymmetric import rsa

    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key()

    import jwt as pyjwt

    token = pyjwt.encode(
        {"sub": "user_x", "iat": int(time.time()), "exp": int(time.time()) + 3600},
        private,
        algorithm="RS256",
    )

    # 캐시: token kid → signing key
    cache: dict[str, Any] = {}

    def _verify_with_cache(tok: str) -> dict:
        header = pyjwt.get_unverified_header(tok)
        kid = header.get("kid", "default")
        if kid not in cache:
            cache[kid] = public  # cold path
        key = cache[kid]
        claims = pyjwt.decode(tok, key, algorithms=["RS256"], options={"verify_aud": False})
        return {"sub": claims["sub"]}

    # 1st = cold
    t0 = time.time()
    _verify_with_cache(token)
    cold_ms = (time.time() - t0) * 1000

    # warm samples
    samples = []
    for _ in range(50):
        t0 = time.time()
        _verify_with_cache(token)
        samples.append((time.time() - t0) * 1000)

    return {
        "cold_ms": round(cold_ms, 2),
        "warm_p50_ms": round(statistics.median(samples), 2),
        "warm_mean_ms": round(statistics.fmean(samples), 2),
    }


# ---------------------------------------------------------------------------
# 분석 + report 데이터 생성
# ---------------------------------------------------------------------------

def analyze_queries() -> dict[str, Any]:
    """수집된 query timing 을 분석 — Top slow + phase별 합계."""
    by_phase: dict[str, list[float]] = {}
    for q in QUERY_TIMINGS:
        by_phase.setdefault(q["phase"], []).append(q["ms"])

    phase_summary = {
        phase: {
            "count": len(samples),
            "total_ms": round(sum(samples), 2),
            "p50_ms": round(statistics.median(samples), 2) if samples else 0,
            "max_ms": round(max(samples), 2) if samples else 0,
        }
        for phase, samples in by_phase.items()
    }

    top_slow = sorted(QUERY_TIMINGS, key=lambda x: -x["ms"])[:10]
    return {"by_phase": phase_summary, "top_10_slow_queries": top_slow}


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

async def amain() -> dict[str, Any]:
    """전체 spike 실행."""
    QUERY_TIMINGS.clear()
    sim_result = await simulate_dashboard_first_visit()
    cache_result = await measure_jwt_with_cache()
    query_analysis = analyze_queries()
    return {
        "simulation": sim_result,
        "jwt_cache_simulation": cache_result,
        "query_analysis": query_analysis,
    }


def main() -> None:
    profiler = cProfile.Profile()
    profiler.enable()
    result = asyncio.run(amain())
    profiler.disable()

    # Top 30 cumulative
    s = io.StringIO()
    pstats.Stats(profiler, stream=s).sort_stats("cumulative").print_stats(30)
    cumulative_top = s.getvalue()

    # tottime Top 30
    s2 = io.StringIO()
    pstats.Stats(profiler, stream=s2).sort_stats("tottime").print_stats(30)
    tottime_top = s2.getvalue()

    # stdout
    print("=" * 80)
    print("Sprint 24 Wave 2 T-BE-PERF spike — dashboard 4 API 첫 진입 profiling")
    print("=" * 80)
    print()
    print("[A] JWT verify timing (Top 1 fix 검증)")
    print(json.dumps({
        "cold_ms_first_call": result["simulation"]["timings"].get("jwt_verify_cold_ms"),
        "no_cache_p50_ms": result["simulation"]["timings"].get("jwt_verify_no_cache_p50_ms"),
        "with_cache_p50_ms_after_fix": result["simulation"]["timings"].get("jwt_verify_with_cache_p50_ms"),
        "_synthetic_cache_simulation_cold_ms": result["jwt_cache_simulation"]["cold_ms"],
        "_synthetic_cache_simulation_warm_p50_ms": result["jwt_cache_simulation"]["warm_p50_ms"],
    }, indent=2))
    print()

    print("[B] API timing 매트릭스")
    print(json.dumps(result["simulation"]["api_timings"], indent=2, ensure_ascii=False))
    print()
    print("[C] Serial 4 API")
    print(json.dumps({
        "first_visit_ms": result["simulation"]["timings"].get("serial_4_api_first_visit_ms"),
        "warm_ms": result["simulation"]["timings"].get("serial_4_api_warm_ms"),
    }, indent=2))
    print()

    print("[D] Top slow queries")
    print(json.dumps(result["query_analysis"]["top_10_slow_queries"], indent=2, ensure_ascii=False))
    print()

    print("[E] Per-phase query summary")
    print(json.dumps(result["query_analysis"]["by_phase"], indent=2, ensure_ascii=False))
    print()

    print("[F] cProfile Top 30 cumulative")
    print(cumulative_top)
    print()
    print("[G] cProfile Top 30 tottime")
    print(tottime_top)

    # JSON dump — report 용
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(
        json.dumps(
            {
                **result,
                "cprofile_cumulative_top_30": cumulative_top,
                "cprofile_tottime_top_30": tottime_top,
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )
    print(f"\n[OK] dumped → {REPORT_JSON.relative_to(BACKEND_DIR.parent)}")


if __name__ == "__main__":
    main()
