from __future__ import annotations

from uuid import UUID

from src.application.ports.task_repository import TaskRepository
from src.domain.entities.task import Task
from src.domain.enums.task_status import TaskStatus
from src.domain.exceptions import TaskAlreadyTerminal, TaskNotFound


class CancelTask:
    def __init__(self, task_repository: TaskRepository) -> None:
        self._task_repository = task_repository

    async def execute(self, task_id: UUID, user_id: UUID) -> Task:
        task = await self._task_repository.get_by_id(task_id, user_id)
        if task is None:
            raise TaskNotFound(str(task_id))

        if task.status not in (TaskStatus.PENDING, TaskStatus.PROCESSING):
            raise TaskAlreadyTerminal(task.status.value)

        updated = await self._task_repository.update_status(
            task_id, TaskStatus.CANCELLED
        )
        if updated is None:
            raise TaskNotFound(str(task_id))
        return updated
