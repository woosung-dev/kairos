# Sprint 16 Stage 0 — pgvector 도메인 용어 grill (당근 DB 노하우 lock-in)

> **날짜**: 2026-05-15
> **워크트리**: `~/project/agy-project/kairos-pgvector-opt` (sprint-16/pgvector-optimization)
> **plan**: `~/.claude/plans/karrot-eager-marshmallow.md`
> **근거**: 당근(Karrot) DB 밋업 1회 (백은빈) — `pgvector 검색 최적화`

---

## 1. 배경

기존 ivfflat (lists=100, cosine_ops) + `Vector(1536)` 구성. 동적 임베딩 삽입 / RBAC·visibility 포스트필터링 / 운영 인덱스 관리 측면에서 다음 한계 발견:

| 영역 | 현 상태 | 한계 |
|---|---|---|
| 인덱스 타입 | ivfflat lists=100 | 정적 리스트, 임베딩 추가 시 재구성 필요. 그래프 탐색 미지원 |
| 벡터 타입 | `Vector(1536)` (fp32, 4B/dim) | 저장공간 6.0KB/row, 캐시 효율 ↓ |
| pgvector | >=0.4.0 | `iterative_scan` 미지원 → 포스트필터 시 결과 부족 |
| 세션 변수 | 미설정 | `ef_search` 기본 40, `iterative_scan` 기본 off |
| 운영 | REINDEX 정책 0 | bloat 누적 시 성능 저하 + 수동 개입 |

---

## 2. 도메인 용어 정의 (헌법 lock-in 대상)

| 용어 | 정의 | 출처 |
|---|---|---|
| **halfvec** | 16bit 반정밀 부동소수 벡터 타입. dim당 2B (fp32 대비 절반). 유효자릿수 3~4자리. pgvector 0.7+ 지원 | 당근 §2-A |
| **HNSW** | Hierarchical Navigable Small World. 계층 그래프 ANN 인덱스. 동적 데이터에 적합 (재구성 불요) | 당근 §2-B |
| **m** | HNSW 빌드 파라미터. 노드 1개가 연결할 수 있는 최대 이웃 수. 기본 16 | 당근 §B-인덱스 생성 |
| **ef_construction** | HNSW 빌드 파라미터. 노드 삽입 시 연결 후보로 고려하는 최대 노드 수. 기본 64. m≤ef_construction | 당근 §B-인덱스 생성 |
| **ef_search** | HNSW 탐색 파라미터. 쿼리 시 후보로 고려하는 최대 노드 수. 기본 40. 쿼리마다 `SET LOCAL`로 동적 변경 가능 | 당근 §B-쿼리 탐색 |
| **iterative_scan** | pgvector 0.8+ 기능. WHERE + LIMIT 조건 만족 시까지 자동 추가 스캔. 포스트필터 한계 해소 | 당근 §B-쿼리패턴 |
| **relaxed_order** | iterative_scan 정렬 모드. 순서 약간 흐트러져도 빠르게 다수 결과. 당근 기본 채택 | 당근 §B-정렬모드 |
| **strict_order** | iterative_scan 정렬 모드. 정확한 거리 정렬 보장, 느림 | 당근 §B-정렬모드 |
| **max_scan_tuples** | iterative_scan 상한. 기본 20000. 무한 스캔 방지 | 당근 §B-제한 |
| **scan_multiplier** | iterative_scan 곱계수. 기본 1 | 당근 §B-제한 |
| **REINDEX CONCURRENTLY** | 무중단 인덱스 재빌드. 락 없이 신규 인덱스 생성 후 swap. bloat 정리 정책 | 당근 §5-B |
| **index bloat** | 인덱스 팽창률. dead tuple 누적 + Vacuum 후에도 파일 크기 미감소. pgstattuple로 측정 | 당근 §5-B |
| **partition pruning** | 쿼리에서 WHERE 조건으로 불필요 파티션 제외. 캐시 효율 ↑. (본 sprint 제외, BL-022 등재) | 당근 §4-A |

---

## 3. 적용 결정 (4가지)

### 3-1. halfvec 전환
- **대상**: `EmbeddingChunk.embedding` + `SemanticCache.question_embedding` 양쪽
- **저장 효과**: 1536 × (4B→2B) = 6.0KB → 3.0KB per row
- **정합 검증**: Stage 5에서 cosine 유사도 baseline 대비 ≥0.95 (recall@10)
- **위험**: 유효자릿수 3~4자리 → 거리 미세 차이 발생. OpenAI text-embedding-3-small 임베딩의 L2 norm ≈ 1.0이라 코사인 거리에서 영향 작음 (당근도 동일 결론).

### 3-2. ivfflat → HNSW 전환
- **파라미터**: `m=16, ef_construction=64, ef_search=40` (당근 운영 기본값 그대로 채택)
- **이유**: 동적 데이터 (memory capture / meeting transcript 지속 삽입) 친화. ivfflat은 lists 정적이라 재구성 부담.
- **트레이드오프**: 인덱스 빌드 시간 ↑, 인덱스 크기 ↑ (당근도 동일 인정)
- **롤백** (AD-56 정정 2026-05-15 Stage 5): 단일 마이그레이션에서 ivfflat drop + 컬럼 타입 halfvec + HNSW 재정의 동시 진행. `vector_cosine_ops`가 halfvec 컬럼과 호환 불가 → ivfflat 운영 유지 불가. 안전망 = alembic downgrade에서 vector 컬럼 + ivfflat 재생성.

### 3-3. pgvector 0.4 → 0.8+ + iterative_scan
- **세션 변수** (`SET LOCAL`, 트랜잭션 범위):
  - `hnsw.ef_search = 40`
  - `hnsw.iterative_scan = 'relaxed_order'`
  - `hnsw.max_scan_tuples = 20000`
- **호출 위치**: `embeddings/repository.py` `vector_search` + `find_similar_cache` 진입 헬퍼 `_apply_hnsw_session_params(session)`
- **사전 차단**: Neon Postgres `SELECT default_version FROM pg_available_extensions WHERE name='vector'` ≥0.8 검증. 미지원 시 Stage 중단.
- **이유**: RBAC/visibility 적용 RAG 쿼리에서 포스트필터 후 `LIMIT` 미달 → "검색 결과 0건" 케이스 자동 해소.

### 3-4. REINDEX CONCURRENTLY 운영 스크립트
- **위치**: `backend/scripts/reindex_vectors.py` (신설)
- **트리거**: bloat ≥30% 또는 월 1회 cron
- **동작**: pgstattuple로 dead tuple 비율 측정 → `REINDEX INDEX CONCURRENTLY idx_chunks_hnsw` + `idx_cache_hnsw`
- **운영 가이드**: `docs/guides/pgvector-reindex.md` (신설)

---

## 4. 제외 결정

### 4-1. 파티셔닝
- **이유**: 당근은 1000만+ 통테이블에서 필요. kairos 현 데이터 규모 작음 (chunk 수만 단위).
- **등재**: `docs/REFACTORING-BACKLOG.md` **BL-022** (Stage 5에서 등재) — Trigger: workspace 100+ 또는 chunk 100만+
- **BL ID 점유 현황**: BL-020까지 등재, BL-021 e2e hotfix 점유 → 본 sprint BL는 **BL-022부터** 부여

### 4-2. inner_product 거리 함수
- **이유**: 텍스트 의미 유사도 검색이라 cosine 유지. inner_product는 추천 시스템 용 (당근 §2-C).

---

## 5. 헌법 patch 매트릭스 (Stage 0 동일 commit 강제)

| 파일 | patch 내용 |
|---|---|
| `CONTEXT-MAP.md` §2 | `EmbeddingChunk` 행: `1536d 벡터` → `1536d **halfvec** 벡터`. `SemanticCache` 행: 동일 표기. `embedding` 별칭 금지 표 유지 |
| `CONTEXT-MAP.md` §6 | **I-20** 신설 — 벡터 컬럼 타입은 `halfvec(1536)`, ivfflat 금지 HNSW(m=16, ef_construction=64)만. **I-21** 신설 — 벡터 검색 쿼리는 트랜잭션 진입 시 SET LOCAL ef_search/iterative_scan/max_scan_tuples 강제 |
| `backend/src/embeddings/CONTEXT.md` | **신설** — §1 책임 §2 비책임 §3 엔티티(HALFVEC 명시) §4 의존 §5 불변식 E-1~E-8 (I-6/I-7/I-8/I-9/I-20/I-21 mirror + cosine `<=>` + REINDEX 정책) §6 엔드포인트 없음 §7 부채 |
| `backend/src/rag/CONTEXT.md` | §4 Layer 1/3 표기 변경: `pgvector` → `pgvector HNSW(halfvec, ef_search=40, iterative_scan=relaxed_order)`. **R-13** 신설 — Layer 1/3 진입 시 ef_search/iterative_scan SET LOCAL 강제 (embeddings/repository 위임) |

---

## 6. 후속 (Stage 1~6 진입 조건)

- Stage 1: ADR-020 (Nygard) + prd RAG KPI + rag-pipeline.md Layer 표기 patch + ADR-014/019 cross-link
- Stage 3: alembic 마이그레이션 순서 + autocommit_block + NULL safe 캐스팅 + Neon branch 백업 절차
- Stage 4: 코드 변경 7행 매트릭스 (plan §Stage 4)
- Stage 5: recall@10 ≥0.95×baseline + p50/p95 합격 + BL-022 등재 + ADR-020 Accepted
- Stage 6: TODO + memory + lessons

---

## 7. Open Questions (Stage 3 진입 전 차단 조건)

1. **Neon pgvector 버전**: production Neon DB에서 `SELECT default_version FROM pg_available_extensions WHERE name='vector'` 결과 ≥0.8 확인 필요. 미지원 시 Neon plan/region 변경 또는 본 sprint 보류.
2. ~~**pgvector Python 클래스명**: `pgvector.sqlalchemy` 0.3+ 에서 `Halfvec` vs `HALFVEC` import 명 확인 필요.~~ **[해소 2026-05-15]** pgvector 0.4.2 sqlalchemy/__init__.py 확인 — `HALFVEC` (대문자) export. 본 sprint는 `from pgvector.sqlalchemy import HALFVEC` 사용.
3. **데이터 캐스팅 NULL safety**: `embedding IS NULL` row 존재 여부 — `SELECT COUNT(*) FROM embedding_chunks WHERE embedding IS NULL` 사전 측정. 존재 시 `CASE WHEN NULL` 캐스팅 형식 채택.
4. **production chunk 분포**: recall@10 측정용 fixture 합성 vs 실제 데이터 export 결정 — dev/staging DB chunk 수 확인 후 결정.

---

## 8. 관련

- plan: `~/.claude/plans/karrot-eager-marshmallow.md`
- 워크트리 격리 결정: 본 sprint = `origin/main` 베이스. sprint-15/personal-workspace 영향 0. PR #29 머지(2026-05-14, 7036e71) 후 fast-forward로 main 동기화 완료.
- ADR-014: orchestrator 패턴 — `_apply_hnsw_session_params`는 repository 내부 헬퍼로 처리, RAG service 변경 없음.
- ADR-019 Phase B: Gemini 2.5-flash → 3.1-flash-lite swap은 별도 commit (Sprint 16 첫 코드 commit, 충돌 회피).
- BL-003 완료: RAG `_enrich_context` N+1 해소 (Sprint 13 PR #21).
