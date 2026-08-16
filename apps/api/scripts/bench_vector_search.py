#!/usr/bin/env python3
# 벡터 검색 latency + recall + nDCG + precision + 인덱스 빌드 시간 (Sprint 16 Stage 5 / BL-026)
"""pgvector HNSW + halfvec 성능 측정 (Sprint 16 ADR-020 + BL-026 확장).

당근(Karrot) DB 밋업 §4-A 측정 + BL-026 (nDCG / precision / 빌드 시간 / EXPLAIN).

사용 예:
    cd apps/api
    uv run python scripts/bench_vector_search.py --mode latency --iter 1000
    uv run python scripts/bench_vector_search.py --mode recall          # recall + nDCG + precision
    uv run python scripts/bench_vector_search.py --mode build-time      # HNSW CREATE INDEX 측정
    uv run python scripts/bench_vector_search.py --mode explain         # EXPLAIN ANALYZE
    uv run python scripts/bench_vector_search.py --mode memory-recall   # memory/repository.py 측정
    uv run python scripts/bench_vector_search.py --mode all

ADR-020 §"Verification" 합격선:
    recall@10 >= baseline * 0.95
    p50 <= baseline * 1.0
    p95 <= baseline * 1.2
BL-026 추가 합격선:
    nDCG@10 >= 0.95
    precision@10 >= 0.90

fixture: apps/api/tests/embeddings/fixtures/recall_corpus.json
         (없으면 `python tests/embeddings/fixtures/generate_recall_corpus.py` 먼저 실행)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
import time
import uuid
from pathlib import Path
from statistics import median

# 스크립트 실행 시 apps/api/src 모듈 import 가능하도록 sys.path 보정
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from sqlalchemy import text

from src.common.database import (  # noqa: E402
    dispose_engine,
    get_session_factory,
    init_engine,
)
from src.core.config import get_settings  # noqa: E402
from src.embeddings.repository import EmbeddingRepository  # noqa: E402

# 런타임에 init_engine 호출 후 get_session_factory()로 채워짐
_session_factory = None


def async_session_factory():
    """런타임 초기화된 session factory 호출 wrapper.

    bench script는 lifespan 외부에서 실행되므로 init_engine + get_session_factory를
    명시 호출해야 한다 (Sprint 16 Stage 5 — async_session_factory 직접 import 불가).
    """
    if _session_factory is None:
        raise RuntimeError(
            "init_engine 미호출 — bench script 진입 시점에 _ensure_engine 호출 필요"
        )
    return _session_factory()


def _ensure_engine() -> None:
    global _session_factory
    if _session_factory is not None:
        return
    init_engine(get_settings().database_url)
    _session_factory = get_session_factory()

FIXTURE_PATH = (
    Path(__file__).parent.parent
    / "tests"
    / "embeddings"
    / "fixtures"
    / "recall_corpus.json"
)


# ── 공용 통계 ────────────────────────────────────────────


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round(p / 100.0 * (len(s) - 1)))))
    return s[k]


def dcg(relevances: list[int]) -> float:
    """DCG — relevances는 0/1 binary."""
    return sum(
        rel / math.log2(i + 2) for i, rel in enumerate(relevances)
    )


def ndcg_at_k(got_ids: list[str], expected_top_k: list[str], k: int = 10) -> float:
    """nDCG@K — got의 각 위치가 expected_top_k에 포함되는지 binary relevance."""
    expected_set = set(expected_top_k[:k])
    relevances = [1 if cid in expected_set else 0 for cid in got_ids[:k]]
    ideal = sorted(relevances, reverse=True)
    idcg = dcg(ideal)
    if idcg == 0:
        return 0.0
    return dcg(relevances) / idcg


def precision_at_k(got_ids: list[str], expected_top_k: list[str], k: int = 10) -> float:
    expected_set = set(expected_top_k[:k])
    if not got_ids:
        return 0.0
    hits = sum(1 for cid in got_ids[:k] if cid in expected_set)
    return hits / min(k, len(got_ids))


# ── fixture 로딩 ─────────────────────────────────────────


def _load_fixture() -> dict | None:
    if not FIXTURE_PATH.exists():
        print(
            f"[error] fixture 부재 — {FIXTURE_PATH}\n"
            "        먼저 다음 실행: "
            "uv run python tests/embeddings/fixtures/generate_recall_corpus.py"
        )
        return None
    return json.loads(FIXTURE_PATH.read_text())


# ── latency 측정 ─────────────────────────────────────────


async def measure_latency(iters: int) -> dict:
    """동일 쿼리 N회 실행 — p50/p95/p99 (ms)."""
    qvec = [0.01] * 1536
    workspace_id = uuid.UUID("00000000-0000-0000-0000-000000000aaa")
    timings_ms: list[float] = []
    async with async_session_factory() as session:
        repo = EmbeddingRepository(session)
        for _ in range(iters):
            t0 = time.perf_counter()
            await repo.vector_search(
                query_embedding=qvec,
                workspace_id=workspace_id,
                limit=50,
            )
            timings_ms.append((time.perf_counter() - t0) * 1000)
    return {
        "iters": iters,
        "p50_ms": round(median(timings_ms), 2),
        "p95_ms": round(percentile(timings_ms, 95), 2),
        "p99_ms": round(percentile(timings_ms, 99), 2),
        "min_ms": round(min(timings_ms), 2),
        "max_ms": round(max(timings_ms), 2),
    }


# ── recall + nDCG + precision (BL-026) ─────────────────


async def measure_recall_quality() -> dict:
    """recall@10 + nDCG@10 + precision@10."""
    data = _load_fixture()
    if data is None:
        return {"error": "fixture 부재"}

    queries = data.get("queries", [])
    chunks = data.get("chunks", [])
    if not queries or not chunks:
        return {"error": "fixture 비어 있음"}

    # seed: production-grade는 fixture chunks를 직접 INSERT 필요. 본 스크립트는 read-only 가정.
    # → fixture chunks가 실제 DB에 시드돼야 결과 의미 있음. seed 절차는 README 참조.

    recall_sum = 0.0
    ndcg_sum = 0.0
    precision_sum = 0.0
    n = 0
    async with async_session_factory() as session:
        repo = EmbeddingRepository(session)
        for q in queries:
            qvec = q["embedding"]
            wid = uuid.UUID(q["workspace_id"])
            expected = list(q.get("expected_top10", []))
            if not expected:
                continue
            results = await repo.vector_search(
                query_embedding=qvec,
                workspace_id=wid,
                limit=10,
            )
            got_ids = [str(r.get("id")) for r in results]
            expected_set = set(expected)
            got_set = set(got_ids)
            recall_sum += len(expected_set & got_set) / len(expected_set)
            ndcg_sum += ndcg_at_k(got_ids, expected, k=10)
            precision_sum += precision_at_k(got_ids, expected, k=10)
            n += 1

    if n == 0:
        return {"error": "유효 query 0건"}
    return {
        "n_queries": n,
        "recall@10": round(recall_sum / n, 4),
        "nDCG@10": round(ndcg_sum / n, 4),
        "precision@10": round(precision_sum / n, 4),
    }


# ── memory recall (memory/repository.py 검증) ──────────


async def measure_memory_recall(iters: int) -> dict:
    """memory/repository.py:vector_search 별도 latency 측정 (E-9 검증)."""
    from src.memory.repository import MemoryRepository

    qvec = [0.01] * 1536
    workspace_id = uuid.UUID("00000000-0000-0000-0000-000000000aaa")
    timings_ms: list[float] = []
    async with async_session_factory() as session:
        repo = MemoryRepository(session)
        for _ in range(iters):
            t0 = time.perf_counter()
            await repo.vector_search(
                workspace_id=workspace_id,
                query_embedding=qvec,
                top_k=10,
            )
            timings_ms.append((time.perf_counter() - t0) * 1000)
    return {
        "iters": iters,
        "p50_ms": round(median(timings_ms), 2),
        "p95_ms": round(percentile(timings_ms, 95), 2),
        "p99_ms": round(percentile(timings_ms, 99), 2),
    }


# ── 인덱스 빌드 시간 측정 ─────────────────────────────


async def measure_build_time() -> dict:
    """HNSW CREATE INDEX 측정 — production 데이터 규모에서 실행 권장.

    주의: 본 스크립트는 측정용 임시 인덱스 생성 + 즉시 drop. production index에 영향 없음.
    """
    async with async_session_factory() as session:
        # 사전 EXPLAIN으로 row 수 측정
        row_count_q = await session.execute(
            text("SELECT count(*) FROM embedding_chunks")
        )
        row_count = row_count_q.scalar_one()

        # 임시 인덱스 — autocommit 필요 (CONCURRENTLY)
        conn = await session.connection()
        await conn.execution_options(isolation_level="AUTOCOMMIT")

        t0 = time.perf_counter()
        await session.execute(
            text(
                "CREATE INDEX CONCURRENTLY idx_bench_temp_hnsw "
                "ON embedding_chunks USING hnsw (embedding halfvec_cosine_ops) "
                "WITH (m = 16, ef_construction = 64)"
            )
        )
        elapsed = time.perf_counter() - t0

        size_q = await session.execute(
            text(
                "SELECT pg_size_pretty(pg_relation_size('idx_bench_temp_hnsw'::regclass))"
            )
        )
        size = size_q.scalar_one()

        # 즉시 drop
        await session.execute(
            text("DROP INDEX CONCURRENTLY idx_bench_temp_hnsw")
        )
    return {
        "row_count": row_count,
        "build_time_seconds": round(elapsed, 2),
        "index_size": size,
        "params": "m=16, ef_construction=64, halfvec_cosine_ops",
    }


# ── EXPLAIN ANALYZE 헬퍼 ────────────────────────────────


async def explain_vector_search() -> dict:
    """대표 쿼리에 대한 EXPLAIN ANALYZE 출력 — Index Scan 사용 검증."""
    qvec = [0.01] * 1536
    qvec_str = "[" + ",".join(str(x) for x in qvec) + "]"
    workspace_id = "00000000-0000-0000-0000-000000000aaa"
    async with async_session_factory() as session:
        await session.execute(text("SET LOCAL hnsw.ef_search = 40"))
        await session.execute(
            text("SET LOCAL hnsw.iterative_scan = 'relaxed_order'")
        )
        result = await session.execute(
            text(
                f"EXPLAIN (ANALYZE, BUFFERS) "
                f"SELECT id FROM embedding_chunks "
                f"WHERE workspace_id = :wid AND chunk_level = 2 "
                f"ORDER BY embedding <=> CAST('{qvec_str}' AS halfvec) "
                f"LIMIT 10"
            ),
            {"wid": workspace_id},
        )
        plan = [row[0] for row in result.all()]
    uses_hnsw = any("idx_chunks_hnsw" in line for line in plan)
    return {
        "plan": plan,
        "uses_hnsw_index": uses_hnsw,
    }


# ── 인덱스 + 테이블 정보 ───────────────────────────────


async def show_state() -> None:
    async with async_session_factory() as session:
        print("--- 인덱스 ---")
        r = await session.execute(
            text(
                "SELECT indexname, pg_size_pretty(pg_relation_size(indexname::regclass)) "
                "FROM pg_indexes WHERE tablename IN "
                "('embedding_chunks','semantic_caches','memory_query_embedding_cache') "
                "ORDER BY tablename, indexname"
            )
        )
        for row in r:
            print(f"  {row[0]}: {row[1]}")

        print("\n--- 테이블 옵션 (fillfactor + autovacuum) ---")
        r = await session.execute(
            text(
                "SELECT relname, reloptions FROM pg_class "
                "WHERE relname IN "
                "('embedding_chunks','semantic_caches','memory_query_embedding_cache')"
            )
        )
        for row in r:
            print(f"  {row[0]}: {row[1]}")


# ── main ─────────────────────────────────────────────────


async def run(*, mode: str, iters: int) -> int:
    _ensure_engine()
    try:
        return await _run_inner(mode=mode, iters=iters)
    finally:
        await dispose_engine()


async def _run_inner(*, mode: str, iters: int) -> int:
    await show_state()

    if mode in ("latency", "all"):
        print(f"\n--- latency ({iters} iters) ---")
        print(json.dumps(await measure_latency(iters), indent=2))

    if mode in ("recall", "all"):
        print("\n--- recall + nDCG + precision (BL-026) ---")
        print(json.dumps(await measure_recall_quality(), indent=2))

    if mode in ("memory-recall", "all"):
        print(f"\n--- memory recall latency ({iters} iters) ---")
        print(json.dumps(await measure_memory_recall(iters), indent=2))

    if mode in ("build-time", "all"):
        print("\n--- HNSW 인덱스 빌드 시간 ---")
        print(json.dumps(await measure_build_time(), indent=2))

    if mode in ("explain", "all"):
        print("\n--- EXPLAIN (ANALYZE, BUFFERS) ---")
        explain = await explain_vector_search()
        for line in explain["plan"]:
            print(f"  {line}")
        print(f"\n  uses_hnsw_index: {explain['uses_hnsw_index']}")

    if mode not in ("latency", "recall", "memory-recall", "build-time", "explain", "all"):
        print(f"unknown mode: {mode}")
        return 1
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="pgvector HNSW 성능 + 품질 측정")
    p.add_argument(
        "--mode",
        choices=("latency", "recall", "memory-recall", "build-time", "explain", "all"),
        default="all",
    )
    p.add_argument("--iter", dest="iters", type=int, default=1000)
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    raise SystemExit(asyncio.run(run(mode=args.mode, iters=args.iters)))
