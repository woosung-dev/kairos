# backend/src/rag/service.py
"""RAG 서비스 — 캐시 확인 → Hybrid Search → RRF → Gemini SSE."""
import json
import logging
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta

from src.embeddings.models import SemanticCache
from src.embeddings.repository import EmbeddingRepository
from src.embeddings.service import EmbeddingService
from src.services.ai_processing import AIProcessingService

logger = logging.getLogger(__name__)


class RagService:
    def __init__(
        self,
        embedding_repo: EmbeddingRepository,
        embedding_service: EmbeddingService,
        ai_service: AIProcessingService,
    ) -> None:
        self.embedding_repo = embedding_repo
        self.embedding_service = embedding_service
        self.ai_service = ai_service

    async def _advance_onboarding(self, user_id: uuid.UUID) -> None:
        """Sprint 22 OBN-02: 첫 RAG 성공 응답 시 step=4 + onboarded_at.

        self.embedding_repo.session 재사용 (DI 통한 already-injected session).
        Codex 2차 finding P2: cache-hit / cache-miss 양 path 모두 commit 명시 — 다른 hook 처럼
        domain commit 이 동반되지 않으므로 본 위치에서 직접 commit 안 하면 rollback 됨.
        실패해도 RAG 응답 자체는 영향 받지 않도록 graceful (비치명적).
        """
        try:
            from src.onboarding.service import OnboardingService
            session = self.embedding_repo.session
            onboarding = OnboardingService(session)
            await onboarding.increment_step(user_id, 4)
            await session.commit()
        except Exception as ob_err:
            logger.warning("onboarding step=4 advance 실패 (비치명적): %s", ob_err)

    async def ask(
        self,
        question: str,
        workspace_id: uuid.UUID,
        requester_user_id: uuid.UUID,
        requester_role: str,
        project_id: uuid.UUID | None = None,
        time_range: str | None = None,
        source_type: str | None = None,
    ) -> AsyncGenerator[dict, None]:
        """RAG 파이프라인. SSE 이벤트를 yield.

        ISSUE-040 fix: requester_user_id + requester_role 을 받아 vector/text
        검색에서 ADR-014 visibility filter 적용. 글로벌 쿼리 (project_id=None)
        에서도 private project chunks 가 비-멤버에게 노출되지 않도록.
        """

        # [1] 질문 임베딩
        t_start = time.perf_counter()
        embeddings = await self.embedding_service.generate_embeddings([question])
        question_embedding = embeddings[0]
        t_embed = time.perf_counter()

        # [2] Semantic Cache 확인 — BL-041: requester visibility 검증 포함
        # Codex F-2 fix (Sprint 24 Wave 2 P2): time_range filter 있을 때 cache skip.
        # cache key 가 question/workspace/project 기반이라 time_range 무관 hit 시
        # unfiltered (전체 기간) 결과 반환 위험. 안전한 default = filtered query 는
        # cache miss 처리 (cache key 확장은 별도 BL).
        is_time_filtered = time_range is not None and time_range != "all"
        cache_hit = None
        if not is_time_filtered:
            cache_hit = await self.embedding_repo.find_similar_cache(
                question_embedding,
                workspace_id,
                requester_user_id=requester_user_id,
                requester_role=requester_role,
                project_id=project_id,
            )
        # CAND-E completeness: CAND-A fix 이전에 저장된 캐시는 sources 에 "sourceId"
        # 키가 없다 (fresh 검색만 _format_sources 로 sourceId 부여). sourceId 없는
        # 캐시를 그대로 serve 하면 FE SourceViewer 가 chunk id 로 폴백 → /meetings/{chunkId}
        # 404 retry storm. 하나라도 sourceId 부재면 cache MISS 로 처리 → fresh 검색
        # (sourceId 부여) 으로 fall-through. cache 는 재생성 시 자연히 치유된다.
        if cache_hit and not all(
            isinstance(s, dict) and "sourceId" in s
            for s in cache_hit.get("sources", [])
        ):
            cache_hit = None
        if cache_hit:
            yield {
                "event": "search_results",
                "data": json.dumps(
                    {"chunks": cache_hit["sources"]}, ensure_ascii=False
                ),
            }
            yield {
                "event": "answer",
                "data": json.dumps(
                    {"token": cache_hit["answer"]}, ensure_ascii=False
                ),
            }
            # Sprint 22 OBN-02: cache hit 도 첫 RAG 성공 응답 — step=4 advance.
            await self._advance_onboarding(requester_user_id)
            yield {
                "event": "done",
                "data": json.dumps(
                    {"cached": True, "sourceCount": len(cache_hit["sources"])}
                ),
            }
            return

        # [3] Thinking
        yield {
            "event": "thinking",
            "data": json.dumps({"status": "검색 중..."}, ensure_ascii=False),
        }

        # [4] Hybrid Search — visibility filter 포함 (ISSUE-040)
        # Sprint 24 Wave 2 T-RAG-TIME-FILTER: time_range chain 전달.
        # PERF-r2-3 판정 근거: vector/text 개별 계측 (병렬화 이득 = min(vector, text)).
        t0 = time.perf_counter()
        vector_results = await self.embedding_repo.vector_search(
            question_embedding,
            workspace_id,
            requester_user_id=requester_user_id,
            requester_role=requester_role,
            project_id=project_id,
            source_type=source_type,
            time_range=time_range,
            limit=50,
        )
        vector_ms = (time.perf_counter() - t0) * 1000
        t0 = time.perf_counter()
        text_results = await self.embedding_repo.text_search(
            question,
            workspace_id,
            requester_user_id=requester_user_id,
            requester_role=requester_role,
            project_id=project_id,
            source_type=source_type,
            time_range=time_range,
            limit=50,
        )
        text_ms = (time.perf_counter() - t0) * 1000

        # [5] RRF 융합
        fused = self._reciprocal_rank_fusion(text_results, vector_results, top_n=10)

        if not fused:
            yield {
                "event": "answer",
                "data": json.dumps(
                    {"token": "제공된 소스에서 관련 정보를 찾지 못했습니다."},
                    ensure_ascii=False,
                ),
            }
            yield {
                "event": "done",
                "data": json.dumps({"cached": False, "sourceCount": 0}),
            }
            return

        # [6] Context Enrichment — parent 청크 포함
        # PERF-r2-7: enrich(find_chunks_by_ids 1 RTT) 개별 계측.
        t0 = time.perf_counter()
        enriched = await self._enrich_context(fused)
        enrich_ms = (time.perf_counter() - t0) * 1000

        # [7] search_results 이벤트
        sources_for_client = self._format_sources(enriched)
        yield {
            "event": "search_results",
            "data": json.dumps(
                {"chunks": sources_for_client}, ensure_ascii=False
            ),
        }

        # [8] Generation (Gemini SSE) — SafetyFilter / API 오류 graceful degrade.
        # 5xx 대신 SSE error event + done event 송출 후 캐시 저장 skip.
        sources_text = self._format_sources_for_prompt(enriched)

        # PERF-SSE-COMMIT: 검색 read 트랜잭션을 스트리밍 진입 전에 종료 — Gemini
        # 스트리밍(수 초) 동안 DB 커넥션을 pool 에 반납. 동시 스트림 수만큼 커넥션이
        # 잠기면 pool(15) 고갈로 전체 API 가 블로킹되는 것을 방지. 이후 cache save /
        # onboarding 은 새 트랜잭션(autobegin) 으로 각자 commit.
        # PERF-r2-7: commit(1 RTT) 개별 계측.
        t0 = time.perf_counter()
        await self.embedding_repo.commit()
        commit_ms = (time.perf_counter() - t0) * 1000
        t_search = time.perf_counter()

        full_answer = ""
        try:
            async for token in self.ai_service.stream_rag_answer(question, sources_text):
                full_answer += token
                yield {
                    "event": "answer",
                    "data": json.dumps({"token": token}, ensure_ascii=False),
                }
        except Exception as ai_err:
            # SafetyFilter / 빈 candidate / google.genai.errors / 네트워크 오류 등 모두 graceful.
            logger.exception("RAG Gemini 스트리밍 실패 — graceful degrade: %s", ai_err)
            yield {
                "event": "error",
                "data": json.dumps(
                    {
                        "message": "질문을 처리할 수 없습니다. 다시 시도해주세요.",
                        "retryAfter": 3,
                    },
                    ensure_ascii=False,
                ),
            }
            yield {
                "event": "done",
                "data": json.dumps({"cached": False, "sourceCount": 0}),
            }
            return

        # 빈 답변 — 캐시 오염 방지 위해 저장 skip
        if not full_answer.strip():
            yield {
                "event": "done",
                "data": json.dumps(
                    {"cached": False, "sourceCount": len(sources_for_client)}
                ),
            }
            return

        # [9] Cache Store — BL-042: max_visibility 동시 저장 (fast path 인덱스)
        try:
            source_chunk_ids = [
                s["id"] for s in sources_for_client
                if isinstance(s, dict) and "id" in s
            ]
            max_vis = await self.embedding_repo.compute_max_visibility(source_chunk_ids)
            cache = SemanticCache(
                workspace_id=workspace_id,
                project_id=project_id,
                question=question,
                question_embedding=question_embedding,
                answer=full_answer,
                sources=sources_for_client,
                max_visibility=max_vis,
                expires_at=datetime.utcnow() + timedelta(days=7),
            )
            # Codex F-2 fix: time_range filter 적용된 answer 는 cache 저장 skip
            # (다른 filter / no-filter 사용자에게 누수 방지)
            if not is_time_filtered:
                await self.embedding_repo.save_cache(cache)
                await self.embedding_repo.commit()
        except Exception as cache_err:
            logger.warning("캐시 저장 실패 (비치명적): %s", cache_err)

        # Sprint 22 OBN-02: 첫 RAG 성공 응답 — step=4 advance + onboarded_at set.
        await self._advance_onboarding(requester_user_id)

        # BL-S27e-1 관측: stage 별 latency 분포 (p95 < 5s 목표 판단 근거)
        t_llm = time.perf_counter()
        logger.info(
            "rag.timing embed=%.0fms search=%.0fms vector=%.0fms text=%.0fms "
            "enrich=%.0fms commit=%.0fms llm=%.0fms total=%.0fms",
            (t_embed - t_start) * 1000,
            (t_search - t_embed) * 1000,
            vector_ms,
            text_ms,
            enrich_ms,
            commit_ms,
            (t_llm - t_search) * 1000,
            (t_llm - t_start) * 1000,
        )

        yield {
            "event": "done",
            "data": json.dumps(
                {"cached": False, "sourceCount": len(sources_for_client)}
            ),
        }

    @staticmethod
    def _reciprocal_rank_fusion(
        text_results: list[dict],
        vector_results: list[dict],
        k: int = 60,
        top_n: int = 10,
    ) -> list[dict]:
        """RRF 융합. k=60 표준값."""
        scores: dict[str, float] = {}
        result_map: dict[str, dict] = {}

        for rank, r in enumerate(text_results):
            rid = str(r["id"])
            scores[rid] = scores.get(rid, 0) + 1 / (k + rank + 1)
            result_map[rid] = r

        for rank, r in enumerate(vector_results):
            rid = str(r["id"])
            scores[rid] = scores.get(rid, 0) + 1 / (k + rank + 1)
            result_map[rid] = r

        sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
        return [result_map[rid] for rid in sorted_ids[:top_n]]

    async def _enrich_context(self, results: list[dict]) -> list[dict]:
        """Level 2 검색 결과에 parent Level 1 컨텍스트 추가. 배치 쿼리 1회."""
        # uuid.UUID(str(...)) — DB에서 UUID 객체로 올 수도 있고 문자열로 올 수도 있어 str 경유
        parent_ids = [
            uuid.UUID(str(r["parent_chunk_id"]))
            for r in results if r.get("parent_chunk_id")
        ]
        parents = await self.embedding_repo.find_chunks_by_ids(parent_ids) if parent_ids else {}
        enriched = []
        for r in results:
            parent_text = ""
            pid = r.get("parent_chunk_id")
            if pid:
                parent = parents.get(uuid.UUID(str(pid)))
                if parent:
                    parent_text = parent.chunk_text
            enriched.append({**r, "parent_text": parent_text})
        return enriched

    @staticmethod
    def _format_sources(results: list[dict]) -> list[dict]:
        """클라이언트용 소스 포맷."""
        sources = []
        for r in results:
            meta = r.get("metadata_json") or {}
            created = r.get("created_at")
            freshness = "recent"
            if created:
                if isinstance(created, str):
                    try:
                        created = datetime.fromisoformat(created)
                    except ValueError:
                        created = None
                if created:
                    age = datetime.utcnow() - created
                    if age > timedelta(days=90):
                        freshness = "stale"
                    elif age > timedelta(days=30):
                        freshness = "normal"

            sources.append({
                "id": str(r["id"]),
                # CAND-E: 클라이언트의 SourceViewer full-detail fetch 는 source 엔티티 id 가
                # 필요하다. id(=EmbeddingChunk PK)로 /meetings/{id} 를 호출하면 항상 404 →
                # console retry storm. source_id(=meeting/note PK)를 별도 노출한다.
                # source_id 부재 시(구 캐시 등) id 로 폴백 → 회귀 없음(기존 동작 유지).
                "sourceId": str(r.get("source_id") or r["id"]),
                "text": r["chunk_text"][:200],
                "source": meta.get("title", ""),
                "sourceType": r.get("source_type", ""),
                "date": created.isoformat() if created else "",
                "speaker": meta.get("speaker"),
                "score": round(float(r.get("score", 0)), 3),
                "freshness": freshness,
            })
        return sources

    @staticmethod
    def _format_sources_for_prompt(results: list[dict]) -> str:
        """Gemini 프롬프트용 소스 텍스트."""
        parts = []
        for i, r in enumerate(results, 1):
            meta = r.get("metadata_json") or {}
            header = f"[소스 {i}] {meta.get('title', '제목 없음')}"
            if meta.get("speaker"):
                header += f" — 발언자: {meta['speaker']}"
            created = r.get("created_at")
            if created:
                if isinstance(created, datetime):
                    header += f" ({created.strftime('%Y-%m-%d')})"
                elif isinstance(created, str):
                    header += f" ({created[:10]})"

            text = r.get("parent_text") or r["chunk_text"]
            parts.append(f"{header}\n{text}")
        return "\n\n---\n\n".join(parts)
