from __future__ import annotations

from abc import ABC, abstractmethod


class AudioExtractor(ABC):
    @abstractmethod
    async def extract(self, video_path: str, output_path: str) -> str:
        """Extract audio from video file. Returns the path to the extracted audio file."""
        ...
