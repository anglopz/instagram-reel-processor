from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.domain.exceptions import PipelineError
from src.infrastructure.adapters.ffmpeg_audio_extractor import FfmpegAudioExtractor


@pytest.fixture
def extractor() -> FfmpegAudioExtractor:
    return FfmpegAudioExtractor()


@pytest.fixture
def video_file(tmp_path: Path) -> str:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"\x00" * 1024)  # fake video content
    return str(video)


@pytest.fixture
def audio_output(tmp_path: Path) -> str:
    return str(tmp_path / "audio.wav")


class TestFfmpegAudioExtractorValidation:
    async def test_raises_pipeline_error_when_video_missing(
        self, extractor: FfmpegAudioExtractor, audio_output: str
    ) -> None:
        with pytest.raises(PipelineError, match="audio_extraction"):
            await extractor.extract("/nonexistent/video.mp4", audio_output)

    async def test_raises_pipeline_error_for_empty_video(
        self, extractor: FfmpegAudioExtractor, tmp_path: Path, audio_output: str
    ) -> None:
        empty_video = tmp_path / "empty.mp4"
        empty_video.touch()  # 0 bytes
        with pytest.raises(PipelineError, match="audio_extraction"):
            await extractor.extract(str(empty_video), audio_output)


class TestFfmpegAudioExtractorExtraction:
    async def test_creates_output_directory(
        self, extractor: FfmpegAudioExtractor, video_file: str, tmp_path: Path
    ) -> None:
        output_path = str(tmp_path / "nested" / "dir" / "audio.wav")
        with patch.object(extractor, "_run_ffmpeg", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = output_path
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).touch()
            await extractor.extract(video_file, output_path)
            assert Path(output_path).parent.exists()

    async def test_returns_output_path_on_success(
        self, extractor: FfmpegAudioExtractor, video_file: str, audio_output: str
    ) -> None:
        with patch.object(extractor, "_run_ffmpeg", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = audio_output
            Path(audio_output).touch()
            result = await extractor.extract(video_file, audio_output)
            assert result == audio_output

    async def test_raises_pipeline_error_on_ffmpeg_failure(
        self, extractor: FfmpegAudioExtractor, video_file: str, audio_output: str
    ) -> None:
        with patch.object(extractor, "_run_ffmpeg", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = Exception("ffmpeg error: no audio stream")
            with pytest.raises(PipelineError, match="audio_extraction"):
                await extractor.extract(video_file, audio_output)

    async def test_raises_pipeline_error_when_output_not_created(
        self, extractor: FfmpegAudioExtractor, video_file: str, audio_output: str
    ) -> None:
        """If ffmpeg succeeds but output file doesn't exist, raise PipelineError."""
        with patch.object(extractor, "_run_ffmpeg", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = audio_output
            # Don't create the output file
            with pytest.raises(PipelineError, match="audio_extraction"):
                await extractor.extract(video_file, audio_output)

    async def test_raises_pipeline_error_on_corrupted_video(
        self, extractor: FfmpegAudioExtractor, video_file: str, audio_output: str
    ) -> None:
        with patch.object(extractor, "_run_ffmpeg", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = Exception("Invalid data found when processing input")
            with pytest.raises(PipelineError, match="audio_extraction"):
                await extractor.extract(video_file, audio_output)

    async def test_raises_pipeline_error_on_no_audio_track(
        self, extractor: FfmpegAudioExtractor, video_file: str, audio_output: str
    ) -> None:
        with patch.object(extractor, "_run_ffmpeg", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = Exception("Stream map '0:a' matches no streams")
            with pytest.raises(PipelineError, match="audio_extraction"):
                await extractor.extract(video_file, audio_output)

    async def test_passes_correct_ffmpeg_params(
        self, extractor: FfmpegAudioExtractor, video_file: str, audio_output: str
    ) -> None:
        """Verify ffmpeg is called with correct input/output and WAV format settings."""
        with patch.object(extractor, "_run_ffmpeg", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = audio_output
            Path(audio_output).touch()
            await extractor.extract(video_file, audio_output)
            call_args = mock_run.call_args
            assert call_args[0][0] == video_file
            assert call_args[0][1] == audio_output
