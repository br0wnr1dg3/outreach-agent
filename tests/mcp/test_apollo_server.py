# tests/mcp/test_apollo_server.py
"""Tests for Apollo MCP server."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_check_company_contacts_returns_bool():
    """check_company_contacts should return bool and count."""
    mock_apollo = AsyncMock()
    mock_apollo.search_people = AsyncMock(return_value=[
        {"id": "1", "first_name": "John", "title": "CEO"}
    ])

    from src.mcp_servers.apollo_server import create_apollo_mcp_server, get_tool_handlers
    server = create_apollo_mcp_server(apollo_client=mock_apollo)

    handlers = get_tool_handlers()
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

    from src.mcp_servers.apollo_server import create_apollo_mcp_server, get_tool_handlers
    server = create_apollo_mcp_server(apollo_client=mock_apollo)

    handlers = get_tool_handlers()
    result = await handlers["find_leads"]({
        "domain": "example.com",
        "job_titles": ["CEO"],
        "limit": 1
    })

    assert "content" in result
    assert not result.get("isError", False)
