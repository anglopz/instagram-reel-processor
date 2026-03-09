from __future__ import annotations

import logging
from uuid import UUID

from celery import chain

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Orchestrates the full processing pipeline as a Celery task chain.

    The orchestrator dispatches a chain of five sequential Celery tasks:
    download_video → extract_audio → transcribe_audio → analyze_text → persist_results

    Each step checks for cancellation before executing. The chain ID is returned
    so the caller can store it on the Task entity for cancellation via revoke().
    """

    async def orchestrate(self, task_id: UUID, reel_url: str) -> str:
        """Dispatch the pipeline chain.

        Returns the Celery chain AsyncResult ID for cancellation support.
        """
        from src.infrastructure.celery.tasks import (
            analyze_text,
            download_video,
            extract_audio,
            persist_results,
            transcribe_audio,
        )

        pipeline = chain(
            download_video.s(str(task_id), reel_url),
            extract_audio.s(),
            transcribe_audio.s(),
            analyze_text.s(),
            persist_results.s(),
        )

        result = pipeline.apply_async()
        logger.info(
            "Task %s: pipeline dispatched — chain_id=%s", task_id, result.id
        )
        return result.id
