# pgvector HNSW 인덱스 운영 가이드 (Sprint 16 ADR-020)

> **목적**: REINDEX CONCURRENTLY로 bloat 정리 + 인덱스 크기/성능 모니터링.
> **상위 결정**: `docs/adr/020-pgvector-hnsw-halfvec.md` (ADR-020)
> **헌법**: `CONTEXT-MAP.md` I-20/I-21
> **스크립트**: `apps/backend/scripts/reindex_vectors.py`

---

## 1. 왜 REINDEX인가 (당근 §5-B)

- Vacuum은 dead tuple을 제거하지만 **인덱스 파일 크기**는 줄어들지 않음 (index bloat).
- 대량 삭제/갱신 후 점진적 성능 저하 + shared_buffers 캐시 비효율.
- HNSW는 그래프 구조라 ivfflat 대비 bloat 영향이 더 직접적 (그래프 노드 dangling).
- `REINDEX CONCURRENTLY`는 락 없이 신규 인덱스 빌드 후 swap — 무중단.

## 2. 측정 (Bloat 비율)

```bash
cd apps/backend
uv run python scripts/reindex_vectors.py --dry-run
```

출력 예:
```
idx_chunks_hnsw: size=523 MB, bloat=12.3%
idx_cache_hnsw: size=18 MB, bloat=3.1%
[dry-run] would REINDEX INDEX CONCURRENTLY idx_chunks_hnsw   # bloat 임계값 도달 시
```

내부 동작:
- `CREATE EXTENSION IF NOT EXISTS pgstattuple` (1회)
- `SELECT * FROM pgstattuple('idx_chunks_hnsw')` — dead_tuple_percent + free_percent 합산
- `pg_size_pretty(pg_relation_size(indexname::regclass))` — 인덱스 크기

## 3. 운영 빈도

| 트리거 | 빈도 | 액션 |
|---|---|---|
| 정기 점검 | **월 1회** | `--dry-run`으로 측정. 모든 인덱스 bloat <30%면 skip. |
| 임계 도달 | bloat ≥ **30%** | 자동 `REINDEX CONCURRENTLY` (스크립트 기본 동작) |
| 대량 삭제 후 | 1만 row+ 삭제 직후 | `--force` 옵션으로 강제 REINDEX |
| 빌드 시간 추적 | 분기 1회 | `bench_vector_search.py --mode both` 실행 후 ADR-020 §"Consequences" 갱신 |

## 4. 실행 방법

### 4-A. 측정 only

```bash
uv run python apps/backend/scripts/reindex_vectors.py --dry-run
```

### 4-B. 임계값 기반 자동 reindex

```bash
uv run python apps/backend/scripts/reindex_vectors.py
# bloat ≥30% 인덱스만 REINDEX
```

### 4-C. 강제 reindex (대량 삭제 직후)

```bash
uv run python apps/backend/scripts/reindex_vectors.py --force
# 모든 INDEXES 대상 REINDEX
```

## 5. cron 등록 (선택)

운영 환경(예: Cloud Run Jobs)에서 월 1회 실행:

```bash
# crontab 또는 Cloud Run Scheduler
0 3 1 * *   cd /app/backend && uv run python scripts/reindex_vectors.py
```

## 6. 실패 대응

| 증상 | 원인 | 대응 |
|---|---|---|
| `pgstattuple 측정 실패` | extension 미설치 | 한 번 권한 있는 user로 `CREATE EXTENSION pgstattuple` 수동 실행 |
| `REINDEX ... lock conflict` | autocommit 미설정 | 스크립트 내부 `isolation_level=AUTOCOMMIT` 명시. 그래도 실패 시 활성 트랜잭션 확인 |
| `disk full` | 신규 인덱스 빌드 중 디스크 부족 | Neon plan upgrade 또는 `pg_size_pretty(pg_total_relation_size('embedding_chunks'))` 측정 + 정리 |
| REINDEX 후에도 bloat 그대로 | pgstattuple 캐싱 | `VACUUM ANALYZE embedding_chunks` 후 재측정 |
| 빌드 시간 너무 길음 (분 이상) | 대용량 + HNSW 그래프 |	`ef_construction` 일시 감소 (ADR-020 재튜닝 검토). 또는 분할 빌드 |

## 7. ivfflat 인덱스 (구) drop — **동일 마이그레이션 처리 (AD-56 정정 2026-05-15)**

본 sprint는 컬럼 타입을 `vector(1536)` → `halfvec(1536)`로 변경하므로 ivfflat 인덱스(`vector_cosine_ops`)를 동일 마이그레이션 b2c3d4e5f6a7 내에서 drop 강제. `vector_cosine_ops`가 halfvec 컬럼과 호환 불가 → ALTER COLUMN TYPE 시 `DatatypeMismatchError`. `apps/backend/AGENTS.md` §9 2단계 배포는 **컬럼 타입 유지 expression index 패턴** 전용.

```sql
-- apps/backend/alembic/versions/b2c3d4e5f6a7_pgvector_hnsw_halfvec.py upgrade() step 2.5
-- (CONCURRENTLY는 autocommit_block 내부 실행)
DROP INDEX CONCURRENTLY IF EXISTS idx_chunks_vector;
DROP INDEX CONCURRENTLY IF EXISTS idx_cache_vector;
```

안전망 = alembic downgrade가 vector 컬럼 + ivfflat 인덱스 양방향 복구 (`CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chunks_vector USING ivfflat (embedding vector_cosine_ops) WITH (lists=100)` 등).

## 8. 모니터링 지표 (Sprint 16+ 후속)

| 지표 | 도구 | 알람 임계값 |
|---|---|---|
| 인덱스 크기 (`pg_size_pretty`) | bench script 정기 출력 | 2x 증가 시 알림 |
| bloat 비율 | pgstattuple | ≥30% |
| p95 latency | `bench_vector_search.py --mode latency` | ≥ baseline × 1.5 |
| recall@10 (회귀) | `bench_vector_search.py --mode recall` | < 0.90 |

후속 자동화: Sprint 17+에서 metrics infra(`MemoryEvent.recall_latency_ms`)와 통합.
