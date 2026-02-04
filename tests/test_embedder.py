"""Tests for app/logic/embedder.py"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock


class TestGetEmbedding:
    """Test get_embedding function."""

    def test_empty_text_returns_zeros(self):
        """Empty text should return zero vector."""
        from app.logic.embedder import get_embedding

        result = get_embedding("")
        assert len(result) == 1536
        assert all(v == 0.0 for v in result)

    def test_whitespace_only_returns_zeros(self):
        """Whitespace-only text should return zero vector."""
        from app.logic.embedder import get_embedding

        result = get_embedding("   \n\t  ")
        assert len(result) == 1536
        assert all(v == 0.0 for v in result)

    @patch('app.logic.embedder.openai')
    def test_calls_openai_with_text(self, mock_openai, mock_embedding):
        """Should call OpenAI API with the text."""
        mock_openai.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=mock_embedding)]
        )

        from app.logic.embedder import get_embedding

        result = get_embedding("test text")

        mock_openai.embeddings.create.assert_called_once()
        call_args = mock_openai.embeddings.create.call_args
        assert "test text" in str(call_args)

    @patch('app.logic.embedder.openai')
    def test_truncates_long_text(self, mock_openai, mock_embedding):
        """Should truncate text longer than 30000 chars."""
        mock_openai.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=mock_embedding)]
        )

        from app.logic.embedder import get_embedding

        long_text = "x" * 50000
        get_embedding(long_text)

        call_args = mock_openai.embeddings.create.call_args
        # The input should be truncated
        input_text = call_args.kwargs.get('input') or call_args[1].get('input')
        assert len(input_text) <= 30000

    @patch('app.logic.embedder.openai')
    def test_returns_embedding_from_response(self, mock_openai):
        """Should return the embedding from API response."""
        expected = [0.5] * 1536
        mock_openai.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=expected)]
        )

        from app.logic.embedder import get_embedding

        result = get_embedding("test")

        assert result == expected


class TestCosineSimilarity:
    """Test cosine_similarity function."""

    def test_identical_vectors(self):
        """Identical vectors should have similarity 1.0."""
        from app.logic.embedder import cosine_similarity

        vec = [1.0, 2.0, 3.0]
        result = cosine_similarity(vec, vec)

        assert abs(result - 1.0) < 0.0001

    def test_orthogonal_vectors(self):
        """Orthogonal vectors should have similarity 0.0."""
        from app.logic.embedder import cosine_similarity

        vec1 = [1.0, 0.0]
        vec2 = [0.0, 1.0]
        result = cosine_similarity(vec1, vec2)

        assert abs(result) < 0.0001

    def test_opposite_vectors(self):
        """Opposite vectors should have similarity -1.0."""
        from app.logic.embedder import cosine_similarity

        vec1 = [1.0, 2.0, 3.0]
        vec2 = [-1.0, -2.0, -3.0]
        result = cosine_similarity(vec1, vec2)

        assert abs(result + 1.0) < 0.0001

    def test_zero_vector_returns_zero(self):
        """Zero vector should result in 0.0 similarity."""
        from app.logic.embedder import cosine_similarity

        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 2.0, 3.0]
        result = cosine_similarity(vec1, vec2)

        assert result == 0.0

    def test_similar_vectors(self):
        """Similar vectors should have high similarity."""
        from app.logic.embedder import cosine_similarity

        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.1, 2.1, 3.1]
        result = cosine_similarity(vec1, vec2)

        assert result > 0.99
