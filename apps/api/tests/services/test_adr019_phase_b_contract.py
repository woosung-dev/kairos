# T-AI-1 ADR-019 Phase B post-swap LLM 계약 회귀 테스트 (Sprint 25 Wave 3)
"""
배경:
- ADR-019 Phase A spike (2026-05-14) — Gemini 3.1-flash-lite validated
  (5.76x speedup / 20% cost / schema 3/3).
- ADR-019 Phase B swap (2026-05-15, commit 003908a) — main 적용 완료.
- Sprint 24 Wave 2 T-AI-DATE — due_date hallucinate fix (BUG-CURIOUS-001).
- Sprint 24 Wave 2 DELTA-3 — assignee 누락 + 회의 일정 over-extraction fix.

본 contract 테스트는 실 LLM 호출 없이 (mock 기반):
1. 모델 선택이 Phase B 결정 (gemini-3.1-flash-lite) 에 lock-in 되었는지
2. 프롬프트의 핵심 가드 (current_year context, JSON 스키마, assignee 의무,
   회의 일정 over-extraction 방지) 가 모두 자리에 있는지
3. 후처리 (_validate_action_dates) 가 hallucinate guard 동작하는지
verify. 회귀 시 즉시 fail.

실 LLM 품질 측정 (P/R/F1 vs Sprint 16 baseline) 은 API 비용 + Cloud Run
trace 필요 → 별도 sprint (BL-NEW-DELTA3-REMEASURE Sprint 24 carry).
"""
from src.common.prompts import (
    MEETING_ACTIONS_AND_LINKING_PROMPT,
    MEETING_SUMMARY_SYSTEM_PROMPT,
    MeetingActionsResult,
    MeetingSummaryResult,
)
from src.services.ai_processing import GEMINI_MODEL, _validate_action_dates


class TestModelLockIn:
    """ADR-019 Phase B 모델 선택 lock-in (의도하지 않은 downgrade 차단)."""

    def test_gemini_model_is_phase_b_3_1_flash_lite(self):
        """GEMINI_MODEL == 'gemini-3.1-flash-lite' (ADR-019 Phase B).

        회귀 시점: 2.5-flash (EOL 2026-06-17) 로 되돌아가면 즉시 fail.
        """
        assert GEMINI_MODEL == "gemini-3.1-flash-lite", (
            f"ADR-019 Phase B 결정과 불일치 — 현재={GEMINI_MODEL}. "
            "Gemini 2.5-flash EOL 2026-06-17 회피 결정. ADR-019 §결정 참조."
        )


class TestPromptContract:
    """프롬프트 핵심 가드가 자리에 있는지 (DELTA-3 + BL-024 회귀 가드)."""

    def test_summary_prompt_has_json_schema(self):
        prompt = MEETING_SUMMARY_SYSTEM_PROMPT
        assert "JSON" in prompt and '"summary"' in prompt
        for field in (
            "key_decisions",
            "risks_and_issues",
            "participants",
            "topics",
            "next_meeting_agenda",
        ):
            assert field in prompt, f"summary 스키마 필드 누락: {field}"

    def test_actions_prompt_has_current_year_context(self):
        """BL-024 fix: 현재 연도 context — 프롬프트에 placeholder 또는 직접 라인."""
        prompt = MEETING_ACTIONS_AND_LINKING_PROMPT
        assert "현재 연도" in prompt or "current_year" in prompt, (
            "actions 프롬프트에 현재 연도 컨텍스트 라인 누락 — BL-024 hallucinate 가드 깨짐"
        )

    def test_actions_prompt_enforces_assignee(self):
        """DELTA-3 fix: assignee 명시 의무 가드."""
        prompt = MEETING_ACTIONS_AND_LINKING_PROMPT
        assert "assignee" in prompt or "담당자" in prompt, (
            "actions 프롬프트에 assignee 명시 의무 라인 누락 — DELTA-3 회귀 가드 깨짐"
        )

    def test_actions_prompt_blocks_meeting_schedule_over_extraction(self):
        """DELTA-3 fix: 회의 일정 over-extraction 방지 가드."""
        prompt = MEETING_ACTIONS_AND_LINKING_PROMPT
        assert "회의 일정" in prompt or "일정 자체" in prompt, (
            "actions 프롬프트에 회의 일정 over-extraction 방지 가이드 누락"
        )

    def test_actions_prompt_has_fewshot_examples(self):
        """Phase B post-swap: Few-shot 예시 강제 (DELTA-3 회복 패턴)."""
        prompt = MEETING_ACTIONS_AND_LINKING_PROMPT
        assert "Few-shot" in prompt or "예시" in prompt, (
            "actions 프롬프트에 Few-shot 예시 section 누락 — 모델 swap 후 품질 보장 가드 부재"
        )


class TestPostProcessingGuards:
    """후처리 hallucinate guard 동작 (BL-024 carry)."""

    def test_past_year_due_date_is_dropped(self):
        actions = [{"title": "old", "dueDate": "2024-07-25"}]
        validated = _validate_action_dates(actions, current_year=2026)
        assert validated[0]["dueDate"] is None, (
            "과거 연도 (2024) due_date 가 drop 되지 않음 — BL-024 가드 회귀"
        )

    def test_current_year_kept(self):
        actions = [{"title": "valid", "dueDate": "2026-07-25"}]
        validated = _validate_action_dates(actions, current_year=2026)
        assert validated[0]["dueDate"] == "2026-07-25"

    def test_far_future_kept(self):
        actions = [{"title": "future", "dueDate": "2031-07-25"}]
        validated = _validate_action_dates(actions, current_year=2026)
        assert validated[0]["dueDate"] == "2031-07-25"

    def test_invalid_format_dropped(self):
        actions = [{"title": "bad", "dueDate": "not-a-date"}]
        validated = _validate_action_dates(actions, current_year=2026)
        assert validated[0]["dueDate"] is None


class TestPydanticSchemaContract:
    """ai_processing.py 출력 → Pydantic 스키마 정합 (BL-004 carry)."""

    def test_summary_result_validates_typical_response(self):
        payload = {
            "summary": "OKR 회의 요약",
            "key_decisions": ["완료일 7월 29일 조정"],
            "risks_and_issues": ["Stripe 연동 지연"],
            "participants": ["김PM"],
            "topics": ["OKR", "Stripe"],
            "next_meeting_agenda": ["다음주 OKR 회고"],
        }
        result = MeetingSummaryResult.model_validate(payload)
        assert result.summary == "OKR 회의 요약"
        assert len(result.key_decisions) == 1

    def test_actions_result_validates_typical_response(self):
        # 주의: MeetingActionsResult 는 BL-004 의도적 loose 계약 — actionItems/
        # suggestedProject 는 dict (LLM 출력 변형 tolerance). 본 테스트는 list/dict
        # 구조만 verify, 필드 타입은 다운스트림 ActionRepository 가 검증.
        payload = {
            "actionItems": [
                {
                    "title": "박개발: 인증 모듈 완료",
                    "description": "박개발이 7월 25일까지 완료",
                    "priority": "high",
                    "dueDate": "2026-07-25",
                }
            ],
            "suggestedProject": {
                "existingProjectId": None,
                "newProjectTitle": "인증",
                "confidence": 0.5,
            },
            "suggestedTags": ["인증"],
        }
        result = MeetingActionsResult.model_validate(payload)
        assert len(result.actionItems) == 1
        assert result.actionItems[0]["title"].startswith("박개발")
        assert result.suggestedProject["newProjectTitle"] == "인증"
        assert "인증" in result.suggestedTags

    def test_actions_result_accepts_empty_optional_fields(self):
        # suggestedTags 비어있어도 (no actions detected) 검증 통과
        payload = {
            "actionItems": [],
            "suggestedProject": {},
            "suggestedTags": [],
        }
        result = MeetingActionsResult.model_validate(payload)
        assert result.actionItems == []
        assert result.suggestedProject == {}
