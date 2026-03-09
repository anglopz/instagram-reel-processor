from __future__ import annotations

import os
import shutil
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.domain.entities.task import Task
from src.domain.enums.task_status import TaskStatus
from src.application.ports.transcriber import TranscriptionResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_TASK_ID = str(uuid4())
FAKE_USER_ID = uuid4()
FAKE_URL = "https://www.instagram.com/reel/abc123/"
TMP_DIR = f"/tmp/tasks/{FAKE_TASK_ID}"


def _make_task(status: TaskStatus = TaskStatus.PROCESSING) -> Task:
    return Task(
        id=UUID(FAKE_TASK_ID),
        reel_url=FAKE_URL,
        status=status,
        user_id=FAKE_USER_ID,
    )


@pytest.fixture(autouse=True)
def _celery_eager():
    from src.infrastructure.celery.app import celery_app

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager = False
    celery_app.conf.task_eager_propagates = False


@pytest.fixture()
def mock_ports():
    """Register mock port implementations and clean up after test."""
    from src.infrastructure.celery.tasks import register_ports, reset_ports

    repo = AsyncMock()
    downloader = AsyncMock()
    extractor = AsyncMock()
    transcriber = AsyncMock()
    analyzer = AsyncMock()

    ports = {
        "task_repository": repo,
        "video_downloader": downloader,
        "audio_extractor": extractor,
        "transcriber": transcriber,
        "text_analyzer": analyzer,
    }
    register_ports(**ports)
    yield ports
    reset_ports()


@pytest.fixture(autouse=True)
def _cleanup_tmp():
    """Remove temp directory after each test."""
    yield
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)


# ---------------------------------------------------------------------------
# Celery app configuration tests
# ---------------------------------------------------------------------------


class TestCeleryAppConfig:
    def test_celery_app_uses_redis_broker(self):
        from src.infrastructure.celery.app import celery_app

        assert "redis" in celery_app.conf.broker_url

    def test_celery_app_json_serializer(self):
        from src.infrastructure.celery.app import celery_app

        assert celery_app.conf.task_serializer == "json"


# ---------------------------------------------------------------------------
# Task retry policy tests
# ---------------------------------------------------------------------------


class TestRetryPolicies:
    def test_download_video_max_retries_is_3(self):
        from src.infrastructure.celery.tasks import download_video

        assert download_video.max_retries == 3

    def test_extract_audio_max_retries_is_0(self):
        from src.infrastructure.celery.tasks import extract_audio

        assert extract_audio.max_retries == 0

    def test_transcribe_audio_max_retries_is_2(self):
        from src.infrastructure.celery.tasks import transcribe_audio

        assert transcribe_audio.max_retries == 2

    def test_analyze_text_max_retries_is_0(self):
        from src.infrastructure.celery.tasks import analyze_text

        assert analyze_text.max_retries == 0

    def test_persist_results_max_retries_is_0(self):
        from src.infrastructure.celery.tasks import persist_results

        assert persist_results.max_retries == 0


# ---------------------------------------------------------------------------
# download_video task
# ---------------------------------------------------------------------------


class TestDownloadVideoTask:
    def test_happy_path(self, mock_ports):
        from src.infrastructure.celery.tasks import download_video

        mock_ports["task_repository"].update_status.return_value = _make_task()
        mock_ports["video_downloader"].download.return_value = f"{TMP_DIR}/video.mp4"

        result = download_video.apply(args=[FAKE_TASK_ID, FAKE_URL]).get()

        assert result["task_id"] == FAKE_TASK_ID
        assert result["video_path"] == f"{TMP_DIR}/video.mp4"
        mock_ports["task_repository"].update_status.assert_awaited_once_with(
            UUID(FAKE_TASK_ID), TaskStatus.PROCESSING
        )
        mock_ports["video_downloader"].download.assert_awaited_once()

    def test_aborts_when_cancelled(self, mock_ports):
        from src.infrastructure.celery.tasks import download_video

        mock_ports["task_repository"].update_status.return_value = None

        result = download_video.apply(args=[FAKE_TASK_ID, FAKE_URL]).get()

        assert result["cancelled"] is True
        mock_ports["video_downloader"].download.assert_not_awaited()

    def test_creates_tmp_directory(self, mock_ports):
        from src.infrastructure.celery.tasks import download_video

        mock_ports["task_repository"].update_status.return_value = _make_task()
        mock_ports["video_downloader"].download.return_value = f"{TMP_DIR}/video.mp4"

        download_video.apply(args=[FAKE_TASK_ID, FAKE_URL]).get()

        assert os.path.isdir(TMP_DIR)


# ---------------------------------------------------------------------------
# extract_audio task
# ---------------------------------------------------------------------------


class TestExtractAudioTask:
    def test_happy_path(self, mock_ports):
        from src.infrastructure.celery.tasks import extract_audio

        mock_ports["task_repository"].update_status.return_value = _make_task()
        mock_ports["audio_extractor"].extract.return_value = f"{TMP_DIR}/audio.wav"

        prev = {"task_id": FAKE_TASK_ID, "video_path": f"{TMP_DIR}/video.mp4"}
        result = extract_audio.apply(args=[prev]).get()

        assert result["task_id"] == FAKE_TASK_ID
        assert result["audio_path"] == f"{TMP_DIR}/audio.wav"
        mock_ports["audio_extractor"].extract.assert_awaited_once()

    def test_propagates_cancellation(self, mock_ports):
        from src.infrastructure.celery.tasks import extract_audio

        prev = {"task_id": FAKE_TASK_ID, "cancelled": True}
        result = extract_audio.apply(args=[prev]).get()

        assert result["cancelled"] is True
        mock_ports["audio_extractor"].extract.assert_not_awaited()

    def test_aborts_when_status_update_returns_none(self, mock_ports):
        from src.infrastructure.celery.tasks import extract_audio

        mock_ports["task_repository"].update_status.return_value = None

        prev = {"task_id": FAKE_TASK_ID, "video_path": f"{TMP_DIR}/video.mp4"}
        result = extract_audio.apply(args=[prev]).get()

        assert result["cancelled"] is True


# ---------------------------------------------------------------------------
# transcribe_audio task
# ---------------------------------------------------------------------------


class TestTranscribeAudioTask:
    def test_happy_path(self, mock_ports):
        from src.infrastructure.celery.tasks import transcribe_audio

        mock_ports["task_repository"].update_status.return_value = _make_task()
        mock_ports["transcriber"].transcribe.return_value = TranscriptionResult(
            text="Hello world", language="en"
        )

        prev = {"task_id": FAKE_TASK_ID, "audio_path": f"{TMP_DIR}/audio.wav"}
        result = transcribe_audio.apply(args=[prev]).get()

        assert result["task_id"] == FAKE_TASK_ID
        assert result["transcript"] == "Hello world"
        assert result["language"] == "en"

    def test_propagates_cancellation(self, mock_ports):
        from src.infrastructure.celery.tasks import transcribe_audio

        prev = {"task_id": FAKE_TASK_ID, "cancelled": True}
        result = transcribe_audio.apply(args=[prev]).get()

        assert result["cancelled"] is True
        mock_ports["transcriber"].transcribe.assert_not_awaited()


# ---------------------------------------------------------------------------
# analyze_text task
# ---------------------------------------------------------------------------


class TestAnalyzeTextTask:
    def test_happy_path(self, mock_ports):
        from src.infrastructure.celery.tasks import analyze_text

        mock_ports["task_repository"].update_status.return_value = _make_task()
        mock_ports["text_analyzer"].extract_topics.return_value = [
            "python",
            "coding",
        ]

        prev = {
            "task_id": FAKE_TASK_ID,
            "transcript": "Hello world",
            "language": "en",
        }
        result = analyze_text.apply(args=[prev]).get()

        assert result["task_id"] == FAKE_TASK_ID
        assert result["topics"] == ["python", "coding"]
        assert result["transcript"] == "Hello world"
        assert result["language"] == "en"

    def test_propagates_cancellation(self, mock_ports):
        from src.infrastructure.celery.tasks import analyze_text

        prev = {"task_id": FAKE_TASK_ID, "cancelled": True}
        result = analyze_text.apply(args=[prev]).get()

        assert result["cancelled"] is True


# ---------------------------------------------------------------------------
# persist_results task
# ---------------------------------------------------------------------------


class TestPersistResultsTask:
    def test_updates_results_and_completes(self, mock_ports):
        from src.infrastructure.celery.tasks import persist_results

        mock_ports["task_repository"].update_results.return_value = _make_task(
            TaskStatus.COMPLETED
        )
        mock_ports["task_repository"].update_status.return_value = _make_task(
            TaskStatus.COMPLETED
        )

        prev = {
            "task_id": FAKE_TASK_ID,
            "transcript": "Hello world",
            "language": "en",
            "topics": ["python"],
        }
        result = persist_results.apply(args=[prev]).get()

        assert result["task_id"] == FAKE_TASK_ID
        assert result["status"] == "completed"
        mock_ports["task_repository"].update_results.assert_awaited_once_with(
            UUID(FAKE_TASK_ID), "Hello world", "en", ["python"]
        )
        mock_ports["task_repository"].update_status.assert_awaited_once_with(
            UUID(FAKE_TASK_ID), TaskStatus.COMPLETED
        )

    def test_cleans_up_temp_files(self, mock_ports):
        from src.infrastructure.celery.tasks import persist_results

        os.makedirs(TMP_DIR, exist_ok=True)
        with open(f"{TMP_DIR}/video.mp4", "w") as f:
            f.write("fake")

        mock_ports["task_repository"].update_results.return_value = _make_task(
            TaskStatus.COMPLETED
        )
        mock_ports["task_repository"].update_status.return_value = _make_task(
            TaskStatus.COMPLETED
        )

        prev = {
            "task_id": FAKE_TASK_ID,
            "transcript": "Hello",
            "language": "en",
            "topics": [],
        }
        persist_results.apply(args=[prev]).get()

        assert not os.path.exists(TMP_DIR)

    def test_propagates_cancellation(self, mock_ports):
        from src.infrastructure.celery.tasks import persist_results

        prev = {"task_id": FAKE_TASK_ID, "cancelled": True}
        result = persist_results.apply(args=[prev]).get()

        assert result["cancelled"] is True
        mock_ports["task_repository"].update_results.assert_not_awaited()


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------


class TestCallbacks:
    def test_handle_failure_updates_task_to_failed(self, mock_ports):
        from src.infrastructure.celery.callbacks import handle_failure

        mock_ports["task_repository"].update_status.return_value = _make_task(
            TaskStatus.FAILED
        )

        handle_failure(FAKE_TASK_ID, "download", Exception("Network error"))

        mock_ports["task_repository"].update_status.assert_awaited_once_with(
            UUID(FAKE_TASK_ID),
            TaskStatus.FAILED,
            error_message="Pipeline failed at download: Network error",
        )

    def test_handle_failure_cleans_up_temp_files(self, mock_ports):
        from src.infrastructure.celery.callbacks import handle_failure

        os.makedirs(TMP_DIR, exist_ok=True)
        with open(f"{TMP_DIR}/video.mp4", "w") as f:
            f.write("fake")

        mock_ports["task_repository"].update_status.return_value = _make_task(
            TaskStatus.FAILED
        )

        handle_failure(FAKE_TASK_ID, "download", Exception("fail"))

        assert not os.path.exists(TMP_DIR)

    def test_cleanup_temp_files_removes_directory(self):
        from src.infrastructure.celery.callbacks import cleanup_temp_files

        os.makedirs(TMP_DIR, exist_ok=True)
        with open(f"{TMP_DIR}/test.txt", "w") as f:
            f.write("data")

        cleanup_temp_files(FAKE_TASK_ID)

        assert not os.path.exists(TMP_DIR)

    def test_cleanup_temp_files_no_error_when_missing(self):
        from src.infrastructure.celery.callbacks import cleanup_temp_files

        cleanup_temp_files(FAKE_TASK_ID)  # should not raise


# ---------------------------------------------------------------------------
# PipelineOrchestrator
# ---------------------------------------------------------------------------


class TestPipelineOrchestrator:
    @pytest.mark.asyncio
    async def test_orchestrate_dispatches_chain(self):
        from src.application.services.pipeline_orchestrator import PipelineOrchestrator

        orchestrator = PipelineOrchestrator()

        with patch(
            "src.application.services.pipeline_orchestrator.chain"
        ) as mock_chain:
            mock_result = MagicMock()
            mock_result.id = "celery-chain-id-123"
            mock_chain.return_value.apply_async.return_value = mock_result

            chain_id = await orchestrator.orchestrate(
                UUID(FAKE_TASK_ID), FAKE_URL
            )

            assert chain_id == "celery-chain-id-123"
            mock_chain.assert_called_once()
            mock_chain.return_value.apply_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrate_chain_has_five_steps(self):
        from src.application.services.pipeline_orchestrator import PipelineOrchestrator

        orchestrator = PipelineOrchestrator()

        with patch(
            "src.application.services.pipeline_orchestrator.chain"
        ) as mock_chain:
            mock_result = MagicMock()
            mock_result.id = "id"
            mock_chain.return_value.apply_async.return_value = mock_result

            await orchestrator.orchestrate(UUID(FAKE_TASK_ID), FAKE_URL)

            args = mock_chain.call_args[0]
            assert len(args) == 5

    @pytest.mark.asyncio
    async def test_orchestrate_first_step_receives_task_id_and_url(self):
        from src.application.services.pipeline_orchestrator import PipelineOrchestrator

        orchestrator = PipelineOrchestrator()

        with patch(
            "src.application.services.pipeline_orchestrator.chain"
        ) as mock_chain:
            mock_result = MagicMock()
            mock_result.id = "id"
            mock_chain.return_value.apply_async.return_value = mock_result

            await orchestrator.orchestrate(UUID(FAKE_TASK_ID), FAKE_URL)

            first_step = mock_chain.call_args[0][0]
            assert first_step.args == (FAKE_TASK_ID, FAKE_URL)


# ---------------------------------------------------------------------------
# Full pipeline integration (eager mode)
# ---------------------------------------------------------------------------


class TestPipelineIntegration:
    def test_full_chain_happy_path(self, mock_ports):
        """Run the entire chain in eager mode with mocked ports."""
        from src.infrastructure.celery.tasks import (
            download_video,
            extract_audio,
            transcribe_audio,
            analyze_text,
            persist_results,
        )
        from celery import chain as celery_chain

        mock_ports["task_repository"].update_status.return_value = _make_task()
        mock_ports["video_downloader"].download.return_value = f"{TMP_DIR}/video.mp4"
        mock_ports["audio_extractor"].extract.return_value = f"{TMP_DIR}/audio.wav"
        mock_ports["transcriber"].transcribe.return_value = TranscriptionResult(
            text="Hola mundo", language="es"
        )
        mock_ports["text_analyzer"].extract_topics.return_value = ["mundo", "hola"]
        mock_ports["task_repository"].update_results.return_value = _make_task(
            TaskStatus.COMPLETED
        )

        pipeline = celery_chain(
            download_video.s(FAKE_TASK_ID, FAKE_URL),
            extract_audio.s(),
            transcribe_audio.s(),
            analyze_text.s(),
            persist_results.s(),
        )
        result = pipeline.apply().get()

        assert result["status"] == "completed"
        mock_ports["task_repository"].update_results.assert_awaited_once()

    def test_chain_aborts_on_cancellation_at_step_2(self, mock_ports):
        """If extract_audio detects cancellation, downstream tasks skip."""
        from src.infrastructure.celery.tasks import (
            download_video,
            extract_audio,
            transcribe_audio,
            analyze_text,
            persist_results,
        )
        from celery import chain as celery_chain

        # Step 1 succeeds
        mock_ports["task_repository"].update_status.side_effect = [
            _make_task(),  # download checks status
            None,          # extract_audio: cancelled
        ]
        mock_ports["video_downloader"].download.return_value = f"{TMP_DIR}/video.mp4"

        pipeline = celery_chain(
            download_video.s(FAKE_TASK_ID, FAKE_URL),
            extract_audio.s(),
            transcribe_audio.s(),
            analyze_text.s(),
            persist_results.s(),
        )
        result = pipeline.apply().get()

        assert result["cancelled"] is True
        mock_ports["audio_extractor"].extract.assert_not_awaited()
        mock_ports["transcriber"].transcribe.assert_not_awaited()
        mock_ports["task_repository"].update_results.assert_not_awaited()
