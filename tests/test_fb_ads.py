from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.fb_ads import extract_domain, search_ads, get_advertiser_domains


def test_extract_domain_simple():
    assert extract_domain("https://glossybrand.com/shop") == "glossybrand.com"


def test_extract_domain_with_www():
    assert extract_domain("https://www.example.com/page") == "example.com"


def test_extract_domain_with_subdomain():
    assert extract_domain("https://shop.mystore.com/products") == "shop.mystore.com"


def test_extract_domain_invalid_url():
    assert extract_domain("not a url") is None
    assert extract_domain("") is None


@pytest.mark.asyncio
async def test_search_ads_returns_results():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {
                "page_id": "123",
                "page_name": "Glossy Brand",
                "link_url": "https://glossybrand.com/shop"
            },
            {
                "page_id": "456",
                "page_name": "Beauty Co",
                "link_url": "https://beautyco.com/products"
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("src.fb_ads.SCRAPECREATORS_API_KEY", "test-api-key"):
        with patch("src.fb_ads.httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            results = await search_ads("collagen supplement", country="US", limit=10)

            assert len(results) == 2
            assert results[0]["page_id"] == "123"
            assert results[0]["link_url"] == "https://glossybrand.com/shop"


@pytest.mark.asyncio
async def test_search_ads_no_api_key_returns_empty():
    with patch("src.fb_ads.SCRAPECREATORS_API_KEY", ""):
        results = await search_ads("test keyword")
        assert results == []


@pytest.mark.asyncio
async def test_get_advertiser_domains_dedupes_by_domain():
    with patch("src.fb_ads.search_ads") as mock_search:
        mock_search.return_value = [
            {"page_id": "123", "page_name": "Brand A", "link_url": "https://brand-a.com/page1"},
            {"page_id": "123", "page_name": "Brand A", "link_url": "https://brand-a.com/page2"},
            {"page_id": "456", "page_name": "Brand B", "link_url": "https://brand-b.com/shop"},
        ]

        results = await get_advertiser_domains("test", country="US", limit=10)

        assert len(results) == 2
        domains = [r["domain"] for r in results]
        assert "brand-a.com" in domains
        assert "brand-b.com" in domains


@pytest.mark.asyncio
async def test_get_advertiser_domains_skips_invalid_urls():
    with patch("src.fb_ads.search_ads") as mock_search:
        mock_search.return_value = [
            {"page_id": "123", "page_name": "Valid", "link_url": "https://valid.com"},
            {"page_id": "456", "page_name": "Invalid", "link_url": ""},
            {"page_id": "789", "page_name": "None", "link_url": None},
        ]

        results = await get_advertiser_domains("test")

        assert len(results) == 1
        assert results[0]["domain"] == "valid.com"
