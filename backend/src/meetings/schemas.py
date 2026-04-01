# backend/src/meetings/schemas.py
"""Meeting 스키마."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CreateMeetingRequest(BaseModel):
    title: str
    file_key: str = Field(alias="fileKey")
    recorded_at: datetime | None = Field(default=None, alias="recordedAt")

    model_config = {"populate_by_name": True}


class MeetingCreatedResponse(BaseModel):
    id: str
    status: str
    message: str


class MeetingStatusResponse(BaseModel):
    status: str
    error_message: str | None = None
