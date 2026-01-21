# tests/test_seed_analyzer.py
"""Tests for seed analyzer service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_analyze_seed_returns_markdown():
    """analyze_seed should return markdown analysis."""
    with patch("src.services.seed_analyzer.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "<html><body><h1>Collagen Brand</h1></body></html>"
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        with patch("src.services.seed_analyzer.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_claude = MagicMock()
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text="# Analysis\n\nThis is a collagen brand.")]
            mock_claude.messages.create = AsyncMock(return_value=mock_message)
            mock_anthropic.return_value = mock_claude

            from src.services.seed_analyzer import SeedAnalyzer
            analyzer = SeedAnalyzer()
            result = await analyzer.analyze_seed("https://example.com")

            assert isinstance(result, str)
            assert len(result) > 0
