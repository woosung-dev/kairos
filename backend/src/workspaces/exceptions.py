# backend/src/workspaces/exceptions.py
"""Workspace 도메인 예외."""
from src.common.exceptions import AlreadyExistsError, NotFoundError


class WorkspaceNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("워크스페이스")


class MemberAlreadyExistsError(AlreadyExistsError):
    def __init__(self) -> None:
        super().__init__("멤버")
