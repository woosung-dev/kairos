# Sprint 16 Stage 5/6 — pgvector 검증 + 회고 진입 인계

> **날짜**: 2026-05-15
> **워크트리**: `~/project/agy-project/kairos-pgvector-opt` (sprint-16/pgvector-optimization)
> **plan**: `~/.claude/plans/karrot-eager-marshmallow.md`
> **상위 ADR**: `docs/dev-log/020-pgvector-hnsw-halfvec.md`

---

## 1. 완료 상태 (commit history)

```
(예정) Stage 5 코드 산출물 — 통합 테스트 + recall corpus 생성기 + bench 보강 (BL-026 일부)
bf0ea8c Stage 4 보강 — memory 도메인 patch + 운영 정책 + BL-023~026 (P0/P1 retrofit)
c5e3861 Stage 5 진입 — HALFVEC 정정 + Python/서버 분리 + BL-022 + handoff
51acf11 feat(embeddings): Stage 4 — pgvector HNSW + halfvec 전환 + iterative_scan + REINDEX 운영
2017d86 docs(sprint-16): Stage 3 — pgvector 마이그레이션 plan + 사전 차단 체크리스트
55f8008 docs(sprint-16): Stage 1 — ADR-020 신설 + PRD RAG KPI + rag-pipeline HNSW 표기
ed062c3 docs(sprint-16): Stage 0 — pgvector 도메인 용어 lock-in + I-20/I-21 신설
```

origin/main 대비 **7 commits ahead, 미푸시**.

### Stage 5 코드 산출물 (사용자 환경 무관 — 본 보강 commit)

**통합 테스트** — `backend/tests/embeddings/test_halfvec_migration.py` (10 케이스):
- 컬럼 타입 halfvec 검증 (3 테이블)
- INSERT + cosine `<=>` 정합
- _apply_hnsw_session_params SET LOCAL 효과 (SHOW)
- vector_search + find_similar_cache + memory/repository.py:vector_search 진입 시 헬퍼 적용 (I-21 / E-9)
- NULL embedding 보존
- semantic_caches hit_count UPDATE
- EXPLAIN — HNSW 인덱스 사용 (정보성)

**recall corpus 생성기** — `backend/tests/embeddings/fixtures/generate_recall_corpus.py`:
- 결정론적 (seed 42), L2 정규화 (OpenAI text-embedding-3-small 모사)
- 3분포: 동일 chunk (recall 1.0) / 노이즈 추가 (0.9+) / 새 random (ranking 검증)
- 기본 200 chunk × 30 query × 1536d

**bench script 보강** — `backend/scripts/bench_vector_search.py` (BL-026 일부):
- 신규 mode: `latency` / `recall` / `memory-recall` / `build-time` / `explain` / `all`
- nDCG@10 + precision@10 측정 (BL-026 합격선: ≥0.95 / ≥0.90)
- HNSW 인덱스 빌드 시간 측정 (`measure_build_time`)
- EXPLAIN ANALYZE 헬퍼 — `uses_hnsw_index` 자동 판정
- p99 추가 + memory recall 별도 측정 (E-9 검증)

### 보강 commit 내용 (Stage 4 P0/P1 누락 retrofit)

**P0 누락 적발 (사용자 지적 2026-05-15 — 본 sprint 깊이 부족 진단)**:
- `memory/repository.py:vector_search` — `embedding_chunks` 직접 SQL JOIN. `_VECTOR_TYPE = Vector(1536)` bind. SET LOCAL 미호출 → I-21 위반
- `memory/models.py:MemoryQueryEmbeddingCache.embedding` — `Vector(1536)` (Sprint 15 신설)
- alembic 마이그레이션에 `memory_query_embedding_cache` 컬럼 변경 미포함

**P1 누락 적발 (영상 §4-B 갱신 잦은 컬럼 분리 권고)**:
- `semantic_caches.hit_count` 매 hit UPDATE → dead tuple 양산. fillfactor + autovacuum 정책 0회 적용
- HNSW 그래프 통계 갱신을 위한 ANALYZE 빈도 조정 누락

**P0/P1 해소 (본 보강 commit)**:
- `memory/repository.py` — `_VECTOR_TYPE` → `_HALFVEC_TYPE` + `_apply_hnsw_session_params` import + 호출
- `memory/models.py` — `Vector` → `HALFVEC` (MemoryQueryEmbeddingCache)
- alembic — step 3-b (`memory_query_embedding_cache` halfvec ALTER) + step 6 (fillfactor 80 + autovacuum_analyze_scale_factor 0.02/0.05)
- `embeddings/CONTEXT.md` — E-9 (외부 도메인 헬퍼 호출 강제) + E-10 (운영 정책) 신설
- ADR-020 §"Decision" 1 — 적용 범위 3개 컬럼 명시 + AD-57~59 추가
- plan §11 — memory 영향 LOW → HIGH 정정
- CONTEXT-MAP §2 — MemoryQueryEmbeddingCache halfvec 표기
- erd.md 220줄 — halfvec 표기

**BL 등재 (P2/P3)**:
- BL-023 — `semantic_caches.hit_count` 별도 테이블 분리 (장기, 컬럼 분리)
- BL-024 — pg_prewarm 정책 (Cloud Run cold start 시 인덱스 워밍업)
- BL-025 — 읽기 분산 (Neon read replica + 라우팅)
- BL-026 — 측정 강화 (nDCG / precision / 인덱스 빌드 시간 / EXPLAIN ANALYZE 헬퍼)

| Stage | 산출물 | 상태 |
|---|---|---|
| 0 grill | `docs/dev-log/2026-05-15-sprint16-pgvector-grill.md` + CONTEXT-MAP I-20/I-21 + embeddings/CONTEXT.md(신설) + rag/CONTEXT.md R-13 | ✅ |
| 1 ADR + PRD | ADR-020 Proposed + prd §4.1 RAG KPI + rag-pipeline §3/§4 footnote + ADR-014/019 cross-link | ✅ |
| 3 plan | `2026-05-15-sprint16-pgvector-plan.md` (사전 차단 + 마이그레이션 순서 + 측정 fixture 인터페이스) | ✅ |
| 4 코드 | models.py / repository.py / alembic / pyproject / scripts / guide / erd.md | ✅ |
| 5 검증 | 측정 fixture + verification doc + BL-022 등재 + ADR Accepted | ⬜ 본 doc 이후 |
| 6 회고 | TODO / memory / lessons | ⬜ Stage 5 통과 후 |

---

## 2. 사용자 환경 작업 (Stage 5 진입 차단 조건)

다음 세션이 진행하기 전 사용자가 워크트리에서 직접 실행:

### 2-A. Neon pgvector 서버 확장 ≥0.8 검증 (차단)

```bash
# Neon Postgres 연결 후
psql "$DATABASE_URL" -c "SELECT default_version, installed_version FROM pg_available_extensions WHERE name='vector';"
```

**합격선**: `default_version >= '0.8.0'`. 미달 시 본 sprint 보류 + Neon plan/region 검토.

### 2-B. uv sync — 의존성 설치

```bash
cd ~/project/agy-project/kairos-pgvector-opt/backend
uv sync
```

`pgvector>=0.4.2,<1.0.0` 설치 확인.

### 2-C. Neon branch 백업 (alembic upgrade 전)

```bash
neon branches create --parent main pre-pgvector-opt-2026-05-15
neon branches list  # 확인
```

### 2-D. 기존 ivfflat 인덱스 baseline 측정

```bash
cd backend
uv run python scripts/bench_vector_search.py --mode both --iter 1000 > /tmp/baseline_ivfflat.json
```

**저장**: `/tmp/baseline_ivfflat.json` 출력 → Stage 5 verification doc에 첨부.

### 2-E. NULL embedding row 카운트

```bash
psql "$DATABASE_URL" -c "
  SELECT
    (SELECT COUNT(*) FROM embedding_chunks WHERE embedding IS NULL) AS null_chunks,
    (SELECT COUNT(*) FROM semantic_caches WHERE question_embedding IS NULL) AS null_caches;
"
```

**기록**: ADR-020 §"비용/리스크" 갱신용.

### 2-F. alembic upgrade — HNSW 인덱스 + halfvec 전환

```bash
cd backend
uv run alembic upgrade head
# 1. ALTER EXTENSION vector UPDATE
# 2. HNSW 인덱스 생성 (CONCURRENTLY)
# 3. 컬럼 타입 vector → halfvec
# 4. 인덱스 재정의 (직접 컬럼)
```

**검증**:
```bash
psql "$DATABASE_URL" -c "SELECT indexname, indexdef FROM pg_indexes WHERE tablename IN ('embedding_chunks', 'semantic_caches');"
```
`idx_chunks_hnsw` + `idx_cache_hnsw` 존재 확인.

### 2-G. bench 재측정 (HNSW after)

```bash
uv run python scripts/bench_vector_search.py --mode both --iter 1000 > /tmp/after_hnsw.json
```

`/tmp/baseline_ivfflat.json` vs `/tmp/after_hnsw.json` 비교 → Stage 5 verification doc에 기록.

### 2-H. 다운그레이드 검증 (회귀 안전망)

```bash
uv run alembic downgrade -1
uv run alembic upgrade head
# 오류 없이 사이클 통과 시 OK
```

---

## 3. 다음 세션 진입 점검

새 세션 첫 read 순서:

1. **본 doc** (`docs/dev-log/2026-05-15-sprint16-stage5-handoff.md`)
2. `~/.claude/plans/karrot-eager-marshmallow.md` (plan)
3. `docs/dev-log/020-pgvector-hnsw-halfvec.md` (ADR-020)
4. `docs/dev-log/2026-05-15-sprint16-pgvector-plan.md` (Stage 3 plan)
5. `backend/scripts/bench_vector_search.py` (측정 도구)
6. 사용자가 §2 절차 수행 결과 (`/tmp/baseline_ivfflat.json` + `/tmp/after_hnsw.json`)

---

## 4. Stage 5 산출물 (다음 세션 작업)

### 4-A. recall@10 corpus 결정 — **옵션 B 스크립트 commit됨**

| 옵션 | 상태 | 비고 |
|---|---|---|
| A. dev DB export | ⏸ BL-026 후속 | production export + cosine ground truth 산출 절차 미구현 |
| B. 합성 corpus | ✅ **commit됨** | `backend/tests/embeddings/fixtures/generate_recall_corpus.py` |

실행:
```bash
cd backend
uv run python tests/embeddings/fixtures/generate_recall_corpus.py
# → recall_corpus.json (gitignore, 결정론적 seed=42)
```

기본 200 chunk × 30 query × 1536d. 옵션:
- 30% — 기존 chunk 그대로 (recall 1.0 예상)
- 40% — chunk + 노이즈 std=0.05 (recall 0.9+ 예상)
- 30% — 새 random vector (ranking 검증)

산출물 path: `backend/tests/embeddings/fixtures/recall_corpus.json`

### 4-B. 통합 테스트 — **commit됨**

`backend/tests/embeddings/test_halfvec_migration.py` (7개 테스트 케이스):

1. `test_embedding_chunks_column_is_halfvec` — information_schema 검증
2. `test_semantic_caches_column_is_halfvec` — 동일
3. `test_memory_query_embedding_cache_column_is_halfvec` — AD-58 검증 (sprint-15 신설본 halfvec 전환)
4. `test_insert_halfvec_and_cosine_search` — INSERT + cosine `<=>` 정합
5. `test_apply_hnsw_session_params_sets_variables` — SHOW로 SET LOCAL 효과 검증
6. `test_vector_search_invokes_hnsw_params` — EmbeddingRepository.vector_search 진입 시 SET LOCAL
7. `test_null_embedding_preserved` — NULL 보존
8. `test_semantic_cache_find_and_hit_count` — find_similar_cache + hit_count UPDATE
9. `test_memory_repository_vector_search_applies_hnsw_params` — E-9 검증 (외부 도메인 헬퍼 호출)
10. `test_explain_uses_hnsw_index` — EXPLAIN 정보성

TestContainers `pgvector/pgvector:pg16` 사용 — 사용자 환경 무관 즉시 실행.

실행:
```bash
cd backend
uv run pytest tests/embeddings/test_halfvec_migration.py -v
```

### 4-C. verification doc

`docs/dev-log/sprint-16-pgvector-verification.md`:

| 항목 | baseline (ivfflat) | after (HNSW) | delta | 합격 |
|---|---|---|---|---|
| recall@10 | 측정값 | 측정값 | (after/baseline) | ≥0.95 |
| p50 (ms) | 측정값 | 측정값 | 비율 | ≤1.0× |
| p95 (ms) | 측정값 | 측정값 | 비율 | ≤1.2× |
| 인덱스 크기 (idx_chunks_*) | 측정값 | 측정값 | 비율 | (참고) |
| 인덱스 빌드 시간 | 측정값 | 측정값 | 비율 | (참고) — BL-026 |
| nDCG@10 | 측정값 | 측정값 | 비율 | ≥0.95 (BL-026) |
| precision@10 | 측정값 | 측정값 | 비율 | ≥0.90 (BL-026) |
| memory recall (`memory/repository.py:vector_search`) | 측정값 | 측정값 | 비율 | ef_search 적용 EXPLAIN 검증 |

### 4-D. ADR-020 Status → Accepted

측정 모두 합격 시 `docs/dev-log/020-pgvector-hnsw-halfvec.md` 헤더 `> **상태:** Proposed` → `Accepted` patch.

### 4-E. (별도 PR) ivfflat drop

본 PR 머지 후 별도 PR로:
```python
# backend/alembic/versions/<new>_drop_ivfflat_indexes.py
with op.get_context().autocommit_block():
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_chunks_vector")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_cache_vector")
```

AD-56 — 2단계 배포 원칙 (backend.md §9).

---

## 5. Stage 6 회고 산출물

- `docs/TODO.md` — Sprint 16 완료 `[x]`
- 메모리 — `~/.claude/projects/.../memory/`에 `project_sprint16_done.md` 신설 + MEMORY.md 인덱스
- `.ai/project/lessons.md` (sprint-15에 있는지 확인 후, 없으면 본 워크트리 main 베이스라 skip):
  - alembic CONCURRENTLY = autocommit_block 필수
  - pgvector 캐스팅 = NULL safe (CASE WHEN)
  - SET LOCAL은 트랜잭션 범위 — repository 진입에서 매번 호출
  - Neon branch backup = pgvector 메이저 마이그레이션 안전망
  - 2단계 배포: 신규 인덱스 → 측정 → 별도 PR로 구 인덱스 drop
  - **pgvector Python 패키지(`HALFVEC`) vs 서버 확장(`iterative_scan`) 의존 분리**
  - **pgvector-python 0.4.2 sqlalchemy 모듈 export 이름은 `HALFVEC` (대문자) — 0.3+ 명세 다를 수 있어 직접 소스 확인 필수**

---

## 6. 충돌 시나리오 (Sprint 15 PR #29 머지 완료 후)

| 영역 | 본 sprint 변경 | 상태 |
|---|---|---|
| `embeddings/models.py` | HALFVEC import + Halfvec(1536) column | ✅ origin/main에서 sprint-15 변경 없음, fast-forward로 동기화 완료 |
| `embeddings/service.py` | 본 sprint 미수정 | ✅ Sprint 15 I-9 4-C assertion 포함 상태 그대로 |
| `embeddings/repository.py` | _apply_hnsw_session_params + CAST halfvec | ✅ Sprint 15 변경 없었음 |
| `CONTEXT-MAP.md` | §2 EmbeddingChunk/SemanticCache halfvec 표기 + §6 I-20/I-21 | ✅ Sprint 15 신설 I-18/I-19 + 본 sprint I-20/I-21 선형 추가 |
| `alembic/versions/` | b2c3d4e5f6a7 신설 (down_revision = a1b2c3d4e5f6) | ✅ Sprint 15 head 위 선형 체인 |

**Rebase 불요** — 본 sprint는 origin/main 기반이고 PR #29 머지본을 fast-forward로 흡수.

---

## 7. ADR-019 Phase B 진행 권고

ADR-019 (Gemini 2.5 → 3.1-flash-lite) Phase B 코드 swap은 본 sprint와 직교. 권고 commit 순서:

1. ✅ 본 sprint Stage 0/1/3/4 완료 (현재 4 commits)
2. ⬜ 사용자가 §2 환경 작업 수행
3. ⬜ 다음 세션 Stage 5 측정 + verification + ADR Accepted
4. ⬜ Stage 6 회고 + PR 푸시
5. ⬜ PR 머지
6. ⬜ ADR-019 Phase B 별도 PR (model_id swap, 6 spots) — 데모 종료 (Day 14 = 2026-05-28) 후
7. ⬜ ivfflat drop 별도 PR (Stage 5 측정 통과 + 본 sprint PR 머지 후)

---

## 8. Open Questions (Stage 5 진입 시점)

1. **recall@10 corpus 선택**: 옵션 A (dev DB export) vs 옵션 B (합성). dev DB chunk 수 측정 후 결정. → 다음 세션 첫 액션.
2. **bench 측정 환경**: dev DB vs staging DB. fixture 정합 위해 동일 환경에서 baseline + after 측정 필요.
3. **ADR-020 Status 변경 시점**: Stage 5 verification doc commit과 동일 commit 또는 별도 commit. **권고**: 동일 commit (Atomic Update).
4. **PR 분리 전략**: 본 sprint Stage 0~5 단일 PR vs Stage 0~3(docs) + Stage 4(코드) 2-PR. **권고**: 단일 PR — Atomic Update 매트릭스 강제 위해.
