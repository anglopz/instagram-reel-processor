from __future__ import annotations

import asyncio
import logging
import os
from typing import Any
from uuid import UUID

from src.domain.enums.task_status import TaskStatus
from src.infrastructure.celery.app import celery_app

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Port registry — populated by the DI container at app startup
# ---------------------------------------------------------------------------

_port_registry: dict[str, Any] = {}


def register_ports(**ports: Any) -> None:
    _port_registry.update(ports)


def reset_ports() -> None:
    _port_registry.clear()


def _get_port(name: str) -> Any:
    if name not in _port_registry:
        raise RuntimeError(
            f"Port '{name}' not registered. "
            "Call register_ports() during app initialization."
        )
    return _port_registry[name]


def _run_async(coro: Any) -> Any:
    """Run an async coroutine from synchronous Celery task context."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Helper — cancellation check
# ---------------------------------------------------------------------------


def _check_cancelled(task_id: str, step: str) -> bool:
    """Update status to PROCESSING; return True if the task was cancelled."""
    repo = _get_port("task_repository")
    result = _run_async(repo.update_status(UUID(task_id), TaskStatus.PROCESSING))
    if result is None:
        logger.info("Task %s cancelled before %s — aborting", task_id, step)
        return True
    return False


def _cancelled_result(task_id: str) -> dict[str, Any]:
    return {"task_id": task_id, "cancelled": True}


# ---------------------------------------------------------------------------
# Pipeline step 1: Download video
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    name="pipeline.download_video",
    max_retries=3,
    default_retry_delay=5,
)
def download_video(self: Any, task_id: str, reel_url: str) -> dict[str, Any]:
    if _check_cancelled(task_id, "download"):
        return _cancelled_result(task_id)

    tmp_dir = f"/tmp/tasks/{task_id}"
    os.makedirs(tmp_dir, exist_ok=True)

    try:
        downloader = _get_port("video_downloader")
        video_path = _run_async(
            downloader.download(reel_url, f"{tmp_dir}/video.mp4")
        )
        logger.info("Task %s: video downloaded to %s", task_id, video_path)
        return {"task_id": task_id, "video_path": video_path}
    except Exception as exc:
        if self.request.retries < self.max_retries:
            logger.warning(
                "Task %s: download retry %d/%d — %s",
                task_id,
                self.request.retries + 1,
                self.max_retries,
                exc,
            )
            raise self.retry(exc=exc)
        from src.infrastructure.celery.callbacks import handle_failure

        handle_failure(task_id, "download", exc)
        raise


# ---------------------------------------------------------------------------
# Pipeline step 2: Extract audio
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    name="pipeline.extract_audio",
    max_retries=0,
)
def extract_audio(self: Any, prev_result: dict[str, Any]) -> dict[str, Any]:
    task_id = prev_result["task_id"]
    if prev_result.get("cancelled"):
        return _cancelled_result(task_id)

    if _check_cancelled(task_id, "extract_audio"):
        return _cancelled_result(task_id)

    try:
        extractor = _get_port("audio_extractor")
        video_path = prev_result["video_path"]
        audio_path = f"/tmp/tasks/{task_id}/audio.wav"
        _run_async(extractor.extract(video_path, audio_path))
        logger.info("Task %s: audio extracted to %s", task_id, audio_path)
        return {"task_id": task_id, "audio_path": audio_path}
    except Exception as exc:
        from src.infrastructure.celery.callbacks import handle_failure

        handle_failure(task_id, "extract_audio", exc)
        raise


# ---------------------------------------------------------------------------
# Pipeline step 3: Transcribe audio
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    name="pipeline.transcribe_audio",
    max_retries=2,
    default_retry_delay=10,
)
def transcribe_audio(self: Any, prev_result: dict[str, Any]) -> dict[str, Any]:
    task_id = prev_result["task_id"]
    if prev_result.get("cancelled"):
        return _cancelled_result(task_id)

    if _check_cancelled(task_id, "transcribe"):
        return _cancelled_result(task_id)

    try:
        transcriber = _get_port("transcriber")
        audio_path = prev_result["audio_path"]
        result = _run_async(transcriber.transcribe(audio_path))
        logger.info(
            "Task %s: transcription done — language=%s", task_id, result.language
        )
        return {
            "task_id": task_id,
            "transcript": result.text,
            "language": result.language,
        }
    except Exception as exc:
        if self.request.retries < self.max_retries:
            logger.warning(
                "Task %s: transcribe retry %d/%d — %s",
                task_id,
                self.request.retries + 1,
                self.max_retries,
                exc,
            )
            raise self.retry(exc=exc)
        from src.infrastructure.celery.callbacks import handle_failure

        handle_failure(task_id, "transcribe", exc)
        raise


# ---------------------------------------------------------------------------
# Pipeline step 4: Analyze text (topic extraction)
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    name="pipeline.analyze_text",
    max_retries=0,
)
def analyze_text(self: Any, prev_result: dict[str, Any]) -> dict[str, Any]:
    task_id = prev_result["task_id"]
    if prev_result.get("cancelled"):
        return _cancelled_result(task_id)

    if _check_cancelled(task_id, "analyze"):
        return _cancelled_result(task_id)

    try:
        analyzer = _get_port("text_analyzer")
        transcript = prev_result["transcript"]
        topics = _run_async(analyzer.extract_topics(transcript))
        logger.info("Task %s: analysis done — %d topics", task_id, len(topics))
        return {
            "task_id": task_id,
            "transcript": prev_result["transcript"],
            "language": prev_result["language"],
            "topics": topics,
        }
    except Exception as exc:
        from src.infrastructure.celery.callbacks import handle_failure

        handle_failure(task_id, "analyze", exc)
        raise


# ---------------------------------------------------------------------------
# Pipeline step 5: Persist results
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    name="pipeline.persist_results",
    max_retries=0,
)
def persist_results(self: Any, prev_result: dict[str, Any]) -> dict[str, Any]:
    task_id = prev_result["task_id"]
    if prev_result.get("cancelled"):
        return _cancelled_result(task_id)

    try:
        repo = _get_port("task_repository")
        _run_async(
            repo.update_results(
                UUID(task_id),
                prev_result["transcript"],
                prev_result["language"],
                prev_result["topics"],
            )
        )
        _run_async(repo.update_status(UUID(task_id), TaskStatus.COMPLETED))
        logger.info("Task %s: results persisted, status COMPLETED", task_id)
        return {"task_id": task_id, "status": "completed"}
    except Exception as exc:
        from src.infrastructure.celery.callbacks import handle_failure

        handle_failure(task_id, "persist_results", exc)
        raise
    finally:
        from src.infrastructure.celery.callbacks import cleanup_temp_files

        cleanup_temp_files(task_id)
