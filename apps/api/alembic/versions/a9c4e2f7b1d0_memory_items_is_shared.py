"""memory_items.is_shared — 메모 작성자 전용 규칙 (C-020 결정 (a))

Revision ID: a9c4e2f7b1d0
Revises: c1a7e0b5d3f2
Create Date: 2026-09-27 00:00:00.000000

2026-09-26 실사용 준비 정검 C-020: 팀 워크스페이스에서 캡처한 메모를 같은 워크스페이스의
다른 멤버가 recall·상세·RAG 로 원문까지 읽었다. 사용자 결정 (a) = **메모는 작성자 전용**.
예외는 사용자가 "팀으로 올리기"(promote)로 명시적으로 공유한 사본뿐이다.

- 가산형: NOT NULL + server_default false → 구 api 이미지가 이 스키마 위에서 그대로 동작한다
  (롤백 = 이미지 태그 되돌리기).
- backfill: 과거 promote 로 만들어진 사본을 is_shared=true 로 표시한다. 사본 id 는
  memory_events(event_type='promote').event_metadata->>'new_memory_id' 에만 남아 있다
  (PromotionAudit 에는 원본 id 만 있다). 이벤트가 없는 사본은 작성자 전용으로 남는다 = fail-closed.
  **원본 작성자가 직접 올린 사본만** 공유로 본다 (me.user_id = 원본 user_id). 수정 전에는 남의 메모도
  올릴 수 있었는데, 그렇게 만든 사본까지 공유로 표시하면 결정 (a) 이전의 누수를 확정하게 된다 (E2-05).
  원본이 지워졌거나 공유 사본을 다시 올린 경우도 작성자 전용으로 남는다.
  text 로 비교한다 — 형식이 깨진 값이 있어도 uuid CAST 실패로 마이그레이션이 멈추지 않게.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a9c4e2f7b1d0"
down_revision: Union[str, Sequence[str], None] = "c1a7e0b5d3f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "memory_items",
        sa.Column(
            "is_shared",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.execute(
        """
        UPDATE memory_items mi
        SET is_shared = true
        WHERE EXISTS (
            SELECT 1
            FROM memory_events me
            JOIN memory_items src
              ON CAST(src.id AS text) = me.event_metadata->>'source_memory_id'
            WHERE me.event_type = 'promote'
              AND me.event_metadata->>'new_memory_id' = CAST(mi.id AS text)
              AND src.user_id = me.user_id
        )
        """
    )


def downgrade() -> None:
    op.drop_column("memory_items", "is_shared")
