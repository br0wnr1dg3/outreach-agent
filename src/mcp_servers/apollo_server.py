# src/mcp_servers/apollo_server.py
"""Apollo operations as MCP server for Claude Agent SDK.

Tools:
- check_company_contacts: Quick check if contacts exist at domain
- find_leads: Full enrichment to get leads with emails
"""

import json
from typing import Any, Optional

from claude_agent_sdk import SdkMcpTool, McpSdkServerConfig, create_sdk_mcp_server
import structlog

from src import apollo

log = structlog.get_logger()

_tool_handlers: dict[str, Any] = {}


def get_tool_handlers() -> dict[str, Any]:
    """Get the current tool handlers for testing."""
    return _tool_handlers


class ApolloClient:
    """Wrapper for Apollo module functions."""

    async def search_people(
        self,
        domain: str,
        job_titles: list[str],
        limit: int = 10,
    ) -> list[dict]:
        """Search for people at a company."""
        return await apollo.search_people(domain, job_titles, limit)

    async def find_leads_at_company(
        self,
        domain: str,
        job_titles: list[str],
        max_leads: int = 3,
    ) -> list[dict]:
        """Find and enrich leads at a company."""
        return await apollo.find_leads_at_company(domain, job_titles, max_leads)


def create_apollo_mcp_server(
    apollo_client: Optional[ApolloClient] = None,
) -> McpSdkServerConfig:
    """Create an MCP server with Apollo tools.

    Args:
        apollo_client: Optional client instance for testing.

    Returns:
        McpSdkServerConfig for the MCP server.
    """
    global _tool_handlers

    if apollo_client is None:
        apollo_client = ApolloClient()

    async def check_company_contacts_handler(args: dict[str, Any]) -> dict[str, Any]:
        """Quick check if decision-makers exist at a company.

        This is Gate 1 - a cheap check before expensive website analysis.

        Args:
            args: Dict with keys:
                - domain (str): Company domain
                - job_titles (list[str]): Job titles to search for

        Returns:
            MCP response with has_contacts bool and count.
        """
        domain = args.get("domain")
        job_titles = args.get("job_titles", [])

        if not domain:
            return {
                "content": [{"type": "text", "text": json.dumps({"error": "domain is required"})}],
                "isError": True,
            }

        try:
            # Quick search without enrichment
            people = await apollo_client.search_people(domain, job_titles, limit=5)

            result = {
                "domain": domain,
                "has_contacts": len(people) > 0,
                "contact_count": len(people),
                "sample_titles": [p.get("title") for p in people[:3] if p.get("title")],
            }
            return {"content": [{"type": "text", "text": json.dumps(result)}]}

        except Exception as e:
            log.error("apollo_check_error", error=str(e), domain=domain)
            return {
                "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                "isError": True,
            }

    async def find_leads_handler(args: dict[str, Any]) -> dict[str, Any]:
        """Find and enrich leads at a company.

        Full enrichment to get email addresses. Use after Gate 1 and Gate 2 pass.

        Args:
            args: Dict with keys:
                - domain (str): Company domain
                - job_titles (list[str]): Job titles to search for
                - limit (int, optional): Max leads (default: 1)

        Returns:
            MCP response with enriched leads.
        """
        domain = args.get("domain")
        job_titles = args.get("job_titles", [])
        limit = args.get("limit", 1)

        if not domain:
            return {
                "content": [{"type": "text", "text": json.dumps({"error": "domain is required"})}],
                "isError": True,
            }

        try:
            leads = await apollo_client.find_leads_at_company(domain, job_titles, limit)

            result = {
                "domain": domain,
                "leads": leads,
                "count": len(leads),
            }
            return {"content": [{"type": "text", "text": json.dumps(result)}]}

        except Exception as e:
            log.error("apollo_find_error", error=str(e), domain=domain)
            return {
                "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                "isError": True,
            }

    _tool_handlers = {
        "check_company_contacts": check_company_contacts_handler,
        "find_leads": find_leads_handler,
    }

    check_contacts_tool = SdkMcpTool(
        name="check_company_contacts",
        description="Quick check if decision-makers exist at a company (Gate 1). Cheaper than full enrichment.",
        input_schema={
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Company domain (e.g., 'acme.com')",
                },
                "job_titles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Job titles to search for (e.g., ['CMO', 'VP Marketing', 'Founder'])",
                },
            },
            "required": ["domain", "job_titles"],
        },
        handler=check_company_contacts_handler,
    )

    find_leads_tool = SdkMcpTool(
        name="find_leads",
        description="Find and enrich leads at a company to get email addresses. Use after company passes Gate 1 and Gate 2.",
        input_schema={
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Company domain",
                },
                "job_titles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Job titles to search for, in priority order",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum leads to return (default: 1)",
                    "default": 1,
                },
            },
            "required": ["domain", "job_titles"],
        },
        handler=find_leads_handler,
    )

    return create_sdk_mcp_server(
        name="apollo",
        version="1.0.0",
        tools=[check_contacts_tool, find_leads_tool],
    )
