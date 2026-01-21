# Project Reorganization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reorganize project structure by business domain, consolidate MCP servers and email templates, reduce file count.

**Architecture:** Move files into domain folders (core/, outreach/, discovery/, clients/, services/), consolidate 4 MCP server files into 1, merge 3 email templates into 1 with frontmatter.

**Tech Stack:** Python, Pydantic, Claude Agent SDK, pytest

---

## Task 1: Create Directory Structure

**Files:**
- Create: `src/core/__init__.py`
- Create: `src/outreach/__init__.py`
- Create: `src/discovery/__init__.py`
- Create: `src/clients/__init__.py`
- Create: `tests/core/__init__.py`
- Create: `tests/outreach/__init__.py`
- Create: `tests/discovery/__init__.py`
- Create: `tests/clients/__init__.py`
- Create: `tests/services/__init__.py`

**Step 1: Create all directories and __init__.py files**

```bash
mkdir -p src/core src/outreach src/discovery src/clients
mkdir -p tests/core tests/outreach tests/discovery tests/clients tests/services
touch src/core/__init__.py src/outreach/__init__.py src/discovery/__init__.py src/clients/__init__.py
touch tests/core/__init__.py tests/outreach/__init__.py tests/discovery/__init__.py tests/clients/__init__.py tests/services/__init__.py
```

**Step 2: Verify directories exist**

Run: `ls -la src/*/`
Expected: See __init__.py in each new directory

**Step 3: Commit**

```bash
git add src/core src/outreach src/discovery src/clients tests/core tests/outreach tests/discovery tests/clients tests/services
git commit -m "chore: create new directory structure for reorganization"
```

---

## Task 2: Move Core Files

**Files:**
- Move: `src/cli.py` → `src/core/cli.py`
- Move: `src/config.py` → `src/core/config.py`
- Move: `src/db.py` → `src/core/db.py`

**Step 1: Move files**

```bash
mv src/cli.py src/core/cli.py
mv src/config.py src/core/config.py
mv src/db.py src/core/db.py
```

**Step 2: Update src/core/__init__.py exports**

```python
"""Core infrastructure: CLI, config, database."""

from src.core.config import (
    Settings,
    SequenceConfig,
    SendingConfig,
    GmailConfig,
    LeadGenConfig,
    load_settings,
    load_template,
    render_template,
    load_lead_gen_config,
)
from src.core.db import (
    init_db,
    get_lead,
    get_leads_by_status,
    insert_lead,
    update_lead,
    Lead,
)
```

**Step 3: Verify files moved**

Run: `ls src/core/`
Expected: `__init__.py  cli.py  config.py  db.py`

**Step 4: Commit**

```bash
git add -A
git commit -m "refactor: move core files to src/core/"
```

---

## Task 3: Move Client Files

**Files:**
- Move: `src/apollo.py` → `src/clients/apollo.py`
- Move: `src/fb_ads.py` → `src/clients/fb_ads.py`
- Move: `src/supabase_client.py` → `src/clients/supabase.py`

**Step 1: Move files**

```bash
mv src/apollo.py src/clients/apollo.py
mv src/fb_ads.py src/clients/fb_ads.py
mv src/supabase_client.py src/clients/supabase.py
```

**Step 2: Update src/clients/__init__.py exports**

```python
"""External API clients: Apollo, FB Ads, Supabase."""

from src.clients.apollo import (
    search_people,
    enrich_people,
    find_leads_at_company,
)
from src.clients.fb_ads import (
    search_ads,
    get_advertiser_domains,
    extract_domain,
)
from src.clients.supabase import SupabaseClient
```

**Step 3: Verify files moved**

Run: `ls src/clients/`
Expected: `__init__.py  apollo.py  fb_ads.py  supabase.py`

**Step 4: Commit**

```bash
git add -A
git commit -m "refactor: move API clients to src/clients/"
```

---

## Task 4: Move Outreach Files

**Files:**
- Move: `src/importer.py` → `src/outreach/importer.py`
- Move: `src/enricher.py` → `src/outreach/enricher.py`
- Move: `src/composer.py` → `src/outreach/composer.py`
- Move: `src/sender.py` → `src/outreach/sender.py`
- Move: `src/scheduler.py` → `src/outreach/scheduler.py`

**Step 1: Move files**

```bash
mv src/importer.py src/outreach/importer.py
mv src/enricher.py src/outreach/enricher.py
mv src/composer.py src/outreach/composer.py
mv src/sender.py src/outreach/sender.py
mv src/scheduler.py src/outreach/scheduler.py
```

**Step 2: Update src/outreach/__init__.py exports**

```python
"""Email outreach pipeline: import, enrich, compose, send, schedule."""

from src.outreach.importer import import_leads_from_excel
from src.outreach.enricher import enrich_lead
from src.outreach.composer import generate_email_1
from src.outreach.sender import send_email, check_for_reply
from src.outreach.scheduler import run_send_cycle
```

**Step 3: Verify files moved**

Run: `ls src/outreach/`
Expected: `__init__.py  composer.py  enricher.py  importer.py  scheduler.py  sender.py`

**Step 4: Commit**

```bash
git add -A
git commit -m "refactor: move outreach pipeline to src/outreach/"
```

---

## Task 5: Move Discovery Files and Consolidate MCP Tools

**Files:**
- Move: `src/agents/discovery_agent.py` → `src/discovery/agent.py`
- Move: `src/lead_generator.py` → `src/discovery/lead_generator.py`
- Create: `src/discovery/mcp_tools.py` (consolidated from 4 MCP server files)
- Delete: `src/mcp_servers/` folder
- Delete: `src/agents/` folder

**Step 1: Move discovery_agent.py and lead_generator.py**

```bash
mv src/agents/discovery_agent.py src/discovery/agent.py
mv src/lead_generator.py src/discovery/lead_generator.py
```

**Step 2: Create consolidated mcp_tools.py**

Create `src/discovery/mcp_tools.py` with all MCP tool definitions:

```python
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
```

**Step 3: Update src/discovery/__init__.py**

```python
"""Lead discovery pipeline: agent, lead generator, MCP tools."""

from src.discovery.mcp_tools import (
    create_apollo_mcp_server,
    create_fb_ads_mcp_server,
    create_supabase_mcp_server,
    create_web_mcp_server,
    get_apollo_handlers,
    get_fb_ads_handlers,
    get_supabase_handlers,
    get_web_handlers,
)
```

**Step 4: Delete old mcp_servers and agents folders**

```bash
rm -rf src/mcp_servers
rm -rf src/agents
```

**Step 5: Verify structure**

Run: `ls src/discovery/`
Expected: `__init__.py  agent.py  lead_generator.py  mcp_tools.py`

**Step 6: Commit**

```bash
git add -A
git commit -m "refactor: move discovery files and consolidate MCP tools"
```

---

## Task 6: Consolidate Email Templates

**Files:**
- Create: `config/templates.md` (consolidated from 3 files)
- Delete: `config/email_1.md`
- Delete: `config/followup_1.md`
- Delete: `config/followup_2.md`

**Step 1: Create consolidated templates.md**

```markdown
---
template: email_1
delay_days: 0
---

subject: {{generated_subject}}

Hey {{first_name}},

{{generated_joke_opener}}

Anyway, terrible jokes aside...

I'm researching how marketers leverage affiliates and creators to create a content machine for paid media campaigns. I'd love to ask your advice to help round out my research & can share some of what I've learned so far. Do you have 10min for a short interview in the next few days?

Chris

---
template: followup_1
delay_days: 3
---

subject: re: {{original_subject}}

Hey {{first_name}},

Following up on my own cold email. The audacity.

Genuinely curious if creator/affiliate stuff is on your radar or if I should take the hint.

Chris

---
template: followup_2
delay_days: 7
---

subject: re: {{original_subject}}

Hey {{first_name}},

Last one, I promise. After this I'll quietly accept defeat and move on with my life.

If timing's just bad, happy to reconnect later. If it's a "not interested" - totally get it, no hard feelings.

Chris
```

**Step 2: Delete old template files**

```bash
rm config/email_1.md config/followup_1.md config/followup_2.md
```

**Step 3: Verify config folder**

Run: `ls config/`
Expected: `context.md  lead_gen.yaml  settings.yaml  templates.md`

**Step 4: Commit**

```bash
git add -A
git commit -m "refactor: consolidate email templates into templates.md with frontmatter"
```

---

## Task 7: Add Seed Customers to lead_gen.yaml

**Files:**
- Modify: `config/lead_gen.yaml`

**Step 1: Add seed_customers section**

Add to end of `config/lead_gen.yaml`:

```yaml
# Seed customers for ICP analysis
seed_customers:
  - domain: "example1.com"
    name: "Example Company 1"
  - domain: "example2.com"
    name: "Example Company 2"
```

**Step 2: Commit**

```bash
git add config/lead_gen.yaml
git commit -m "feat: add seed_customers section to lead_gen.yaml"
```

---

## Task 8: Add Template Parser to config.py

**Files:**
- Modify: `src/core/config.py`

**Step 1: Add EmailTemplate model and load_templates function**

Add to `src/core/config.py`:

```python
import re

class EmailTemplate(BaseModel):
    """Email template with timing metadata."""
    name: str
    delay_days: int
    subject: str
    body: str


def load_templates(config_path: Path = DEFAULT_CONFIG_PATH) -> list[EmailTemplate]:
    """Load and parse templates.md into list of EmailTemplate objects."""
    templates_file = config_path / "templates.md"

    if not templates_file.exists():
        return []

    content = templates_file.read_text()

    # Split on frontmatter delimiters (---)
    sections = re.split(r'^---\s*$', content, flags=re.MULTILINE)

    templates = []
    # Process pairs of (frontmatter, body)
    i = 1
    while i < len(sections) - 1:
        frontmatter = sections[i].strip()
        body = sections[i + 1].strip()

        if not frontmatter:
            i += 2
            continue

        # Parse YAML frontmatter
        meta = yaml.safe_load(frontmatter)
        if not meta or "template" not in meta:
            i += 2
            continue

        # Extract subject from body
        lines = body.split('\n')
        subject = ""
        body_start = 0
        for idx, line in enumerate(lines):
            if line.startswith('subject:'):
                subject = line.replace('subject:', '').strip()
                body_start = idx + 1
                break

        body_content = '\n'.join(lines[body_start:]).strip()

        templates.append(EmailTemplate(
            name=meta["template"],
            delay_days=meta.get("delay_days", 0),
            subject=subject,
            body=body_content,
        ))

        i += 2

    return templates
```

**Step 2: Write failing test first**

Create `tests/core/test_config.py` (or add to existing):

```python
def test_load_templates():
    """Test loading templates from templates.md."""
    from src.core.config import load_templates

    templates = load_templates()

    assert len(templates) == 3
    assert templates[0].name == "email_1"
    assert templates[0].delay_days == 0
    assert "{{generated_subject}}" in templates[0].subject or templates[0].subject

    assert templates[1].name == "followup_1"
    assert templates[1].delay_days == 3

    assert templates[2].name == "followup_2"
    assert templates[2].delay_days == 7
```

**Step 3: Run test to verify it passes**

Run: `python -m pytest tests/core/test_config.py::test_load_templates -v`
Expected: PASS

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: add template parser for consolidated templates.md"
```

---

## Task 9: Update All Import Paths

**Files:**
- Modify: `run.py`
- Modify: `run_agent.py`
- Modify: `src/discovery/agent.py`
- Modify: `src/discovery/lead_generator.py`
- Modify: `src/outreach/scheduler.py`
- Modify: `src/outreach/composer.py`
- Modify: `src/outreach/sender.py`
- Modify: `src/outreach/enricher.py`
- Modify: `src/outreach/importer.py`
- Modify: `src/services/seed_analyzer.py`
- Modify: `src/services/slack_notifier.py`

**Step 1: Update run.py**

```python
# Before
from src.cli import cli

# After
from src.core.cli import cli
```

**Step 2: Update run_agent.py**

```python
# Before
from src.agents.discovery_agent import DiscoveryAgent

# After
from src.discovery.agent import DiscoveryAgent
```

**Step 3: Update src/discovery/agent.py**

```python
# Before
from src.mcp_servers.apollo_server import create_apollo_mcp_server
from src.mcp_servers.fb_ads_server import create_fb_ads_mcp_server
from src.mcp_servers.supabase_server import create_supabase_mcp_server
from src.mcp_servers.web_server import create_web_mcp_server
from src.config import load_lead_gen_config

# After
from src.discovery.mcp_tools import (
    create_apollo_mcp_server,
    create_fb_ads_mcp_server,
    create_supabase_mcp_server,
    create_web_mcp_server,
)
from src.core.config import load_lead_gen_config
```

**Step 4: Update src/discovery/lead_generator.py**

```python
# Before
from src import apollo, fb_ads
from src.supabase_client import SupabaseClient

# After
from src.clients import apollo, fb_ads
from src.clients.supabase import SupabaseClient
```

**Step 5: Update src/outreach/scheduler.py**

```python
# Before
from src.db import get_leads_by_status, update_lead
from src.composer import generate_email_1
from src.sender import send_email, check_for_reply
from src.config import load_settings

# After
from src.core.db import get_leads_by_status, update_lead
from src.outreach.composer import generate_email_1
from src.outreach.sender import send_email, check_for_reply
from src.core.config import load_settings
```

**Step 6: Update src/outreach/composer.py**

```python
# Before
from src.config import load_template, render_template

# After
from src.core.config import load_template, render_template
```

**Step 7: Update src/outreach/sender.py**

```python
# Before
from src.config import load_settings

# After
from src.core.config import load_settings
```

**Step 8: Update src/outreach/enricher.py**

```python
# Before
from src.db import update_lead

# After
from src.core.db import update_lead
```

**Step 9: Update src/outreach/importer.py**

```python
# Before
from src.db import insert_lead

# After
from src.core.db import insert_lead
```

**Step 10: Update src/core/cli.py**

```python
# Before
from src.db import init_db, get_lead, get_leads_by_status
from src.importer import import_leads_from_excel
from src.scheduler import run_send_cycle

# After
from src.core.db import init_db, get_lead, get_leads_by_status
from src.outreach.importer import import_leads_from_excel
from src.outreach.scheduler import run_send_cycle
```

**Step 11: Verify imports work**

Run: `python -c "from src.core.cli import cli; print('OK')"`
Expected: OK

**Step 12: Commit**

```bash
git add -A
git commit -m "refactor: update all import paths for new structure"
```

---

## Task 10: Move Test Files

**Files:**
- Move: `tests/test_cli.py` → `tests/core/test_cli.py`
- Move: `tests/test_config.py` → `tests/core/test_config.py`
- Move: `tests/test_db.py` → `tests/core/test_db.py`
- Move: `tests/test_composer.py` → `tests/outreach/test_composer.py`
- Move: `tests/test_enricher.py` → `tests/outreach/test_enricher.py`
- Move: `tests/test_sender.py` → `tests/outreach/test_sender.py`
- Move: `tests/test_importer.py` → `tests/outreach/test_importer.py`
- Move: `tests/test_scheduler.py` → `tests/outreach/test_scheduler.py`
- Move: `tests/test_apollo.py` → `tests/clients/test_apollo.py`
- Move: `tests/test_fb_ads.py` → `tests/clients/test_fb_ads.py`
- Move: `tests/test_supabase_client.py` → `tests/clients/test_supabase.py`
- Move: `tests/test_discovery_agent.py` → `tests/discovery/test_agent.py`
- Move: `tests/test_lead_generator.py` → `tests/discovery/test_lead_generator.py`
- Move: `tests/mcp/*` → `tests/discovery/test_mcp_tools.py` (consolidated)
- Move: `tests/test_slack_notifier.py` → `tests/services/test_slack_notifier.py`
- Move: `tests/test_seed_analyzer.py` → `tests/services/test_seed_analyzer.py`
- Move: `tests/test_embedding_service.py` → `tests/services/test_embedding_service.py`

**Step 1: Move core tests**

```bash
mv tests/test_cli.py tests/core/test_cli.py
mv tests/test_config.py tests/core/test_config.py
mv tests/test_db.py tests/core/test_db.py
```

**Step 2: Move outreach tests**

```bash
mv tests/test_composer.py tests/outreach/test_composer.py
mv tests/test_enricher.py tests/outreach/test_enricher.py
mv tests/test_sender.py tests/outreach/test_sender.py
mv tests/test_importer.py tests/outreach/test_importer.py
mv tests/test_scheduler.py tests/outreach/test_scheduler.py
```

**Step 3: Move client tests**

```bash
mv tests/test_apollo.py tests/clients/test_apollo.py
mv tests/test_fb_ads.py tests/clients/test_fb_ads.py
mv tests/test_supabase_client.py tests/clients/test_supabase.py
```

**Step 4: Move discovery tests**

```bash
mv tests/test_discovery_agent.py tests/discovery/test_agent.py
mv tests/test_lead_generator.py tests/discovery/test_lead_generator.py
```

**Step 5: Move service tests**

```bash
mv tests/test_slack_notifier.py tests/services/test_slack_notifier.py
mv tests/test_seed_analyzer.py tests/services/test_seed_analyzer.py
mv tests/test_embedding_service.py tests/services/test_embedding_service.py
```

**Step 6: Consolidate MCP tests into discovery**

Manually combine `tests/mcp/test_*.py` files into `tests/discovery/test_mcp_tools.py`, then delete the mcp folder:

```bash
rm -rf tests/mcp
```

**Step 7: Commit**

```bash
git add -A
git commit -m "refactor: reorganize tests to mirror src structure"
```

---

## Task 11: Update Test Import Paths

**Files:**
- Modify: All test files to use new import paths

**Step 1: Update each test file's imports**

For each test file, update imports to match new paths:

```python
# Example for tests/core/test_db.py
# Before
from src.db import init_db, insert_lead

# After
from src.core.db import init_db, insert_lead
```

```python
# Example for tests/outreach/test_composer.py
# Before
from src.composer import generate_email_1

# After
from src.outreach.composer import generate_email_1
```

```python
# Example for tests/clients/test_apollo.py
# Before
from src.apollo import search_people

# After
from src.clients.apollo import search_people
```

```python
# Example for tests/discovery/test_agent.py
# Before
from src.agents.discovery_agent import DiscoveryAgent

# After
from src.discovery.agent import DiscoveryAgent
```

```python
# Example for tests/discovery/test_mcp_tools.py
# Before
from src.mcp_servers.apollo_server import create_apollo_mcp_server

# After
from src.discovery.mcp_tools import create_apollo_mcp_server
```

**Step 2: Run all tests**

Run: `python -m pytest -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add -A
git commit -m "fix: update test imports for new structure"
```

---

## Task 12: Clean Up Old Files

**Files:**
- Delete: `src/__init__.py` (if now empty/unused)
- Verify: No orphaned files in src/

**Step 1: Check for orphaned files**

Run: `ls src/*.py`
Expected: Only `src/__init__.py` (which can be kept or removed)

**Step 2: Update src/__init__.py to re-export from new structure (optional)**

```python
"""Outreach boilerplate package."""

# Re-export commonly used items for backwards compatibility
from src.core.config import Settings, load_settings
from src.core.db import Lead, init_db
```

**Step 3: Final test run**

Run: `python -m pytest -v`
Expected: All tests pass

**Step 4: Final commit**

```bash
git add -A
git commit -m "chore: clean up and finalize project reorganization"
```

---

## Summary

| Task | Description | Files Changed |
|------|-------------|---------------|
| 1 | Create directory structure | 9 new dirs |
| 2 | Move core files | 3 files |
| 3 | Move client files | 3 files |
| 4 | Move outreach files | 5 files |
| 5 | Move discovery + consolidate MCP | 4 files, delete 6 |
| 6 | Consolidate email templates | 1 new, delete 3 |
| 7 | Add seed customers | 1 file |
| 8 | Add template parser | 1 file |
| 9 | Update import paths | ~12 files |
| 10 | Move test files | ~18 files |
| 11 | Update test imports | ~18 files |
| 12 | Clean up | Verify |

**Total commits:** 12
**Estimated steps:** ~50

After completion, run full test suite to verify everything works:
```bash
python -m pytest -v
python run.py status
python -c "from src.core.cli import cli; print('CLI OK')"
python -c "from src.discovery.agent import DiscoveryAgent; print('Agent OK')"
```
