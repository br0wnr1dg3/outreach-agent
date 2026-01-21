# src/mcp_servers/fb_ads_server.py
"""FB Ads operations as MCP server for Claude Agent SDK.

Tools:
- search_advertisers: Search FB Ad Library for companies by keyword
"""

import json
from typing import Any, Optional

from claude_agent_sdk import SdkMcpTool, McpSdkServerConfig, create_sdk_mcp_server
import structlog

from src import fb_ads

log = structlog.get_logger()

# Module-level storage for tool handlers (for testing access)
_tool_handlers: dict[str, Any] = {}


def get_tool_handlers() -> dict[str, Any]:
    """Get the current tool handlers for testing."""
    return _tool_handlers


class FbAdsClient:
    """Wrapper for FB Ads module functions."""

    async def get_advertiser_domains(
        self,
        keyword: str,
        country: str = "US",
        status: str = "ACTIVE",
        limit: int = 50,
    ) -> list[dict]:
        """Search FB Ad Library and return unique advertiser domains."""
        return await fb_ads.get_advertiser_domains(keyword, country, status, limit)


def create_fb_ads_mcp_server(
    fb_ads_client: Optional[FbAdsClient] = None,
) -> McpSdkServerConfig:
    """Create an MCP server with FB Ads tools.

    Args:
        fb_ads_client: Optional client instance for testing.

    Returns:
        McpSdkServerConfig for the MCP server.
    """
    global _tool_handlers

    if fb_ads_client is None:
        fb_ads_client = FbAdsClient()

    async def search_advertisers_handler(args: dict[str, Any]) -> dict[str, Any]:
        """Search FB Ad Library for advertisers by keyword.

        Args:
            args: Dict with keys:
                - keyword (str): Search keyword
                - country (str, optional): Country code (default: US)
                - status (str, optional): Ad status (default: ACTIVE)
                - limit (int, optional): Max results (default: 50)

        Returns:
            MCP-compliant response with advertiser domains.
        """
        keyword = args.get("keyword")
        if not keyword:
            return {
                "content": [{"type": "text", "text": json.dumps({"error": "keyword is required"})}],
                "isError": True,
            }

        country = args.get("country", "US")
        status = args.get("status", "ACTIVE")
        limit = args.get("limit", 50)

        try:
            companies = await fb_ads_client.get_advertiser_domains(
                keyword=keyword,
                country=country,
                status=status,
                limit=limit,
            )

            result = {
                "companies": companies,
                "count": len(companies),
                "keyword": keyword,
                "country": country,
            }
            return {"content": [{"type": "text", "text": json.dumps(result)}]}

        except Exception as e:
            log.error("fb_ads_search_error", error=str(e), keyword=keyword)
            return {
                "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                "isError": True,
            }

    # Store handlers for testing
    _tool_handlers = {
        "search_advertisers": search_advertisers_handler,
    }

    # Create tool definitions
    search_advertisers_tool = SdkMcpTool(
        name="search_advertisers",
        description="Search Facebook Ad Library for active advertisers by keyword. Returns unique company domains.",
        input_schema={
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Search keyword (e.g., 'collagen supplement', 'beauty DTC')",
                },
                "country": {
                    "type": "string",
                    "description": "Country code (default: US)",
                    "default": "US",
                },
                "status": {
                    "type": "string",
                    "description": "Ad status filter (default: ACTIVE)",
                    "default": "ACTIVE",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results (default: 50)",
                    "default": 50,
                },
            },
            "required": ["keyword"],
        },
        handler=search_advertisers_handler,
    )

    return create_sdk_mcp_server(
        name="fb_ads",
        version="1.0.0",
        tools=[search_advertisers_tool],
    )
