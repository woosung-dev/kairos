# backend/src/services/ai_processing.py
"""Claude AI 처리 서비스. 모든 Claude 호출을 여기서 집중 관리."""
import anthropic

from src.common.prompts import MEETING_SUMMARY_SYSTEM_PROMPT, parse_json_response
from src.core.config import get_settings

# Claude 모델 고정 — 임의 변경 금지
CLAUDE_MODEL = "claude-sonnet-4-20250514"


class AIProcessingService:
    """Claude API를 통한 회의 요약 생성."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value()
        )

    async def summarize(self, transcript: str) -> dict:
        """트랜스크립트 → 구조화된 요약 dict.

        반환 형식:
        {
            "summary": str,
            "key_decisions": list[str],
            "risks_and_issues": list[str],
            "participants": list[str],
            "topics": list[str],
            "next_meeting_agenda": list[str],
        }
        """
        response = await self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=MEETING_SUMMARY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": transcript}],
        )
        return parse_json_response(response.content[0].text)
