from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from src.application.ports.audio_extractor import AudioExtractor
from src.domain.exceptions import PipelineError

logger = logging.getLogger(__name__)


class FfmpegAudioExtractor(AudioExtractor):
    """Extracts audio from video files using ffmpeg-python."""

    async def extract(self, video_path: str, output_path: str) -> str:
        self._validate_input(video_path)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            await self._run_ffmpeg(video_path, output_path)
        except Exception as exc:
            logger.error("ffmpeg failed for %s: %s", video_path, exc)
            raise PipelineError("audio_extraction", str(exc))

        if not Path(output_path).exists():
            raise PipelineError(
                "audio_extraction",
                f"Extraction completed but output file not found at {output_path}",
            )

        logger.info("Extracted audio to %s", output_path)
        return output_path

    async def _run_ffmpeg(self, video_path: str, output_path: str) -> str:
        """Run ffmpeg in a thread pool to avoid blocking the event loop."""
        import ffmpeg

        def _extract() -> str:
            (
                ffmpeg.input(video_path)
                .output(
                    output_path,
                    acodec="pcm_s16le",
                    ar="16000",
                    ac=1,
                )
                .overwrite_output()
                .run(quiet=True)
            )
            return output_path

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _extract)

    @staticmethod
    def _validate_input(video_path: str) -> None:
        path = Path(video_path)
        if not path.exists():
            raise PipelineError(
                "audio_extraction",
                f"Video file not found: {video_path}",
            )
        if path.stat().st_size == 0:
            raise PipelineError(
                "audio_extraction",
                f"Video file is empty: {video_path}",
            )
