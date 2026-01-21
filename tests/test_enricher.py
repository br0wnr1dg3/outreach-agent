import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.db import init_db, insert_lead, get_lead_by_id
from src.enricher import enrich_lead, scrape_linkedin_posts


@pytest.mark.asyncio
async def test_scrape_linkedin_posts_success():
    """Test scraping LinkedIn posts with async polling approach."""
    # Mock responses for the 3-step process:
    # 1. POST to start run -> returns run_id
    # 2. GET to poll status -> returns SUCCEEDED with dataset_id
    # 3. GET dataset items -> returns posts

    # The run response now includes defaultDatasetId immediately
    run_response_data = {"data": {"id": "run123", "defaultDatasetId": "dataset456"}}
    status_response_data = {"data": {"status": "SUCCEEDED"}}
    dataset_items = [
        {"text": "Excited about our new product launch!"},
        {"text": "Q4 is always organized chaos."},
    ]

    with patch("src.enricher.APIFY_API_KEY", "test-key"):
        with patch("src.enricher.httpx.AsyncClient") as mock_client:
            # Create mock responses
            run_response = MagicMock()
            run_response.json.return_value = run_response_data
            run_response.raise_for_status.return_value = None

            status_response = MagicMock()
            status_response.json.return_value = status_response_data
            status_response.raise_for_status.return_value = None

            dataset_response = MagicMock()
            dataset_response.json.return_value = dataset_items
            dataset_response.raise_for_status.return_value = None

            # Create the async client instance mock
            mock_instance = AsyncMock()
            mock_instance.post.return_value = run_response
            mock_instance.get.side_effect = [status_response, dataset_response]
            mock_client.return_value.__aenter__.return_value = mock_instance

            posts = await scrape_linkedin_posts("https://linkedin.com/in/test")

            assert len(posts) == 2
            assert "new product launch" in posts[0]


@pytest.mark.asyncio
async def test_scrape_linkedin_posts_empty():
    """Test scraping when no posts found."""
    run_response_data = {"data": {"id": "run123", "defaultDatasetId": "dataset456"}}
    status_response_data = {"data": {"status": "SUCCEEDED"}}
    dataset_items = []

    with patch("src.enricher.APIFY_API_KEY", "test-key"):
        with patch("src.enricher.httpx.AsyncClient") as mock_client:
            run_response = MagicMock()
            run_response.json.return_value = run_response_data
            run_response.raise_for_status.return_value = None

            status_response = MagicMock()
            status_response.json.return_value = status_response_data
            status_response.raise_for_status.return_value = None

            dataset_response = MagicMock()
            dataset_response.json.return_value = dataset_items
            dataset_response.raise_for_status.return_value = None

            mock_instance = AsyncMock()
            mock_instance.post.return_value = run_response
            mock_instance.get.side_effect = [status_response, dataset_response]
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
        mock_profile = {"fullName": "Test User", "headline": "CEO"}

        with patch("src.enricher.scrape_linkedin_posts", new_callable=AsyncMock) as mock_posts_scrape:
            with patch("src.enricher.scrape_linkedin_profile", new_callable=AsyncMock) as mock_profile_scrape:
                mock_posts_scrape.return_value = mock_posts
                mock_profile_scrape.return_value = mock_profile

                result = await enrich_lead(lead_id, db_path)

                assert result["success"] is True
                assert result["posts"] == mock_posts
                assert result["profile"] == mock_profile

                lead = get_lead_by_id(db_path, lead_id)
                assert lead["enriched_at"] is not None
