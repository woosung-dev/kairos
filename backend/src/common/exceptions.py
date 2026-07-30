# backend/src/common/exceptions.py
"""공통 예외 및 FastAPI 예외 핸들러."""
from fastapi import HTTPException


class NotFoundError(HTTPException):
    """리소스를 찾을 수 없음."""

    def __init__(self, resource: str) -> None:
        self.detail = f"{resource}을(를) 찾을 수 없습니다"
        self.status_code = 404
        super().__init__(status_code=self.status_code, detail=self.detail)


class AlreadyExistsError(HTTPException):
    """리소스가 이미 존재함."""

    def __init__(self, resource: str) -> None:
        self.detail = f"이미 {resource}입니다"
        self.status_code = 409
        super().__init__(status_code=self.status_code, detail=self.detail)


class UnauthorizedError(HTTPException):
    """인증 필요."""

    def __init__(self) -> None:
        super().__init__(status_code=401, detail="인증이 필요합니다")


class ForbiddenError(HTTPException):
    """권한 없음."""

    def __init__(self) -> None:
        super().__init__(status_code=403, detail="권한이 없습니다")


class EncryptionError(Exception):
    """암호화 또는 복호화에 실패."""

    def __init__(self, message: str = "암호화 처리에 실패했습니다") -> None:
        self.message = message
        super().__init__(self.message)
