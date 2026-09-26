"""meetings.error_message 정제 — 기존 실패 행의 원문 제거 (C-023)

Revision ID: b3d5f8a1c2e4
Revises: a9c4e2f7b1d0
Create Date: 2026-09-27 00:00:00.000000

2026-09-26 실사용 준비 정검 C-023: 파이프라인이 실패하면 `error_message=str(e)` 를 저장했고
viewer 이상에게 그대로 반환됐다. 실측 값에 R2 계정 endpoint·버킷명·access key id·1시간
서명 URL 이 들어 있었다. promote 사본도 같은 값을 복제한다 (`meetings/service.py` promote).

코드는 이번 PR 에서 일반 문구만 저장하도록 바뀌었다 (`pipeline_service._public_error_message`).
이 리비전은 **이미 저장된** 원문을 같은 일반 문구로 덮는다.

- 데이터 전용 · 스키마 불변 → 구 이미지 롤백에 영향 없음.
- 되돌릴 수 없다 (원문은 docker logs 에만 남는다). downgrade 는 no-op.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b3d5f8a1c2e4"
down_revision: Union[str, Sequence[str], None] = "a9c4e2f7b1d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# pipeline_service.PIPELINE_FAILURE_MESSAGE 와 같은 문구 (마이그레이션은 앱 코드를 import 하지 않는다).
_SCRUBBED = "회의 처리 중 오류가 발생했습니다. 다시 시도하거나 관리자에게 문의하세요."


def upgrade() -> None:
    op.execute(
        "UPDATE meetings SET error_message = '"
        + _SCRUBBED
        + "' WHERE error_message IS NOT NULL AND error_message <> '"
        + _SCRUBBED
        + "'"
    )


def downgrade() -> None:
    # 원문 복구 불가 (의도). 스키마 변경이 없으므로 되돌릴 것도 없다.
    pass
