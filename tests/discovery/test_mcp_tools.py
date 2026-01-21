"""Tests for consolidated MCP tools."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# =============================================================================
# Apollo Tests
# =============================================================================


@pytest.mark.asyncio
async def test_check_company_contacts_returns_bool():
    """check_company_contacts should return bool and count."""
    mock_apollo = AsyncMock()
    mock_apollo.search_people = AsyncMock(return_value=[
        {"id": "1", "first_name": "John", "title": "CEO"}
    ])

    from src.discovery.mcp_tools import create_apollo_mcp_server, get_apollo_handlers
    server = create_apollo_mcp_server(apollo_client=mock_apollo)

    handlers = get_apollo_handlers()
    result = await handlers["check_company_contacts"]({
        "domain": "example.com",
        "job_titles": ["CEO", "Founder"]
    })

    assert "content" in result
    assert not result.get("isError", False)


@pytest.mark.asyncio
async def test_find_leads_returns_enriched_leads():
    """find_leads should return enriched leads with emails."""
    mock_apollo = AsyncMock()
    mock_apollo.find_leads_at_company = AsyncMock(return_value=[
        {"email": "john@example.com", "first_name": "John", "last_name": "Doe",
         "company": "Example Inc", "title": "CEO", "linkedin_url": "https://linkedin.com/in/john"}
    ])

    from src.discovery.mcp_tools import create_apollo_mcp_server, get_apollo_handlers
    server = create_apollo_mcp_server(apollo_client=mock_apollo)

    handlers = get_apollo_handlers()
    result = await handlers["find_leads"]({
        "domain": "example.com",
        "job_titles": ["CEO"],
        "limit": 1
    })

    assert "content" in result
    assert not result.get("isError", False)


# =============================================================================
# FB Ads Tests
# =============================================================================


@pytest.mark.asyncio
async def test_search_advertisers_tool_returns_companies():
    """search_advertisers tool should return list of companies."""
    mock_fb_ads = AsyncMock()
    mock_fb_ads.get_advertiser_domains = AsyncMock(return_value=[
        {"domain": "example.com", "page_id": "123", "company_name": "Example Inc"}
    ])

    from src.discovery.mcp_tools import create_fb_ads_mcp_server, get_fb_ads_handlers
    server = create_fb_ads_mcp_server(fb_ads_client=mock_fb_ads)

    handlers = get_fb_ads_handlers()
    result = await handlers["search_advertisers"]({"keyword": "test", "country": "US"})

    assert "content" in result
    assert not result.get("isError", False)


# =============================================================================
# Supabase Tests
# =============================================================================


@pytest.mark.asyncio
async def test_check_company_searched_returns_bool():
    """check_company_searched should return boolean."""
    mock_client = MagicMock()
    mock_client.check_company_searched.return_value = False

    from src.discovery.mcp_tools import create_supabase_mcp_server, get_supabase_handlers
    server = create_supabase_mcp_server(supabase_client=mock_client)

    handlers = get_supabase_handlers()
    result = await handlers["check_company_searched"]({"domain": "example.com"})

    assert "content" in result
    assert not result.get("isError", False)


@pytest.mark.asyncio
async def test_get_quota_status_returns_stats():
    """get_quota_status should return quota information."""
    mock_client = MagicMock()
    mock_client.get_quota_status.return_value = {
        "leads_today": 5,
        "target": 10,
        "remaining": 5,
        "quota_met": False,
    }

    from src.discovery.mcp_tools import create_supabase_mcp_server, get_supabase_handlers
    server = create_supabase_mcp_server(supabase_client=mock_client)

    handlers = get_supabase_handlers()
    result = await handlers["get_quota_status"]({"daily_target": 10})

    assert "content" in result
    assert not result.get("isError", False)


# =============================================================================
# Web Tests
# =============================================================================


@pytest.mark.asyncio
async def test_fetch_company_page_returns_content():
    """fetch_company_page should return page content as markdown."""
    with patch("src.discovery.mcp_tools.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "<html><body><h1>Test Company</h1><p>We sell widgets.</p></body></html>"
        mock_response.status_code = 200
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        from src.discovery.mcp_tools import create_web_mcp_server, get_web_handlers
        server = create_web_mcp_server()

        handlers = get_web_handlers()
        result = await handlers["fetch_company_page"]({"url": "https://example.com"})

        assert "content" in result
        assert not result.get("isError", False)
