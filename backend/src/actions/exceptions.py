# backend/src/actions/exceptions.py
"""ActionItem 도메인 예외."""
from src.common.exceptions import NotFoundError


class ActionItemNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("액션 아이템")
