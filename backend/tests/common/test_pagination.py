# backend/tests/common/test_pagination.py
"""PaginatedResponse + PaginationParams 단위 테스트.

common/pagination.py 의 has_next computed field + offset 계산 fence-post 회귀 가드.
"""
from pydantic import BaseModel

from src.common.pagination import PaginatedResponse, PaginationParams


class Item(BaseModel):
    """테스트용 아이템."""
    id: int
    name: str


class TestPaginatedResponse:
    def test_has_next_true_when_more_pages(self):
        resp = PaginatedResponse[Item](
            items=[Item(id=1, name="a")], total=100, page=1, page_size=10
        )
        # 1 * 10 = 10 < 100 → True
        assert resp.has_next is True

    def test_has_next_false_at_last_page(self):
        """마지막 페이지 fence — page * page_size == total → False."""
        resp = PaginatedResponse[Item](items=[], total=20, page=2, page_size=10)
        # 2 * 10 = 20 < 20 → False
        assert resp.has_next is False

    def test_has_next_false_when_empty(self):
        resp = PaginatedResponse[Item](items=[], total=0, page=1, page_size=20)
        assert resp.has_next is False

    def test_has_next_false_beyond_last(self):
        """존재하지 않는 page (off-by-one 가드)."""
        resp = PaginatedResponse[Item](items=[], total=5, page=3, page_size=10)
        # 3 * 10 = 30 < 5 → False
        assert resp.has_next is False

    def test_serialize_includes_has_next(self):
        """computed_field 가 model_dump 에 포함."""
        resp = PaginatedResponse[Item](
            items=[Item(id=1, name="a")], total=100, page=1, page_size=10
        )
        data = resp.model_dump()
        assert "has_next" in data
        assert data["has_next"] is True


class TestPaginationParams:
    def test_defaults(self):
        p = PaginationParams()
        assert p.page == 1
        assert p.page_size == 20
        assert p.offset == 0

    def test_offset_page_2(self):
        p = PaginationParams(page=2, page_size=20)
        assert p.offset == 20

    def test_offset_custom_page_size(self):
        p = PaginationParams(page=3, page_size=50)
        assert p.offset == 100

    def test_offset_page_1_always_zero(self):
        """page=1 이면 page_size 무관 offset=0."""
        for ps in (1, 10, 100, 1000):
            assert PaginationParams(page=1, page_size=ps).offset == 0
