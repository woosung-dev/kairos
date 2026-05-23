# Svix 서명 검증 Depends — Clerk webhook 의 svix-id/svix-timestamp/svix-signature 헤더 검증
"""Svix 서명 검증.

Sprint 25 ADR-022 회수 옵션 5단계 중 §2 (Svix 검증 middleware) 구현.
Sprint 27b ADR-024 supersede 진입.

검증 흐름:
1. 3개 svix-* 헤더 필수 (누락 시 401 INVALID_SIGNATURE)
2. Webhook(secret).verify(body, headers) 호출 — Svix SDK 가 HMAC + timestamp drift 검증
3. WebhookVerificationError → 401 (timestamp 관련 message → STALE_TIMESTAMP, 그 외 → INVALID_SIGNATURE)

검증된 payload (dict) 를 endpoint 로 전달 — body 재read 방지.
"""
from fastapi import Depends, HTTPException, Request
from svix.webhooks import Webhook, WebhookVerificationError

from src.core.config import Settings, get_settings


async def verify_svix_signature(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Clerk webhook Svix 서명을 검증하고 payload dict 를 반환.

    검증 실패 시 401 발생 (DB write 도달 전 차단). 검증 성공 시 body 는 이미 verify 내부에서
    JSON parse 되어 dict 로 반환되므로 endpoint 는 재 await request.json() 불필요.
    """
    svix_id = request.headers.get("svix-id", "")
    svix_timestamp = request.headers.get("svix-timestamp", "")
    svix_signature = request.headers.get("svix-signature", "")

    if not (svix_id and svix_timestamp and svix_signature):
        raise HTTPException(status_code=401, detail="INVALID_SIGNATURE")

    headers = {
        "svix-id": svix_id,
        "svix-timestamp": svix_timestamp,
        "svix-signature": svix_signature,
    }

    body_bytes = await request.body()
    secret = settings.clerk_webhook_secret.get_secret_value()

    try:
        wh = Webhook(secret)
        verified_payload = wh.verify(body_bytes, headers)
        return verified_payload
    except WebhookVerificationError as e:
        msg = str(e).lower()
        if "timestamp" in msg:
            raise HTTPException(status_code=401, detail="STALE_TIMESTAMP")
        raise HTTPException(status_code=401, detail="INVALID_SIGNATURE")
    except Exception:
        # base64 decode 실패 / signature format 오류 등 → 401 INVALID_SIGNATURE 통일.
        # WebhookVerificationError 외 standardwebhooks 가 raise 하는 binascii.Error / ValueError
        # / IndexError 모두 동일 의미 (검증 실패) — 사용자에게 동일 응답.
        raise HTTPException(status_code=401, detail="INVALID_SIGNATURE")
