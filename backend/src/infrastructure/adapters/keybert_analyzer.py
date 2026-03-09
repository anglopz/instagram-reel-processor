from __future__ import annotations

import asyncio
import logging

from keybert import KeyBERT

from src.application.ports.text_analyzer import TextAnalyzer

logger = logging.getLogger(__name__)


class KeybertAnalyzer(TextAnalyzer):
    """TextAnalyzer adapter using KeyBERT for keyphrase extraction.

    Uses 'all-MiniLM-L6-v2' sentence-transformer by default.
    Extracts top-5 keyphrases from the given text.
    """

    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2") -> None:
        self._embedding_model = embedding_model
        self._model: KeyBERT | None = None

    def _load_model(self) -> KeyBERT:
        """Lazily load the KeyBERT model on first use."""
        if self._model is None:
            logger.info("Loading KeyBERT with model: %s", self._embedding_model)
            self._model = KeyBERT(model=self._embedding_model)
        return self._model

    async def extract_topics(self, text: str) -> list[str]:
        """Extract top-5 keyphrases from text using KeyBERT."""
        if not text or not text.strip():
            return []

        try:
            model = self._load_model()
        except Exception:
            logger.exception("Failed to load KeyBERT model")
            return []

        try:
            keywords = await asyncio.to_thread(
                model.extract_keywords,
                text,
                top_n=5,
                stop_words="english",
                use_mmr=True,
                diversity=0.5,
            )
        except Exception:
            logger.exception("KeyBERT extraction failed")
            return []

        return [kw for kw, _score in keywords]
