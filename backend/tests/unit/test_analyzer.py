from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.adapters.keybert_analyzer import KeybertAnalyzer


class TestKeybertAnalyzer:
    """Unit tests for KeybertAnalyzer adapter."""

    def setup_method(self) -> None:
        self.analyzer = KeybertAnalyzer()

    # --- Happy path ---

    @pytest.mark.asyncio
    async def test_extract_topics_returns_list_of_strings(self) -> None:
        mock_model = MagicMock()
        mock_model.extract_keywords.return_value = [
            ("machine learning", 0.85),
            ("neural networks", 0.78),
            ("deep learning", 0.72),
            ("artificial intelligence", 0.68),
            ("data science", 0.61),
        ]

        with patch.object(self.analyzer, "_model", mock_model):
            result = await self.analyzer.extract_topics(
                "Machine learning and neural networks are part of deep learning "
                "and artificial intelligence, which is core to data science."
            )

        assert isinstance(result, list)
        assert len(result) == 5
        assert all(isinstance(t, str) for t in result)

    @pytest.mark.asyncio
    async def test_extract_topics_returns_top_5(self) -> None:
        mock_model = MagicMock()
        mock_model.extract_keywords.return_value = [
            ("topic1", 0.9),
            ("topic2", 0.8),
            ("topic3", 0.7),
            ("topic4", 0.6),
            ("topic5", 0.5),
        ]

        with patch.object(self.analyzer, "_model", mock_model):
            result = await self.analyzer.extract_topics("Some text about many topics.")

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_extract_topics_returns_keyphrases_without_scores(self) -> None:
        mock_model = MagicMock()
        mock_model.extract_keywords.return_value = [
            ("python programming", 0.9),
            ("web development", 0.7),
        ]

        with patch.object(self.analyzer, "_model", mock_model):
            result = await self.analyzer.extract_topics("Python programming and web development.")

        assert result == ["python programming", "web development"]

    @pytest.mark.asyncio
    async def test_extract_topics_calls_keybert_with_correct_params(self) -> None:
        mock_model = MagicMock()
        mock_model.extract_keywords.return_value = [("test", 0.5)]

        with patch.object(self.analyzer, "_model", mock_model):
            await self.analyzer.extract_topics("test text")

        mock_model.extract_keywords.assert_called_once()
        call_kwargs = mock_model.extract_keywords.call_args
        assert call_kwargs[0][0] == "test text" or call_kwargs[1].get("docs") == "test text"
        # Should request top_n=5
        assert call_kwargs[1].get("top_n") == 5

    # --- Error handling: empty text ---

    @pytest.mark.asyncio
    async def test_extract_topics_returns_empty_list_for_empty_text(self) -> None:
        result = await self.analyzer.extract_topics("")
        assert result == []

    @pytest.mark.asyncio
    async def test_extract_topics_returns_empty_list_for_whitespace(self) -> None:
        result = await self.analyzer.extract_topics("   ")
        assert result == []

    # --- Error handling: very short text ---

    @pytest.mark.asyncio
    async def test_extract_topics_handles_short_text(self) -> None:
        mock_model = MagicMock()
        mock_model.extract_keywords.return_value = [("hello", 0.5)]

        with patch.object(self.analyzer, "_model", mock_model):
            result = await self.analyzer.extract_topics("Hello")

        assert result == ["hello"]

    # --- Error handling: model failure ---

    @pytest.mark.asyncio
    async def test_extract_topics_returns_empty_on_model_error(self) -> None:
        """Topic extraction is non-critical; errors should return empty list, not raise."""
        mock_model = MagicMock()
        mock_model.extract_keywords.side_effect = RuntimeError("Model error")

        with patch.object(self.analyzer, "_model", mock_model):
            result = await self.analyzer.extract_topics("Some text.")

        assert result == []

    # --- Lazy loading ---

    def test_lazy_model_loading(self) -> None:
        analyzer = KeybertAnalyzer()
        assert analyzer._model is None

    @pytest.mark.asyncio
    async def test_model_loading_failure_returns_empty(self) -> None:
        """If KeyBERT fails to load, gracefully return empty topics."""
        analyzer = KeybertAnalyzer()

        with patch(
            "src.infrastructure.adapters.keybert_analyzer.KeyBERT",
            side_effect=RuntimeError("Model load failed"),
        ):
            result = await analyzer.extract_topics("Some text.")

        assert result == []

    # --- Embedding model configuration ---

    def test_default_embedding_model(self) -> None:
        analyzer = KeybertAnalyzer()
        assert analyzer._embedding_model == "all-MiniLM-L6-v2"

    def test_custom_embedding_model(self) -> None:
        analyzer = KeybertAnalyzer(embedding_model="paraphrase-MiniLM-L3-v2")
        assert analyzer._embedding_model == "paraphrase-MiniLM-L3-v2"

    # --- Port compliance ---

    def test_implements_text_analyzer_port(self) -> None:
        from src.application.ports.text_analyzer import TextAnalyzer

        assert isinstance(self.analyzer, TextAnalyzer)
