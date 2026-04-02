# backend/src/rag/exceptions.py
"""RAG 관련 예외."""


class RagError(Exception):
    def __init__(self, message: str = "RAG 검색 중 오류가 발생했습니다") -> None:
        self.message = message
        super().__init__(self.message)
