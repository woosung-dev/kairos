<!-- rag 도메인 — RAG 6-Layer 검색 + Gemini 답변 + SSE 스트리밍 -->

# rag CONTEXT

> 상위: `/apps/backend/CONTEXT.md` → `/CONTEXT-MAP.md`. 상세 설계: `docs/architecture/rag-pipeline.md`.

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
                           인덱스: pgvector HNSW(halfvec, m=16, ef_construction=64, ef_search=40,
                                                iterative_scan=relaxed_order) — Sprint 16 ADR-020
[2] Query Processing       질문 정제 + 임베딩 생성 + 키워드 추출
[3] Hybrid Search          pgvector (chunk_level=2) + pg_trgm 키워드 검색 (`embedding_repo.text_search()`)
                           벡터 인덱스: 동일 HNSW(halfvec, ef_search=40, iterative_scan=relaxed_order)
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
| R-5 | **콘텐츠 변경 시 캐시 무효화와 안전한 재사용** — 콘텐츠 변경 경로의 무효화는 project scope로 남아 있다 (`notes/pipeline_service.py:75-77,149`, 2026-08-01 코드 기준; BL-NOTES-CACHE-2). 이 문서는 캐시 hit에서 삭제된 출처를 서빙하지 않아야 한다는 정책을 먼저 올바르게 적었지만, 2026-08-01 이전 구현은 그 정책을 따라가지 못했다. 현재 읽기·쓰기 보장은 R-15를 따른다. |
| R-6 | **Gemini 응답에는 항상 출처(sources) 인용 포함** — 인용 없는 답변 금지 |
| R-7 | **답변은 한국어 우선** — 사용자 질문 언어에 맞춤 |
| R-8 | **SSE 스트리밍**: `EventSourceResponse` (`sse_starlette.sse`) — 내부적으로 `text/event-stream`. `StreamingResponse` 직접 사용 금지 — 헌법 B-14 |
| R-9 | **융합 알고리즘은 RRF (Reciprocal Rank Fusion), k=60** — Gemini re-rank 아님. `service.py:152 _reciprocal_rank_fusion` |
| R-10 | **권한 검증은 `RagPipelineService.ask` 진입에서 SSE 시작 *전* 완료** (Sprint 6 ADR-014 옵션 A). visibility=draft → creator + admin/owner / visibility=private → ProjectMember + admin/owner. 검증 실패 시 `error` + `done` SSE 이벤트로 종료 (스트리밍 시작 안 함). 권한 누락이 ADR-010 M1 RAG 품질 시그널을 오염하지 않도록. |
| R-11 | **Gemini 예외는 graceful** — SafetyFilter / API 오류 / 네트워크 오류 발생 시 5xx 대신 SSE `error` + `done` 이벤트 송출 (Sprint 14 BUG-C01). 캐시 오염 방지를 위해 SemanticCache 저장 skip. 빈 답변(`full_answer.strip() == ""`)도 동일 정책. |
| R-12 | **질문 입력 검증** — `RagAskRequest.question` 은 strip 후 2자 이상 + 500자 이하 (Sprint 14 BUG-C01). prompt-injection 류 거대 입력 차단 + Pydantic 422로 5xx 회피. |
| R-13 | **Layer 1/3 진입 시 HNSW 세션 변수 강제** (Sprint 16 ADR-020 + CONTEXT-MAP I-21). `embeddings/repository.py`의 `_apply_hnsw_session_params(session)` 헬퍼가 `vector_search` / `find_similar_cache` 진입 직전 `SET LOCAL hnsw.ef_search=40` + `iterative_scan=relaxed_order` + `max_scan_tuples=20000` 적용. RAG 서비스가 별도 호출하지 않음 (embeddings 도메인 캡슐화). 결과: RBAC/visibility 포스트필터 적용 시 결과 부족 자동 해소. |
| R-14 | **외부 원본 source type** — `source_type` 허용값 SSOT는 `apps/backend/src/embeddings/repository.py`의 `_ALLOWED_SOURCE_TYPES`다. `save_chunk` insert 경로는 이 화이트리스트를 assert하고 `save_chunks`는 이를 우회하므로, `external_document`는 검증된 `save_chunk` 경로로 저장해 RAG 검색을 허용한다. 새 source type은 화이트리스트와 FE의 `(A)` 타입 union, `(B)` 좁은 캐스트/const 목록, `(C)` 라벨·아이콘·분기 구분을 함께 갱신한다. 상세 결정은 `docs/adr/026-external-source-ingest-rail.md` D6을 따른다. 검색 대상은 R-1에 따라 `chunk_level = 2`만이다. |
| R-15 | **SemanticCache 출처 무결성** (2026-08-01) — **읽기**: 비-admin 요청자에게는 `sources` 청크의 실제 가시성을 매번 재검사한다. 행이 없는 청크는 위반으로 본다. `max_visibility` 라벨은 더 이상 검증을 건너뛰는 근거가 아니다. **쓰기**: source 청크가 하나라도 사라진 상태에서는 캐시행을 만들지 않는다. admin/owner 우회는 검색 경로와 같은 정책으로 유지한다. |

> `max_visibility`는 BL-042의 fast path 인덱스에서 저장 시점 라벨로 강등됐다. 브라우저 QA의 scenario_b는 소스 청크가 살아 있는 상태에서 프로젝트 visibility가 `public`에서 `private`로 바뀌어 라벨이 stale해졌고, 변경 전에는 누출됐으나 현재 비-admin 요청에서는 차단됨을 관측했다 (`.claude/spike-gdrive/artifacts/QA.qa.json`, 2026-08-01).
>
> 남는 한계: 무효화 scope는 BL-NOTES-CACHE-2의 project 단위로 남아 있으며, admin에게는 삭제된 콘텐츠가 TTL 만료까지 서빙될 수 있다. 이는 권한 확대가 아니라 캐시 데이터 수명 문제다.

---

## 7. 엔드포인트

> `/api/v1/workspaces/{workspace_id}/rag` prefix.

```
POST /ask    질문 → 답변 + 출처 (SSE 스트리밍, EventSourceResponse)
```

---

## 8. 엣지 케이스

- 검색 결과 0건 → "관련 콘텐츠를 찾을 수 없습니다" + 가이드
- 비-admin 캐시 hit이지만 출처 청크가 삭제됐거나 현재 가시성을 통과하지 못함 → 캐시행을 서빙하지 않고 cache miss로 처리해 재검색. 캐시행 자체를 즉시 삭제하지는 않음; admin/owner 우회에는 TTL 만료 전 삭제된 콘텐츠가 남을 수 있음 (R-15)
- Gemini API 실패 (SafetyFilter / 빈 candidate / 네트워크) → SSE `error` 이벤트 (한국어 안내 + retryAfter=3초) + `done` 이벤트 종료 + 캐시 저장 skip (R-11)
- Gemini 빈 답변 (strip 후 빈 문자열) → 캐시 저장 skip + `done` 이벤트 정상 종료
- 질문 길이 위반: strip 후 < 2자 또는 > 500자 → Pydantic 422 (R-12)
- prompt-injection 류 거대 입력 (>500자) → max_length 초과로 SSE 진입 전 422

---

## 9. 부채 (CONTEXT-MAP §7)

- ~~D-3: `rag → embeddings.service` 직접 의존~~ **[해소 1차 2026-05-11, ADR-014 옵션 A]** — `RagPipelineService` 신설로 진입 권한 검증 + 위임. `RagService` 내부 6-Layer embedding 호출은 그대로 (cross-domain shared service 정책, ADR-014 §1). 완전 분리는 sprint 7+ 검토 (ADR-014 §"비용/리스크" R-3).
