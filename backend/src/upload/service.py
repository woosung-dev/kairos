# Upload 검증 도메인 서비스 — size + MIME + 확장자 + content signature
"""Sprint 25 T-SEC-3 (BUG-SENTINEL-003) — AsyncSession import 금지 (stateless 검증)."""
from src.core.config import get_settings
from src.upload.exceptions import (
    ContentMismatchError,
    EmptyFileError,
    FileTooLargeError,
    MimeExtensionMismatchError,
    UnsupportedMimeError,
)

# 확장자 → 허용 MIME family 매핑 (검증 양방향)
_EXT_TO_MIME_FAMILY: dict[str, set[str]] = {
    "mp3": {"audio/mpeg"},
    "m4a": {"audio/mp4", "audio/x-m4a"},
    "mp4": {"audio/mp4"},  # 비디오 mp4는 audio-only 추출용으로 허용
    "wav": {"audio/wav", "audio/x-wav"},
    "webm": {"audio/webm"},
    "ogg": {"audio/ogg"},
    "pdf": {"application/pdf"},
    "txt": {"text/plain"},
    "md": {"text/markdown", "text/plain"},
}


def _detect_mime_from_signature(head: bytes) -> str | None:
    """파일 head 512byte로 실제 MIME 추정. 미식별은 None (whitelist 허용)."""
    if len(head) < 4:
        return None
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    # MP3: ID3v2 헤더 또는 MPEG frame sync (0xFF 0xFB/0xF3/0xF2)
    if head.startswith(b"ID3"):
        return "audio/mpeg"
    if head[0] == 0xFF and head[1] in (0xFB, 0xF3, 0xF2, 0xFA, 0xF2):
        return "audio/mpeg"
    # WAV: "RIFF....WAVE"
    if head.startswith(b"RIFF") and len(head) >= 12 and head[8:12] == b"WAVE":
        return "audio/wav"
    # MP4/M4A: "ftyp" at offset 4-8 (container box)
    if len(head) >= 12 and head[4:8] == b"ftyp":
        return "audio/mp4"
    # WebM/Matroska: EBML header
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return "audio/webm"
    # Ogg: "OggS"
    if head.startswith(b"OggS"):
        return "audio/ogg"
    # PNG / JPEG / GIF (이미지 거부용 식별)
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"GIF8"):
        return "image/gif"
    # ZIP / docx / xlsx (오피스 거부용)
    if head.startswith(b"PK\x03\x04"):
        return "application/zip"
    return None


def _is_signature_compatible(detected: str | None, declared: str) -> bool:
    """signature와 declared MIME 호환성.

    F3 fix (Sprint 25 polish, codex+agy review): unknown signature 는 text/* 만
    허용 (UTF-8 check 가 후속 가드). binary 형식은 fail-closed — random/위장 바이트
    가 audio/mp4 등으로 통과하는 bypass 차단.
    """
    if detected is None:
        # binary 형식은 signature 의무. text/* 만 unknown 허용 (UTF-8 후속 검증).
        return declared.startswith("text/")
    if detected == declared:
        return True
    # audio family 내에서 codec/container variant 허용
    if declared.startswith("audio/") and detected.startswith("audio/"):
        return True
    return False


def _check_text_content(head: bytes, declared: str) -> bool:
    """text/* 형식이면 head를 UTF-8 디코드 가능해야 함."""
    if not declared.startswith("text/"):
        return True
    try:
        head.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _parse_allowed_mimes(csv: str) -> set[str]:
    return {m.strip() for m in csv.split(",") if m.strip()}


def _get_extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


class UploadValidator:
    """upload 검증기 — 4 layer (size / MIME 화이트리스트 / 확장자 정합 / content signature)."""

    def __init__(
        self,
        max_bytes: int | None = None,
        allowed_mimes: set[str] | None = None,
    ) -> None:
        settings = get_settings()
        self.max_bytes = max_bytes if max_bytes is not None else settings.max_upload_bytes
        self.allowed_mimes = allowed_mimes or _parse_allowed_mimes(
            settings.allowed_upload_mimes
        )

    def validate_pre_upload(self, filename: str, declared_mime: str) -> None:
        """Pre-upload 검증 (presigned-url 흐름용 — size/signature 제외).

        F1 fix (Sprint 25 polish, agy review): /presigned-url 가 T-SEC-3 검증
        bypass 던 critical 결손 해소. 파일 미존재 시점 (URL 발급 시) 에 가능한
        MIME 화이트리스트 + 확장자 정합만 1차 차단. size/signature 는 R2 PUT 이
        후 별도 검증 필요 (BL carry).
        """
        if declared_mime not in self.allowed_mimes:
            raise UnsupportedMimeError(declared_mime)
        ext = _get_extension(filename)
        if ext and ext in _EXT_TO_MIME_FAMILY:
            if declared_mime not in _EXT_TO_MIME_FAMILY[ext]:
                raise MimeExtensionMismatchError(ext, declared_mime)
        elif ext:
            # F4 fix: text/* family 는 확장자 자유 (.csv/.json/.rtf 등 정당
            # 텍스트 파일 차단 회피 — signature/UTF-8 가드가 충분).
            if not declared_mime.startswith("text/"):
                raise MimeExtensionMismatchError(ext, declared_mime)

    def validate(self, filename: str, declared_mime: str, data: bytes) -> None:
        """검증 실패 시 도메인 예외 raise. 성공 시 None.

        Proxy upload (`/file`) 흐름용 — pre_upload 검증 + size + signature 까지
        4 계층 모두 적용.
        """
        # 1. size
        if len(data) == 0:
            raise EmptyFileError()
        if len(data) > self.max_bytes:
            raise FileTooLargeError(len(data), self.max_bytes)
        # 2+3. MIME 화이트리스트 + 확장자 정합 (pre_upload 와 동일 로직 재사용)
        self.validate_pre_upload(filename, declared_mime)
        # 4. content signature (data 의존)
        detected = _detect_mime_from_signature(data[:512])
        if not _is_signature_compatible(detected, declared_mime):
            raise ContentMismatchError(detected or "unknown", declared_mime)
        if not _check_text_content(data[:512], declared_mime):
            raise ContentMismatchError("non-utf8 bytes", declared_mime)
