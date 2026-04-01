# backend/src/meetings/exceptions.py
"""Meeting 도메인 예외."""
from src.common.exceptions import NotFoundError


class MeetingNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("회의")
