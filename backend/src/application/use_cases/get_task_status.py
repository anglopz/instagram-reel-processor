from __future__ import annotations

from uuid import UUID

from src.application.ports.task_repository import TaskRepository
from src.domain.entities.task import Task
from src.domain.exceptions import TaskNotFound


class GetTaskStatus:
    def __init__(self, task_repository: TaskRepository) -> None:
        self._task_repository = task_repository

    async def execute(self, task_id: UUID, user_id: UUID) -> Task:
        task = await self._task_repository.get_by_id(task_id, user_id)
        if task is None:
            raise TaskNotFound(str(task_id))
        return task
