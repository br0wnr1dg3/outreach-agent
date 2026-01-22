"""Consolidated MCP tools for discovery agent.

Combines tools from:
- Apollo: check_company_contacts, find_leads
- FB Ads: search_advertisers
- Supabase: check_company_searched, mark_company_searched, insert_lead, get_daily_stats, get_quota_status
- Web: fetch_company_page
"""

import json
import re
from html.parser import HTMLParser
from typing import Any, Optional

import httpx
from claude_agent_sdk import SdkMcpTool, McpSdkServerConfig, create_sdk_mcp_server
import structlog

from src.clients import apollo, fb_ads
from src.clients.supabase import SupabaseClient
from src.core.db import (
    DEFAULT_DB_PATH,
    init_db,
    is_company_searched,
    insert_searched_company,
    insert_lead,
    get_daily_stats,
    get_quota_status,
)

log = structlog.get_logger()

# Tool handlers for testing access
_apollo_handlers: dict[str, Any] = {}
_fb_ads_handlers: dict[str, Any] = {}
_supabase_handlers: dict[str, Any] = {}
_web_handlers: dict[str, Any] = {}


def get_apollo_handlers() -> dict[str, Any]:
    """Get Apollo tool handlers for testing."""
    return _apollo_handlers


def get_fb_ads_handlers() -> dict[str, Any]:
    """Get FB Ads tool handlers for testing."""
    return _fb_ads_handlers


def get_supabase_handlers() -> dict[str, Any]:
    """Get Supabase tool handlers for testing."""
    return _supabase_handlers


def get_web_handlers() -> dict[str, Any]:
    """Get Web tool handlers for testing."""
    return _web_handlers


# =============================================================================
# HTML to Markdown converter (for web fetching)
# =============================================================================


class SimpleHTMLToMarkdown(HTMLParser):
    """Simple HTML to Markdown converter."""

    def __init__(self):
        super().__init__()
        self.result = []
        self.current_tag = None
        self.skip_content = False

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        if tag in ('script', 'style', 'nav', 'footer', 'header'):
            self.skip_content = True
        elif tag == 'h1':
            self.result.append('\n# ')
        elif tag == 'h2':
            self.result.append('\n## ')
        elif tag == 'h3':
            self.result.append('\n### ')
        elif tag == 'p':
            self.result.append('\n\n')
        elif tag == 'li':
            self.result.append('\n- ')
        elif tag == 'a':
            href = dict(attrs).get('href', '')
            if href and not href.startswith('#'):
                self.result.append('[')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'nav', 'footer', 'header'):
            self.skip_content = False
        elif tag in ('h1', 'h2', 'h3'):
            self.result.append('\n')
        self.current_tag = None

    def handle_data(self, data):
        if not self.skip_content:
            text = data.strip()
            if text:
                self.result.append(text + ' ')

    def get_markdown(self) -> str:
        text = ''.join(self.result)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        return text.strip()


def html_to_markdown(html: str) -> str:
    """Convert HTML to simple markdown."""
    parser = SimpleHTMLToMarkdown()
    parser.feed(html)
    return parser.get_markdown()


# =============================================================================
# Apollo Client Wrapper
# =============================================================================


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


# =============================================================================
# FB Ads Client Wrapper
# =============================================================================


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


# =============================================================================
# MCP Server Creators
# =============================================================================


def create_apollo_mcp_server(
    apollo_client: Optional[ApolloClient] = None,
) -> McpSdkServerConfig:
    """Create MCP server with Apollo tools."""
    global _apollo_handlers

    if apollo_client is None:
        apollo_client = ApolloClient()

    async def check_company_contacts_handler(args: dict[str, Any]) -> dict[str, Any]:
        """Quick check if decision-makers exist at a company (Gate 1)."""
        domain = args.get("domain")
        job_titles = args.get("job_titles", [])

        if not domain:
            return {
                "content": [{"type": "text", "text": json.dumps({"error": "domain is required"})}],
                "isError": True,
            }

        try:
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
        """Find and enrich leads at a company."""
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
            result = {"domain": domain, "leads": leads, "count": len(leads)}
            return {"content": [{"type": "text", "text": json.dumps(result)}]}
        except Exception as e:
            log.error("apollo_find_error", error=str(e), domain=domain)
            return {
                "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                "isError": True,
            }

    _apollo_handlers = {
        "check_company_contacts": check_company_contacts_handler,
        "find_leads": find_leads_handler,
    }

    tools = [
        SdkMcpTool(
            name="check_company_contacts",
            description="Quick check if decision-makers exist at a company (Gate 1). Cheaper than full enrichment.",
            input_schema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Company domain (e.g., 'acme.com')"},
                    "job_titles": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Job titles to search for",
                    },
                },
                "required": ["domain", "job_titles"],
            },
            handler=check_company_contacts_handler,
        ),
        SdkMcpTool(
            name="find_leads",
            description="Find and enrich leads at a company to get email addresses. Use after Gate 1 and Gate 2 pass.",
            input_schema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Company domain"},
                    "job_titles": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Job titles to search for, in priority order",
                    },
                    "limit": {"type": "integer", "description": "Maximum leads to return (default: 1)", "default": 1},
                },
                "required": ["domain", "job_titles"],
            },
            handler=find_leads_handler,
        ),
    ]

    return create_sdk_mcp_server(name="apollo", version="1.0.0", tools=tools)


def create_fb_ads_mcp_server(
    fb_ads_client: Optional[FbAdsClient] = None,
) -> McpSdkServerConfig:
    """Create MCP server with FB Ads tools."""
    global _fb_ads_handlers

    if fb_ads_client is None:
        fb_ads_client = FbAdsClient()

    async def search_advertisers_handler(args: dict[str, Any]) -> dict[str, Any]:
        """Search FB Ad Library for advertisers by keyword."""
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
                keyword=keyword, country=country, status=status, limit=limit
            )
            result = {"companies": companies, "count": len(companies), "keyword": keyword, "country": country}
            return {"content": [{"type": "text", "text": json.dumps(result)}]}
        except Exception as e:
            log.error("fb_ads_search_error", error=str(e), keyword=keyword)
            return {
                "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                "isError": True,
            }

    _fb_ads_handlers = {"search_advertisers": search_advertisers_handler}

    tools = [
        SdkMcpTool(
            name="search_advertisers",
            description="Search Facebook Ad Library for active advertisers by keyword. Returns unique company domains.",
            input_schema={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Search keyword"},
                    "country": {"type": "string", "description": "Country code (default: US)", "default": "US"},
                    "status": {"type": "string", "description": "Ad status filter (default: ACTIVE)", "default": "ACTIVE"},
                    "limit": {"type": "integer", "description": "Maximum results (default: 50)", "default": 50},
                },
                "required": ["keyword"],
            },
            handler=search_advertisers_handler,
        ),
    ]

    return create_sdk_mcp_server(name="fb_ads", version="1.0.0", tools=tools)


def create_supabase_mcp_server(
    supabase_client: Optional[SupabaseClient] = None,
) -> McpSdkServerConfig:
    """Create MCP server with Supabase tools."""
    global _supabase_handlers

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
            supabase_client.mark_company_searched(
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

    _supabase_handlers = {
        "check_company_searched": check_company_searched_handler,
        "mark_company_searched": mark_company_searched_handler,
        "insert_lead": insert_lead_handler,
        "get_daily_stats": get_daily_stats_handler,
        "get_quota_status": get_quota_status_handler,
    }

    tools = [
        SdkMcpTool(
            name="check_company_searched",
            description="Check if a company domain has already been searched",
            input_schema={
                "type": "object",
                "properties": {"domain": {"type": "string", "description": "Company domain to check"}},
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
                    "passed_gate_1": {"type": "boolean", "description": "Whether company passed Gate 1"},
                    "passed_gate_2": {"type": "boolean", "description": "Whether company passed Gate 2"},
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
                "properties": {"daily_target": {"type": "integer", "description": "Daily target (default: 10)", "default": 10}},
                "required": [],
            },
            handler=get_quota_status_handler,
        ),
    ]

    return create_sdk_mcp_server(name="supabase", version="1.0.0", tools=tools)


# SQLite handlers for testing
_sqlite_handlers: dict[str, Any] = {}


def get_sqlite_handlers() -> dict[str, Any]:
    """Get SQLite tool handlers for testing."""
    return _sqlite_handlers


def create_sqlite_mcp_server() -> McpSdkServerConfig:
    """Create MCP server with SQLite tools (local alternative to Supabase)."""
    global _sqlite_handlers

    # Ensure database exists
    init_db(DEFAULT_DB_PATH)

    async def check_company_searched_handler(args: dict[str, Any]) -> dict[str, Any]:
        """Check if a company domain has already been searched."""
        domain = args.get("domain")
        if not domain:
            return {
                "content": [{"type": "text", "text": json.dumps({"error": "domain is required"})}],
                "isError": True,
            }
        try:
            searched = is_company_searched(DEFAULT_DB_PATH, domain)
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
            insert_searched_company(
                db_path=DEFAULT_DB_PATH,
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
            lead_id = insert_lead(
                db_path=DEFAULT_DB_PATH,
                email=email,
                first_name=first_name,
                last_name=args.get("last_name"),
                company=args.get("company"),
                title=args.get("title"),
                linkedin_url=args.get("linkedin_url"),
            )
            if lead_id:
                result = {"success": True, "lead_id": lead_id, "email": email}
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
            stats = get_daily_stats(DEFAULT_DB_PATH)
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
            status = get_quota_status(DEFAULT_DB_PATH, daily_target)
            return {"content": [{"type": "text", "text": json.dumps(status)}]}
        except Exception as e:
            return {
                "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                "isError": True,
            }

    _sqlite_handlers = {
        "check_company_searched": check_company_searched_handler,
        "mark_company_searched": mark_company_searched_handler,
        "insert_lead": insert_lead_handler,
        "get_daily_stats": get_daily_stats_handler,
        "get_quota_status": get_quota_status_handler,
    }

    tools = [
        SdkMcpTool(
            name="check_company_searched",
            description="Check if a company domain has already been searched",
            input_schema={
                "type": "object",
                "properties": {"domain": {"type": "string", "description": "Company domain to check"}},
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
                    "passed_gate_1": {"type": "boolean", "description": "Whether company passed Gate 1"},
                    "passed_gate_2": {"type": "boolean", "description": "Whether company passed Gate 2"},
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
                "properties": {"daily_target": {"type": "integer", "description": "Daily target (default: 10)", "default": 10}},
                "required": [],
            },
            handler=get_quota_status_handler,
        ),
    ]

    return create_sdk_mcp_server(name="sqlite", version="1.0.0", tools=tools)


def create_web_mcp_server() -> McpSdkServerConfig:
    """Create MCP server with web fetching tools."""
    global _web_handlers

    async def fetch_company_page_handler(args: dict[str, Any]) -> dict[str, Any]:
        """Fetch company website and return as markdown (Gate 2)."""
        url = args.get("url")
        if not url:
            return {
                "content": [{"type": "text", "text": json.dumps({"error": "url is required"})}],
                "isError": True,
            }

        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; OutreachBot/1.0)"},
                )

                if response.status_code != 200:
                    return {
                        "content": [{"type": "text", "text": json.dumps({"error": f"HTTP {response.status_code}", "url": url})}],
                        "isError": True,
                    }

                html = response.text
                markdown = html_to_markdown(html)

                if len(markdown) > 8000:
                    markdown = markdown[:8000] + "\n\n[Content truncated...]"

                result = {"url": url, "content": markdown, "content_length": len(markdown)}
                return {"content": [{"type": "text", "text": json.dumps(result)}]}

        except httpx.TimeoutException:
            return {
                "content": [{"type": "text", "text": json.dumps({"error": "Timeout", "url": url})}],
                "isError": True,
            }
        except Exception as e:
            log.error("web_fetch_error", error=str(e), url=url)
            return {
                "content": [{"type": "text", "text": json.dumps({"error": str(e), "url": url})}],
                "isError": True,
            }

    _web_handlers = {"fetch_company_page": fetch_company_page_handler}

    tools = [
        SdkMcpTool(
            name="fetch_company_page",
            description="Fetch company website and convert to markdown for ICP analysis (Gate 2)",
            input_schema={
                "type": "object",
                "properties": {"url": {"type": "string", "description": "Company website URL"}},
                "required": ["url"],
            },
            handler=fetch_company_page_handler,
        ),
    ]

    return create_sdk_mcp_server(name="web", version="1.0.0", tools=tools)
