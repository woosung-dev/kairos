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

# F-2A v3 (codex 3차 P2): ISO-BMFF ftyp brand allowlist.
# HEIC/AVIF/heif 등 image brand (heic/heix/mif1/avif/avis/hevc 등) 는 누락 →
# `_detect_mime_from_signature` 에서 None 반환 → binary fail-closed.
# 출처: ISO/IEC 14496-12 + Apple QuickTime spec + Apple HEIC FAQ.
_MP4_BRANDS: set[bytes] = {
    b"isom",  # ISO Base Media File Format
    b"iso2",
    b"iso3",
    b"iso4",
    b"iso5",
    b"iso6",
    b"mp41",  # MP4 v1
    b"mp42",  # MP4 v2
    b"mp71",  # MPEG-7
    b"avc1",  # AVC (H.264)
    b"MSNV",  # MSN Video
    b"M4A ",  # iTunes audio (note trailing space)
    b"M4B ",  # iTunes audiobook
    b"M4P ",  # iTunes protected
    b"M4V ",  # iTunes video
    b"f4v ",  # Flash video
    b"dash",  # MPEG-DASH segment
}

# 확장자 → 허용 MIME family 매핑 (검증 양방향)
# BUG-S27d-3 fix (Sprint 27d): 이전엔 매핑에 없는 확장자라도 declared text/* 면 자유 통과
# (.exe + text/plain 우회 경로). 정당 텍스트 확장자를 명시 매핑으로 흡수하고 free-pass 제거.
_EXT_TO_MIME_FAMILY: dict[str, set[str]] = {
    "mp3": {"audio/mpeg"},
    "m4a": {"audio/mp4", "audio/x-m4a"},
    # F-2A fix (Sprint 25 polish v2, codex 2차): 브라우저가 video container 파일을
    # video/* MIME 으로 전송. STT 파이프라인은 audio track 만 추출. accept.
    "mp4": {"audio/mp4", "video/mp4"},
    "mov": {"video/quicktime"},
    "wav": {"audio/wav", "audio/x-wav"},
    "webm": {"audio/webm", "video/webm"},
    "ogg": {"audio/ogg"},
    "pdf": {"application/pdf"},
    "txt": {"text/plain"},
    "md": {"text/markdown", "text/plain"},
    # 정당 텍스트 family — declared MIME text/plain 로 전송되는 일반 형식
    "csv": {"text/plain"},
    "json": {"text/plain"},
    "log": {"text/plain"},
    "rtf": {"text/plain"},
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
    # MP4/M4A/MOV: "ftyp" at offset 4-8 (container box).
    # F-2A v3 (codex 3차 P2 fix): ftyp brand (offset 8-12) 기반 allowlist —
    # ISO-BMFF image (HEIC/AVIF/heif) 도 ftyp 사용 → 무차별 audio/mp4 매핑이
    # bypass 위험 (image renamed to .mp4 + declared video/mp4 통과). 알려진
    # mp4/m4a/mov brand 만 허용, 그 외 (image brand 포함) → None (fail-closed).
    if len(head) >= 12 and head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand == b"qt  ":
            return "video/quicktime"
        if brand in _MP4_BRANDS:
            return "audio/mp4"
        return None
    # WebM/Matroska: EBML header (audio-only 또는 video container 공용)
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

    F3 fix (Sprint 25 polish v1): unknown signature 는 text/* 만 허용 (UTF-8 check
    가 후속 가드). binary 형식은 fail-closed.

    F-2A v2 fix (Sprint 25 polish v2, codex+agy 2차): MP4/WebM container 는
    audio/video subtype 공용 — signature 가 container 만 식별, audio-only vs
    video-with-audio 구분 불가. declared MIME 이 같은 container subtype 이면 허용.
    """
    if detected is None:
        return declared.startswith("text/")
    if detected == declared:
        return True
    # MP4 container: audio-only 와 video-with-audio 가 동일 ftyp 박스 사용.
    # FFmpeg STT 가 audio track 만 추출하므로 video/mp4 + video/quicktime 도 허용.
    if detected == "audio/mp4" and declared in {
        "audio/mp4",
        "audio/x-m4a",
        "video/mp4",
        "video/quicktime",
    }:
        return True
    # WebM container: audio-only 와 video-with-audio 가 동일 EBML 박스.
    if detected == "audio/webm" and declared in {"audio/webm", "video/webm"}:
        return True
    # QuickTime 시그니처(ftypqt) 가 video/quicktime 외 mp4 family 도 허용
    if detected == "video/quicktime" and declared in {"video/quicktime", "video/mp4"}:
        return True
    # audio family 내에서 codec/container variant 허용 (기존 보존)
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
        # BUG-S27d-3 fix (Sprint 27d opus follow-up): 이전엔 ext 가 매핑에 없을 때
        # declared MIME text/* 만으로 통과 → `evil.exe` + `text/plain` 우회 (signature 가
        # None 이고 text/* 면 _is_signature_compatible 도 통과). 정당 텍스트 형식은
        # `_EXT_TO_MIME_FAMILY` 에 명시 추가 (csv/json/log/rtf), 매핑 외 확장자는 항상 reject.
        if ext and ext in _EXT_TO_MIME_FAMILY:
            if declared_mime not in _EXT_TO_MIME_FAMILY[ext]:
                raise MimeExtensionMismatchError(ext, declared_mime)
        elif ext:
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
