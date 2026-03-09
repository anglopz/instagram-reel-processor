from __future__ import annotations

from src.infrastructure.adapters.ffmpeg_audio_extractor import FfmpegAudioExtractor
from src.infrastructure.adapters.keybert_analyzer import KeybertAnalyzer
from src.infrastructure.adapters.postgres_task_repository import (
    PostgresTaskRepository,
)
from src.infrastructure.adapters.whisper_transcriber import WhisperTranscriber
from src.infrastructure.adapters.ytdlp_downloader import YtdlpDownloader
from src.infrastructure.celery.tasks import register_ports
from src.infrastructure.database.session import create_session_factory


def init_container() -> None:
    """Wire adapter implementations to port interfaces.

    Must be called once at application startup so Celery tasks
    can resolve their port dependencies via the registry.
    """
    session_factory = create_session_factory()

    register_ports(
        task_repository=PostgresTaskRepository(session_factory),
        video_downloader=YtdlpDownloader(),
        audio_extractor=FfmpegAudioExtractor(),
        transcriber=WhisperTranscriber(),
        text_analyzer=KeybertAnalyzer(),
    )
