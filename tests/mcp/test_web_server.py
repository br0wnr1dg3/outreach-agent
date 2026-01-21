# tests/mcp/test_web_server.py
"""Tests for Web MCP server."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_fetch_company_page_returns_content():
    """fetch_company_page should return page content as markdown."""
    with patch("src.mcp_servers.web_server.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "<html><body><h1>Test Company</h1><p>We sell widgets.</p></body></html>"
        mock_response.status_code = 200
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        from src.mcp_servers.web_server import create_web_mcp_server, get_tool_handlers
        server = create_web_mcp_server()

        handlers = get_tool_handlers()
        result = await handlers["fetch_company_page"]({"url": "https://example.com"})

        assert "content" in result
        assert not result.get("isError", False)
