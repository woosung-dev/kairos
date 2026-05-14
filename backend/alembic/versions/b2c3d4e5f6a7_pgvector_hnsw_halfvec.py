# pgvector HNSW + halfvec 전환 마이그레이션 (Sprint 16 ADR-020)
"""pgvector HNSW + halfvec 전환 (Sprint 16 ADR-020)

ADR-020 (docs/dev-log/020-pgvector-hnsw-halfvec.md) — ivfflat → HNSW + Vector → Halfvec.
당근(Karrot) DB 밋업 1회 (백은빈) pgvector 최적화 노하우 적용.

작업 순서:
1. `ALTER EXTENSION vector UPDATE` — 서버측 pgvector 0.8+ 갱신 (iterative_scan 지원)
2. HNSW 인덱스 신규 생성 (`embedding::halfvec(1536)` expression index, CONCURRENTLY)
3. 기존 ivfflat 인덱스 drop (`vector_cosine_ops`는 halfvec 컬럼과 호환 불가 → ALTER COLUMN TYPE 차단)
4. 컬럼 타입 `vector(1536)` → `halfvec(1536)` 변경 (NULL safe 캐스팅)
5. 컬럼 타입 변경 후 인덱스 재정의 (직접 컬럼 참조)

AD-56 정정 (Stage 5 측정 발견): 2단계 배포 원칙 "신규 인덱스 → 측정 → 별도 PR drop"은
컬럼 타입을 유지하는 expression index 패턴 전용. 본 sprint는 vector→halfvec 컬럼 타입을
바꾸므로 PG operator class 호환성 검증으로 ivfflat 운영 유지 불가. ivfflat drop을 동일
마이그레이션에 포함 (안전망: alembic downgrade로 vector + ivfflat 양방향 복구 가능).

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6 (Sprint 15 memory + workspace.type)
Create Date: 2026-05-15
"""
from collections.abc import Sequence
from typing import Union

from alembic import op


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 서버측 pgvector 확장 갱신 (Neon은 default_version 도달 시점에 한정)
    op.execute("ALTER EXTENSION vector UPDATE")

    # 2. 신규 HNSW 인덱스 생성 (현재 컬럼은 vector(1536), expression index로 halfvec 캐스팅)
    #    CONCURRENTLY는 트랜잭션 외부 필요 — autocommit_block 사용.
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chunks_hnsw
            ON embedding_chunks
            USING hnsw ((embedding::halfvec(1536)) halfvec_cosine_ops)
            WITH (m = 16, ef_construction = 64)
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cache_hnsw
            ON semantic_caches
            USING hnsw ((question_embedding::halfvec(1536)) halfvec_cosine_ops)
            WITH (m = 16, ef_construction = 64)
            """
        )

    # 2.5. 기존 ivfflat 인덱스 drop — `vector_cosine_ops` operator class가 halfvec과 호환 불가.
    #      Stage 5 측정 (Sprint 16, 2026-05-15)에서 ALTER COLUMN TYPE 시도 시
    #      `DatatypeMismatchError` 발생 확인. AD-56 2단계 배포는 expression index 패턴 전용 —
    #      컬럼 타입 변경 마이그레이션은 동일 revision drop 필수.
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_chunks_vector")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_cache_vector")

    # 3. 컬럼 타입 변경 — NULL safe 캐스팅 (plan §1-C 검증 결과 NULL row 0건이어도 안전 우선).
    op.execute(
        """
        ALTER TABLE embedding_chunks
        ALTER COLUMN embedding TYPE halfvec(1536)
        USING (CASE WHEN embedding IS NULL THEN NULL ELSE embedding::halfvec(1536) END)
        """
    )
    op.execute(
        """
        ALTER TABLE semantic_caches
        ALTER COLUMN question_embedding TYPE halfvec(1536)
        USING (CASE WHEN question_embedding IS NULL THEN NULL
                    ELSE question_embedding::halfvec(1536) END)
        """
    )
    # 3-b. memory_query_embedding_cache (Sprint 15 신설) — 동일 sprint 일관 halfvec 전환.
    #      memory/repository.py:vector_search가 embedding_chunks (halfvec) JOIN하므로
    #      query 임베딩 캐시도 동일 타입이 정합. 인덱스 없음 (PK lookup).
    op.execute(
        """
        ALTER TABLE memory_query_embedding_cache
        ALTER COLUMN embedding TYPE halfvec(1536)
        USING embedding::halfvec(1536)
        """
    )

    # 4. 컬럼 타입 변경 후 인덱스 재정의 (캐스팅 표현 → 직접 컬럼 참조).
    #    planner 최적화 + 인덱스 정의 단순화.
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_chunks_hnsw")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_cache_hnsw")
        op.execute(
            """
            CREATE INDEX CONCURRENTLY idx_chunks_hnsw
            ON embedding_chunks
            USING hnsw (embedding halfvec_cosine_ops)
            WITH (m = 16, ef_construction = 64)
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY idx_cache_hnsw
            ON semantic_caches
            USING hnsw (question_embedding halfvec_cosine_ops)
            WITH (m = 16, ef_construction = 64)
            """
        )

    # 5. 기존 ivfflat 인덱스 drop은 step 2.5에서 이미 수행 (컬럼 타입 호환성 필수).
    #    AD-56 정정 (Stage 5 측정 발견) — 본 sprint는 컬럼 타입 변경 → 같은 revision drop 강제.

    # 6. 운영 정책 — fillfactor (HOT update) + autovacuum_analyze_scale_factor.
    #    당근 DB 밋업 §4-B "갱신 잦은 컬럼 분리" 권고를 단기 적용 (컬럼 분리는 BL-023 등재).
    #    semantic_caches.hit_count는 매 hit마다 UPDATE → HOT update 활성화 + 통계 자주 갱신.
    op.execute(
        "ALTER TABLE semantic_caches "
        "SET (fillfactor = 80, autovacuum_analyze_scale_factor = 0.02)"
    )
    # embedding_chunks는 INSERT 위주이나 HNSW 그래프 통계 갱신을 위해 analyze 빈도 상향.
    op.execute(
        "ALTER TABLE embedding_chunks "
        "SET (autovacuum_analyze_scale_factor = 0.05)"
    )
    # memory_query_embedding_cache는 INSERT/DELETE 위주 (TTL 7일 만료). 동일 정책.
    op.execute(
        "ALTER TABLE memory_query_embedding_cache "
        "SET (autovacuum_analyze_scale_factor = 0.05)"
    )


def downgrade() -> None:
    # 역순: 운영 정책 RESET → HNSW drop → halfvec → vector 컬럼 복귀 → ivfflat 재생성.
    op.execute("ALTER TABLE semantic_caches RESET (fillfactor, autovacuum_analyze_scale_factor)")
    op.execute("ALTER TABLE embedding_chunks RESET (autovacuum_analyze_scale_factor)")
    op.execute("ALTER TABLE memory_query_embedding_cache RESET (autovacuum_analyze_scale_factor)")

    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_chunks_hnsw")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_cache_hnsw")

    op.execute(
        """
        ALTER TABLE embedding_chunks
        ALTER COLUMN embedding TYPE vector(1536)
        USING (CASE WHEN embedding IS NULL THEN NULL ELSE embedding::vector(1536) END)
        """
    )
    op.execute(
        """
        ALTER TABLE semantic_caches
        ALTER COLUMN question_embedding TYPE vector(1536)
        USING (CASE WHEN question_embedding IS NULL THEN NULL
                    ELSE question_embedding::vector(1536) END)
        """
    )
    op.execute(
        """
        ALTER TABLE memory_query_embedding_cache
        ALTER COLUMN embedding TYPE vector(1536)
        USING embedding::vector(1536)
        """
    )

    # ivfflat 인덱스 재생성 — upgrade step 2.5에서 drop된 인덱스 복구.
    #   원본: e2c3782ab9c6_add_sprint3_tables_embedding_chunks_.py:57-58, 103-104
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chunks_vector
            ON embedding_chunks USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cache_vector
            ON semantic_caches USING ivfflat (question_embedding vector_cosine_ops)
            """
        )
