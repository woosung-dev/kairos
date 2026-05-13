# backend/src/rag/schemas.py
"""RAG 요청/응답 스키마."""
from pydantic import BaseModel, Field, field_validator


class RagAskRequest(BaseModel):
    # max_length=500: prompt-injection 류 거대 입력 차단. min_length=1은 422 우회를 막고
    # 실제 ≥2자 검증은 field_validator(strip 후)에서 수행한다.
    question: str = Field(min_length=1, max_length=500)
    project_id: str | None = Field(default=None, alias="projectId")
    time_range: str | None = Field(default=None, alias="timeRange")  # 1m, 3m, 6m
    source_type: str | None = Field(default=None, alias="sourceType")  # meeting, note

    @field_validator("question")
    @classmethod
    def strip_and_require_min_length(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 2:
            raise ValueError("질문은 공백 제외 2자 이상이어야 합니다.")
        return stripped

    model_config = {"populate_by_name": True}
