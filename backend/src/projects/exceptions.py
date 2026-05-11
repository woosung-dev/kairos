# backend/src/projects/exceptions.py
"""Project 도메인 예외."""
from fastapi import HTTPException

from src.common.exceptions import NotFoundError


class ProjectNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("프로젝트")


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
