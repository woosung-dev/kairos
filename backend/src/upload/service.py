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
    """signature와 declared MIME 호환성. unknown은 허용 (텍스트 등 signature 없는 형식)."""
    if detected is None:
        return True
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

    def validate(self, filename: str, declared_mime: str, data: bytes) -> None:
        """검증 실패 시 도메인 예외 raise. 성공 시 None."""
        # 1. size
        if len(data) == 0:
            raise EmptyFileError()
        if len(data) > self.max_bytes:
            raise FileTooLargeError(len(data), self.max_bytes)
        # 2. MIME 화이트리스트
        if declared_mime not in self.allowed_mimes:
            raise UnsupportedMimeError(declared_mime)
        # 3. 확장자 정합 (확장자 → 허용 MIME family 매핑)
        ext = _get_extension(filename)
        if ext and ext in _EXT_TO_MIME_FAMILY:
            if declared_mime not in _EXT_TO_MIME_FAMILY[ext]:
                raise MimeExtensionMismatchError(ext, declared_mime)
        elif ext:
            # 알 수 없는 확장자 → 거부 (위장 차단)
            raise MimeExtensionMismatchError(ext, declared_mime)
        # 4. content signature
        detected = _detect_mime_from_signature(data[:512])
        if not _is_signature_compatible(detected, declared_mime):
            raise ContentMismatchError(detected or "unknown", declared_mime)
        if not _check_text_content(data[:512], declared_mime):
            raise ContentMismatchError("non-utf8 bytes", declared_mime)
