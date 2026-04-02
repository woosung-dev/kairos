# backend/src/projects/exceptions.py
"""Project 도메인 예외."""
from src.common.exceptions import NotFoundError


class ProjectNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("프로젝트")
