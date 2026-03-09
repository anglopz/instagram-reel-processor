from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

from src.application.ports.video_downloader import VideoDownloader
from src.domain.exceptions import InvalidURL, PipelineError

logger = logging.getLogger(__name__)

_INSTAGRAM_URL_PATTERN = re.compile(
    r"^https?://(www\.)?instagram\.com/(reel|p|reels)/[\w-]+/?",
)


class YtdlpDownloader(VideoDownloader):
    """Downloads Instagram reels/posts using yt-dlp."""

    async def download(self, url: str, output_path: str) -> str:
        self._validate_url(url)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        opts = {
            "outtmpl": output_path,
            "format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
            "retries": 3,
        }

        try:
            await self._run_ytdlp(url, opts)
        except asyncio.TimeoutError:
            logger.error("Network timeout downloading %s", url)
            raise PipelineError("download", f"Network timeout downloading {url}")
        except Exception as exc:
            logger.error("yt-dlp failed for %s: %s", url, exc)
            raise PipelineError("download", str(exc))

        if not Path(output_path).exists():
            raise PipelineError(
                "download",
                f"Download completed but output file not found at {output_path}",
            )

        logger.info("Downloaded video to %s", output_path)
        return output_path

    async def _run_ytdlp(self, url: str, opts: dict) -> str:
        """Run yt-dlp in a thread pool to avoid blocking the event loop."""
        import yt_dlp

        def _download() -> str:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            return opts["outtmpl"]

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _download)

    @staticmethod
    def _validate_url(url: str) -> None:
        if not url or not url.strip():
            raise InvalidURL(url or "(empty)")
        if not _INSTAGRAM_URL_PATTERN.match(url):
            raise InvalidURL(url)
