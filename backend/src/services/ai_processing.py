# backend/src/services/ai_processing.py
"""Gemini AI 처리 서비스. 모든 LLM 호출을 여기서 집중 관리."""
from collections.abc import AsyncGenerator

from google import genai

from src.common.prompts import (
    MEETING_ACTIONS_AND_LINKING_PROMPT,
    MEETING_SUMMARY_SYSTEM_PROMPT,
    RAG_SYSTEM_PROMPT,
    parse_json_response,
)
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

    async def extract_actions_and_link(
        self,
        transcript: str,
        summary: str,
        existing_projects: list[dict],
    ) -> dict:
        """트랜스크립트 → 액션 아이템 + 프로젝트 연결 추천.

        반환 형식:
        {
            "actionItems": [
                {
                    "title": str,
                    "description": str | None,
                    "priority": "high" | "medium" | "low",
                    "dueDate": "YYYY-MM-DD" | None,
                }
            ],
            "suggestedProject": {
                "existingProjectId": str | None,
                "newProjectTitle": str | None,
                "confidence": float,
            },
            "suggestedTags": list[str],
        }
        """
        projects_context = "\n".join(
            f"- {p['id']}: {p['title']} ({p['status']})"
            for p in existing_projects
        ) or "기존 프로젝트 없음"

        prompt = MEETING_ACTIONS_AND_LINKING_PROMPT.format(
            transcript=transcript,
            summary=summary,
            projects_context=projects_context,
        )

        response = await self.client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        return parse_json_response(response.text)

    async def stream_rag_answer(
        self,
        question: str,
        sources_text: str,
    ) -> AsyncGenerator[str, None]:
        """RAG 답변 스트리밍. Gemini의 토큰을 하나씩 yield."""
        prompt = RAG_SYSTEM_PROMPT.format(
            sources=sources_text,
            question=question,
        )

        stream = await self.client.aio.models.generate_content_stream(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        async for chunk in stream:
            if chunk.text:
                yield chunk.text
