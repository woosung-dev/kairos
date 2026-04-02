# backend/src/embeddings/repository.py
"""임베딩 청크 + 시맨틱 캐시 DB 접근."""
import uuid

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.embeddings.models import EmbeddingChunk, SemanticCache


class EmbeddingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- 청크 저장/삭제 ---

    async def save_chunks(self, chunks: list[EmbeddingChunk]) -> None:
        """벌크 저장."""
        for chunk in chunks:
            self.session.add(chunk)
        await self.session.flush()

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
        """pgvector 코사인 유사도 검색."""
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
                   1 - (embedding <=> :qvec::vector) AS score
            FROM embedding_chunks
            WHERE {filters}
            ORDER BY embedding <=> :qvec::vector
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

    # --- 캐시 ---

    async def find_similar_cache(
        self,
        question_embedding: list[float],
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        threshold: float = 0.93,
    ) -> dict | None:
        """시맨틱 캐시 검색. similarity >= threshold → HIT."""
        filters = "workspace_id = :wid AND expires_at > now()"
        params: dict = {"wid": str(workspace_id), "threshold": threshold}

        if project_id:
            filters += " AND project_id = :pid"
            params["pid"] = str(project_id)

        query = text(f"""
            SELECT id, answer, sources, hit_count,
                   1 - (question_embedding <=> :qvec::vector) AS similarity
            FROM semantic_caches
            WHERE {filters}
              AND 1 - (question_embedding <=> :qvec::vector) >= :threshold
            ORDER BY question_embedding <=> :qvec::vector
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
