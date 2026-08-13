# common/pagination.py 단위 테스트 — wire format(camelCase) 조립 계약
"""PR-2 c2: 죽은 PaginatedResponse/PaginationParams 를 실사용 계약
(to_offset/build_page/empty_page) 으로 교체 — 5개 도메인 service 조립 사이트의
"hasNext": page*page_size < total 복붙을 흡수한다."""
from src.common.pagination import build_page, empty_page, to_offset


class TestToOffset:
    def test_first_page_zero(self):
        assert to_offset(1, 20) == 0

    def test_second_page(self):
        assert to_offset(2, 10) == 10


class TestBuildPage:
    def test_wire_format_keys_camel_case(self):
        page = build_page(["x"], total=1, page=1, page_size=20)
        assert set(page) == {"items", "total", "page", "pageSize", "hasNext"}

    def test_has_next_boundary(self):
        # 정확히 마지막 페이지: 2*10 = 20 == total → hasNext False
        assert build_page([], total=20, page=2, page_size=10)["hasNext"] is False
        assert build_page([], total=21, page=2, page_size=10)["hasNext"] is True

    def test_items_passthrough(self):
        items = [{"id": 1}, {"id": 2}]
        assert build_page(items, total=2, page=1, page_size=20)["items"] is items


class TestEmptyPage:
    def test_empty_page_shape(self):
        page = empty_page(3, 10)
        assert page == {
            "items": [],
            "total": 0,
            "page": 3,
            "pageSize": 10,
            "hasNext": False,
        }
