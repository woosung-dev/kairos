# backend/src/rag/schemas.py
"""RAG 요청/응답 스키마."""
from pydantic import BaseModel, Field


class RagAskRequest(BaseModel):
    question: str = Field(min_length=1)
    project_id: str | None = Field(default=None, alias="projectId")
    time_range: str | None = Field(default=None, alias="timeRange")  # 1m, 3m, 6m
    source_type: str | None = Field(default=None, alias="sourceType")  # meeting, note

    model_config = {"populate_by_name": True}
