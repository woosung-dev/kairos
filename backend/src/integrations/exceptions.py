"""Integrations 도메인 예외."""
from typing import ClassVar

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


class DriveClientError(Exception):
    """Google Drive 원본 동기화 실패의 안전한 도메인 예외."""

    allows_purge: ClassVar[bool] = False
    message: ClassVar[str] = "Google Drive 원본을 확인할 수 없습니다."

    def __init__(self) -> None:
        super().__init__(self.message)


class DriveSourceMissingError(DriveClientError):
    """Drive에서 원본 삭제가 확인되어 purge가 가능한 실패."""

    allows_purge = True
    message = "Google Drive 원본이 존재하지 않습니다."


class DrivePermissionRevokedError(DriveClientError):
    """Drive 접근 권한 회수가 확인되어 purge가 가능한 실패."""

    allows_purge = True
    message = "Google Drive 접근 권한이 회수되었습니다."


class DriveReauthenticationRequiredError(DriveClientError):
    """재인증이 필요한 실패. 원본 purge는 허용하지 않는다."""

    message = "Google Drive 재인증이 필요합니다."


class DriveTemporaryError(DriveClientError):
    """일시 장애 또는 판단 불가 실패. 기존 원본을 보존한다."""

    message = "Google Drive 일시 장애입니다."


class DriveUnsupportedMimeTypeError(DriveClientError):
    """현재 수집 대상이 아닌 MIME 형식."""

    message = "지원하지 않는 Google Drive MIME 형식입니다."
