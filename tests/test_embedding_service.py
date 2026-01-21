# tests/test_embedding_service.py
"""Tests for embedding service."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.mark.asyncio
async def test_generate_embedding_returns_list():
    """generate_embedding should return list of floats."""
    with patch("src.services.embedding_service.AsyncOpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        from src.services.embedding_service import EmbeddingService
        service = EmbeddingService()
        result = await service.generate_embedding("test text")

        assert isinstance(result, list)
        assert len(result) == 1536
        assert all(isinstance(x, float) for x in result)
