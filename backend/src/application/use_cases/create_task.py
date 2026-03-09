from __future__ import annotations

from uuid import UUID, uuid4

from src.application.ports.task_repository import TaskRepository
from src.domain.entities.task import Task
from src.domain.enums.task_status import TaskStatus


class CreateTask:
    def __init__(self, task_repository: TaskRepository) -> None:
        self._task_repository = task_repository

    async def execute(self, reel_url: str, user_id: UUID) -> Task:
        task = Task(
            id=uuid4(),
            reel_url=reel_url,
            status=TaskStatus.PENDING,
            user_id=user_id,
        )
        return await self._task_repository.create(task)
