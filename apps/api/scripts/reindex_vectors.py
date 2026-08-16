#!/usr/bin/env python3
# pgvector 인덱스 bloat 모니터링 + REINDEX CONCURRENTLY (Sprint 16 ADR-020)
"""pgvector HNSW 인덱스 운영 스크립트.

당근(Karrot) DB 밋업 1회 §5-B 노하우 — Vacuum 후 bloat은 남는다.
REINDEX CONCURRENTLY로 무중단 인덱스 재빌드.

사용 예:
    uv run python apps/api/scripts/reindex_vectors.py --dry-run
    uv run python apps/api/scripts/reindex_vectors.py             # bloat >= 30%만 reindex
    uv run python apps/api/scripts/reindex_vectors.py --force     # 강제 reindex

운영 가이드: docs/guides/pgvector-reindex.md.
"""
from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import text

from src.common.database import async_session_factory

THRESHOLD_BLOAT_RATIO = 0.30  # 30% 이상 dead_tuple_percent + free_percent
INDEXES = ("idx_chunks_hnsw", "idx_cache_hnsw")


async def check_bloat(index_name: str) -> tuple[float, str]:
    """pgstattuple로 bloat 비율 + 인덱스 크기 측정.

    Returns:
        (bloat_ratio, size_pretty)
    """
    async with async_session_factory() as session:
        await session.execute(text("CREATE EXTENSION IF NOT EXISTS pgstattuple"))
        # pgstattuple은 인덱스도 지원
        r = await session.execute(text("SELECT * FROM pgstattuple(:idx)"), {"idx": index_name})
        row = r.first()
        if not row:
            return 0.0, "unknown"
        dead = float(getattr(row, "dead_tuple_percent", 0.0) or 0.0)
        free = float(getattr(row, "free_percent", 0.0) or 0.0)
        bloat = (dead + free) / 100.0
        size_q = await session.execute(
            text("SELECT pg_size_pretty(pg_relation_size(:idx::regclass))"),
            {"idx": index_name},
        )
        size = size_q.scalar() or "unknown"
        return bloat, str(size)


async def reindex(index_name: str, *, dry_run: bool) -> None:
    """REINDEX CONCURRENTLY 실행 (autocommit 필요)."""
    if dry_run:
        print(f"[dry-run] would REINDEX INDEX CONCURRENTLY {index_name}")
        return
    async with async_session_factory() as session:
        conn = await session.connection()
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        await session.execute(text(f"REINDEX INDEX CONCURRENTLY {index_name}"))
        print(f"[done] REINDEX {index_name}")


async def main(*, dry_run: bool, force: bool) -> int:
    exit_code = 0
    for idx in INDEXES:
        try:
            bloat, size = await check_bloat(idx)
        except Exception as e:  # noqa: BLE001 — 운영 스크립트 안전
            print(f"[skip] {idx}: pgstattuple 측정 실패 — {e}")
            exit_code = 1
            continue
        print(f"{idx}: size={size}, bloat={bloat:.1%}")
        if bloat >= THRESHOLD_BLOAT_RATIO or force:
            try:
                await reindex(idx, dry_run=dry_run)
            except Exception as e:  # noqa: BLE001
                print(f"[fail] REINDEX {idx}: {e}")
                exit_code = 2
    return exit_code


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="pgvector HNSW 인덱스 운영 도구")
    p.add_argument("--dry-run", action="store_true", help="실제 REINDEX 없이 측정만")
    p.add_argument("--force", action="store_true", help="bloat 미달이어도 강제 REINDEX")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    raise SystemExit(asyncio.run(main(dry_run=args.dry_run, force=args.force)))
