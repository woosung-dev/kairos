# backend/src/common/pagination.py
"""페이지네이션 유틸."""
from typing import Generic, TypeVar

from pydantic import BaseModel, computed_field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """오프셋 기반 페이지네이션 응답."""

    items: list[T]
    total: int
    page: int
    page_size: int

    @computed_field
    @property
    def has_next(self) -> bool:
        return self.page * self.page_size < self.total


class PaginationParams(BaseModel):
    """페이지네이션 쿼리 파라미터."""

    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
