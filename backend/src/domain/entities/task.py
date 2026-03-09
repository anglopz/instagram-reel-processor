from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.domain.enums.task_status import TaskStatus


@dataclass
class Task:
    id: UUID
    reel_url: str
    status: TaskStatus
    user_id: UUID
    celery_task_id: str | None = None
    transcript: str | None = None
    language: str | None = None
    topics: list[str] = field(default_factory=list)
    error_message: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
