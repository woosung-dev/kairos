# backend/src/actions/exceptions.py
"""ActionItem 도메인 예외."""
from fastapi import HTTPException

from src.common.exceptions import NotFoundError


class ActionItemNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("액션 아이템")


# ── Sprint 23 D4 Task 2 Step 2.5: promote 검증 예외 (inbox/notes/meetings 패턴 정렬) ──


class TargetWorkspaceInvalidError(HTTPException):
    """target workspace 미존재 또는 promoter 가 멤버 아님."""

    def __init__(self) -> None:
        super().__init__(
            status_code=403, detail="대상 워크스페이스가 유효하지 않습니다"
        )


class CannotPromoteToPersonalError(HTTPException):
    """personal workspace 로 promote 시도."""

    def __init__(self) -> None:
        super().__init__(
            status_code=400, detail="개인 워크스페이스로는 promote 할 수 없습니다"
        )


class CannotPromoteToSameWorkspaceError(HTTPException):
    """source/target workspace 동일."""

    def __init__(self) -> None:
        super().__init__(
            status_code=400, detail="같은 워크스페이스로는 promote 할 수 없습니다"
        )
