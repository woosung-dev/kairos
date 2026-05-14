# Memory DB 접근 — AsyncSession 유일 보유자
"""Memory Repository — DB access only.

backend rules §3 — AsyncSession은 Repository만 보유. service는 import 금지.
R3 추가: vector_search (pgvector typed bind A7) + search_keyword (O-B token overlap)
       + query embedding cache (C3 7일 TTL).
"""
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import bindparam, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.memory.models import (
    MemoryAICall,
    MemoryEvent,
    MemoryItem,
    MemoryQueryEmbeddingCache,
    PromotionAudit,
)

try:
    from pgvector.sqlalchemy import Vector

    _VECTOR_TYPE: Any = Vector(1536)
except ImportError:
    _VECTOR_TYPE = None


class MemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_item(self, item: MemoryItem) -> MemoryItem:
        self.session.add(item)
        await self.session.flush()
        return item

    async def get_by_id(
        self, memory_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> MemoryItem | None:
        stmt = select(MemoryItem).where(
            MemoryItem.id == memory_id,
            MemoryItem.workspace_id == workspace_id,
            MemoryItem.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_distilled(
        self,
        memory_id: uuid.UUID,
        distilled_json: dict,
        status: str,
    ) -> None:
        await self.session.execute(
            update(MemoryItem)
            .where(MemoryItem.id == memory_id)
            .values(distilled_json=distilled_json, status=status)
        )

    async def update_embedding(
        self,
        memory_id: uuid.UUID,
        embedding_chunk_id: uuid.UUID,
        status: str,
    ) -> None:
        await self.session.execute(
            update(MemoryItem)
            .where(MemoryItem.id == memory_id)
            .values(embedding_chunk_id=embedding_chunk_id, status=status)
        )

    async def update_status(
        self, memory_id: uuid.UUID, status: str
    ) -> None:
        await self.session.execute(
            update(MemoryItem)
            .where(MemoryItem.id == memory_id)
            .values(status=status)
        )

    async def update_transcript(
        self, memory_id: uuid.UUID, raw_content: str
    ) -> None:
        await self.session.execute(
            update(MemoryItem)
            .where(MemoryItem.id == memory_id)
            .values(raw_content=raw_content)
        )

    async def get_metrics_counts(self, workspace_id: uuid.UUID) -> dict[str, int]:
        """C7 — memory_events 기반 capture/recall/promote count."""
        from sqlalchemy import func
        stmt = (
            select(MemoryEvent.event_type, func.count(MemoryEvent.id))
            .where(MemoryEvent.workspace_id == workspace_id)
            .group_by(MemoryEvent.event_type)
        )
        result = await self.session.execute(stmt)
        return {row[0]: int(row[1]) for row in result.all()}

    async def get_recall_latency_percentiles(
        self, workspace_id: uuid.UUID
    ) -> tuple[int | None, int | None]:
        """C7 — recall latency p50/p95 (PostgreSQL percentile_cont)."""
        stmt = text(
            """
            SELECT
                percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms) AS p50,
                percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95
            FROM memory_events
            WHERE workspace_id = :wid
              AND event_type = 'recall'
              AND latency_ms IS NOT NULL
            """
        )
        result = await self.session.execute(stmt, {"wid": workspace_id})
        row = result.one_or_none()
        if row is None:
            return None, None
        p50 = int(row[0]) if row[0] is not None else None
        p95 = int(row[1]) if row[1] is not None else None
        return p50, p95

    async def list_expired_audio(self, cutoff: datetime) -> list[MemoryItem]:
        """Sprint 15 R-CRON — 생성 후 cutoff 이전 + r2_audio_key 보유한 MemoryItem 목록."""
        stmt = select(MemoryItem).where(
            MemoryItem.r2_audio_key.is_not(None),
            MemoryItem.created_at < cutoff,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def clear_r2_audio_key(self, memory_id: uuid.UUID) -> None:
        """r2_audio_key NULL 처리 — R2 객체 삭제 후 호출."""
        await self.session.execute(
            update(MemoryItem)
            .where(MemoryItem.id == memory_id)
            .values(r2_audio_key=None)
        )

    async def save_ai_call(self, call: MemoryAICall) -> None:
        self.session.add(call)

    async def save_event(self, event: MemoryEvent) -> None:
        self.session.add(event)

    async def save_promotion_audit(
        self, audit: PromotionAudit
    ) -> PromotionAudit:
        """R6: promotion_audit row 저장 — id flush 후 반환."""
        self.session.add(audit)
        await self.session.flush()
        return audit

    async def commit(self) -> None:
        await self.session.commit()

    # ── R3 recall ──

    async def vector_search(
        self,
        workspace_id: uuid.UUID,
        query_embedding: list[float],
        top_k: int,
    ) -> list[tuple]:
        """pgvector cosine similarity (A7 typed bind). I-9 workspace_id 강제."""
        sql = text(
            """
            SELECT mi.id, mi.distilled_json, mi.raw_content, mi.created_at,
                   1 - (ec.embedding <=> :qvec) AS score
            FROM embedding_chunks ec
            JOIN memory_items mi ON ec.source_id = mi.id
            WHERE ec.workspace_id = :wid
              AND ec.source_type = 'memory'
              AND mi.deleted_at IS NULL
            ORDER BY ec.embedding <=> :qvec
            LIMIT :limit
            """
        )
        if _VECTOR_TYPE is not None:
            sql = sql.bindparams(bindparam("qvec", type_=_VECTOR_TYPE))
        result = await self.session.execute(
            sql,
            {
                "qvec": query_embedding,
                "wid": workspace_id,
                "limit": top_k,
            },
        )
        return list(result.all())

    async def search_keyword(
        self,
        workspace_id: uuid.UUID,
        tokens: list[str],
        limit: int,
    ) -> list[tuple[MemoryItem, int]]:
        """O-B: token overlap count fallback. raw_content + distilled_json 텍스트 ILIKE 합산.

        BM25는 Sprint 17+ defer. workspace_id 필터 강제 (I-9).
        """
        if not tokens:
            return []
        params: dict[str, Any] = {"wid": workspace_id, "limit": limit}
        cases: list[str] = []
        for i, t in enumerate(tokens):
            tok_key = f"tok{i}"
            params[tok_key] = f"%{t}%"
            cases.append(
                f"(CASE WHEN mi.raw_content ILIKE :{tok_key} THEN 1 ELSE 0 END) + "
                f"(CASE WHEN COALESCE(mi.distilled_json::text, '') ILIKE :{tok_key} "
                f"THEN 1 ELSE 0 END)"
            )
        sum_expr = " + ".join(cases)
        sql = text(
            f"""
            SELECT mi.id, ({sum_expr}) AS overlap
            FROM memory_items mi
            WHERE mi.workspace_id = :wid
              AND mi.deleted_at IS NULL
              AND mi.status = 'active'
              AND ({sum_expr}) > 0
            ORDER BY overlap DESC, mi.created_at DESC
            LIMIT :limit
            """
        )
        result = await self.session.execute(sql, params)
        rows = list(result.all())
        if not rows:
            return []
        ids = [row[0] for row in rows]
        items_q = select(MemoryItem).where(MemoryItem.id.in_(ids))
        items_result = await self.session.execute(items_q)
        items_map = {item.id: item for item in items_result.scalars().all()}
        return [
            (items_map[row[0]], int(row[1]))
            for row in rows
            if row[0] in items_map
        ]

    async def get_query_embedding_cache(
        self,
        workspace_id: uuid.UUID,
        normalized_query: str,
        ttl_days: int = 7,
    ) -> list[float] | None:
        """C3: 7일 TTL cache lookup."""
        cutoff = datetime.utcnow() - timedelta(days=ttl_days)
        stmt = select(MemoryQueryEmbeddingCache).where(
            MemoryQueryEmbeddingCache.workspace_id == workspace_id,
            MemoryQueryEmbeddingCache.normalized_query == normalized_query,
            MemoryQueryEmbeddingCache.created_at >= cutoff,
        )
        result = await self.session.execute(stmt)
        cached = result.scalar_one_or_none()
        if cached is None:
            return None
        return list(cached.embedding) if cached.embedding else None

    async def save_query_embedding_cache(
        self,
        workspace_id: uuid.UUID,
        normalized_query: str,
        embedding: list[float],
    ) -> None:
        """C3: cache 저장. composite PK 중복 시 INSERT skip (race condition safe)."""
        # PostgreSQL ON CONFLICT DO NOTHING — 동시 recall 두 건이 동일 query 미스 시 두 번째 INSERT가 IntegrityError 일으키지 않음
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = (
            pg_insert(MemoryQueryEmbeddingCache.__table__)
            .values(
                workspace_id=workspace_id,
                normalized_query=normalized_query,
                embedding=embedding,
            )
            .on_conflict_do_nothing(
                index_elements=["workspace_id", "normalized_query"]
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()
