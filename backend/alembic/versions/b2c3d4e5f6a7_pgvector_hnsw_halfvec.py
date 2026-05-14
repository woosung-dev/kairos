# pgvector HNSW + halfvec 전환 마이그레이션 (Sprint 16 ADR-020)
"""pgvector HNSW + halfvec 전환 (Sprint 16 ADR-020)

ADR-020 (docs/dev-log/020-pgvector-hnsw-halfvec.md) — ivfflat → HNSW + Vector → Halfvec.
당근(Karrot) DB 밋업 1회 (백은빈) pgvector 최적화 노하우 적용.

작업 순서:
1. `ALTER EXTENSION vector UPDATE` — 서버측 pgvector 0.8+ 갱신 (iterative_scan 지원)
2. HNSW 인덱스 신규 생성 (`embedding::halfvec(1536)` expression index, CONCURRENTLY)
3. 컬럼 타입 `vector(1536)` → `halfvec(1536)` 변경 (NULL safe 캐스팅)
4. 컬럼 타입 변경 후 인덱스 재정의 (직접 컬럼 참조)
5. 기존 ivfflat 인덱스는 본 revision에서 drop 하지 않음 (AD-56 — 별도 PR로 진행)

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

    # 5. 기존 ivfflat 인덱스는 본 revision에서 drop 하지 않음 (AD-56 / backend.md §9 2단계 배포).
    #    Stage 5 측정 통과 후 별도 PR에서:
    #       DROP INDEX CONCURRENTLY IF EXISTS idx_chunks_vector;
    #       DROP INDEX CONCURRENTLY IF EXISTS idx_cache_vector;


def downgrade() -> None:
    # 역순: HNSW drop + halfvec → vector 컬럼 복귀 (ivfflat은 유지된 상태 가정).
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
