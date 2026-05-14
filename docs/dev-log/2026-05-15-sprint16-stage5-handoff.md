# Sprint 16 Stage 5/6 — pgvector 검증 + 회고 진입 인계

> **날짜**: 2026-05-15
> **워크트리**: `~/project/agy-project/kairos-pgvector-opt` (sprint-16/pgvector-optimization)
> **plan**: `~/.claude/plans/karrot-eager-marshmallow.md`
> **상위 ADR**: `docs/dev-log/020-pgvector-hnsw-halfvec.md`

---

## 1. 완료 상태 (commit history)

```
51acf11 feat(embeddings): Stage 4 — pgvector HNSW + halfvec 전환 + iterative_scan + REINDEX 운영
2017d86 docs(sprint-16): Stage 3 — pgvector 마이그레이션 plan + 사전 차단 체크리스트
55f8008 docs(sprint-16): Stage 1 — ADR-020 신설 + PRD RAG KPI + rag-pipeline HNSW 표기
ed062c3 docs(sprint-16): Stage 0 — pgvector 도메인 용어 lock-in + I-20/I-21 신설
```

origin/main 대비 **4 commits ahead, 미푸시**.

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

### 4-A. recall@10 corpus 결정

| 옵션 | 내용 | 우선 |
|---|---|---|
| A. dev DB export | `SELECT id, chunk_text, embedding, workspace_id FROM embedding_chunks LIMIT 1000` + 임의 50 query 추출 | 우선 |
| B. 합성 corpus | `sklearn.TfidfVectorizer` + numpy 임베딩 + 임계 노이즈 | 폴백 |

산출물: `backend/tests/embeddings/fixtures/recall_corpus.json`.

### 4-B. 통합 테스트 신설

`backend/tests/embeddings/test_halfvec_migration.py`:

```python
# 검증 항목:
# 1. INSERT halfvec 임베딩 → cosine `<=>` SELECT 정합
# 2. NULL embedding 보존
# 3. _apply_hnsw_session_params 호출 후 EXPLAIN에서 Index Scan using idx_chunks_hnsw
# 4. iterative_scan 적용 시 WHERE 포스트필터 + LIMIT 도달 자동 추가 스캔 동작
# 5. find_similar_cache threshold 0.93 동작 유지
```

TestContainers `pgvector/pgvector:pg16` 이미 0.8+ 지원이라 통합 테스트 즉시 실행.

### 4-C. verification doc

`docs/dev-log/sprint-16-pgvector-verification.md`:

| 항목 | baseline (ivfflat) | after (HNSW) | delta | 합격 |
|---|---|---|---|---|
| recall@10 | 측정값 | 측정값 | (after/baseline) | ≥0.95 |
| p50 (ms) | 측정값 | 측정값 | 비율 | ≤1.0× |
| p95 (ms) | 측정값 | 측정값 | 비율 | ≤1.2× |
| 인덱스 크기 (idx_chunks_*) | 측정값 | 측정값 | 비율 | (참고) |
| 인덱스 빌드 시간 | 측정값 | 측정값 | 비율 | (참고) |

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
