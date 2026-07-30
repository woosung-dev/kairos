"""Integrations 도메인 예외."""
from fastapi import HTTPException

from src.common.exceptions import NotFoundError


class IntegrationConnectionNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("연동 연결")


class ExternalDocumentNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("외부 문서")


class IntegrationEncryptionError(HTTPException):
    """연동 토큰 암호화·복호화 실패를 HTTP 경계에 안전하게 변환한다."""

    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            detail="연동 인증 정보를 처리할 수 없습니다. 잠시 후 다시 시도해주세요.",
        )
