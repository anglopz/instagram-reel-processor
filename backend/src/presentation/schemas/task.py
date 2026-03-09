from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.enums.task_status import TaskStatus


class CreateTaskRequest(BaseModel):
    reel_url: str = Field(..., pattern=r"^https?://")


class TaskResponse(BaseModel):
    id: UUID
    reel_url: str
    status: TaskStatus
    language: str | None = None
    topics: list[str] | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]


class TranscriptResponse(BaseModel):
    transcript: str
    language: str | None = None
    topics: list[str] | None = None
