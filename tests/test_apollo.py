"""Tests for Apollo.io API client."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from src.apollo import search_people


@pytest.mark.asyncio
async def test_search_people_returns_results():
    """Test searching for people returns structured results."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "people": [
            {
                "id": "abc123",
                "first_name": "John",
                "last_name": "Doe",
                "title": "CEO",
                "organization": {"name": "Acme Inc"},
                "linkedin_url": "https://linkedin.com/in/johndoe"
            }
        ]
    }
    mock_response.raise_for_status.return_value = None

    with patch("src.apollo.APOLLO_API_KEY", "test-key"):
        with patch("src.apollo.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            results = await search_people("acme.com", ["CEO", "Founder"], limit=5)

            assert len(results) == 1
            assert results[0]["first_name"] == "John"
            assert results[0]["title"] == "CEO"


@pytest.mark.asyncio
async def test_search_people_no_api_key_returns_empty():
    """Test that missing API key returns empty list."""
    with patch("src.apollo.APOLLO_API_KEY", ""):
        results = await search_people("test.com", ["CEO"])
        assert results == []


@pytest.mark.asyncio
async def test_search_people_handles_error():
    """Test that API errors return empty list."""
    with patch("src.apollo.APOLLO_API_KEY", "test-key"):
        with patch("src.apollo.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = Exception("API error")
            mock_client.return_value.__aenter__.return_value = mock_instance

            results = await search_people("acme.com", ["CEO"])

            assert results == []
