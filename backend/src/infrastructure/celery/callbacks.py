from __future__ import annotations

import asyncio
import logging
import shutil
from uuid import UUID

from src.domain.enums.task_status import TaskStatus

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from synchronous context."""
    return asyncio.run(coro)


def handle_failure(task_id: str, step: str, exc: Exception) -> None:
    """Update the task to FAILED and clean up temp files."""
    from src.infrastructure.celery.tasks import _get_port

    error_message = f"Pipeline failed at {step}: {exc}"
    logger.error("Task %s: %s", task_id, error_message)

    try:
        repo = _get_port("task_repository")
        _run_async(
            repo.update_status(
                UUID(task_id),
                TaskStatus.FAILED,
                error_message=error_message,
            )
        )
    except Exception:
        logger.exception("Task %s: failed to update status to FAILED", task_id)

    cleanup_temp_files(task_id)


def cleanup_temp_files(task_id: str) -> None:
    """Remove the temp directory for a task."""
    tmp_dir = f"/tmp/tasks/{task_id}"
    if shutil.os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir, ignore_errors=True)
        logger.info("Task %s: cleaned up temp files at %s", task_id, tmp_dir)
