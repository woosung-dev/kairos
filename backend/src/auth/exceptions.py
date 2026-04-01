# backend/src/auth/exceptions.py
"""Auth 도메인 예외."""
from src.common.exceptions import NotFoundError, UnauthorizedError


class UserNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("사용자")


class InvalidTokenError(UnauthorizedError):
    pass
