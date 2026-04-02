# backend/src/notes/exceptions.py
from src.common.exceptions import NotFoundError


class NoteNotFoundError(NotFoundError):
    def __init__(self) -> None:
        super().__init__("노트")
