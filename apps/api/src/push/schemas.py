# 웹 푸시 API 입출력 Pydantic V2 스키마 (API-001~003, camelCase alias I-16) + 내부 발송 DTO
import base64
import binascii
import ipaddress
import re
import uuid
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

# 발송 이벤트 종류 (pwa.md §5.4). 사람이 읽는 문구는 SW 가 kind 로 정한다.
PushKind = Literal["meeting.completed", "meeting.failed"]

# 푸시 서비스 호스트 allowlist (pwa.md §5.2, R-6 SSRF 차단).
# 점으로 시작하지 않으면 정확 일치, 점으로 시작하면 하위 도메인 접미사 일치.
# `.notify.windows.com` (Edge/WNS) 은 호스트 형식·실제 발송 모두 미검증이다.
PUSH_HOST_ALLOWLIST: tuple[str, ...] = (
    "fcm.googleapis.com",
    "android.googleapis.com",
    ".push.services.mozilla.com",
    ".push.apple.com",
    ".notify.windows.com",
)

PUSH_ENDPOINT_MAX_LENGTH = 2048

_BASE64URL_RE = re.compile(r"^[A-Za-z0-9_-]+={0,2}$")
# 공백·제어문자·역슬래시 — 우리 URL 파서(urllib)와 HTTP 클라이언트(yarl)의 해석이 갈릴 수 있는 문자
_FORBIDDEN_ENDPOINT_CHARS_RE = re.compile(r"[\s\\\x00-\x1f\x7f]")


def _decode_base64url(value: str) -> bytes | None:
    """base64url(패딩 선택) 디코드. 알파벳 밖 문자·깨진 길이는 None."""
    if not _BASE64URL_RE.fullmatch(value):
        return None
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (binascii.Error, ValueError):
        return None


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def _is_allowed_push_host(host: str) -> bool:
    for entry in PUSH_HOST_ALLOWLIST:
        if entry.startswith("."):
            if host.endswith(entry):
                return True
        elif host == entry:
            return True
    return False


class PushConfigResponse(BaseModel):
    """API-001 응답 — VAPID 3개 설정이 다 있을 때만 isEnabled=true."""

    model_config = ConfigDict(populate_by_name=True)

    is_enabled: bool = Field(alias="isEnabled")
    # 기본값 없음 — 계약에서 항상 존재하는 `string | null` 로 나가게 (FE 가 optional 분기를 안 하게)
    vapid_public_key: str | None = Field(alias="vapidPublicKey")


class PushSubscriptionKeys(BaseModel):
    """PushSubscription.toJSON().keys — 둘 다 base64url."""

    p256dh: str
    auth: str

    @field_validator("p256dh")
    @classmethod
    def _validate_p256dh(cls, value: str) -> str:
        decoded = _decode_base64url(value)
        if decoded is None or len(decoded) != 65 or decoded[0] != 0x04:
            raise ValueError(
                "p256dh must be a base64url uncompressed P-256 public key (65 bytes)"
            )
        return value

    @field_validator("auth")
    @classmethod
    def _validate_auth(cls, value: str) -> str:
        decoded = _decode_base64url(value)
        if decoded is None or len(decoded) != 16:
            raise ValueError("auth must be a base64url secret (16 bytes)")
        return value


class PushSubscriptionUpsertRequest(BaseModel):
    """API-002 요청 — PushSubscription.toJSON() 의 부분집합 (그 외 필드는 무시)."""

    endpoint: str = Field(max_length=PUSH_ENDPOINT_MAX_LENGTH)
    keys: PushSubscriptionKeys

    @field_validator("endpoint")
    @classmethod
    def _validate_endpoint(cls, value: str) -> str:
        """SSRF 차단 (pwa.md §5.2). 오류 문구에 URL 을 다시 담지 않는다."""
        # ASCII 만 받는다 — 실제 푸시 서비스 endpoint 는 전부 ASCII 다. 비ASCII 는 IDN 호스트의 punycode
        # 변환(우리 파서 vs HTTP 클라이언트 해석 차이), btree 인덱스 행 한도 초과(2048자 × 3바이트),
        # lone surrogate 의 DB 인코딩 실패로 이어져 422 가 아니라 500 이 됐다 (EVAL-P2-1 D1).
        if not value.isascii():
            raise ValueError("endpoint must be ASCII")
        if _FORBIDDEN_ENDPOINT_CHARS_RE.search(value):
            raise ValueError("endpoint contains forbidden characters")
        try:
            parts = urlsplit(value)
        except ValueError as exc:
            raise ValueError("endpoint is not a valid URL") from exc
        if parts.scheme != "https":
            raise ValueError("endpoint must use https")
        if "@" in parts.netloc:
            raise ValueError("endpoint must not contain userinfo")
        try:
            port = parts.port
        except ValueError as exc:
            raise ValueError("endpoint port is invalid") from exc
        if port not in (None, 443):
            raise ValueError("endpoint port must be omitted or 443")
        host = parts.hostname
        if not host:
            raise ValueError("endpoint host is missing")
        if _is_ip_literal(host):
            raise ValueError("endpoint host must not be an IP literal")
        if not _is_allowed_push_host(host):
            raise ValueError("endpoint host is not an allowed push service")
        return value


class PushSubscriptionUpsertResponse(BaseModel):
    """API-002 응답 — 같은 endpoint 면 id 가 유지된다."""

    id: uuid.UUID


@dataclass(frozen=True, slots=True)
class PushTarget:
    """발송 대상 구독의 원시 값 복사본 (pwa.md §5.3 1c).

    조회 세션을 닫은 뒤 발송 단계에서 쓰므로 ORM 객체가 아니라 값만 담는다.
    endpoint·keys 는 repr 에서 뺀다 — 실수로 로그에 찍혀도 capability URL 이 새지 않게.
    """

    id: uuid.UUID
    endpoint: str = field(repr=False)
    p256dh: str = field(repr=False)
    auth: str = field(repr=False)
