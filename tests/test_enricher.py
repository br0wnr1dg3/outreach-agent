import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.db import init_db, insert_lead, get_lead_by_id
from src.enricher import enrich_lead, scrape_linkedin_posts


@pytest.mark.asyncio
async def test_scrape_linkedin_posts_success():
    mock_response_data = [
        {
            "recentPosts": [
                {"text": "Excited about our new product launch!"},
                {"text": "Q4 is always organized chaos."},
            ]
        }
    ]

    with patch("src.enricher.APIFY_API_KEY", "test-key"):
        with patch("src.enricher.httpx.AsyncClient") as mock_client:
            # Create a response mock with sync json() method
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None

            # Create the async client instance mock
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            posts = await scrape_linkedin_posts("https://linkedin.com/in/test")

            assert len(posts) == 2
            assert "new product launch" in posts[0]


@pytest.mark.asyncio
async def test_scrape_linkedin_posts_empty():
    mock_response_data = [{"recentPosts": []}]

    with patch("src.enricher.APIFY_API_KEY", "test-key"):
        with patch("src.enricher.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None

            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            posts = await scrape_linkedin_posts("https://linkedin.com/in/test")

            assert posts == []


@pytest.mark.asyncio
async def test_enrich_lead_updates_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        lead_id = insert_lead(
            db_path, "test@example.com", "Test", None, "Acme", None,
            "https://linkedin.com/in/test"
        )

        mock_posts = ["Post about marketing", "Another post"]

        with patch("src.enricher.scrape_linkedin_posts", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = mock_posts

            result = await enrich_lead(lead_id, db_path)

            assert result["success"] is True
            assert result["posts"] == mock_posts

            lead = get_lead_by_id(db_path, lead_id)
            assert lead["enriched_at"] is not None
