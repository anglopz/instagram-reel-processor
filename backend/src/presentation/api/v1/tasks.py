from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from src.application.ports.task_repository import TaskRepository
from src.application.use_cases.cancel_task import CancelTask
from src.application.use_cases.create_task import CreateTask
from src.application.use_cases.get_task_status import GetTaskStatus
from src.application.use_cases.get_transcript import GetTranscript
from src.application.use_cases.list_user_tasks import ListUserTasks
from src.domain.entities.task import Task
from src.infrastructure.adapters.postgres_task_repository import (
    PostgresTaskRepository,
)
from src.infrastructure.database.session import create_session_factory
from src.presentation.api.dependencies import get_current_user
from src.presentation.schemas.task import (
    CreateTaskRequest,
    TaskListResponse,
    TaskResponse,
    TranscriptResponse,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_task_repository() -> TaskRepository:
    return PostgresTaskRepository(create_session_factory())


def _task_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        reel_url=task.reel_url,
        status=task.status,
        language=task.language,
        topics=task.topics or None,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    user_id: UUID = Depends(get_current_user),
    repo: TaskRepository = Depends(get_task_repository),
    limit: int = 20,
    offset: int = 0,
) -> TaskListResponse:
    use_case = ListUserTasks(repo)
    tasks = await use_case.execute(user_id, limit, offset)
    return TaskListResponse(tasks=[_task_response(t) for t in tasks])


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    body: CreateTaskRequest,
    user_id: UUID = Depends(get_current_user),
    repo: TaskRepository = Depends(get_task_repository),
) -> TaskResponse:
    use_case = CreateTask(repo)
    task = await use_case.execute(str(body.reel_url), user_id)

    # Dispatch processing pipeline and store chain ID for cancellation
    from src.application.services.pipeline_orchestrator import PipelineOrchestrator

    orchestrator = PipelineOrchestrator()
    chain_id = await orchestrator.orchestrate(task.id, task.reel_url)
    await repo.set_celery_task_id(task.id, chain_id)

    return _task_response(task)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    user_id: UUID = Depends(get_current_user),
    repo: TaskRepository = Depends(get_task_repository),
) -> TaskResponse:
    use_case = GetTaskStatus(repo)
    task = await use_case.execute(task_id, user_id)
    return _task_response(task)


@router.get("/{task_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(
    task_id: UUID,
    user_id: UUID = Depends(get_current_user),
    repo: TaskRepository = Depends(get_task_repository),
) -> TranscriptResponse:
    get_tx = GetTranscript(repo)
    transcript = await get_tx.execute(task_id, user_id)
    get_status = GetTaskStatus(repo)
    task = await get_status.execute(task_id, user_id)
    return TranscriptResponse(
        transcript=transcript,
        language=task.language,
        topics=task.topics or None,
    )


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: UUID,
    user_id: UUID = Depends(get_current_user),
    repo: TaskRepository = Depends(get_task_repository),
) -> TaskResponse:
    use_case = CancelTask(repo)
    task = await use_case.execute(task_id, user_id)
    return _task_response(task)
