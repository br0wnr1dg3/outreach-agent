# tests/mcp/test_fb_ads_server.py
"""Tests for FB Ads MCP server."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_search_advertisers_tool_returns_companies():
    """search_advertisers tool should return list of companies."""
    mock_fb_ads = AsyncMock()
    mock_fb_ads.get_advertiser_domains = AsyncMock(return_value=[
        {"domain": "example.com", "page_id": "123", "company_name": "Example Inc"}
    ])

    from src.mcp_servers.fb_ads_server import create_fb_ads_mcp_server, get_tool_handlers
    server = create_fb_ads_mcp_server(fb_ads_client=mock_fb_ads)

    handlers = get_tool_handlers()
    result = await handlers["search_advertisers"]({"keyword": "test", "country": "US"})

    assert "content" in result
    assert not result.get("isError", False)
