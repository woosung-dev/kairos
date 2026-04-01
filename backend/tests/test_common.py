# backend/tests/test_common.py
"""공통 유틸 테스트."""
import pytest

from src.common.exceptions import AlreadyExistsError, NotFoundError
from src.common.pagination import PaginatedResponse
from src.common.prompts import (
    MEETING_SUMMARY_SYSTEM_PROMPT,
    parse_json_response,
)


class TestExceptions:
    def test_not_found_error(self):
        err = NotFoundError("워크스페이스")
        assert err.status_code == 404
        assert "워크스페이스" in err.detail

    def test_already_exists_error(self):
        err = AlreadyExistsError("멤버")
        assert err.status_code == 409
        assert "멤버" in err.detail


class TestPagination:
    def test_paginated_response_has_next(self):
        resp = PaginatedResponse(
            items=["a", "b"],
            total=50,
            page=1,
            page_size=20,
        )
        assert resp.has_next is True

    def test_paginated_response_no_next(self):
        resp = PaginatedResponse(
            items=["a"],
            total=1,
            page=1,
            page_size=20,
        )
        assert resp.has_next is False

    def test_paginated_response_last_page(self):
        resp = PaginatedResponse(
            items=["c"],
            total=41,
            page=3,
            page_size=20,
        )
        assert resp.has_next is False


class TestPrompts:
    def test_meeting_summary_prompt_exists(self):
        assert "JSON" in MEETING_SUMMARY_SYSTEM_PROMPT
        assert len(MEETING_SUMMARY_SYSTEM_PROMPT) > 50

    def test_parse_json_response_clean(self):
        raw = '{"summary": "테스트 요약", "key_decisions": []}'
        result = parse_json_response(raw)
        assert result["summary"] == "테스트 요약"

    def test_parse_json_response_with_code_fence(self):
        raw = '```json\n{"summary": "테스트"}\n```'
        result = parse_json_response(raw)
        assert result["summary"] == "테스트"

    def test_parse_json_response_invalid(self):
        with pytest.raises(ValueError, match="JSON 파싱 실패"):
            parse_json_response("이건 JSON이 아닙니다")
