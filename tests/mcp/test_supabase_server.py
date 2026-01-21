# tests/mcp/test_supabase_server.py
"""Tests for Supabase MCP server."""

import pytest
from unittest.mock import MagicMock


@pytest.mark.asyncio
async def test_check_company_searched_returns_bool():
    """check_company_searched should return boolean."""
    mock_client = MagicMock()
    mock_client.check_company_searched.return_value = False

    from src.mcp_servers.supabase_server import create_supabase_mcp_server, get_tool_handlers
    server = create_supabase_mcp_server(supabase_client=mock_client)

    handlers = get_tool_handlers()
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

    from src.mcp_servers.supabase_server import create_supabase_mcp_server, get_tool_handlers
    server = create_supabase_mcp_server(supabase_client=mock_client)

    handlers = get_tool_handlers()
    result = await handlers["get_quota_status"]({"daily_target": 10})

    assert "content" in result
    assert not result.get("isError", False)
