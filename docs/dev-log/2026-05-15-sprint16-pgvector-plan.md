# Sprint 16 Stage 3 — pgvector 마이그레이션 plan / brainstorm

> **날짜**: 2026-05-15
> **워크트리**: `~/project/agy-project/kairos-pgvector-opt` (sprint-16/pgvector-optimization)
> **plan 진입점**: `~/.claude/plans/karrot-eager-marshmallow.md`
> **상위 ADR**: `docs/dev-log/020-pgvector-hnsw-halfvec.md`
> **grill**: `docs/dev-log/2026-05-15-sprint16-pgvector-grill.md`

---

## 1. 사전 차단 조건 (Stage 4 진입 직전 필수 검증)

### 1-A. Neon Postgres pgvector 버전

```sql
-- Neon production / staging / dev 각각 실행
SELECT default_version, installed_version
FROM pg_available_extensions
WHERE name = 'vector';
```

**합격선**: `default_version >= '0.8.0'` AND (`installed_version >= '0.8.0'` 또는 `ALTER EXTENSION vector UPDATE` 후 0.8+ 가능).

**미달 시**: 본 sprint 보류. Neon plan upgrade 또는 region 변경 검토. ADR-020 Status 미변경 (Proposed 유지).

### 1-B. pgvector Python 패키지 클래스명 확인 — **해소 2026-05-15**

```bash
# dev 환경에서 (검증 완료)
uv pip show pgvector  # >= 0.4.2 필요
uv run python -c "from pgvector.sqlalchemy import HALFVEC; print(HALFVEC.__module__)"
# 출력: pgvector.sqlalchemy.halfvec
```

**확정**: pgvector 0.4.2 `sqlalchemy/__init__.py`에서 `HALFVEC` (대문자) export. 본 sprint 코드는 `from pgvector.sqlalchemy import HALFVEC` 사용. 별칭 없음.

### 1-C. NULL embedding row 존재 여부

```sql
SELECT
  (SELECT COUNT(*) FROM embedding_chunks WHERE embedding IS NULL) AS null_chunks,
  (SELECT COUNT(*) FROM semantic_caches WHERE question_embedding IS NULL) AS null_caches;
```

**대응**: NULL row 존재 시 `USING` 절을 NULL safe 캐스팅으로 작성. NULL 0건이라도 안전을 위해 NULL safe 형식 채택.

### 1-D. 기존 인덱스 + 크기 baseline

```sql
SELECT indexname, pg_size_pretty(pg_relation_size(indexname::regclass)) AS size
FROM pg_indexes
WHERE tablename IN ('embedding_chunks', 'semantic_caches');
```

**기록 대상**: `idx_chunks_vector`, `idx_cache_vector` ivfflat 크기 → ADR-020 §"Consequences" 갱신용.

---

## 2. Neon branch 백업 (Stage 4 마이그레이션 직전)

```bash
# Neon CLI 설치 시
neon branches create --parent main pre-pgvector-opt-2026-05-15

# 검증
neon branches list
```

**롤백 시 swap**: production main branch → backup branch 포인터 변경. 또는 본 워크트리 `alembic downgrade -1` 후 backup branch 데이터로 시드 비교 (검증용).

---

## 3. alembic 마이그레이션 순서

### 3-A. 단일 revision 권장 — `op.get_context().autocommit_block()` 사용

```python
# backend/alembic/versions/<id>_pgvector_hnsw_halfvec.py
"""pgvector HNSW + halfvec 전환 (Sprint 16 ADR-020).

Revision ID: <generated>
Revises: a1b2c3d4e5f6  (Sprint 15 memory + workspace.type)
Create Date: 2026-05-XX
"""
from alembic import op

revision = "<generated>"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. pgvector 0.8+ 확장 갱신
    op.execute("ALTER EXTENSION vector UPDATE")

    # 2. HNSW 인덱스 신규 생성 (CONCURRENTLY는 트랜잭션 외부 필요)
    with op.get_context().autocommit_block():
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chunks_hnsw
            ON embedding_chunks
            USING hnsw ((embedding::halfvec(1536)) halfvec_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cache_hnsw
            ON semantic_caches
            USING hnsw ((question_embedding::halfvec(1536)) halfvec_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)

    # 3. 컬럼 타입 변경 (NULL safe 캐스팅)
    op.execute("""
        ALTER TABLE embedding_chunks
        ALTER COLUMN embedding TYPE halfvec(1536)
        USING (CASE WHEN embedding IS NULL THEN NULL ELSE embedding::halfvec(1536) END)
    """)
    op.execute("""
        ALTER TABLE semantic_caches
        ALTER COLUMN question_embedding TYPE halfvec(1536)
        USING (CASE WHEN question_embedding IS NULL THEN NULL
                    ELSE question_embedding::halfvec(1536) END)
    """)

    # 4. 컬럼 타입 변경 후 인덱스 재정의 (캐스팅 표현 → 직접 컬럼)
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_chunks_hnsw")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_cache_hnsw")
        op.execute("""
            CREATE INDEX CONCURRENTLY idx_chunks_hnsw
            ON embedding_chunks
            USING hnsw (embedding halfvec_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)
        op.execute("""
            CREATE INDEX CONCURRENTLY idx_cache_hnsw
            ON semantic_caches
            USING hnsw (question_embedding halfvec_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)

    # 5. 기존 ivfflat 인덱스는 본 revision에서 drop 하지 않음 (AD-56 — 별도 PR)
    # Stage 5 측정 통과 후 별도 commit에서:
    # op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_chunks_vector")
    # op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_cache_vector")


def downgrade() -> None:
    # 역순: halfvec → vector 컬럼 + HNSW drop + ivfflat은 유지된 상태 가정
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_chunks_hnsw")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_cache_hnsw")

    op.execute("""
        ALTER TABLE embedding_chunks
        ALTER COLUMN embedding TYPE vector(1536)
        USING (CASE WHEN embedding IS NULL THEN NULL ELSE embedding::vector(1536) END)
    """)
    op.execute("""
        ALTER TABLE semantic_caches
        ALTER COLUMN question_embedding TYPE vector(1536)
        USING (CASE WHEN question_embedding IS NULL THEN NULL
                    ELSE question_embedding::vector(1536) END)
    """)
```

### 3-B. 왜 CONCURRENTLY인가

당근 §5-B + Postgres 공식 — `CREATE INDEX` 단독은 `ShareLock` 보유 → 쓰기 차단. `CONCURRENTLY`는 락 회피 + 백그라운드 빌드. 단점은 트랜잭션 외부 실행 강제 (alembic `autocommit_block` 필요).

### 3-C. 왜 인덱스 2회 생성 (CAST 형식 → 직접 컬럼)

컬럼 타입이 `vector(1536)`인 상태에서 HNSW 인덱스를 `halfvec_cosine_ops`로 만들려면 `embedding::halfvec(1536)` expression index 필요. 컬럼 타입 변경 후 expression 불요 → 직접 컬럼 참조로 재정의. 인덱스 정의 단순화 + planner 최적화. 한 번에 모든 작업이 끝나는 단일 마이그레이션 유지.

대안 (분할 마이그레이션 2개):
- mig1: 컬럼 타입만 변경 (인덱스 없음 — 쿼리 느려짐)
- mig2: HNSW 인덱스 생성

→ **rejected**: mig1과 mig2 사이에 production 쿼리 latency 폭증 위험. 단일 revision으로 일관성 보장.

---

## 4. 쿼리 패턴 변경 (`backend/src/embeddings/repository.py`)

### 4-A. 신규 헬퍼

```python
async def _apply_hnsw_session_params(session: AsyncSession) -> None:
    """벡터 검색 트랜잭션 진입 시 SET LOCAL (I-21).

    pgvector ≥0.8 의존. RBAC/visibility 포스트필터 결과 부족 해소.
    """
    await session.execute(text("SET LOCAL hnsw.ef_search = 40"))
    await session.execute(text("SET LOCAL hnsw.iterative_scan = 'relaxed_order'"))
    await session.execute(text("SET LOCAL hnsw.max_scan_tuples = 20000"))
```

### 4-B. 호출 위치 + CAST 변경

```python
# vector_search (line 67 진입)
async def vector_search(self, ...):
    await _apply_hnsw_session_params(self.session)  # 신규
    ...
    query = text(f"""
        SELECT id, chunk_text, source_id, source_type, metadata_json,
               parent_chunk_id, created_at,
               1 - (embedding <=> CAST(:qvec AS halfvec)) AS score   -- vector → halfvec
        FROM embedding_chunks
        WHERE {filters}
        ORDER BY embedding <=> CAST(:qvec AS halfvec)                 -- vector → halfvec
        LIMIT :limit
    """)
    ...

# find_similar_cache (line 152 진입)
async def find_similar_cache(self, ...):
    await _apply_hnsw_session_params(self.session)  # 신규
    ...
    # CAST(:qvec AS vector) → CAST(:qvec AS halfvec) 동일 패치
```

### 4-C. text_search 미변경

`text_search` (pg_trgm `%`)는 본 ADR scope 외. SET LOCAL 불요.

### 4-D. 호출 흐름 검증

- `rag/service.py` Layer 1/3 → `EmbeddingRepository.vector_search` / `find_similar_cache` 호출 → 내부에서 SET LOCAL → cosine `<=>`
- `memory/service.py` recall 진입도 동일 경로 (BL-006 등재 — pipeline_service 분리는 별도 작업)
- ADR-014 옵션 A 책임 분리 유지: embeddings 도메인 캡슐화

---

## 5. 모델 변경 (`backend/src/embeddings/models.py`)

```python
# before
from pgvector.sqlalchemy import Vector
embedding: list[float] | None = Field(
    default=None,
    sa_column=Column(Vector(1536)) if Vector else Column(Text),
)

# after
from pgvector.sqlalchemy import HALFVEC
embedding: list[float] | None = Field(
    default=None,
    sa_column=Column(HALFVEC(1536)) if HALFVEC else Column(Text),
)
```

**try/except ImportError fallback** 유지 — pgvector 패키지 미설치 환경(테스트?)에서 Text 컬럼으로 대체.

---

## 6. pgproject.toml 변경

```toml
# before
"pgvector>=0.4.0",
# after
"pgvector>=0.4.2,<1.0.0",  # sqlalchemy.HALFVEC 지원 (0.4.2+). 서버 확장은 별도 0.8+ 요구.
```

> **중요 — Python 패키지 vs 서버 확장 구분**:
> - **Python 패키지** `pgvector` (PyPI) — `pgvector.sqlalchemy.HALFVEC` 는 **0.4.2+에서 export** (확인됨: `pgvector/sqlalchemy/__init__.py` `from .halfvec import HALFVEC`)
> - **서버 확장** `vector` (PostgreSQL) — `iterative_scan` / `relaxed_order` 는 **0.8.0+에서 지원**. Neon에서 `SELECT default_version FROM pg_available_extensions WHERE name='vector'` 결과 ≥0.8 필수 (§1-A 사전 차단)

`uv lock` 후 재설치. CI/CD Dockerfile 빌드 캐시 무효화 자동.

---

## 7. 운영 스크립트

### 7-A. `backend/scripts/reindex_vectors.py`

```python
#!/usr/bin/env python3
"""pgvector 인덱스 bloat 모니터링 + REINDEX CONCURRENTLY (Sprint 16 ADR-020)."""

import asyncio
import argparse
from sqlalchemy import text
from src.common.database import async_session_factory

THRESHOLD_BLOAT_RATIO = 0.30  # 30% 이상 dead tuple
INDEXES = ["idx_chunks_hnsw", "idx_cache_hnsw"]


async def check_bloat(index_name: str) -> tuple[float, str]:
    """pgstattuple로 bloat 비율 + 인덱스 크기 측정."""
    async with async_session_factory() as session:
        await session.execute(text("CREATE EXTENSION IF NOT EXISTS pgstattuple"))
        r = await session.execute(
            text("SELECT * FROM pgstattuple(:idx)"),
            {"idx": index_name},
        )
        row = r.first()
        if not row:
            return 0.0, "unknown"
        # dead_tuple_percent + free_percent
        bloat = (row.dead_tuple_percent or 0) + (row.free_percent or 0)
        size_q = await session.execute(
            text("SELECT pg_size_pretty(pg_relation_size(:idx::regclass))"),
            {"idx": index_name},
        )
        size = size_q.scalar() or "unknown"
        return bloat / 100.0, size


async def reindex(index_name: str, dry_run: bool) -> None:
    async with async_session_factory() as session:
        if dry_run:
            print(f"[dry-run] would REINDEX INDEX CONCURRENTLY {index_name}")
            return
        # autocommit
        conn = await session.connection()
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        await session.execute(text(f"REINDEX INDEX CONCURRENTLY {index_name}"))
        print(f"[done] REINDEX {index_name}")


async def main(dry_run: bool, force: bool) -> None:
    for idx in INDEXES:
        bloat, size = await check_bloat(idx)
        print(f"{idx}: size={size}, bloat={bloat:.1%}")
        if bloat >= THRESHOLD_BLOAT_RATIO or force:
            await reindex(idx, dry_run)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    asyncio.run(main(args.dry_run, args.force))
```

### 7-B. `backend/scripts/bench_vector_search.py` (구조만)

```python
"""벡터 검색 p50/p95 + recall@K baseline vs HNSW 비교 (Sprint 16 Stage 5)."""

# --mode latency: 1000회 timeit → numpy.percentile [50, 95]
# --mode recall: fixtures/recall_corpus.json → SELECT TOP-10 → ground truth 매칭률
```

상세 구현은 Stage 4에서. 본 plan은 인터페이스만 lock-in.

### 7-C. `docs/guides/pgvector-reindex.md`

운영 가이드:
- 빈도: 월 1회 cron 또는 `--force`
- bloat ≥30% 트리거 알림
- REINDEX 실패 시 (락 충돌 / 디스크 부족) 알림 + 수동 대응 절차

---

## 8. 측정 fixture

### 8-A. recall@10 corpus 결정

**옵션 A** — dev/staging DB 실제 chunk 1000건 export
- 장점: 실제 분포 반영
- 단점: 데이터 의존, 환경마다 결과 변동

**옵션 B** — 합성 corpus (sklearn TfidfVectorizer + 노이즈 추가)
- 장점: 결정론적, 재현 가능
- 단점: 실제 임베딩 분포 미반영

**자의 결정**: 옵션 A 우선, 미가용 시 옵션 B 폴백. fixture 형식:

```json
{
  "version": "2026-05-15",
  "chunks": [
    {"id": "c001", "text": "...", "embedding": [1536 floats], "workspace_id": "ws-test"}
  ],
  "queries": [
    {
      "id": "q01",
      "text": "...",
      "embedding": [1536 floats],
      "expected_top10": ["c003", "c042", ...]
    }
  ]
}
```

### 8-B. p50/p95 측정 절차

- ivfflat baseline: 본 마이그레이션 직전 측정
- HNSW after: 본 마이그레이션 직후 측정
- 측정 환경: dev DB (동일 chunk seed) + locust 또는 timeit 1000회
- 출력: ADR-020 §"Consequences" 갱신 + verification doc 표

---

## 9. 호환성 확인

| 항목 | 영향 | 검증 |
|---|---|---|
| Neon Postgres pgvector 0.8 | 차단 가능 | §1-A 사전 SQL |
| Cloud Run Dockerfile pgvector 빌드 | 서버 미설치 (서버측 확장) | 무관 |
| `psycopg` / `asyncpg` halfvec 직렬화 | pgvector-python 0.3+에서 처리 | §1-B 확인 |
| pgvector-python의 `array.array("e", ...)` (fp16) | Python ≥3.6 native | OK |
| sqlmodel `Column(HALFVEC(1536))` autogenerate | `models.py` 변경 시 alembic autogenerate가 type 차이 감지 | 마이그레이션 수동 작성 (autogenerate에 의존하지 않음) |
| 다른 도메인의 vector 컬럼 사용 | embeddings 단독. 다른 도메인 없음 | grep 확인 |

---

## 10. 롤백 시나리오

| 단계 | 검증 실패 | 액션 |
|---|---|---|
| Stage 3 진입 직전 | Neon 0.8 미지원 | 본 sprint 보류, ADR-020 Status Proposed 유지 |
| Stage 4 alembic upgrade | CONCURRENTLY 락 충돌 / 캐스팅 실패 | downgrade -1 + 원인 분석 + 수정 후 재시도 |
| Stage 4 backend 기존 test 회귀 | repository CAST halfvec 오류 | repository.py revert + 모델 revert + downgrade |
| Stage 5 recall@10 < 0.95×baseline | halfvec 정밀도 부족 | ADR-020 rollback + Neon branch swap. ivfflat 인덱스 유지 상태라 즉시 복구 가능 |
| Stage 5 p95 > baseline × 1.2 | HNSW 그래프 메모리 압박 | ef_search 재튜닝 → 재측정. 또는 m 조정. 그래도 미달 시 rollback |
| (별도 PR) ivfflat drop 후 회귀 | HNSW 인덱스 손상 | `CREATE INDEX CONCURRENTLY idx_chunks_vector USING ivfflat ...` 즉시 복구 + HNSW 재빌드 |

---

## 11. 충돌 점검 (Sprint 15 후속 + ADR-019 Phase B)

| 영역 | Sprint 15 / ADR-019 영향 | 본 sprint 영향 | 충돌 가능성 |
|---|---|---|---|
| `embeddings/models.py` | 미변경 (sprint-15) | Vector → HALFVEC | ✅ 없음 |
| `embeddings/service.py` | I-9 4-C 진입 assertion 강화 (sprint-15) | 미수정 | ✅ 없음 |
| `embeddings/repository.py` | 미변경 | SET LOCAL 헬퍼 + CAST halfvec | ✅ 없음 |
| `alembic/env.py` | sprint-15 모델 import 추가 | 본 sprint 추가 없음 | ✅ 없음 |
| `alembic/versions/` | a1b2c3d4e5f6 (sprint-15 memory) | NEW revision (`down_revision=a1b...`) | ✅ 없음, 선형 체인 |
| `services/ai_processing.py` | ADR-019 Phase B에서 model_id swap 예정 (Sprint 16 별도 commit) | 본 sprint 영향 없음 | ✅ 없음 (별도 commit) |
| `memory/repository.py` ⚠️ **본 sprint patch 필수** | sprint-15 `vector_search` 자체 구현 (`embedding_chunks` 직접 JOIN SQL) + `_VECTOR_TYPE = Vector(1536)` bind + `MemoryQueryEmbeddingCache.embedding Vector(1536)` 컬럼 | `_VECTOR_TYPE` → `_HALFVEC_TYPE` + `_apply_hnsw_session_params(session)` 호출 추가 + MemoryQueryEmbeddingCache halfvec 전환 | 🔴 **HIGH — Stage 4 보강 commit으로 처리** |
| `memory/service.py` | recall path embedding 호출 | _apply_hnsw_session_params는 repository 내부 캡슐화로 호출자 변경 없음 | ✅ 없음 |
| `rag/service.py` / `rag/pipeline_service.py` | sprint-15 미변경 | 호출자 변경 없음 (R-13 강제만) | ✅ 없음 |

**결론**: 본 sprint와 ADR-019 Phase B는 완전 직교. 둘 다 Sprint 16에 들어가도 별도 commit이면 충돌 없음. 권장 commit 순서:
1. 본 ADR-020 Stage 4 코드 swap
2. 본 ADR-020 Stage 5 검증 통과
3. ADR-019 Phase B Gemini model_id swap
4. 본 ADR-020 별도 PR로 ivfflat drop

---

## 12. Stage 4 진입 체크리스트

- [ ] §1-A Neon pgvector ≥0.8 확인 — 사용자 직접 실행 후 결과 본 plan §1-A에 추가
- [ ] §1-B `pgvector.sqlalchemy.HALFVEC` import 검증 — dev 환경
- [ ] §1-C NULL embedding 카운트 측정 — production / staging / dev
- [ ] §1-D 기존 ivfflat 인덱스 크기 baseline 기록 → ADR-020 §"Consequences"
- [ ] §2 Neon branch backup 생성
- [ ] §8-A recall@10 corpus 결정 (옵션 A vs B)

### 모든 체크 통과 시
- Stage 4 진입 = `backend/src/embeddings/models.py` import 변경부터 시작
- Stage 4 매트릭스 = plan `~/.claude/plans/karrot-eager-marshmallow.md` §Stage 4 표 7행

---

## 13. Open Questions (Stage 4 진입 차단 또는 비차단)

1. **Neon production pgvector 버전 확인** (차단) — 사용자 직접 실행
2. ~~**`Halfvec` vs `HALFVEC` 클래스명** (차단) — dev 환경 import 검증~~ **[해소 2026-05-15]** pgvector 0.4.2 `sqlalchemy.HALFVEC` (대문자) 확정. models.py + bench_vector_search.py 본 sprint 코드 반영 완료.
3. **recall@10 corpus 선택** (비차단, 옵션 A 우선) — Stage 4에서 데이터 export 시도
4. **bench latency 1000회 vs 더 큰 N** (비차단) — 기본 1000회로 진행, 분산 큰 경우 N 증가
5. **REINDEX 빈도 (월 1회 vs 주 1회)** (비차단) — 운영 가이드에 "월 1회 기본 + bloat ≥30% 트리거"로 명시
