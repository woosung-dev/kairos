# apps/api/src/workspaces/exceptions.py
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


def _object_particle(word: str) -> str:
    """한국어 목적격 조사(을/를)를 마지막 글자의 받침 유무로 선택.

    받침 있음 → '을', 받침 없음 → '를'. 한글 음절 영역(0xAC00~0xD7A3)에서
    (코드포인트 - 0xAC00) % 28 != 0 이면 종성(받침)이 존재한다.
    비-한글(영문/숫자/빈 문자열)로 끝나면 안전하게 '를' fallback.
    """
    if not word:
        return "를"
    last = word[-1]
    code = ord(last)
    if 0xAC00 <= code <= 0xD7A3:
        has_batchim = (code - 0xAC00) % 28 != 0
        return "을" if has_batchim else "를"
    return "를"


class PersonalWorkspaceProtected(HTTPException):
    """Sprint 15 ADR-016 AD-43: Personal workspace는 항상 1명, 팀 초대 / ProjectMember 추가 불가."""

    def __init__(self, action: str = "operation") -> None:
        super().__init__(
            status_code=403,
            detail=f"개인 워크스페이스에는 {action}{_object_particle(action)} 수행할 수 없습니다",
        )
