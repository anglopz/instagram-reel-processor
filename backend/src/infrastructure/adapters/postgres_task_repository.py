from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.ports.task_repository import TaskRepository
from src.domain.entities.task import Task
from src.domain.enums.task_status import TaskStatus
from src.infrastructure.database.models import TaskModel


class PostgresTaskRepository(TaskRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    def _to_entity(self, model: TaskModel) -> Task:
        return Task(
            id=model.id,
            reel_url=model.reel_url,
            status=TaskStatus(model.status),
            user_id=model.user_id,
            celery_task_id=model.celery_task_id,
            transcript=model.transcript,
            language=model.language,
            topics=model.topics or [],
            error_message=model.error_message,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def create(self, task: Task) -> Task:
        async with self._session_factory() as session:
            model = TaskModel(
                id=task.id,
                user_id=task.user_id,
                reel_url=task.reel_url,
                status=task.status.value,
                celery_task_id=task.celery_task_id,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._to_entity(model)

    async def get_by_id(self, task_id: UUID, user_id: UUID) -> Task | None:
        async with self._session_factory() as session:
            stmt = select(TaskModel).where(
                TaskModel.id == task_id,
                TaskModel.user_id == user_id,
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            return self._to_entity(model) if model else None

    async def get_by_user_id(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> list[Task]:
        async with self._session_factory() as session:
            stmt = (
                select(TaskModel)
                .where(TaskModel.user_id == user_id)
                .order_by(TaskModel.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            return [self._to_entity(m) for m in result.scalars().all()]

    async def update_status(
        self,
        task_id: UUID,
        status: TaskStatus,
        error_message: str | None = None,
    ) -> Task | None:
        async with self._session_factory() as session:
            stmt = select(TaskModel).where(TaskModel.id == task_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            model.status = status.value
            if error_message is not None:
                model.error_message = error_message
            model.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(model)
            return self._to_entity(model)

    async def update_results(
        self,
        task_id: UUID,
        transcript: str,
        language: str,
        topics: list[str],
    ) -> Task | None:
        async with self._session_factory() as session:
            stmt = select(TaskModel).where(TaskModel.id == task_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            model.transcript = transcript
            model.language = language
            model.topics = topics
            model.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(model)
            return self._to_entity(model)
