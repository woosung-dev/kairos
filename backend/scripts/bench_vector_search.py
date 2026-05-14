#!/usr/bin/env python3
# 벡터 검색 p50/p95 + recall@K baseline vs HNSW 비교 (Sprint 16 Stage 5)
"""pgvector HNSW + halfvec 성능 측정 스크립트 (Sprint 16 ADR-020 검증용).

당근(Karrot) DB 밋업 1회 §4-A — p50/p95 latency + recall regression 측정.

사용 예:
    # latency 측정 (1000회 timeit → p50/p95)
    uv run python backend/scripts/bench_vector_search.py --mode latency --iter 1000

    # recall@10 측정 (fixtures/recall_corpus.json 사용)
    uv run python backend/scripts/bench_vector_search.py --mode recall

ADR-020 §"Verification" 합격선:
    recall@10 >= baseline * 0.95
    p50 <= baseline * 1.0
    p95 <= baseline * 1.2
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from pathlib import Path
from statistics import median

from sqlalchemy import text

from src.common.database import async_session_factory
from src.embeddings.repository import EmbeddingRepository

FIXTURE_PATH = Path(__file__).parent.parent / "tests" / "embeddings" / "fixtures" / "recall_corpus.json"


def percentile(values: list[float], p: float) -> float:
    """간단한 percentile (sorted index 보간 없음)."""
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round(p / 100.0 * (len(s) - 1)))))
    return s[k]


async def measure_latency(iters: int) -> dict:
    """동일 쿼리 N회 실행 후 p50/p95 (ms)."""
    # 고정 query embedding 1개 사용 — 분포 측정이 아니라 단일 쿼리 latency
    qvec = [0.01] * 1536
    workspace_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
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
        "min_ms": round(min(timings_ms), 2),
        "max_ms": round(max(timings_ms), 2),
    }


async def measure_recall() -> dict:
    """recall@10 — fixtures/recall_corpus.json 사용."""
    if not FIXTURE_PATH.exists():
        return {"error": f"fixture 부재 — {FIXTURE_PATH}. Stage 3 §8-A 참조."}
    data = json.loads(FIXTURE_PATH.read_text())
    queries = data.get("queries", [])
    if not queries:
        return {"error": "fixture에 queries 없음"}

    hits = 0
    total = 0
    async with async_session_factory() as session:
        repo = EmbeddingRepository(session)
        for q in queries:
            qvec = q["embedding"]
            wid = uuid.UUID(q.get("workspace_id", "00000000-0000-0000-0000-000000000001"))
            expected = set(q.get("expected_top10", []))
            if not expected:
                continue
            results = await repo.vector_search(
                query_embedding=qvec,
                workspace_id=wid,
                limit=10,
            )
            got = {str(r.get("id")) for r in results}
            hits += len(expected & got)
            total += len(expected)
    return {
        "queries": len(queries),
        "recall@10": round(hits / total, 4) if total else 0.0,
        "hits": hits,
        "total": total,
    }


async def show_indexes() -> None:
    """현재 embedding_chunks / semantic_caches 인덱스 + 크기 출력."""
    async with async_session_factory() as session:
        r = await session.execute(
            text(
                """
                SELECT indexname, pg_size_pretty(pg_relation_size(indexname::regclass)) AS size
                FROM pg_indexes
                WHERE tablename IN ('embedding_chunks', 'semantic_caches')
                ORDER BY tablename, indexname
                """
            )
        )
        for row in r:
            print(f"  {row[0]}: {row[1]}")


async def main(*, mode: str, iters: int) -> int:
    print("--- 현재 인덱스 ---")
    await show_indexes()

    if mode == "latency":
        print(f"\n--- latency ({iters} iters) ---")
        result = await measure_latency(iters)
        print(json.dumps(result, indent=2))
    elif mode == "recall":
        print("\n--- recall@10 ---")
        result = await measure_recall()
        print(json.dumps(result, indent=2))
    elif mode == "both":
        print(f"\n--- latency ({iters} iters) ---")
        print(json.dumps(await measure_latency(iters), indent=2))
        print("\n--- recall@10 ---")
        print(json.dumps(await measure_recall(), indent=2))
    else:
        print(f"unknown mode: {mode}")
        return 1
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="pgvector HNSW 성능 측정")
    p.add_argument("--mode", choices=("latency", "recall", "both"), default="both")
    p.add_argument("--iter", dest="iters", type=int, default=1000)
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    raise SystemExit(asyncio.run(main(mode=args.mode, iters=args.iters)))
