# apps/api/tests/rag/test_schemas.py
"""RagAskRequest Pydantic 검증 단위 테스트 (T-1 BUG-C01)."""
import pytest
from pydantic import ValidationError

from src.rag.schemas import RagAskRequest


class TestRagAskRequestValidation:
    """질문 입력 검증 — strip / max_length / min_length 경계."""

    def test_accepts_normal_question(self):
        req = RagAskRequest(question="이번 분기 회의에서 결정된 사항은?")
        assert req.question == "이번 분기 회의에서 결정된 사항은?"

    def test_strips_leading_and_trailing_whitespace(self):
        """공백 strip 후 저장된다."""
        req = RagAskRequest(question="  안녕하세요?  \n")
        assert req.question == "안녕하세요?"

    def test_rejects_whitespace_only_input(self):
        """공백만 있는 입력은 422 검증 (strip 후 빈 문자열)."""
        with pytest.raises(ValidationError) as exc_info:
            RagAskRequest(question="   \n\t  ")
        assert "2자 이상" in str(exc_info.value)

    def test_rejects_single_char_after_strip(self):
        """strip 후 1자 → 거부."""
        with pytest.raises(ValidationError) as exc_info:
            RagAskRequest(question="  a  ")
        assert "2자 이상" in str(exc_info.value)

    def test_accepts_exactly_two_chars_after_strip(self):
        """strip 후 정확히 2자 → 통과."""
        req = RagAskRequest(question=" ab ")
        assert req.question == "ab"

    def test_rejects_empty_string(self):
        """빈 문자열 → min_length=1 위반으로 422."""
        with pytest.raises(ValidationError):
            RagAskRequest(question="")

    def test_accepts_exactly_500_chars(self):
        """경계 — 정확히 500자 입력은 통과."""
        question = "한" * 500
        req = RagAskRequest(question=question)
        assert len(req.question) == 500

    def test_rejects_501_chars(self):
        """경계 — 501자 입력은 max_length 위반으로 422."""
        with pytest.raises(ValidationError) as exc_info:
            RagAskRequest(question="한" * 501)
        # Pydantic 표준 메시지에 길이 관련 단어가 포함됨
        assert "500" in str(exc_info.value) or "length" in str(exc_info.value).lower()

    def test_camelcase_alias_populate(self):
        """camelCase 별칭 (projectId/timeRange/sourceType) 도 받는다 (헌법 I-16)."""
        req = RagAskRequest(
            question="테스트?",
            projectId="abc",
            timeRange="1m",
            sourceType="meeting",
        )
        assert req.project_id == "abc"
        assert req.time_range == "1m"
        assert req.source_type == "meeting"
