<!-- embeddings 도메인 — 임베딩 청크 + 시맨틱 캐시 저장/검색 (pgvector HNSW + halfvec) -->

# embeddings CONTEXT

> 상위: `/apps/api/CONTEXT.md` → `/CONTEXT-MAP.md`. 상세 설계: `docs/architecture/rag-pipeline.md` (Layer 1/3).

---

## 1. 책임

- 임베딩 청크 영속화 (`EmbeddingChunk`, 1536d halfvec, L1/L2 계층)
- 시맨틱 캐시 영속화 (`SemanticCache`, TTL 7일, threshold 0.93)
- 벡터 유사도 검색 (`vector_search` — cosine `<=>`)
- 텍스트 유사도 검색 (`text_search` — pg_trgm `%`)
- 시맨틱 캐시 조회 + 히트 카운트 증가 (`find_similar_cache`)
- HNSW 세션 파라미터 강제 (I-21 — `_apply_hnsw_session_params`)
- 멀티테넌시 격리 강제 (I-9 — `create_chunk` 진입 assertion + Repository read 필터)

## 2. 비책임

- 임베딩 생성 (OpenAI text-embedding-3-small 호출은 `services/` 또는 도메인 pipeline_service)
- 권한 검증 (visibility / RBAC는 orchestrator — `notes/pipeline_service`, `rag/pipeline_service`, `memory/pipeline_service` 호출자. Sprint 24 Wave 2 BL-006 해소로 memory 도 orchestrator 일관성 회복)
- 임베딩 모델 결정 (I-6 — `core/config.py`)
- RAG 6-Layer 조립 (rag/service 책임. embeddings는 read/write API만 제공)
- 콘텐츠 원본 영속화 (각 source 도메인)

---

## 3. 엔티티

- **EmbeddingChunk** — `models.py:15`. 1536d halfvec 벡터 (Sprint 16 ADR-020 — fp16 4B→2B). 계층 `chunk_level` (0=문서, 1=섹션, 2=문단). L0 미사용 (D-4 부채). 검색 대상은 L2만 (I-7).
- **SemanticCache** — `models.py:45`. TTL 7일 (`expires_at`), threshold 0.93. 1536d halfvec. hit_count 누적.

> 별칭 금지 (CONTEXT-MAP §2-별칭 표): `EmbeddingChunk` ↔ Vector / Embedding 단수형 금지. `SemanticCache` ↔ Query Cache / RAG Cache / Answer Cache 금지.

---

## 4. 의존 (in/out)

| 방향 | 대상 | 레벨 | 비고 |
|---|---|---|---|
| in | `notes/pipeline_service` (NotePipelineService) | service | ADR-014 옵션 A — notes 작성 시 청크 적재 |
| in | `meetings/pipeline_service` (process_meeting, capture_text) | service | 회의 transcript / capture 청크 적재 |
| in | `memory/pipeline_service.MemoryPipelineService.save_memory_chunk` (Sprint 24 Wave 2 BL-006 해소, 2026-05-20) | service (orchestrator) | 메모리 capture/promote 시 청크 write — `memory/service.py` 의 lazy import 2 hit 제거, orchestrator 경유. architecture gate `apps/api/tests/architecture/test_no_memory_to_embeddings_lazy_import.py` 회귀 방지. |
| in | `memory/repository.py:vector_search` | repository (직접 SQL) | ⚠️ 본 도메인 우회 — `embedding_chunks` JOIN `memory_items` 직접 query. Sprint 16부터 `_apply_hnsw_session_params` 호출 강제 (E-9 / I-21). **E-9 유지 결정 (Sprint 24 Wave 2 BL-006 closeout)**: capsule 우회 최소 비용 약속, vector_search 자체 흡수는 LOC vs 가치 비대칭 (BL-006 closure rationale 참조). |
| in | `rag/service` | service | RAG 6-Layer Layer 1/3 호출. ADR-014 옵션 A로 진입은 RagPipelineService |
| out | DB (pgvector **서버 확장** ≥0.8 + HNSW + halfvec) | infra | `_apply_hnsw_session_params` 트랜잭션 변수 + `<=>` cosine + pg_trgm `%`. Python 패키지(`pgvector`)는 ≥0.4.2 (HALFVEC export 보장) |
| out | `services/` (OpenAI text-embedding-3-small) | external wrapper | 임베딩 생성은 호출자 책임. embeddings 도메인은 vector 인자 받아 저장만 |

---

## 5. 핵심 불변식

> CONTEXT-MAP §6의 I-6/I-7/I-8/I-9/I-20/I-21 mirror + 도메인 특수 E-7/E-8.

| # | 불변식 | 강제 위치 |
|---|---|---|
| E-1 (= I-6) | 임베딩 모델 OpenAI `text-embedding-3-small` 1536d 고정 | `core/config.py` + 호출자 |
| E-2 (= I-7) | 검색 대상은 `chunk_level = 2` 만. L0(document) 미사용, L1은 parent context 조회용 | `repository.py:vector_search` filter |
| E-3 (= I-8) | SemanticCache TTL 7일, 유사도 threshold 0.93 | `models.py:_default_expires_at`, `repository.py:find_similar_cache` |
| E-4 (= I-9) | 모든 read 쿼리 `workspace_id` 필터. `create_chunk` 진입 시 owner workspace 일치 assertion (Sprint 15 I-9 4-C 강화) | `repository.py` `.where(... workspace_id ...)`, `service.py:create_chunk` |
| E-5 | cosine 거리 연산자 `<=>` 사용. inner_product `<#>` / L2 `<->` 금지 (텍스트 의미 유사도) | `repository.py:81/84/162/165` |
| E-6 | `EmbeddingChunk.embedding` 별칭 금지 — `Vector` / `Embedding` 단수형 사용 금지 (CONTEXT-MAP §2-별칭) | code review |
| E-7 (= I-20) | 벡터 컬럼 타입 `halfvec(1536)` 고정. ivfflat 신규 인덱스 금지. HNSW `m=16, ef_construction=64` 만 | `models.py` (HALFVEC import), `alembic/versions/<pgvector_hnsw_halfvec>.py` |
| E-8 (= I-21) | 벡터 검색 트랜잭션 진입 시 `_apply_hnsw_session_params(session)` 호출 강제 — `ef_search=40` + `iterative_scan=relaxed_order` + `max_scan_tuples=20000` 을 트랜잭션 로컬로(단일 `set_config` 왕복) 설정. RBAC 포스트필터 결과 부족 해소 | `repository.py:vector_search` / `find_similar_cache` 진입 헬퍼 |
| E-9 | **embedding_chunks 직접 SQL 사용 외부 도메인**도 `_apply_hnsw_session_params` 호출 강제 (Sprint 16). 본 도메인이 export하는 module-level 헬퍼를 import 후 진입 시 호출 — 캡슐화 우회의 최소 비용 약속. 현 외부 사용처: `memory/repository.py:33` (1 hit, 의도된 예외). **Sprint 24 Wave 2 BL-006 closure decision**: `memory/service.py` 의 `EmbeddingRepository.save_chunk` lazy import 는 `MemoryPipelineService.save_memory_chunk` 로 흡수 완료 (헌법 §4.2 준수). `memory/repository.py:vector_search` 의 `_apply_hnsw_session_params` 직접 호출은 capsule 우회 최소 비용 약속으로 유지 (vector_search 흡수는 후속 sprint). architecture gate `tests/architecture/test_memory_repository_apply_hnsw_helper_keep` 가 본 import 1 hit 유지를 강제. | `memory/repository.py:33` |
| E-10 | **운영 정책** (Sprint 16 ADR-020 §AD-59) — `semantic_caches` fillfactor 80 + autovacuum_analyze_scale_factor 0.02 (hit_count 빈번 UPDATE 대응). `embedding_chunks` + `memory_query_embedding_cache` autovacuum_analyze_scale_factor 0.05 (HNSW 통계 빈번 갱신). alembic `ALTER TABLE ... SET (...)` 명시. | `apps/api/alembic/versions/b2c3d4e5f6a7_pgvector_hnsw_halfvec.py` step 6 |

> REINDEX CONCURRENTLY 운영 정책은 헌법 불변식이 아니라 운영 가이드 — `docs/operations/pgvector-reindex.md` + `apps/api/scripts/reindex_vectors.py` (Sprint 16 신설).

---

## 6. 엔드포인트

**없음** — 외부 노출 router 미보유. 내부 도메인 (호출자 = notes/meetings/memory/rag pipeline_service).

---

## 7. 엣지 케이스

- `embedding IS NULL` row → 검색 ORDER BY에서 자동 제외 (`<=>` NULL 처리). 마이그레이션 시 `CASE WHEN NULL` 안전 캐스팅 필요 (Sprint 16 Stage 3).
- SemanticCache hit이지만 출처 콘텐츠 삭제됨 → 호출자(rag) 책임. embeddings 도메인은 `expires_at` 기반 만료만 강제.
- workspace_id 미스매치 → `create_chunk` assertion 실패 (Sprint 15 I-9 4-C, `service.py`).
- chunk_text 텍스트 검색에서 한국어 짧은 입력 → pg_trgm `similarity()` 0.0 근접. text_search threshold는 호출자 결정.

---

## 8. 부채 (CONTEXT-MAP §7)

- **D-4**: EmbeddingChunk L0(document) 미사용 — 코드는 L1/L2만 저장 (`service.py:117,140,191,209`). ERD에서 L0 제거 또는 활용 결정 후속.
- **BL-022 (등재 예정, Sprint 16 Stage 5)**: `embedding_chunks` 파티셔닝 — workspace_id hash 또는 created_at range. Trigger: workspace 100+ 또는 chunk 100만+. 당근 §4-A 노하우.

---

## 9. 진입점 (새 세션)

1. 본 CONTEXT
2. `models.py` (HALFVEC 정의 + chunk_level 계층)
3. `repository.py` (`_apply_hnsw_session_params` + vector_search + find_similar_cache)
4. `service.py` (create_chunk 진입 + I-9 4-C assertion)
5. `docs/architecture/rag-pipeline.md` Layer 1/3 (호출자 관점)
6. `docs/adr/020-pgvector-hnsw-halfvec.md` (Sprint 16 ADR-020 — 본 도메인 인덱스/타입 전략)
