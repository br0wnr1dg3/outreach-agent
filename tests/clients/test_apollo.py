"""Tests for Apollo.io API client."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from src.apollo import search_people, enrich_people, find_leads_at_company


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


@pytest.mark.asyncio
async def test_enrich_people_returns_emails():
    """Test bulk enrichment returns people with email addresses."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "matches": [
            {
                "id": "abc123",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@acme.com",
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

            people = [{"id": "abc123", "first_name": "John", "last_name": "Doe"}]
            results = await enrich_people(people)

            assert len(results) == 1
            assert results[0]["email"] == "john@acme.com"


@pytest.mark.asyncio
async def test_enrich_people_empty_list():
    """Test enriching empty list returns empty list."""
    results = await enrich_people([])
    assert results == []


@pytest.mark.asyncio
async def test_find_leads_at_company_returns_leads_with_email():
    """Test finding leads returns enriched leads with emails."""
    with patch("src.apollo.search_people") as mock_search:
        with patch("src.apollo.enrich_people") as mock_enrich:
            mock_search.return_value = [
                {"id": "1", "first_name": "John", "last_name": "Doe", "title": "CEO",
                 "organization": {"name": "Acme"}, "linkedin_url": "https://linkedin.com/in/john"}
            ]
            mock_enrich.return_value = [
                {"id": "1", "first_name": "John", "last_name": "Doe", "email": "john@acme.com",
                 "title": "CEO", "organization": {"name": "Acme"}, "linkedin_url": "https://linkedin.com/in/john"}
            ]

            results = await find_leads_at_company("acme.com", ["CEO"], max_leads=3)

            assert len(results) == 1
            assert results[0]["email"] == "john@acme.com"
            assert results[0]["first_name"] == "John"
            assert results[0]["company"] == "Acme"


@pytest.mark.asyncio
async def test_find_leads_at_company_filters_no_email():
    """Test that leads without email are filtered out."""
    with patch("src.apollo.search_people") as mock_search:
        with patch("src.apollo.enrich_people") as mock_enrich:
            mock_search.return_value = [{"id": "1", "first_name": "John"}]
            mock_enrich.return_value = [
                {"id": "1", "first_name": "John", "email": None},  # No email
            ]

            results = await find_leads_at_company("acme.com", ["CEO"])

            assert len(results) == 0
