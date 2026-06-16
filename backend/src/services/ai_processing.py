# backend/src/services/ai_processing.py
"""Gemini AI 처리 서비스. 모든 LLM 호출을 여기서 집중 관리."""
import logging
from collections.abc import AsyncGenerator
from datetime import date

from google import genai

from src.common.prompts import (
    MEETING_ACTIONS_AND_LINKING_PROMPT,
    MEETING_SUMMARY_SYSTEM_PROMPT,
    RAG_SYSTEM_PROMPT,
    MeetingActionsResult,
    MeetingSummaryResult,
    parse_json_response,
)
from src.core.config import get_settings
from src.services.ai_resilience import (
    GEMINI_STREAM_TIMEOUT_SEC,
    gemini_breaker,
    with_gemini_timeout,
)

logger = logging.getLogger(__name__)

# Gemini 모델 고정
GEMINI_MODEL = "gemini-3.1-flash-lite"


def _validate_action_dates(actions: list[dict], current_year: int) -> list[dict]:
    """T-AI-DATE 후처리 검증: 과거 연도 due_date 또는 파싱 불가 dueDate 를 drop.

    BUG-CURIOUS-001 (Sprint 24 Wave 2) — Gemini 가 연도 hallucinate (예: 2024) 출력 시
    안전망. 5년+ 미래는 keep (의도적 long-term action 가능).

    in-place mutation 후 동일 list 반환 (caller 가 새 list 든 기존 list 든 동일 결과).
    """
    for action in actions:
        due_raw = action.get("dueDate")
        if due_raw is None:
            continue
        try:
            parsed = date.fromisoformat(due_raw)
        except (TypeError, ValueError):
            logger.warning(
                "AI dueDate 파싱 실패, drop",
                extra={"dueDate": due_raw, "title": action.get("title")},
            )
            action["dueDate"] = None
            continue
        if parsed.year < current_year:
            logger.warning(
                "AI hallucinate past year dueDate, drop",
                extra={
                    "dueDate": due_raw,
                    "current_year": current_year,
                    "title": action.get("title"),
                },
            )
            action["dueDate"] = None
    return actions


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
        # Sprint 28 PERF-4 — timeout + circuit breaker (infinite hang 차단).
        response = await with_gemini_timeout(
            self.client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=f"{MEETING_SUMMARY_SYSTEM_PROMPT}\n\n{transcript}",
            )
        )
        raw = parse_json_response(response.text)
        MeetingSummaryResult.model_validate(raw)
        return raw

    async def extract_actions_and_link(
        self,
        transcript: str,
        summary: str,
        existing_projects: list[dict],
        current_year: int | None = None,
    ) -> dict:
        """트랜스크립트 → 액션 아이템 + 프로젝트 연결 추천.

        Sprint 24 Wave 2 T-AI-DATE (BUG-CURIOUS-001):
        - `current_year` 를 프롬프트 컨텍스트에 주입 (연도 미명시 input → 추론).
        - 응답 dueDate 후처리: 과거 연도 또는 파싱 불가 → None drop.

        반환 형식:
        {
            "actionItems": [...],
            "suggestedProject": {...},
            "suggestedTags": [...],
        }
        """
        if current_year is None:
            current_year = date.today().year
        current_date_str = date.today().isoformat()

        projects_context = "\n".join(
            f"- {p['id']}: {p['title']} ({p['status']})"
            for p in existing_projects
        ) or "기존 프로젝트 없음"

        prompt = MEETING_ACTIONS_AND_LINKING_PROMPT.format(
            transcript=transcript,
            summary=summary,
            projects_context=projects_context,
            current_year=current_year,
            current_year_plus_1=current_year + 1,
            current_date=current_date_str,
        )

        # Sprint 28 PERF-4 — timeout + circuit breaker.
        response = await with_gemini_timeout(
            self.client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
        )
        raw = parse_json_response(response.text)
        MeetingActionsResult.model_validate(raw)

        # T-AI-DATE 후처리: 과거 연도 dueDate drop (BUG-CURIOUS-001 안전망)
        raw["actionItems"] = _validate_action_dates(
            raw.get("actionItems", []), current_year=current_year
        )
        return raw

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

        # Sprint 28 PERF-4 — stream init timeout 60s. stream iteration 자체는
        # SSE 토큰 yield 라 별도 timeout 적용 안 함 (사용자 disconnect 시 자연 종료).
        stream = await with_gemini_timeout(
            self.client.aio.models.generate_content_stream(
                model=GEMINI_MODEL,
                contents=prompt,
            ),
            timeout_sec=GEMINI_STREAM_TIMEOUT_SEC,
        )
        # Sprint 29 R1 (svc-breaker): stream init 성공 시 with_gemini_timeout 이 breaker 를
        # reset 하지만, async for 중 mid-stream vendor 실패는 breaker 밖이라 집계되지 않았다
        # → vendor 가 매번 init 후 mid-stream 실패해도 circuit 이 열리지 않는 구멍.
        # mid-stream 실패를 on_failure 로 집계한다. 사용자 disconnect(CancelledError /
        # GeneratorExit = BaseException)는 `except Exception` 이 잡지 않아 vendor 실패로
        # 오집계되지 않는다.
        try:
            async for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except Exception:
            gemini_breaker.on_failure()
            raise
