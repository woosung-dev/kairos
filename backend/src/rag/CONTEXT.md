<!-- rag 도메인 — RAG 6-Layer 검색 + Gemini 답변 + SSE 스트리밍 -->

# rag CONTEXT

> 상위: `/backend/CONTEXT.md` → `/CONTEXT-MAP.md`. 상세 설계: `docs/architecture/rag-pipeline.md`.

---

## 1. 책임

- 사용자 질문 → 답변 생성 (워크스페이스/프로젝트 범위)
- SemanticCache 조회/저장 호출 (TTL 7일, 유사도 ≥0.93) — **저장소 소유는 embeddings**
- 하이브리드 검색 (벡터 + 키워드) → RRF 융합 → Gemini 답변
- 출처 인용 (sources 메타) 반환
- **SSE 스트리밍 응답** (chunk 누적)

## 2. 비책임

- SemanticCache 저장/조회 구현 자체 (`embeddings/repository`)
- 임베딩 생성/저장 (`embeddings` 도메인)
- 콘텐츠 영속화 (각 도메인)

---

## 3. 엔티티 (호출만, 소유 아님)

- **SemanticCache** — `embeddings/models.py:45` 정의, `embeddings/repository.py`가 저장/조회. RAG는 read/write 호출자.
- **EmbeddingChunk** — `embeddings` 도메인 소유. RAG는 read-only.

---

## 4. RAG 6-Layer (개념) ↔ 9 sub-step (코드)

**개념적 6-Layer** (PRD / AGENTS.md / docs/architecture/rag-pipeline.md 명명):
```
[1] Cache Lookup           SemanticCache (≥0.93 유사도) → hit 시 즉시 스트리밍 반환
[2] Query Processing       질문 정제 + 임베딩 생성 + 키워드 추출
[3] Hybrid Search          pgvector (chunk_level=2) + 키워드(검증 필요 — BM25/TS 추정)
[4] Rank Fusion (RRF, k=60) Reciprocal Rank Fusion으로 벡터/키워드 결과 융합 (Gemini re-rank 아님)
[5] Generation             Gemini 답변 + 인용 (sources) — SSE chunk stream
[6] Cache Store            결과 SemanticCache에 저장 (TTL 7일)
```

**코드 9 sub-step** (`rag/service.py` 주석):
```
[1] 질문 임베딩            [2] Semantic Cache 확인       [3] Thinking
[4] Hybrid Search          [5] RRF 융합 (k=60)            [6] Context Enrichment (parent 청크)
[7] search_results SSE 이벤트                            [8] Generation (Gemini SSE)
[9] Cache Store
```

> 두 표현은 정합. 6-Layer는 개념적 분류, 9 sub-step은 구현 세분. 헌법 R-1~R-9는 6-Layer 번호 기준.

---

## 5. 의존 (in/out) — Sprint 6 ADR-014 옵션 A 적용

**진입 = `RagPipelineService.ask` (orchestrator)** → 권한 검증 후 `RagService.ask` 위임. SSE 스트리밍 시작 *전*에 visibility/member 검증 완료 (ADR-014 검증 기준 C-6).

| 방향 | 대상 | 레벨 | 비고 |
|---|---|---|---|
| out (pipeline) | `projects/repository` | Repository (read-only) | visibility 권한 검증 (admin 우회 / draft creator / private member) |
| out (pipeline) | `rag/service` | Service (orchestrator 내부 위임) | RagService.ask AsyncGenerator 위임 |
| out (service) | `embeddings/{models, repository, service}` | service | RagService 내부 호출 — orchestrator 경유로 헌법 §4.2 정합 (ADR-014). 6-Layer 단계별 호출 다수 |
| out (service) | `services/ai_processing` | external wrapper | Gemini 답변 생성 |

---

## 6. 핵심 불변식

| # | 불변식 |
|---|---|
| R-1 | **검색 대상은 `chunk_level = 2` 만** (L2 paragraph) |
| R-2 | **워크스페이스 격리**: `workspace_id` 필터 + (선택) `project_id` 범위 |
| R-3 | **SemanticCache TTL 7일** — `expires_at` 자동 무효화 (embeddings 도메인 책임) |
| R-4 | **유사도 임계값 0.93** — 미만은 cache miss로 간주 |
| R-5 | **콘텐츠 변경 시 캐시 무효화** — `embedding_service.invalidate_cache()` 일부 구현됨 (`meetings/pipeline_service.py:200`). 정책 보강은 Phase B |
| R-6 | **Gemini 응답에는 항상 출처(sources) 인용 포함** — 인용 없는 답변 금지 |
| R-7 | **답변은 한국어 우선** — 사용자 질문 언어에 맞춤 |
| R-8 | **SSE 스트리밍**: `EventSourceResponse` (`sse_starlette.sse`) — 내부적으로 `text/event-stream`. `StreamingResponse` 직접 사용 금지 — 헌법 B-14 |
| R-9 | **융합 알고리즘은 RRF (Reciprocal Rank Fusion), k=60** — Gemini re-rank 아님. `service.py:152 _reciprocal_rank_fusion` |
| R-10 | **권한 검증은 `RagPipelineService.ask` 진입에서 SSE 시작 *전* 완료** (Sprint 6 ADR-014 옵션 A). visibility=draft → creator + admin/owner / visibility=private → ProjectMember + admin/owner. 검증 실패 시 `error` + `done` SSE 이벤트로 종료 (스트리밍 시작 안 함). 권한 누락이 ADR-010 M1 RAG 품질 시그널을 오염하지 않도록. |

---

## 7. 엔드포인트

> `/api/v1/workspaces/{workspace_id}/rag` prefix.

```
POST /ask    질문 → 답변 + 출처 (SSE 스트리밍, EventSourceResponse)
```

---

## 8. 엣지 케이스

- 검색 결과 0건 → "관련 콘텐츠를 찾을 수 없습니다" + 가이드
- 캐시 hit이지만 출처 콘텐츠 삭제됨 → 즉시 무효화 + 재검색
- Gemini API 실패 → 검색 결과만 반환 (요약 없이) — SSE error event
- 너무 짧은 질문 (< 5자) → 질문 재구성 요청

---

## 9. 부채 (CONTEXT-MAP §7)

- ~~D-3: `rag → embeddings.service` 직접 의존~~ **[해소 1차 2026-05-11, ADR-014 옵션 A]** — `RagPipelineService` 신설로 진입 권한 검증 + 위임. `RagService` 내부 6-Layer embedding 호출은 그대로 (cross-domain shared service 정책, ADR-014 §1). 완전 분리는 sprint 7+ 검토 (ADR-014 §"비용/리스크" R-3).
