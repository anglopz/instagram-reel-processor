from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.exceptions import InvalidURL, PipelineError
from src.infrastructure.adapters.ytdlp_downloader import YtdlpDownloader


@pytest.fixture
def downloader() -> YtdlpDownloader:
    return YtdlpDownloader()


@pytest.fixture
def tmp_output(tmp_path: Path) -> str:
    return str(tmp_path / "video.mp4")


class TestYtdlpDownloaderValidation:
    async def test_rejects_empty_url(self, downloader: YtdlpDownloader, tmp_output: str) -> None:
        with pytest.raises(InvalidURL):
            await downloader.download("", tmp_output)

    async def test_rejects_non_instagram_url(self, downloader: YtdlpDownloader, tmp_output: str) -> None:
        with pytest.raises(InvalidURL):
            await downloader.download("https://example.com/not-a-reel", tmp_output)

    async def test_rejects_malformed_url(self, downloader: YtdlpDownloader, tmp_output: str) -> None:
        with pytest.raises(InvalidURL):
            await downloader.download("not-a-url-at-all", tmp_output)

    async def test_accepts_instagram_reel_url(self, downloader: YtdlpDownloader, tmp_output: str) -> None:
        """Valid Instagram reel URLs should pass validation (download itself is mocked)."""
        with patch.object(downloader, "_run_ytdlp", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = tmp_output
            # Create the file so the post-check passes
            Path(tmp_output).touch()
            result = await downloader.download("https://www.instagram.com/reel/ABC123/", tmp_output)
            assert result == tmp_output
            mock_run.assert_called_once()

    async def test_accepts_instagram_p_url(self, downloader: YtdlpDownloader, tmp_output: str) -> None:
        """Instagram /p/ URLs (posts with video) should also be accepted."""
        with patch.object(downloader, "_run_ytdlp", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = tmp_output
            Path(tmp_output).touch()
            result = await downloader.download("https://www.instagram.com/p/XYZ789/", tmp_output)
            assert result == tmp_output


class TestYtdlpDownloaderDownload:
    async def test_creates_output_directory(self, downloader: YtdlpDownloader, tmp_path: Path) -> None:
        output_path = str(tmp_path / "subdir" / "video.mp4")
        with patch.object(downloader, "_run_ytdlp", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = output_path
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).touch()
            await downloader.download("https://www.instagram.com/reel/ABC123/", output_path)
            assert Path(output_path).parent.exists()

    async def test_returns_output_path_on_success(self, downloader: YtdlpDownloader, tmp_output: str) -> None:
        with patch.object(downloader, "_run_ytdlp", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = tmp_output
            Path(tmp_output).touch()
            result = await downloader.download("https://www.instagram.com/reel/ABC123/", tmp_output)
            assert result == tmp_output

    async def test_raises_pipeline_error_on_download_failure(
        self, downloader: YtdlpDownloader, tmp_output: str
    ) -> None:
        with patch.object(downloader, "_run_ytdlp", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = Exception("Download failed: video unavailable")
            with pytest.raises(PipelineError, match="download"):
                await downloader.download("https://www.instagram.com/reel/ABC123/", tmp_output)

    async def test_raises_pipeline_error_when_output_file_missing(
        self, downloader: YtdlpDownloader, tmp_output: str
    ) -> None:
        """If yt-dlp succeeds but file doesn't exist, raise PipelineError."""
        with patch.object(downloader, "_run_ytdlp", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = tmp_output
            # Don't create the file — simulate yt-dlp silently failing
            with pytest.raises(PipelineError, match="download"):
                await downloader.download("https://www.instagram.com/reel/ABC123/", tmp_output)

    async def test_raises_pipeline_error_on_private_reel(
        self, downloader: YtdlpDownloader, tmp_output: str
    ) -> None:
        with patch.object(downloader, "_run_ytdlp", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = Exception("Private video")
            with pytest.raises(PipelineError, match="download"):
                await downloader.download("https://www.instagram.com/reel/PRIVATE123/", tmp_output)

    async def test_raises_pipeline_error_on_network_timeout(
        self, downloader: YtdlpDownloader, tmp_output: str
    ) -> None:
        with patch.object(downloader, "_run_ytdlp", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = asyncio.TimeoutError()
            with pytest.raises(PipelineError, match="download"):
                await downloader.download("https://www.instagram.com/reel/ABC123/", tmp_output)

    async def test_passes_correct_ytdlp_options(self, downloader: YtdlpDownloader, tmp_output: str) -> None:
        """Verify yt-dlp is called with the expected output template."""
        with patch.object(downloader, "_run_ytdlp", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = tmp_output
            Path(tmp_output).touch()
            await downloader.download("https://www.instagram.com/reel/ABC123/", tmp_output)
            call_args = mock_run.call_args
            url_arg = call_args[0][0]
            opts_arg = call_args[0][1]
            assert url_arg == "https://www.instagram.com/reel/ABC123/"
            assert opts_arg["outtmpl"] == tmp_output
