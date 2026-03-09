from __future__ import annotations

from abc import ABC, abstractmethod


class VideoDownloader(ABC):
    @abstractmethod
    async def download(self, url: str, output_path: str) -> str:
        """Download video from URL to output_path. Returns the path to the downloaded file."""
        ...
