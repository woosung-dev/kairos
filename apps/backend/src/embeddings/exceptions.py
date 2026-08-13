# backend/src/embeddings/exceptions.py
"""임베딩 관련 예외."""


class EmbeddingError(Exception):
    """임베딩 생성 실패."""

    def __init__(self, message: str = "임베딩 생성에 실패했습니다") -> None:
        self.message = message
        super().__init__(self.message)
