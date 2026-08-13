# backend/src/projects/exceptions.py
"""Project 도메인 예외."""
from fastapi import HTTPException

from src.common.exceptions import NotFoundError


class ProjectNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("프로젝트")


class ProjectHasContentError(HTTPException):
    """콘텐츠(노트/액션)가 연결된 프로젝트는 삭제 차단 (BL-S27e-5)."""

    def __init__(self, notes: int, actions: int) -> None:
        super().__init__(
            status_code=409,
            detail=(
                f"이 프로젝트에 노트 {notes}개, 액션 {actions}개가 연결되어 있습니다. "
                "먼저 삭제하거나 다른 프로젝트로 이동하세요."
            ),
        )


class CrossWorkspaceMemberError(HTTPException):
    """추가 대상 user가 해당 워크스페이스 멤버가 아님."""

    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            detail="해당 사용자가 워크스페이스 멤버가 아닙니다",
        )


class WorkspaceMismatchError(HTTPException):
    """프로젝트가 path workspace_id에 속하지 않음."""

    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            detail="프로젝트가 해당 워크스페이스에 속하지 않습니다",
        )
