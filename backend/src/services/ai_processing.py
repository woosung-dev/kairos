# backend/src/services/ai_processing.py
"""Gemini AI 처리 서비스. 모든 LLM 호출을 여기서 집중 관리."""
from google import genai

from src.common.prompts import MEETING_SUMMARY_SYSTEM_PROMPT, parse_json_response
from src.core.config import get_settings

# Gemini 모델 고정
GEMINI_MODEL = "gemini-2.5-flash"


class AIProcessingService:
    """Gemini API를 통한 회의 요약 생성."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client = genai.Client(
            api_key=settings.gemini_api_key.get_secret_value()
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
        response = await self.client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"{MEETING_SUMMARY_SYSTEM_PROMPT}\n\n{transcript}",
        )
        return parse_json_response(response.text)
