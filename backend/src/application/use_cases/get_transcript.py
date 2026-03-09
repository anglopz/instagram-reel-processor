from __future__ import annotations

from uuid import UUID

from src.application.ports.task_repository import TaskRepository
from src.domain.enums.task_status import TaskStatus
from src.domain.exceptions import DomainException, TaskNotFound


class GetTranscript:
    def __init__(self, task_repository: TaskRepository) -> None:
        self._task_repository = task_repository

    async def execute(self, task_id: UUID, user_id: UUID) -> str:
        task = await self._task_repository.get_by_id(task_id, user_id)
        if task is None:
            raise TaskNotFound(str(task_id))

        if task.status != TaskStatus.COMPLETED:
            raise DomainException(
                f"Transcript not available. Task status: {task.status.value}",
                status_code=409,
                error_code="TRANSCRIPT_NOT_READY",
            )

        return task.transcript or ""
