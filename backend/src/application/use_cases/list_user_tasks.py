from __future__ import annotations

from uuid import UUID

from src.application.ports.task_repository import TaskRepository
from src.domain.entities.task import Task


class ListUserTasks:
    def __init__(self, task_repository: TaskRepository) -> None:
        self._task_repository = task_repository

    async def execute(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> list[Task]:
        return await self._task_repository.get_by_user_id(user_id, limit, offset)
