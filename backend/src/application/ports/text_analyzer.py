from __future__ import annotations

from abc import ABC, abstractmethod


class TextAnalyzer(ABC):
    @abstractmethod
    async def extract_topics(self, text: str) -> list[str]:
        """Extract key topics/keyphrases from text. Returns list of topic strings."""
        ...
