# Upload 도메인 검증 예외 — Sprint 25 T-SEC-3 (BUG-SENTINEL-003)
"""HTTP 4xx 매핑: Empty→400 / TooLarge→413 / MIME계열 모두→415."""


class UploadValidationError(Exception):
    """upload 검증 실패 base. router에서 HTTPException으로 변환."""


class EmptyFileError(UploadValidationError):
    """파일 크기 0byte."""

    def __init__(self) -> None:
        super().__init__("빈 파일은 업로드할 수 없습니다")


class FileTooLargeError(UploadValidationError):
    """선언 또는 실 size가 max_bytes 초과."""

    def __init__(self, size: int, limit: int) -> None:
        self.size = size
        self.limit = limit
        super().__init__(f"파일 크기 {size}바이트가 한도 {limit}바이트를 초과합니다")


class UnsupportedMimeError(UploadValidationError):
    """declared MIME이 화이트리스트 외."""

    def __init__(self, mime: str) -> None:
        self.mime = mime
        super().__init__(f"지원하지 않는 MIME: {mime}")


class MimeExtensionMismatchError(UploadValidationError):
    """확장자가 declared MIME 패밀리와 불일치."""

    def __init__(self, extension: str, mime: str) -> None:
        self.extension = extension
        self.mime = mime
        super().__init__(f"확장자 .{extension}는 MIME {mime}와 일치하지 않습니다")


class ContentMismatchError(UploadValidationError):
    """실 content signature가 declared MIME과 상충 (위장 MIME)."""

    def __init__(self, detected: str, declared: str) -> None:
        self.detected = detected
        self.declared = declared
        super().__init__(
            f"파일 내용({detected})이 선언 MIME({declared})과 일치하지 않습니다"
        )
