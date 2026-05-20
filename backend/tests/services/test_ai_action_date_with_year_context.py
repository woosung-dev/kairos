# Sprint 24 Wave 2 T-AI-DATE: AI 액션 마감일 hallucinate fix 회귀 테스트 (BUG-CURIOUS-001)
"""
회귀 가드:
- current_year context 가 프롬프트에 주입되어 연도 미명시 input → 현재 연도 추론
- 후처리 _validate_action_dates 가 과거 연도 due_date 를 drop, 미래 연도는 keep
- DELTA-3 회귀 fix:
  - assignee (한국어 이름) 가 명시된 input → 출력 title/description 에 포함
  - 회의 일정 ("8월 첫째주에 회의") 는 action 으로 over-extraction 되지 않음
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_settings():
    settings = MagicMock()
    settings.gemini_api_key.get_secret_value.return_value = "test-gemini-key"
    return settings


def _make_service_with_response(text: str):
    """Gemini mock 응답을 반환하는 AIProcessingService 인스턴스 생성."""
    mock_response = MagicMock()
    mock_response.text = text

    with patch("src.services.ai_processing.get_settings", return_value=_mock_settings()):
        with patch("src.services.ai_processing.genai") as mock_genai:
            mock_client = MagicMock()
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
            mock_genai.Client.return_value = mock_client

            from src.services.ai_processing import AIProcessingService
            service = AIProcessingService()
            return service, mock_client


# ── Case 1: 연도 미명시 → 현재 연도 추론 ──
@pytest.mark.asyncio
async def test_action_with_year_unspecified_uses_current_year():
    """연도 미명시 input + current_year=2026 → 프롬프트에 current_year 주입 + 출력 due_date.year == 2026."""
    # Gemini 가 current_year context 기반으로 2026 출력하도록 mock
    response_text = json.dumps({
        "actionItems": [
            {
                "title": "박개발 인증 모듈 완료",
                "description": "박개발이 7월 25일까지 완료",
                "priority": "high",
                "dueDate": "2026-07-25",
            }
        ],
        "suggestedProject": {"existingProjectId": None, "newProjectTitle": "인증", "confidence": 0.5},
        "suggestedTags": ["인증"],
    })
    service, mock_client = _make_service_with_response(response_text)

    result = await service.extract_actions_and_link(
        transcript="박개발이 7월 25일까지 인증 모듈 완료해야 합니다.",
        summary="인증 모듈 작업",
        existing_projects=[],
        current_year=2026,
    )

    # 프롬프트에 current_year 가 주입되었는지 verify
    call_kwargs = mock_client.aio.models.generate_content.call_args.kwargs
    prompt_sent = call_kwargs["contents"]
    assert "2026" in prompt_sent, f"current_year 가 프롬프트에 주입되지 않음: {prompt_sent[:500]}"
    assert "현재 연도" in prompt_sent, "프롬프트에 '현재 연도' 컨텍스트 라인 누락"

    # 출력 due_date year 확인
    assert len(result["actionItems"]) >= 1
    due = result["actionItems"][0]["dueDate"]
    assert due is not None
    assert due.startswith("2026"), f"기대=2026, 실제={due}"


# ── Case 2: 과거 연도 drop 후처리 ──
def test_action_with_past_year_in_output_is_dropped():
    """후처리 검증: AI 가 과거 연도 (2024) 출력 시 dueDate=None 으로 drop."""
    from src.services.ai_processing import _validate_action_dates

    actions = [
        {"title": "old", "dueDate": "2024-07-25"},
        {"title": "valid", "dueDate": "2026-07-25"},
        {"title": "no_date", "dueDate": None},
        {"title": "invalid_format", "dueDate": "not-a-date"},
    ]
    validated = _validate_action_dates(actions, current_year=2026)
    assert validated[0]["dueDate"] is None  # 과거 연도 drop
    assert validated[1]["dueDate"] == "2026-07-25"  # current_year keep
    assert validated[2]["dueDate"] is None  # 원래 None
    assert validated[3]["dueDate"] is None  # 파싱 실패 drop


# ── Case 3: 5년+ 미래 keep ──
def test_action_with_far_future_year_kept():
    """5년+ 미래 (2031) 도 keep — 의도적 long-term 가능."""
    from src.services.ai_processing import _validate_action_dates

    actions = [{"title": "future", "dueDate": "2031-07-25"}]
    validated = _validate_action_dates(actions, current_year=2026)
    assert validated[0]["dueDate"] == "2031-07-25"


# ── Case 4: explicit current_year+ 명시 연도 keep ──
def test_explicit_year_input_preserved():
    """input 에 명시된 연도 (2027) 는 그대로 keep."""
    from src.services.ai_processing import _validate_action_dates

    actions = [{"title": "explicit_future", "dueDate": "2027-12-31"}]
    validated = _validate_action_dates(actions, current_year=2026)
    assert validated[0]["dueDate"] == "2027-12-31"


# ── Case 5 (DELTA-3 fix): assignee 명시 회귀 가드 ──
@pytest.mark.asyncio
async def test_action_includes_assignee_when_specified():
    """input 에 한국어 assignee 명시 → 프롬프트에 assignee 명시 의무 라인 포함.

    DELTA-3 회귀 fix (post-swap-delta-report.md §4):
    - S3 박개발 누락, S4 김PM 누락 → 프롬프트에 assignee 명시 의무 강제.
    """
    response_text = json.dumps({
        "actionItems": [
            {
                "title": "박개발: 인증 모듈 완료",
                "description": "박개발이 7월 25일까지 인증 모듈 완료",
                "priority": "high",
                "dueDate": "2026-07-25",
            }
        ],
        "suggestedProject": {"existingProjectId": None, "newProjectTitle": None, "confidence": 0.3},
        "suggestedTags": [],
    })
    service, mock_client = _make_service_with_response(response_text)

    transcript = "박개발이 7월 25일까지 인증 모듈 완료해야 합니다."
    result = await service.extract_actions_and_link(
        transcript=transcript,
        summary="인증 작업",
        existing_projects=[],
        current_year=2026,
    )

    # 프롬프트에 assignee 명시 의무 라인 포함 verify
    call_kwargs = mock_client.aio.models.generate_content.call_args.kwargs
    prompt_sent = call_kwargs["contents"]
    assert "assignee" in prompt_sent or "담당자" in prompt_sent, (
        f"프롬프트에 assignee 명시 의무 라인 누락: {prompt_sent[:800]}"
    )

    # 출력에서 assignee 가 title 또는 description 에 포함되어야 (mock 응답 검증)
    action = result["actionItems"][0]
    text_blob = (action.get("title") or "") + " " + (action.get("description") or "")
    assert "박개발" in text_blob, (
        f"assignee '박개발' 이 title/description 어디에도 포함되지 않음: {action}"
    )


# ── Case 6 (DELTA-3 fix): 회의 일정 over-extraction 방지 ──
def test_meeting_schedule_not_extracted_as_action():
    """프롬프트에 'action vs 일정' 구분 Few-shot 예시 포함.

    DELTA-3 회귀 fix (post-swap-delta-report.md §4):
    - S4 "다음주 화요일 디자인 리뷰 회의" 가 action 으로 over-extraction.
    - 프롬프트에 "회의 일정 자체는 action 아님" 명시 + Few-shot 예시 강제.
    """
    from src.common.prompts import MEETING_ACTIONS_AND_LINKING_PROMPT

    # 프롬프트 본문에 over-extraction 방지 가이드 + Few-shot 포함 verify
    prompt_template = MEETING_ACTIONS_AND_LINKING_PROMPT
    # "회의 일정" 또는 "schedule" 같은 가이드 키워드 포함
    assert "회의 일정" in prompt_template or "일정 자체" in prompt_template, (
        "프롬프트에 'action vs 회의 일정' 구분 가이드 라인 누락"
    )
    # Few-shot 예시 마커
    assert "Few-shot" in prompt_template or "예시" in prompt_template, (
        "프롬프트에 Few-shot 예시 section 누락"
    )
