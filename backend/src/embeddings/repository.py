# backend/src/embeddings/repository.py
"""임베딩 청크 + 시맨틱 캐시 DB 접근."""
import uuid

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.embeddings.models import EmbeddingChunk, SemanticCache

# I-9 4-C — 허용된 source_type 화이트리스트. 신규 도메인 추가 시 본 set + ADR 갱신 필수.
_ALLOWED_SOURCE_TYPES: frozenset[str] = frozenset(
    {"meeting", "note", "action", "inbox", "memory"}
)


async def _apply_hnsw_session_params(session: AsyncSession) -> None:
    # Sprint 16 ADR-020 / CONTEXT-MAP I-21: 벡터 검색 트랜잭션 진입 시 SET LOCAL.
    # pgvector >=0.8 의존. RBAC/visibility 포스트필터 결과 부족 자동 해소.
    await session.execute(text("SET LOCAL hnsw.ef_search = 40"))
    await session.execute(text("SET LOCAL hnsw.iterative_scan = 'relaxed_order'"))
    await session.execute(text("SET LOCAL hnsw.max_scan_tuples = 20000"))


class EmbeddingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- 청크 저장/삭제 ---

    async def save_chunks(self, chunks: list[EmbeddingChunk]) -> None:
        """벌크 저장."""
        for chunk in chunks:
            self.session.add(chunk)
        await self.session.flush()

    async def save_chunk(
        self,
        *,
        workspace_id: uuid.UUID,
        source_workspace_id: uuid.UUID,
        source_type: str,
        source_id: uuid.UUID,
        chunk_text: str,
        embedding: list[float],
        chunk_index: int = 0,
        chunk_level: int = 2,
        parent_chunk_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        metadata_json: dict | None = None,
    ) -> EmbeddingChunk:
        """단건 EmbeddingChunk insert + I-9 4-C assertion.

        - workspace_id == source_workspace_id: tenant 격리 위반 방지.
        - source_type ∈ _ALLOWED_SOURCE_TYPES: 의도치 않은 타입 인서트 차단.
        - workspace_id, source_id 필수.
        """
        assert workspace_id is not None, "I-9: workspace_id required for EmbeddingChunk"
        assert source_id is not None, "I-9: source_id required for EmbeddingChunk"
        assert source_workspace_id is not None, (
            "I-9 4-C: source_workspace_id required — caller must verify source entity workspace"
        )
        assert workspace_id == source_workspace_id, (
            f"I-9 4-C violation: chunk workspace_id ({workspace_id}) "
            f"!= source workspace_id ({source_workspace_id})"
        )
        assert source_type in _ALLOWED_SOURCE_TYPES, (
            f"I-9: invalid source_type {source_type!r}, allowed={sorted(_ALLOWED_SOURCE_TYPES)}"
        )

        chunk = EmbeddingChunk(
            workspace_id=workspace_id,
            project_id=project_id,
            source_id=source_id,
            source_type=source_type,
            chunk_text=chunk_text,
            chunk_index=chunk_index,
            chunk_level=chunk_level,
            parent_chunk_id=parent_chunk_id,
            embedding=embedding,
            metadata_json=metadata_json or {},
        )
        self.session.add(chunk)
        await self.session.flush()
        return chunk

    async def delete_by_source(
        self, source_type: str, source_id: uuid.UUID
    ) -> None:
        """특정 소스의 모든 청크 삭제 (재생성 전)."""
        # 자식 먼저 삭제 (FK 제약)
        await self.session.execute(
            delete(EmbeddingChunk).where(
                EmbeddingChunk.source_type == source_type,
                EmbeddingChunk.source_id == source_id,
                EmbeddingChunk.parent_chunk_id.isnot(None),
            )
        )
        await self.session.execute(
            delete(EmbeddingChunk).where(
                EmbeddingChunk.source_type == source_type,
                EmbeddingChunk.source_id == source_id,
            )
        )
        await self.session.flush()

    async def update_project_id(
        self, source_type: str, source_id: uuid.UUID, project_id: uuid.UUID | None
    ) -> None:
        """소스의 청크 project_id 일괄 업데이트."""
        await self.session.execute(
            text("""
                UPDATE embedding_chunks
                SET project_id = :pid
                WHERE source_type = :stype AND source_id = :sid
            """),
            {"pid": str(project_id) if project_id else None, "stype": source_type, "sid": str(source_id)},
        )
        await self.session.flush()

    # --- 검색 ---

    async def vector_search(
        self,
        query_embedding: list[float],
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        source_type: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """pgvector 코사인 유사도 검색 (HNSW halfvec, Sprint 16 ADR-020)."""
        # I-21: 트랜잭션 진입 시 SET LOCAL ef_search/iterative_scan/max_scan_tuples
        await _apply_hnsw_session_params(self.session)

        filters = "workspace_id = :wid AND chunk_level = 2"
        params: dict = {"wid": str(workspace_id), "limit": limit}

        if project_id:
            filters += " AND project_id = :pid"
            params["pid"] = str(project_id)
        if source_type:
            filters += " AND source_type = :stype"
            params["stype"] = source_type

        query = text(f"""
            SELECT id, chunk_text, source_id, source_type, metadata_json,
                   parent_chunk_id, created_at,
                   1 - (embedding <=> CAST(:qvec AS halfvec)) AS score
            FROM embedding_chunks
            WHERE {filters}
            ORDER BY embedding <=> CAST(:qvec AS halfvec)
            LIMIT :limit
        """)
        params["qvec"] = str(query_embedding)

        result = await self.session.execute(query, params)
        return [dict(r._mapping) for r in result]

    async def text_search(
        self,
        query_text: str,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        source_type: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """pg_trgm 트라이그램 유사도 검색."""
        filters = "workspace_id = :wid AND chunk_level = 2"
        params: dict = {"wid": str(workspace_id), "query": query_text, "limit": limit}

        if project_id:
            filters += " AND project_id = :pid"
            params["pid"] = str(project_id)
        if source_type:
            filters += " AND source_type = :stype"
            params["stype"] = source_type

        query = text(f"""
            SELECT id, chunk_text, source_id, source_type, metadata_json,
                   parent_chunk_id, created_at,
                   similarity(chunk_text, :query) AS score
            FROM embedding_chunks
            WHERE {filters}
              AND chunk_text % :query
            ORDER BY similarity(chunk_text, :query) DESC
            LIMIT :limit
        """)

        result = await self.session.execute(query, params)
        return [dict(r._mapping) for r in result]

    async def find_chunk_by_id(self, chunk_id: uuid.UUID) -> EmbeddingChunk | None:
        """ID로 청크 조회 (parent context 조회용)."""
        result = await self.session.execute(
            select(EmbeddingChunk).where(EmbeddingChunk.id == chunk_id)
        )
        return result.scalar_one_or_none()

    async def find_chunks_by_ids(
        self, ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, EmbeddingChunk]:
        """여러 청크를 한 번의 쿼리로 조회한다."""
        if not ids:
            return {}
        result = await self.session.execute(
            select(EmbeddingChunk).where(EmbeddingChunk.id.in_(ids))
        )
        return {c.id: c for c in result.scalars().all()}

    # --- 캐시 ---

    async def find_similar_cache(
        self,
        question_embedding: list[float],
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        threshold: float = 0.93,
    ) -> dict | None:
        """시맨틱 캐시 검색. similarity >= threshold → HIT (HNSW halfvec, Sprint 16 ADR-020)."""
        # I-21: 트랜잭션 진입 시 SET LOCAL ef_search/iterative_scan/max_scan_tuples
        await _apply_hnsw_session_params(self.session)

        filters = "workspace_id = :wid AND expires_at > now()"
        params: dict = {"wid": str(workspace_id), "threshold": threshold}

        if project_id:
            filters += " AND project_id = :pid"
            params["pid"] = str(project_id)

        query = text(f"""
            SELECT id, answer, sources, hit_count,
                   1 - (question_embedding <=> CAST(:qvec AS halfvec)) AS similarity
            FROM semantic_caches
            WHERE {filters}
              AND 1 - (question_embedding <=> CAST(:qvec AS halfvec)) >= :threshold
            ORDER BY question_embedding <=> CAST(:qvec AS halfvec)
            LIMIT 1
        """)
        params["qvec"] = str(question_embedding)

        result = await self.session.execute(query, params)
        row = result.first()
        if row:
            await self.session.execute(
                text("UPDATE semantic_caches SET hit_count = hit_count + 1 WHERE id = :id"),
                {"id": str(row._mapping["id"])},
            )
            return dict(row._mapping)
        return None

    async def save_cache(self, cache: SemanticCache) -> None:
        """캐시 항목 저장."""
        self.session.add(cache)
        await self.session.flush()

    async def delete_caches(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
    ) -> None:
        """캐시 무효화."""
        stmt = delete(SemanticCache).where(
            SemanticCache.workspace_id == workspace_id
        )
        if project_id:
            stmt = stmt.where(SemanticCache.project_id == project_id)
        await self.session.execute(stmt)
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()
