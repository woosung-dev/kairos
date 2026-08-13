# 페이지네이션 유틸 — offset 계산 + wire format(camelCase) 응답 조립의 SSOT
"""PR-2 c2 재정의: 이전 PaginatedResponse/PaginationParams(snake_case Pydantic)는
프로덕션 import 0 인 죽은 추상이었고, 실제 5개 도메인 service 는 camelCase dict
("pageSize"/"hasNext") 를 손조립으로 복붙했다. 실사용 wire 계약으로 교체 —
조립 사이트: inbox/projects/notes/actions/meetings service.
"""


def to_offset(page: int, page_size: int) -> int:
    return (page - 1) * page_size


def build_page(items: list, total: int, page: int, page_size: int) -> dict:
    """오프셋 페이지 응답 조립 (I-16 camelCase wire format)."""
    return {
        "items": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "hasNext": page * page_size < total,
    }


def empty_page(page: int, page_size: int) -> dict:
    """빈 결과 페이지 (meetings 비접근 projectId 필터 등 fail-closed 경로용)."""
    return build_page([], 0, page, page_size)
