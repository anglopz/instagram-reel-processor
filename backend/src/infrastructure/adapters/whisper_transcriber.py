from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import whisper

from src.application.ports.transcriber import Transcriber, TranscriptionResult
from src.domain.exceptions import PipelineError

logger = logging.getLogger(__name__)

# Supported audio formats that Whisper/ffmpeg can handle
_SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".webm", ".mp4"}


class WhisperTranscriber(Transcriber):
    """Transcriber adapter using OpenAI Whisper (local model).

    Uses the 'base' model by default for development speed.
    For production, consider 'small' or 'medium' for better accuracy.
    """

    def __init__(self, model_name: str = "base") -> None:
        self._model_name = model_name
        self._model: whisper.Whisper | None = None

    def _load_model(self) -> whisper.Whisper:
        """Lazily load the Whisper model on first use."""
        if self._model is None:
            try:
                logger.info("Loading Whisper model: %s", self._model_name)
                self._model = whisper.load_model(self._model_name)
            except Exception as exc:
                raise PipelineError(
                    step="transcription",
                    detail=f"Failed to load Whisper model '{self._model_name}': {exc}",
                ) from exc
        return self._model

    async def transcribe(self, audio_path: str) -> TranscriptionResult:
        """Transcribe audio file using Whisper. Returns text and detected language."""
        path = Path(audio_path)

        # Validate file exists
        if not path.exists():
            raise PipelineError(
                step="transcription",
                detail=f"Audio file not found: {audio_path}",
            )

        # Validate file is not empty
        if path.stat().st_size == 0:
            raise PipelineError(
                step="transcription",
                detail=f"Audio file is empty: {audio_path}",
            )

        # Validate supported format
        if path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
            raise PipelineError(
                step="transcription",
                detail=f"Unsupported audio format: {path.suffix}",
            )

        # Load model (lazy)
        model = self._load_model()

        # Run Whisper in a thread pool to avoid blocking the event loop
        try:
            result = await asyncio.to_thread(model.transcribe, str(path))
        except PipelineError:
            raise
        except Exception as exc:
            raise PipelineError(
                step="transcription",
                detail=f"Transcription failed: {exc}",
            ) from exc

        text = result.get("text", "").strip()
        language = result.get("language", "unknown")

        if not text:
            raise PipelineError(
                step="transcription",
                detail="Whisper returned an empty transcript",
            )

        logger.info(
            "Transcription complete: language=%s, length=%d chars",
            language,
            len(text),
        )

        return TranscriptionResult(text=text, language=language)
