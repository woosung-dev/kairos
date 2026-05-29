# 외부 알림 전송 유틸 — Slack incoming webhook (미설정 시 no-op, best-effort)
import logging

import httpx

from src.core.config import get_settings

logger = logging.getLogger(__name__)


async def send_slack_message(text: str) -> bool:
    """Slack incoming webhook 으로 메시지 전송.

    SLACK_FEEDBACK_WEBHOOK_URL 미설정 시 no-op(로그만) — 코드 경로는 항상 동작한다.
    전송 실패는 삼켜서(best-effort) 호출자(피드백 저장) 흐름을 막지 않는다.
    반환값은 실제 전송 여부.
    """
    webhook = get_settings().slack_feedback_webhook_url
    if not webhook:
        logger.info("slack_webhook_unset_noop: %s", text[:120])
        return False
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook, json={"text": text}, timeout=5.0)
            resp.raise_for_status()
        return True
    except Exception as exc:  # best-effort — 알림 실패가 본 흐름을 막지 않음
        logger.warning("slack_send_failed: %s", type(exc).__name__)
        return False
