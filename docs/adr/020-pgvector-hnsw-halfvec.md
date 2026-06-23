# ADR-020: pgvector 인덱스 전략 — ivfflat → HNSW + halfvec + iterative_scan

> **날짜:** 2026-05-15
> **상태:** Accepted (2026-05-15 Stage 5 측정 통과 — `git history`)
> **작성자:** Claude Opus 4.7 (1M context) + 사용자
> **관련:** CONTEXT-MAP §6 I-20/I-21 (Sprint 16 Stage 0 lock-in) · ADR-014 Service Boundary · ADR-019 Gemini EOL · `docs/architecture/rag-pipeline.md` §3/§4/§7 · `backend/src/embeddings/CONTEXT.md` E-7/E-8 · `git history` · `git history` (Stage 5) · BL-003 (RAG N+1 해소, Sprint 13 PR #21)
> **출처:** 당근(Karrot) DB 밋업 1회 (백은빈, 2025-XX) `pgvector 검색 최적화` — youtube `n3_LY7YFCwE`
> **워크플로우:** `.ai/templates/workflow.md` Stage 1 (ADR + PRD) · plan `~/.claude/plans/karrot-eager-marshmallow.md`

---

## 배경

### 현 상태 (2026-05-15 기준)

| 항목 | 값 | 파일 |
|---|---|---|
| 벡터 컬럼 타입 | `Vector(1536)` fp32 (4B/dim) | `backend/src/embeddings/models.py:33-36, 56-59` |
| 인덱스 | ivfflat `(lists=100, vector_cosine_ops)` | `backend/alembic/versions/e2c3782ab9c6_add_sprint3_tables.py:57-58, 103-104` |
| 거리 연산 | cosine `<=>` | `backend/src/embeddings/repository.py:81, 84, 162, 165` |
| pgvector 버전 | >=0.4.0 | `backend/pyproject.toml` |
| 세션 변수 | 미설정 (`ef_search` 기본 40, `iterative_scan` off) | — |
| REINDEX 정책 | 없음 | — |

### 4축 한계

1. **저장공간** — 1536d × 4B = 6KB/row. EmbeddingChunk 100만 row 도달 시 ≈ 6GB 인덱스. shared_buffers 캐시 압박.
2. **인덱스 타입 미스매치** — ivfflat은 lists 정적. 동적 데이터(메모리 capture / 회의 transcript 지속 삽입)에 부적합. 당근 운영 결론 "동적 데이터에는 HNSW".
3. **포스트필터 한계** — 0.4.0은 `iterative_scan` 미지원. RBAC/visibility 필터 + LIMIT 적용 시 후보 부족 → "검색 결과 0건" 빈발. Sprint 6 ADR-014 visibility 도입 이후 RAG 사용자 체감 결함 (M1 시그널 오염 위험).
4. **운영 도구 부재** — Vacuum 후 인덱스 bloat 누적 — REINDEX CONCURRENTLY 정책 없음. 장기 운영 시 점진적 성능 저하.

### 자의 결정 라벨 (본 산출에서 추가)

- **AD-51**: halfvec(fp16) 채택. 자의 = 저장 50% 절감 + 당근 운영 입증 + OpenAI text-embedding-3-small의 L2 norm ≈ 1.0이라 cosine 거리에서 fp16 유효자릿수 3~4 영향 미미 (Stage 5 recall@10 ≥0.95×baseline로 검증).
- **AD-52**: HNSW(m=16, ef_construction=64, ef_search=40) 당근 운영 기본값 그대로. 자의 = 튜닝 산출 없는 상태에서 검증된 기본값 채택. Stage 5 측정 후 필요 시 재튜닝.
- **AD-53**: pgvector 0.8+ 업그레이드 + `iterative_scan = 'relaxed_order'` + `max_scan_tuples = 20000`. 자의 = RBAC 포스트필터 한계 해소 + RAG 사용자 체감 결함 차단. relaxed_order는 당근 운영 채택, RRF 융합 후 순위 재계산이라 strict 불요.
- **AD-54**: 파티셔닝 **제외**. 자의 = kairos 현 데이터 규모 작음(chunk 만 단위) → 조기 최적화 회피. BL-022 등재 (workspace 100+ 또는 chunk 100만+ 트리거).
- **AD-55**: SET LOCAL 호출 위치는 **embeddings/repository.py 내부** (`_apply_hnsw_session_params(session)` 헬퍼). 자의 = embeddings 도메인 캡슐화. RAG service가 별도 호출 안 함 → ADR-014 옵션 A 책임 분리 유지.
- **AD-56 (정정 2026-05-15 Stage 5 측정)**: ivfflat 인덱스 drop은 **동일 마이그레이션** 내 강제. 정정 사유 = `vector_cosine_ops` operator class가 halfvec 컬럼과 호환 불가 → ALTER COLUMN TYPE 시 `DatatypeMismatchError`. backend.md §9 2단계 배포 원칙은 **컬럼 타입을 유지하는 expression index 패턴** 전용. 본 sprint는 vector→halfvec 컬럼 타입 변경이므로 ivfflat 운영 유지 불가. 안전망 = alembic downgrade가 vector 컬럼 + ivfflat 양방향 복구 보장 (b2c3d4e5f6a7 downgrade 검증).
- **AD-57**: Python 패키지(`pgvector` PyPI) vs 서버 확장(`vector` PostgreSQL) 의존 분리 명시. 자의 = 0.4.2 sqlalchemy/__init__.py에서 HALFVEC export 확인 → Python 패키지 ≥0.4.2 충분. 서버 확장 ≥0.8 (iterative_scan)은 별도 검증 (Stage 3 §1-A).
- **AD-58**: `memory_query_embedding_cache.embedding` (Sprint 15 신설) 도 본 sprint에서 halfvec 전환. 자의 = `memory/repository.py:vector_search`가 `embedding_chunks` halfvec와 JOIN하므로 query 임베딩 캐시 타입도 동일해야 cosine `<=>` 정합 + bindparam type 정합. plan §11 누락 retrofit.
- **AD-59**: `semantic_caches` fillfactor 80 + autovacuum_analyze_scale_factor 0.02 본 sprint 적용. 자의 = `hit_count` 매 hit마다 UPDATE → 당근 §4-B "갱신 잦은 컬럼" 권고 단기 대응 (HOT update). 컬럼 분리는 BL-023 등재 (장기). `embedding_chunks` + `memory_query_embedding_cache` 도 analyze scale_factor 0.05로 통계 갱신 빈도 상향 (HNSW 그래프 통계 최신화).

---

## 결정

### 1. 벡터 컬럼 타입 — halfvec(1536) 고정 (I-20)

**적용 범위 (3개 컬럼)**:
- `embedding_chunks.embedding` (embeddings 도메인)
- `semantic_caches.question_embedding` (embeddings 도메인)
- `memory_query_embedding_cache.embedding` (memory 도메인, Sprint 15 신설 — embedding_chunks JOIN 타입 정합 위해 동일 sprint 일관 전환. AD-58)

```python
# backend/src/embeddings/models.py
from pgvector.sqlalchemy import HALFVEC  # 0.3+

class EmbeddingChunk(SQLModel, table=True):
    ...
    embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(HALFVEC(1536)),
    )

class SemanticCache(SQLModel, table=True):
    ...
    question_embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(HALFVEC(1536)),
    )
```

### 2. 인덱스 — HNSW 단독 (I-20)

```sql
CREATE INDEX CONCURRENTLY idx_chunks_hnsw
  ON embedding_chunks
  USING hnsw (embedding halfvec_cosine_ops)
  WITH (m = 16, ef_construction = 64);

CREATE INDEX CONCURRENTLY idx_cache_hnsw
  ON semantic_caches
  USING hnsw (question_embedding halfvec_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

ivfflat 인덱스 (`idx_chunks_vector`, `idx_cache_vector`)는 **동일 마이그레이션**에서 drop (AD-56 정정 2026-05-15). 컬럼 타입 변경 시 PG가 operator class 호환성을 검증하므로 ivfflat 운영 유지 불가.

### 3. pgvector 서버 확장 ≥0.8 + Python 패키지 ≥0.4.2 + 세션 변수 강제 (I-21)

> **버전 매트릭스**:
> - **Python 패키지** `pgvector` (PyPI) — ≥**0.4.2** (`sqlalchemy.HALFVEC` export 보장. 0.4.2 sqlalchemy/__init__.py 확인)
> - **서버 확장** `vector` (PostgreSQL) — ≥**0.8** (`iterative_scan` / `relaxed_order` / `max_scan_tuples` 지원). Neon에서 `SELECT default_version FROM pg_available_extensions WHERE name='vector'` 결과로 검증

```python
# backend/src/embeddings/repository.py
async def _apply_hnsw_session_params(session: AsyncSession) -> None:
    """벡터 검색 트랜잭션 진입 시 SET LOCAL (I-21)."""
    await session.execute(text("SET LOCAL hnsw.ef_search = 40"))
    await session.execute(text("SET LOCAL hnsw.iterative_scan = 'relaxed_order'"))
    await session.execute(text("SET LOCAL hnsw.max_scan_tuples = 20000"))
```

호출 위치 — `vector_search` (line 67 진입), `find_similar_cache` (line 152 진입). 기존 cosine `<=>` 연산자 유지, CAST 변경 `CAST(:qvec AS vector)` → `CAST(:qvec AS halfvec)`.

### 4. REINDEX CONCURRENTLY 운영 정책

- 스크립트: `backend/scripts/reindex_vectors.py` (Sprint 16 Stage 4 신설)
- 트리거: pgstattuple로 bloat ≥30% 또는 월 1회 cron
- 가이드: `docs/guides/pgvector-reindex.md` (Sprint 16 Stage 4 신설)

### 5. 사전 차단 조건 (Stage 3 진입 직전)

```sql
SELECT default_version FROM pg_available_extensions WHERE name='vector';
-- ≥0.8.0 반환 필수. 미지원 시 본 ADR 보류.
```

---

## Consequences

### Positive

- **저장공간 50% 절감** — 1536 × (4B→2B) = 6KB → 3KB per row. EmbeddingChunk 100만 row → 6GB → 3GB
- **동적 데이터 적합** — HNSW 그래프 구조, lists 재구성 불요
- **RBAC 포스트필터 한계 해소** — iterative_scan으로 LIMIT 도달 시까지 자동 추가 스캔. "검색 결과 0건" 케이스 자동 해소
- **운영 가능한 인덱스** — REINDEX CONCURRENTLY로 무중단 bloat 정리
- **헌법 명시화** — I-20/I-21로 향후 회귀 차단 (예: 신규 도메인이 Vector(1536)으로 직접 컬럼 생성하는 사고)

### Negative

- **인덱스 빌드 시간 증가** — HNSW는 ivfflat 대비 그래프 구성 비용. 100만 row 기준 ivfflat 분 단위 → HNSW 10분+ 가능. CONCURRENTLY로 lock 회피 가능하나 빌드 자체는 백그라운드.
- **인덱스 크기 증가** — m=16 그래프 엣지 + 노드 메타로 인덱스 자체는 ivfflat 대비 1.5~2x. halfvec 저장 절감과 일부 상쇄.
- **메모리 압력** — 검색 시 그래프 traversal로 shared_buffers 압박 증가. Neon scale 사양 검증 필요 (Stage 5).
- **halfvec 정밀도 손실** — 유효자릿수 3~4. 코사인 거리 미세 차이. Stage 5 recall@10 ≥0.95×baseline 미달 시 본 ADR rollback.
- **pgvector 0.8 의존** — Neon Postgres ≥0.8 호환 사전 확인 필수 (Stage 3 차단 조건).

---

## Alternatives Considered

### 1. ivfflat 유지 + lists 튜닝
- **rejected** — 정적 lists는 동적 데이터에 부적합. lists 재계산 시 인덱스 재생성 필요. 당근 결론 동일.

### 2. 파티셔닝 (workspace_id hash 또는 created_at range)
- **deferred — BL-022 등재** — kairos 현 데이터 규모 작음. 당근은 1000만+ 통테이블 한정 권장. premature.

### 3. inner_product (`<#>`) 거리
- **rejected** — 텍스트 의미 유사도는 cosine. inner_product는 추천 시스템 용. OpenAI text-embedding 임베딩 L2 norm 변동도 적음.

### 4. Qdrant 등 외부 벡터 DB 전환
- **rejected (기존 결정 유지)** — memory `[[project_qdrant_deferred]]` — Repository 추상화 도입 비용 + Postgres 단일 운영 단순성 + halfvec/HNSW로 pgvector도 충분. 판매 준비 시점에 재검토.

---

## Implementation

### Stage 1 (본 ADR, 2026-05-15)
- ADR-020 (본 문서) Proposed
- `docs/requirements/prd.md` RAG 성능 KPI 신설
- `docs/architecture/rag-pipeline.md` §3/§4 Layer 1/3 HNSW 표기
- ADR-014 / ADR-019 §관련 cross-link

### Stage 3 (plan 산출, 2026-05-15+)
- `git history` 신설
- alembic 마이그레이션 순서 + `autocommit_block` + NULL safe 캐스팅
- Neon branch 백업 절차
- Stage 3 진입 직전: `SELECT default_version FROM pg_available_extensions WHERE name='vector'` ≥0.8 검증

### Stage 4 (코드)
- `backend/src/embeddings/models.py` — `from pgvector.sqlalchemy import HALFVEC`
- `backend/alembic/versions/NEW_pgvector_hnsw_halfvec.py` 신설
- `backend/src/embeddings/repository.py` — `_apply_hnsw_session_params` + CAST halfvec
- `backend/pyproject.toml` — `pgvector>=0.4.2,<1.0.0` (Python 패키지는 0.4.2부터 `sqlalchemy.HALFVEC` 지원. **서버 확장**은 별도로 `>=0.8` 요구 — Stage 3 §1-A 사전 SQL로 검증)
- `backend/scripts/reindex_vectors.py` + `bench_vector_search.py` 신설
- `docs/guides/pgvector-reindex.md` 신설
- ~~(별도 PR) ivfflat drop~~ → **동일 마이그레이션** drop (AD-56 정정 2026-05-15)

### Stage 5 (검증)
- `backend/tests/embeddings/test_halfvec_migration.py` — alembic up/down + EXPLAIN `Index Scan using idx_chunks_hnsw` 검증
- `backend/tests/embeddings/fixtures/recall_corpus.json` — 1000 chunk + 50 query
- `bench_vector_search.py` baseline(ivfflat) vs after(HNSW) 비교
- `git history` Heavy 검증 결과
- BL-022 등재
- 본 ADR Status: Proposed → Accepted

---

## Verification

### Stage 3 차단 조건

```sql
SELECT default_version FROM pg_available_extensions WHERE name='vector';
```
≥0.8.0 미반환 시 본 ADR 보류 + 사용자에게 Neon plan/region 확인 요청.

### Stage 5 합격 기준

- alembic upgrade head → downgrade base → upgrade head 사이클 무오류
- recall@10 ≥ baseline × 0.95 (50 query golden)
- p50 ≤ baseline × 1.0, p95 ≤ baseline × 1.2
- 기존 backend tests 전부 통과
- `SET LOCAL hnsw.ef_search` 미적용 vs 적용 EXPLAIN 차이 (`Index Scan using idx_chunks_hnsw`)
- 인덱스 크기 비교: `pg_size_pretty(pg_total_relation_size('idx_chunks_hnsw'))` vs ivfflat
- 인덱스 빌드 시간 측정 (Neon production 환경 확인용)

---

## Rollback

### 코드 swap 단계 (Stage 4)
- alembic revision 단일 + downgrade에서 ivfflat 인덱스 복구 + halfvec → vector 역캐스팅 (`USING (CASE WHEN embedding IS NULL THEN NULL ELSE embedding::vector(1536) END)`)
- Neon branch 백업: `neon branches create --parent main pre-pgvector-opt-2026-05-15`
- 검증 실패 시 `alembic downgrade -1` + branch swap

### Stage 5 측정 실패 시 (recall@10 < 0.95×baseline)
- 본 ADR rollback. `alembic downgrade -1`이 vector 컬럼 + ivfflat 인덱스 (`idx_chunks_vector` / `idx_cache_vector`) 동시 복구 (AD-56 정정 2026-05-15에서 downgrade 보강).
- `_apply_hnsw_session_params` 호출 제거 + CAST halfvec→vector 복귀 + 컬럼 타입 ALTER 역마이그레이션

---

## 비용 / 리스크

| 항목 | 영향 | 완화 |
|---|---|---|
| 인덱스 빌드 시간 폭증 | Neon production 빌드 분~시간 | `CREATE INDEX CONCURRENTLY` + 사전 dev 환경 측정 |
| Neon pgvector 0.8 미지원 | Stage 차단 | 사전 차단 SQL (위 Verification) |
| halfvec 정밀도 손실 | recall 회귀 | Stage 5 recall@10 ≥0.95 필수 합격 기준 |
| HNSW 그래프 메모리 압력 | shared_buffers 압박 | Neon scale 사양 확인 + p95 측정 |
| pgvector 0.8 SQLModel/asyncpg 호환 | import 실패 | **해소** — pgvector 0.4.2 sqlalchemy 모듈에서 `HALFVEC` export 확인 (2026-05-15 본 sprint 검증). 서버 확장 0.8+는 Stage 3 §1-A 사전 SQL로 검증 |
| 다른 도메인(쿼리)이 SET LOCAL 미적용 | 일부 쿼리 ef_search 기본값 사용 | embeddings/repository 캡슐화 (AD-55) + I-21 헌법 강제 + code review |

---

## 후속

- **Stage 1**: prd KPI / rag-pipeline.md / ADR-014 / ADR-019 cross-link (본 commit)
- **Stage 3**: plan doc + Neon pgvector 버전 사전 확인
- **Stage 4**: 코드 7행 매트릭스 + ivfflat 별도 PR
- **Stage 5**: recall@10 + p50/p95 측정 + BL-022 등재 + 본 ADR Accepted
- **Stage 6**: TODO + memory + lessons
- **장기**: BL-022 파티셔닝 (workspace 100+ 또는 chunk 100만+ 트리거)
- **장기**: Qdrant 전환은 판매 준비 시점 재검토 (`[[project_qdrant_deferred]]`)

---

## 참조

- 당근 DB 밋업 1회 (백은빈) — `pgvector 검색 최적화`, youtube `n3_LY7YFCwE`
- pgvector 0.8 release notes — iterative index scan / halfvec_cosine_ops
- Neon Postgres pgvector 지원 — https://neon.tech/docs/extensions/pgvector (Stage 3에서 production 버전 확인)
- ADR-014 §"비용/리스크" R-3 — orchestrator 책임 분리, embeddings 캡슐화
- ADR-019 — Gemini 코드 swap과 본 ADR 코드 swap은 Sprint 16 별도 commit (충돌 회피)
- BL-003 (RAG `_enrich_context` N+1 해소, Sprint 13 PR #21) — 본 ADR과 직교, parent chunk 조회는 batch query 유지
