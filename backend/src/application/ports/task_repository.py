from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.task import Task
from src.domain.enums.task_status import TaskStatus


class TaskRepository(ABC):
    @abstractmethod
    async def create(self, task: Task) -> Task: ...

    @abstractmethod
    async def get_by_id(self, task_id: UUID, user_id: UUID) -> Task | None: ...

    @abstractmethod
    async def get_by_user_id(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> list[Task]: ...

    @abstractmethod
    async def update_status(
        self,
        task_id: UUID,
        status: TaskStatus,
        error_message: str | None = None,
    ) -> Task | None: ...

    @abstractmethod
    async def set_celery_task_id(
        self, task_id: UUID, celery_task_id: str
    ) -> None: ...

    @abstractmethod
    async def update_results(
        self,
        task_id: UUID,
        transcript: str,
        language: str,
        topics: list[str],
    ) -> Task | None: ...
