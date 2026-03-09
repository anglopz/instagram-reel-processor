from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.application.ports.transcriber import TranscriptionResult
from src.domain.exceptions import PipelineError
from src.infrastructure.adapters.whisper_transcriber import WhisperTranscriber


@pytest.fixture()
def audio_file(tmp_path: Path) -> Path:
    """Create a minimal fake .wav file for tests that need a valid path."""
    f = tmp_path / "audio.wav"
    f.write_bytes(b"RIFF" + b"\x00" * 100)
    return f


class TestWhisperTranscriber:
    """Unit tests for WhisperTranscriber adapter."""

    def setup_method(self) -> None:
        self.transcriber = WhisperTranscriber(model_name="base")

    # --- Happy path ---

    @pytest.mark.asyncio
    async def test_transcribe_returns_transcription_result(
        self, audio_file: Path
    ) -> None:
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "Hello world, this is a test.",
            "language": "en",
        }

        with patch.object(self.transcriber, "_model", mock_model):
            result = await self.transcriber.transcribe(str(audio_file))

        assert isinstance(result, TranscriptionResult)
        assert result.text == "Hello world, this is a test."
        assert result.language == "en"

    @pytest.mark.asyncio
    async def test_transcribe_returns_detected_language(
        self, audio_file: Path
    ) -> None:
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "Hola mundo, esto es una prueba.",
            "language": "es",
        }

        with patch.object(self.transcriber, "_model", mock_model):
            result = await self.transcriber.transcribe(str(audio_file))

        assert result.language == "es"
        assert result.text == "Hola mundo, esto es una prueba."

    @pytest.mark.asyncio
    async def test_transcribe_strips_whitespace_from_text(
        self, audio_file: Path
    ) -> None:
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "  some text with whitespace  ",
            "language": "en",
        }

        with patch.object(self.transcriber, "_model", mock_model):
            result = await self.transcriber.transcribe(str(audio_file))

        assert result.text == "some text with whitespace"

    # --- Error handling: file not found ---

    @pytest.mark.asyncio
    async def test_transcribe_raises_on_nonexistent_file(self) -> None:
        with pytest.raises(PipelineError, match="Audio file not found"):
            await self.transcriber.transcribe("/tmp/nonexistent_audio_12345.wav")

    # --- Error handling: empty audio file ---

    @pytest.mark.asyncio
    async def test_transcribe_raises_on_empty_audio_file(
        self, tmp_path: Path
    ) -> None:
        empty_file = tmp_path / "empty.wav"
        empty_file.write_bytes(b"")

        with pytest.raises(PipelineError, match="empty"):
            await self.transcriber.transcribe(str(empty_file))

    # --- Error handling: unsupported format ---

    @pytest.mark.asyncio
    async def test_transcribe_raises_on_unsupported_format(
        self, tmp_path: Path
    ) -> None:
        bad_file = tmp_path / "audio.xyz"
        bad_file.write_bytes(b"some data")

        with pytest.raises(PipelineError, match="Unsupported audio format"):
            await self.transcriber.transcribe(str(bad_file))

    # --- Error handling: whisper model failure ---

    @pytest.mark.asyncio
    async def test_transcribe_raises_on_model_error(self, audio_file: Path) -> None:
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = RuntimeError("CUDA out of memory")

        with patch.object(self.transcriber, "_model", mock_model):
            with pytest.raises(PipelineError, match="Transcription failed"):
                await self.transcriber.transcribe(str(audio_file))

    # --- Error handling: empty transcript ---

    @pytest.mark.asyncio
    async def test_transcribe_raises_on_empty_transcript(
        self, audio_file: Path
    ) -> None:
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "   ",
            "language": "en",
        }

        with patch.object(self.transcriber, "_model", mock_model):
            with pytest.raises(PipelineError, match="empty transcript"):
                await self.transcriber.transcribe(str(audio_file))

    # --- Model loading ---

    def test_lazy_model_loading(self) -> None:
        """Model should not be loaded until first transcribe call."""
        transcriber = WhisperTranscriber(model_name="base")
        assert transcriber._model is None

    @pytest.mark.asyncio
    async def test_model_loading_failure_raises_pipeline_error(
        self, audio_file: Path
    ) -> None:
        transcriber = WhisperTranscriber(model_name="base")

        with patch(
            "src.infrastructure.adapters.whisper_transcriber.whisper.load_model",
            side_effect=RuntimeError("Failed to load model"),
        ):
            with pytest.raises(PipelineError, match="Failed to load Whisper model"):
                await transcriber.transcribe(str(audio_file))

    # --- Model name configuration ---

    def test_default_model_name(self) -> None:
        transcriber = WhisperTranscriber()
        assert transcriber._model_name == "base"

    def test_custom_model_name(self) -> None:
        transcriber = WhisperTranscriber(model_name="small")
        assert transcriber._model_name == "small"

    # --- Port compliance ---

    def test_implements_transcriber_port(self) -> None:
        from src.application.ports.transcriber import Transcriber

        assert isinstance(self.transcriber, Transcriber)
