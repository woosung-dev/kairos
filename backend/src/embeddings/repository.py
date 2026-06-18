# backend/src/embeddings/repository.py
"""임베딩 청크 + 시맨틱 캐시 DB 접근."""
import uuid
from datetime import timedelta

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import delete, select, text

from src.embeddings.models import EmbeddingChunk, SemanticCache

# I-9 4-C — 허용된 source_type 화이트리스트. 신규 도메인 추가 시 본 set + ADR 갱신 필수.
_ALLOWED_SOURCE_TYPES: frozenset[str] = frozenset(
    {"meeting", "note", "action", "inbox", "memory"}
)

# Sprint 24 Wave 2 T-RAG-TIME-FILTER (BUG-POW-006):
# RAG 검색에 created_at 시간 필터 적용. None / "all" → 필터 없음.
# 허용 값 화이트리스트 — SQL injection 방지 (asyncpg interval native binding 위해
# timedelta 사용 — string interval literal 은 asyncpg DataError).
TIME_RANGE_INTERVAL: dict[str, timedelta | None] = {
    "1w": timedelta(days=7),
    "1m": timedelta(days=30),
    "3m": timedelta(days=90),
    "6m": timedelta(days=180),
    "all": None,
}


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
        await self.session.exec(
            delete(EmbeddingChunk).where(
                EmbeddingChunk.source_type == source_type,
                EmbeddingChunk.source_id == source_id,
                EmbeddingChunk.parent_chunk_id.isnot(None),
            )
        )
        await self.session.exec(
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

    async def find_chunk_project_ids(
        self, source_type: str, source_id: uuid.UUID
    ) -> set[uuid.UUID | None]:
        """소스 청크들의 distinct project_id 집합 (Sprint 29 R1 notes-stale).

        project_id 변경 시 변경 전 scope 의 SemanticCache 를 무효화하기 위해
        갱신 직전의 기존 project_id 들을 수집한다.
        """
        result = await self.session.execute(
            text(
                "SELECT DISTINCT project_id FROM embedding_chunks "
                "WHERE source_type = :stype AND source_id = :sid"
            ),
            {"stype": source_type, "sid": str(source_id)},
        )
        return {row[0] for row in result}

    # --- 검색 ---

    @staticmethod
    def _visibility_filter_sql() -> str:
        """ADR-014 R-10: 검색 결과에서 requester 가 접근 불가한 project chunks 제외.

        chunk 의 project_id 가:
        - NULL : 프로젝트 미연결 chunk → 통과
        - admin/owner role : 모든 visibility 통과
        - public project : 통과
        - draft project : created_by_id == requester 일 때만 통과
        - private project : ProjectMember 매핑 있고 + 현 워크스페이스 멤버일 때만 통과

        ISSUE-040 fix — 이전엔 workspace_id + (optional)project_id 만 필터 →
        member 가 global RAG 쿼리 시 private project 의 chunks 가 응답에 포함.

        CAND-B fix — private 분기에 workspace_members EXISTS 가드 추가. 워크스페이스에서
        제거된 멤버의 orphan ProjectMember 행이 잔재로 남아도 private chunk 접근을
        되찾지 못하도록 차단 (offboard→re-invite privilege residue).
        """
        return """
            AND (
                project_id IS NULL
                OR :req_role IN ('admin', 'owner')
                OR EXISTS (
                    SELECT 1 FROM projects p
                    WHERE p.id = embedding_chunks.project_id
                      AND (
                        p.visibility = 'public'
                        OR (p.visibility = 'draft' AND p.created_by_id = :req_uid)
                        OR (p.visibility = 'private' AND EXISTS (
                            SELECT 1 FROM project_members pm
                            WHERE pm.project_id = p.id AND pm.user_id = :req_uid
                              AND EXISTS (
                                SELECT 1 FROM workspace_members wm
                                WHERE wm.workspace_id = p.workspace_id
                                  AND wm.user_id = :req_uid
                              )
                        ))
                      )
                )
            )
        """

    async def vector_search(
        self,
        query_embedding: list[float],
        workspace_id: uuid.UUID,
        requester_user_id: uuid.UUID,
        requester_role: str,
        project_id: uuid.UUID | None = None,
        source_type: str | None = None,
        time_range: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """pgvector 코사인 유사도 검색 (HNSW halfvec, Sprint 16 ADR-020).

        Sprint 24 Wave 2 T-RAG-TIME-FILTER (BUG-POW-006):
        time_range ∈ {"1w","1m","3m","6m","all"} → created_at >= now() - interval 필터.
        화이트리스트 외 값 / None / "all" → 필터 없음 (fail-safe, SQL injection 차단).
        """
        # I-21: 트랜잭션 진입 시 SET LOCAL ef_search/iterative_scan/max_scan_tuples
        await _apply_hnsw_session_params(self.session)

        filters = "workspace_id = :wid AND chunk_level = 2"
        params: dict = {
            "wid": str(workspace_id),
            "limit": limit,
            "req_uid": str(requester_user_id),
            "req_role": requester_role,
        }

        if project_id:
            filters += " AND project_id = :pid"
            params["pid"] = str(project_id)
        if source_type:
            filters += " AND source_type = :stype"
            params["stype"] = source_type

        # T-RAG-TIME-FILTER: 화이트리스트 매핑 — 미일치 시 silently skip.
        interval = TIME_RANGE_INTERVAL.get(time_range) if time_range else None
        if interval is not None:
            # asyncpg 가 timedelta 를 interval 로 바인딩 → 명시 cast 로 timestamp 산출.
            # `now() - $X::interval` 는 timestamptz 반환 → embedding_chunks.created_at
            # (timestamp without time zone) 과 비교 시 자동 timestamp 캐스팅 불가.
            # 양쪽 캐스팅으로 type 정합 보장.
            filters += (
                " AND created_at >= CAST(now() - CAST(:time_window AS interval)"
                " AS timestamp)"
            )
            params["time_window"] = interval

        visibility_clause = self._visibility_filter_sql()

        query = text(f"""
            SELECT id, chunk_text, source_id, source_type, metadata_json,
                   parent_chunk_id, created_at,
                   1 - (embedding <=> CAST(:qvec AS halfvec)) AS score
            FROM embedding_chunks
            WHERE {filters}
              {visibility_clause}
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
        requester_user_id: uuid.UUID,
        requester_role: str,
        project_id: uuid.UUID | None = None,
        source_type: str | None = None,
        time_range: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """pg_trgm 트라이그램 유사도 검색.

        Sprint 24 Wave 2 T-RAG-TIME-FILTER: time_range 필터는 vector_search 와 동일 의미.
        """
        filters = "workspace_id = :wid AND chunk_level = 2"
        params: dict = {
            "wid": str(workspace_id),
            "query": query_text,
            "limit": limit,
            "req_uid": str(requester_user_id),
            "req_role": requester_role,
        }

        if project_id:
            filters += " AND project_id = :pid"
            params["pid"] = str(project_id)
        if source_type:
            filters += " AND source_type = :stype"
            params["stype"] = source_type

        interval = TIME_RANGE_INTERVAL.get(time_range) if time_range else None
        if interval is not None:
            # asyncpg 가 timedelta 를 interval 로 바인딩 → 명시 cast 로 timestamp 산출.
            # `now() - $X::interval` 는 timestamptz 반환 → embedding_chunks.created_at
            # (timestamp without time zone) 과 비교 시 자동 timestamp 캐스팅 불가.
            # 양쪽 캐스팅으로 type 정합 보장.
            filters += (
                " AND created_at >= CAST(now() - CAST(:time_window AS interval)"
                " AS timestamp)"
            )
            params["time_window"] = interval

        visibility_clause = self._visibility_filter_sql()

        query = text(f"""
            SELECT id, chunk_text, source_id, source_type, metadata_json,
                   parent_chunk_id, created_at,
                   similarity(chunk_text, :query) AS score
            FROM embedding_chunks
            WHERE {filters}
              {visibility_clause}
              AND chunk_text % :query
            ORDER BY similarity(chunk_text, :query) DESC
            LIMIT :limit
        """)

        result = await self.session.execute(query, params)
        return [dict(r._mapping) for r in result]

    async def find_chunk_by_id(self, chunk_id: uuid.UUID) -> EmbeddingChunk | None:
        """ID로 청크 조회 (parent context 조회용)."""
        return (await self.session.exec(
            select(EmbeddingChunk).where(EmbeddingChunk.id == chunk_id)
        )).one_or_none()

    async def find_chunks_by_ids(
        self, ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, EmbeddingChunk]:
        """여러 청크를 한 번의 쿼리로 조회한다."""
        if not ids:
            return {}
        return {
            c.id: c
            for c in (await self.session.exec(
                select(EmbeddingChunk).where(EmbeddingChunk.id.in_(ids))
            )).all()
        }

    # --- 캐시 ---

    async def find_similar_cache(
        self,
        question_embedding: list[float],
        workspace_id: uuid.UUID,
        requester_user_id: uuid.UUID,
        requester_role: str,
        project_id: uuid.UUID | None = None,
        threshold: float = 0.93,
    ) -> dict | None:
        """시맨틱 캐시 검색. similarity >= threshold → HIT (HNSW halfvec, Sprint 16 ADR-020).

        BL-041: cache hit 시 sources 의 chunk 들 중 하나라도 requester 가 visibility
        규칙상 접근 불가하면 cache miss 처리 → 데이터 누출 차단. admin 이 만든
        cache 가 비-멤버 hit 시 private project 노출되던 ISSUE-040 후속 fix.
        """
        # I-21: 트랜잭션 진입 시 SET LOCAL ef_search/iterative_scan/max_scan_tuples
        await _apply_hnsw_session_params(self.session)

        filters = "workspace_id = :wid AND expires_at > now()"
        params: dict = {"wid": str(workspace_id), "threshold": threshold}

        if project_id:
            filters += " AND project_id = :pid"
            params["pid"] = str(project_id)

        query = text(f"""
            SELECT id, answer, sources, hit_count, max_visibility,
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
        if not row:
            return None

        # BL-041 + BL-042: cache hit 시 sources visibility 검증.
        # - admin/owner : 모든 visibility 통과
        # - max_visibility = 'public' : fast path (모든 사용자 통과)
        # - 그 외 : _all_chunks_visible anti-join 으로 chunk 별 검증
        is_admin = requester_role in ("admin", "owner")
        max_vis = row._mapping.get("max_visibility", "public")
        if not is_admin and max_vis != "public":
            sources = row._mapping["sources"] or []
            chunk_ids = [s["id"] for s in sources if isinstance(s, dict) and "id" in s]
            if chunk_ids and not await self._all_chunks_visible(
                chunk_ids, requester_user_id
            ):
                # 누출 위험 — cache miss 처리. hit_count 증가도 skip.
                return None

        await self.session.execute(
            text("UPDATE semantic_caches SET hit_count = hit_count + 1 WHERE id = :id"),
            {"id": str(row._mapping["id"])},
        )
        return dict(row._mapping)

    async def compute_max_visibility(self, chunk_ids: list[str]) -> str:
        """BL-042: sources 의 chunk 들이 참조하는 project 들 중 가장 제한적인
        visibility 반환 ('public' < 'draft' < 'private').

        cache 저장 시 호출 — find_similar_cache 의 fast path 인덱스용.
        chunk.project_id IS NULL 또는 chunk 자체 없으면 'public' (대응 안 함).
        """
        if not chunk_ids:
            return "public"
        query = text("""
            SELECT MAX(
              CASE p.visibility
                WHEN 'private' THEN 3
                WHEN 'draft' THEN 2
                WHEN 'public' THEN 1
                ELSE 0
              END
            ) AS rank
            FROM embedding_chunks ec
            JOIN projects p ON p.id = ec.project_id
            WHERE ec.id = ANY(:chunk_ids)
        """)
        result = await self.session.execute(
            query, {"chunk_ids": [str(cid) for cid in chunk_ids]}
        )
        rank = result.scalar_one_or_none()
        if rank is None or rank <= 1:
            return "public"
        if rank == 2:
            return "draft"
        return "private"

    async def _all_chunks_visible(
        self,
        chunk_ids: list[str],
        requester_user_id: uuid.UUID,
    ) -> bool:
        """BL-041: cache sources 의 모든 chunk 가 requester 에게 visibility 통과하는지.

        한 chunk 라도 fail → False 반환 → 호출자가 cache miss 처리.
        visibility 규칙은 _visibility_filter_sql 와 동일 (ADR-014):
        - chunk.project_id IS NULL → 통과
        - project.visibility = 'public' → 통과
        - project.visibility = 'draft' AND created_by_id = requester → 통과
        - project.visibility = 'private' AND ProjectMember 매핑 + 현 워크스페이스 멤버 → 통과

        CAND-B fix — private 분기에 workspace_members EXISTS 가드를 추가해
        _visibility_filter_sql 와 동일하게 유지 (orphan ProjectMember 잔재 차단).
        """
        if not chunk_ids:
            return True

        # 위반 chunk 1개라도 있는지 — anti-join 으로 1 round-trip 처리.
        # 위반 정의: project_id 있고, visibility 규칙 통과 안 함.
        query = text("""
            SELECT 1 FROM embedding_chunks ec
            WHERE ec.id = ANY(:chunk_ids)
              AND ec.project_id IS NOT NULL
              AND NOT EXISTS (
                SELECT 1 FROM projects p
                WHERE p.id = ec.project_id
                  AND (
                    p.visibility = 'public'
                    OR (p.visibility = 'draft' AND p.created_by_id = :req_uid)
                    OR (p.visibility = 'private' AND EXISTS (
                      SELECT 1 FROM project_members pm
                      WHERE pm.project_id = p.id AND pm.user_id = :req_uid
                        AND EXISTS (
                          SELECT 1 FROM workspace_members wm
                          WHERE wm.workspace_id = p.workspace_id
                            AND wm.user_id = :req_uid
                        )
                    ))
                  )
              )
            LIMIT 1
        """)
        result = await self.session.execute(
            query,
            {
                "chunk_ids": [str(cid) for cid in chunk_ids],
                "req_uid": str(requester_user_id),
            },
        )
        violation = result.first()
        return violation is None

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
        await self.session.exec(stmt)
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()
