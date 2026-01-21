# src/mcp_servers/supabase_server.py
"""Supabase operations as MCP server for Claude Agent SDK.

Tools:
- check_company_searched: Check if domain already searched
- mark_company_searched: Mark domain as searched with results
- insert_lead: Insert a new lead
- get_daily_stats: Get today's statistics
- get_quota_status: Check if daily quota met
"""

import json
from typing import Any, Optional

from claude_agent_sdk import SdkMcpTool, McpSdkServerConfig, create_sdk_mcp_server
import structlog

from src.supabase_client import SupabaseClient

log = structlog.get_logger()

_tool_handlers: dict[str, Any] = {}


def get_tool_handlers() -> dict[str, Any]:
    """Get the current tool handlers for testing."""
    return _tool_handlers


def create_supabase_mcp_server(
    supabase_client: Optional[SupabaseClient] = None,
) -> McpSdkServerConfig:
    """Create an MCP server with Supabase tools.

    Args:
        supabase_client: Optional client instance for testing.

    Returns:
        McpSdkServerConfig for the MCP server.
    """
    global _tool_handlers

    if supabase_client is None:
        supabase_client = SupabaseClient()

    async def check_company_searched_handler(args: dict[str, Any]) -> dict[str, Any]:
        """Check if a company domain has already been searched."""
        domain = args.get("domain")
        if not domain:
            return {
                "content": [{"type": "text", "text": json.dumps({"error": "domain is required"})}],
                "isError": True,
            }

        try:
            searched = supabase_client.check_company_searched(domain)
            result = {"domain": domain, "already_searched": searched}
            return {"content": [{"type": "text", "text": json.dumps(result)}]}
        except Exception as e:
            return {
                "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                "isError": True,
            }

    async def mark_company_searched_handler(args: dict[str, Any]) -> dict[str, Any]:
        """Mark a company as searched with gate results."""
        domain = args.get("domain")
        if not domain:
            return {
                "content": [{"type": "text", "text": json.dumps({"error": "domain is required"})}],
                "isError": True,
            }

        try:
            company = supabase_client.mark_company_searched(
                domain=domain,
                company_name=args.get("company_name"),
                source_keyword=args.get("source_keyword"),
                passed_gate_1=args.get("passed_gate_1"),
                passed_gate_2=args.get("passed_gate_2"),
                fit_score=args.get("fit_score"),
                fit_notes=args.get("fit_notes"),
            )
            result = {"success": True, "domain": domain}
            return {"content": [{"type": "text", "text": json.dumps(result)}]}
        except Exception as e:
            return {
                "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                "isError": True,
            }

    async def insert_lead_handler(args: dict[str, Any]) -> dict[str, Any]:
        """Insert a new lead into the database."""
        email = args.get("email")
        first_name = args.get("first_name")

        if not email or not first_name:
            return {
                "content": [{"type": "text", "text": json.dumps({"error": "email and first_name are required"})}],
                "isError": True,
            }

        try:
            lead = supabase_client.insert_lead(
                email=email,
                first_name=first_name,
                last_name=args.get("last_name"),
                company=args.get("company"),
                title=args.get("title"),
                linkedin_url=args.get("linkedin_url"),
                source="agent",
                source_keyword=args.get("source_keyword"),
                company_fit_score=args.get("company_fit_score"),
                company_fit_notes=args.get("company_fit_notes"),
            )

            if lead:
                result = {"success": True, "lead_id": lead.id, "email": email}
            else:
                result = {"success": False, "reason": "duplicate", "email": email}

            return {"content": [{"type": "text", "text": json.dumps(result)}]}
        except Exception as e:
            return {
                "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                "isError": True,
            }

    async def get_daily_stats_handler(args: dict[str, Any]) -> dict[str, Any]:
        """Get today's statistics."""
        try:
            stats = supabase_client.get_daily_stats()
            return {"content": [{"type": "text", "text": json.dumps(stats)}]}
        except Exception as e:
            return {
                "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                "isError": True,
            }

    async def get_quota_status_handler(args: dict[str, Any]) -> dict[str, Any]:
        """Check if daily quota is met."""
        daily_target = args.get("daily_target", 10)

        try:
            status = supabase_client.get_quota_status(daily_target)
            return {"content": [{"type": "text", "text": json.dumps(status)}]}
        except Exception as e:
            return {
                "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                "isError": True,
            }

    _tool_handlers = {
        "check_company_searched": check_company_searched_handler,
        "mark_company_searched": mark_company_searched_handler,
        "insert_lead": insert_lead_handler,
        "get_daily_stats": get_daily_stats_handler,
        "get_quota_status": get_quota_status_handler,
    }

    # Tool definitions
    tools = [
        SdkMcpTool(
            name="check_company_searched",
            description="Check if a company domain has already been searched",
            input_schema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Company domain to check"},
                },
                "required": ["domain"],
            },
            handler=check_company_searched_handler,
        ),
        SdkMcpTool(
            name="mark_company_searched",
            description="Mark a company as searched with gate results and fit notes",
            input_schema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Company domain"},
                    "company_name": {"type": "string", "description": "Company name"},
                    "source_keyword": {"type": "string", "description": "Search keyword that found this company"},
                    "passed_gate_1": {"type": "boolean", "description": "Whether company passed Gate 1 (has contacts)"},
                    "passed_gate_2": {"type": "boolean", "description": "Whether company passed Gate 2 (ICP fit)"},
                    "fit_score": {"type": "integer", "description": "ICP fit score 1-10"},
                    "fit_notes": {"type": "string", "description": "Notes about why company does/doesn't fit ICP"},
                },
                "required": ["domain"],
            },
            handler=mark_company_searched_handler,
        ),
        SdkMcpTool(
            name="insert_lead",
            description="Insert a new lead into the database",
            input_schema={
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "Lead email address"},
                    "first_name": {"type": "string", "description": "First name"},
                    "last_name": {"type": "string", "description": "Last name"},
                    "company": {"type": "string", "description": "Company name"},
                    "title": {"type": "string", "description": "Job title"},
                    "linkedin_url": {"type": "string", "description": "LinkedIn profile URL"},
                    "source_keyword": {"type": "string", "description": "Search keyword that found this lead"},
                    "company_fit_score": {"type": "integer", "description": "ICP fit score 1-10"},
                    "company_fit_notes": {"type": "string", "description": "ICP fit notes"},
                },
                "required": ["email", "first_name"],
            },
            handler=insert_lead_handler,
        ),
        SdkMcpTool(
            name="get_daily_stats",
            description="Get today's lead generation statistics",
            input_schema={"type": "object", "properties": {}, "required": []},
            handler=get_daily_stats_handler,
        ),
        SdkMcpTool(
            name="get_quota_status",
            description="Check if daily quota is met and how many leads remaining",
            input_schema={
                "type": "object",
                "properties": {
                    "daily_target": {"type": "integer", "description": "Daily target (default: 10)", "default": 10},
                },
                "required": [],
            },
            handler=get_quota_status_handler,
        ),
    ]

    return create_sdk_mcp_server(
        name="supabase",
        version="1.0.0",
        tools=tools,
    )
