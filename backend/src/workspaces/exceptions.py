# backend/src/workspaces/exceptions.py
"""Workspace 도메인 예외."""
from fastapi import HTTPException

from src.common.exceptions import AlreadyExistsError, NotFoundError


class WorkspaceNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("워크스페이스")


class MemberAlreadyExistsError(AlreadyExistsError):
    def __init__(self) -> None:
        super().__init__("멤버")


class InviteNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("초대 링크")


class InviteExpiredError(Exception):
    """초대 링크 만료 또는 사용 한도 초과."""
    def __init__(self, reason: str = "초대 링크가 만료되었거나 사용할 수 없습니다") -> None:
        self.reason = reason
        super().__init__(reason)


class CannotModifyOwnerError(Exception):
    """Owner 역할은 변경/제거 불가."""
    def __init__(self) -> None:
        super().__init__("Owner의 역할을 변경하거나 제거할 수 없습니다")


class MemberNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("멤버")


class PersonalWorkspaceProtected(HTTPException):
    """Sprint 15 ADR-016 AD-43: Personal workspace는 항상 1명, 팀 초대 / ProjectMember 추가 불가."""

    def __init__(self, action: str = "operation") -> None:
        super().__init__(
            status_code=403,
            detail=f"개인 워크스페이스에는 {action}을(를) 수행할 수 없습니다",
        )
