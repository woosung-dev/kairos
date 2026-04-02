# backend/src/inbox/exceptions.py
"""Inbox 도메인 예외."""
from src.common.exceptions import NotFoundError


class InboxItemNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("Inbox 아이템")
