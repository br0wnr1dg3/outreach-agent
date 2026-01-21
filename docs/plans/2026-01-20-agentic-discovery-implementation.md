# Agentic Lead Discovery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the outreach pipeline into an agentic system where a Claude Agent SDK-powered discovery agent autonomously finds and qualifies 10 companies per weekday.

**Architecture:** Claude Agent SDK orchestrator with 4 MCP servers (FB Ads, Apollo, Supabase, Web). Agent reads seed profile analysis files, maintains a search journal, and updates keyword weights based on results.

**Tech Stack:** Python 3.11+, Claude Agent SDK, Supabase (PostgreSQL + pgvector), httpx, Pydantic, structlog

---

## Phase 1: Foundation Setup

### Task 1: Add Claude Agent SDK Dependency

**Files:**
- Modify: `pyproject.toml:7-17`

**Step 1: Update pyproject.toml with new dependencies**

```toml
dependencies = [
    "anthropic>=0.40.0",
    "composio>=0.10.0",
    "openpyxl>=3.1.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0.0",
    "httpx>=0.27.0",
    "structlog>=24.0.0",
    "click>=8.0.0",
    "python-dotenv>=1.0.0",
    "claude-agent-sdk>=0.1.0",
    "supabase>=2.0.0",
    "openai>=1.0.0",
]
```

**Step 2: Install dependencies**

Run: `uv sync`
Expected: Dependencies installed successfully

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "deps: add claude-agent-sdk, supabase, openai for agentic discovery"
```

---

### Task 2: Create Supabase Client Module

**Files:**
- Create: `src/supabase_client.py`
- Test: `tests/test_supabase_client.py`

**Step 1: Write the failing test**

```python
# tests/test_supabase_client.py
"""Tests for Supabase client."""

import pytest
from unittest.mock import MagicMock, patch


def test_supabase_client_init_requires_env_vars():
    """Client should raise if SUPABASE_URL not set."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="SUPABASE_URL"):
            from src.supabase_client import SupabaseClient
            SupabaseClient()


def test_check_company_searched_returns_bool():
    """check_company_searched should return boolean."""
    with patch("src.supabase_client.create_client") as mock_create:
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_create.return_value = mock_client

        with patch.dict("os.environ", {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_KEY": "test-key"}):
            from src.supabase_client import SupabaseClient
            client = SupabaseClient()
            result = client.check_company_searched("example.com")
            assert isinstance(result, bool)
            assert result is False
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_supabase_client.py -v`
Expected: FAIL with "ModuleNotFoundError" or import error

**Step 3: Write minimal implementation**

```python
# src/supabase_client.py
"""Supabase client for leads and companies."""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import uuid4

from supabase import create_client, Client
import structlog

log = structlog.get_logger()


@dataclass
class Lead:
    """Lead record from Supabase."""
    id: str
    email: str
    first_name: str
    last_name: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    linkedin_url: Optional[str] = None
    status: str = "new"
    current_step: int = 0
    source: str = "import"
    source_keyword: Optional[str] = None
    company_fit_score: Optional[int] = None
    company_fit_notes: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class SearchedCompany:
    """Searched company record from Supabase."""
    id: str
    domain: str
    company_name: Optional[str] = None
    source_keyword: Optional[str] = None
    passed_gate_1: Optional[bool] = None
    passed_gate_2: Optional[bool] = None
    leads_found: int = 0
    fit_score: Optional[int] = None
    fit_notes: Optional[str] = None
    searched_at: Optional[datetime] = None


class SupabaseClient:
    """Client for Supabase database operations."""

    def __init__(self):
        """Initialize Supabase client from environment variables."""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url:
            raise ValueError("SUPABASE_URL environment variable is required")
        if not key:
            raise ValueError("SUPABASE_KEY environment variable is required")

        self.client: Client = create_client(url, key)

    def check_company_searched(self, domain: str) -> bool:
        """Check if a company domain has been searched."""
        result = (
            self.client.table("searched_companies")
            .select("id")
            .eq("domain", domain)
            .execute()
        )
        return len(result.data) > 0

    def mark_company_searched(
        self,
        domain: str,
        company_name: Optional[str] = None,
        source_keyword: Optional[str] = None,
        passed_gate_1: Optional[bool] = None,
        passed_gate_2: Optional[bool] = None,
        fit_score: Optional[int] = None,
        fit_notes: Optional[str] = None,
    ) -> SearchedCompany:
        """Mark a company as searched."""
        data = {
            "id": str(uuid4()),
            "domain": domain,
            "company_name": company_name,
            "source_keyword": source_keyword,
            "passed_gate_1": passed_gate_1,
            "passed_gate_2": passed_gate_2,
            "fit_score": fit_score,
            "fit_notes": fit_notes,
            "searched_at": datetime.utcnow().isoformat(),
        }

        result = self.client.table("searched_companies").upsert(data).execute()
        row = result.data[0]

        log.info("company_marked_searched", domain=domain, source_keyword=source_keyword)
        return SearchedCompany(**row)

    def update_company_leads_found(self, domain: str, count: int) -> None:
        """Update the leads_found count for a searched company."""
        self.client.table("searched_companies").update(
            {"leads_found": count}
        ).eq("domain", domain).execute()

    def insert_lead(
        self,
        email: str,
        first_name: str,
        last_name: Optional[str] = None,
        company: Optional[str] = None,
        title: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        source: str = "agent",
        source_keyword: Optional[str] = None,
        company_fit_score: Optional[int] = None,
        company_fit_notes: Optional[str] = None,
    ) -> Optional[Lead]:
        """Insert a lead. Returns Lead or None if duplicate."""
        data = {
            "id": str(uuid4()),
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "company": company,
            "title": title,
            "linkedin_url": linkedin_url,
            "status": "new",
            "current_step": 0,
            "source": source,
            "source_keyword": source_keyword,
            "company_fit_score": company_fit_score,
            "company_fit_notes": company_fit_notes,
            "created_at": datetime.utcnow().isoformat(),
        }

        try:
            result = self.client.table("leads").insert(data).execute()
            row = result.data[0]
            log.info("lead_inserted", email=email, source=source)
            return Lead(**row)
        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                log.info("lead_duplicate_skipped", email=email)
                return None
            raise

    def get_leads_by_status(self, status: str) -> list[Lead]:
        """Get all leads with a given status."""
        result = (
            self.client.table("leads")
            .select("*")
            .eq("status", status)
            .execute()
        )
        return [Lead(**row) for row in result.data]

    def count_leads_generated_today(self) -> int:
        """Count leads generated today."""
        today = datetime.utcnow().date().isoformat()
        result = (
            self.client.table("leads")
            .select("id", count="exact")
            .gte("created_at", f"{today}T00:00:00")
            .lt("created_at", f"{today}T23:59:59")
            .execute()
        )
        return result.count or 0

    def count_companies_checked_today(self) -> int:
        """Count companies checked today."""
        today = datetime.utcnow().date().isoformat()
        result = (
            self.client.table("searched_companies")
            .select("id", count="exact")
            .gte("searched_at", f"{today}T00:00:00")
            .lt("searched_at", f"{today}T23:59:59")
            .execute()
        )
        return result.count or 0

    def get_daily_stats(self) -> dict:
        """Get daily statistics."""
        return {
            "leads_generated_today": self.count_leads_generated_today(),
            "companies_checked_today": self.count_companies_checked_today(),
        }

    def get_quota_status(self, daily_target: int = 10) -> dict:
        """Get quota status for today."""
        leads_today = self.count_leads_generated_today()
        return {
            "leads_today": leads_today,
            "target": daily_target,
            "remaining": max(0, daily_target - leads_today),
            "quota_met": leads_today >= daily_target,
        }
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_supabase_client.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/supabase_client.py tests/test_supabase_client.py
git commit -m "feat: add Supabase client for leads and companies"
```

---

### Task 3: Create Supabase Schema Migration

**Files:**
- Create: `scripts/setup_supabase.sql`

**Step 1: Write the migration SQL**

```sql
-- scripts/setup_supabase.sql
-- Supabase schema for agentic lead discovery

-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Leads table (migrated from SQLite + new fields)
CREATE TABLE IF NOT EXISTS leads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  first_name TEXT NOT NULL,
  last_name TEXT,
  company TEXT,
  title TEXT,
  linkedin_url TEXT,

  -- Enrichment
  linkedin_posts JSONB,
  enriched_at TIMESTAMPTZ,
  enrichment_attempts INT DEFAULT 0,

  -- Email state
  status TEXT DEFAULT 'new',  -- new, active, replied, completed
  current_step INT DEFAULT 0,
  thread_id TEXT,
  last_message_id TEXT,
  email_1_subject TEXT,
  email_1_body TEXT,

  -- Agent metadata
  source TEXT DEFAULT 'import',  -- 'agent' | 'import'
  source_keyword TEXT,
  company_fit_score INT,
  company_fit_notes TEXT,
  company_embedding VECTOR(1536),

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  imported_at TIMESTAMPTZ DEFAULT NOW(),
  last_sent_at TIMESTAMPTZ,
  next_send_at TIMESTAMPTZ
);

-- Companies searched (prevents re-scraping)
CREATE TABLE IF NOT EXISTS searched_companies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain TEXT UNIQUE NOT NULL,
  company_name TEXT,
  source_keyword TEXT,
  fb_page_id TEXT,
  passed_gate_1 BOOLEAN,
  passed_gate_2 BOOLEAN,
  leads_found INT DEFAULT 0,
  fit_score INT,
  fit_notes TEXT,
  website_embedding VECTOR(1536),
  searched_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed profiles (for vector similarity matching)
CREATE TABLE IF NOT EXISTS seed_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain TEXT UNIQUE NOT NULL,
  name TEXT,
  analysis JSONB,
  embedding VECTOR(1536),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sent emails audit log
CREATE TABLE IF NOT EXISTS sent_emails (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID REFERENCES leads(id),
  step INT NOT NULL,
  subject TEXT,
  body TEXT,
  gmail_message_id TEXT,
  sent_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_next_send ON leads(next_send_at);
CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at);
CREATE INDEX IF NOT EXISTS idx_searched_companies_domain ON searched_companies(domain);
CREATE INDEX IF NOT EXISTS idx_searched_companies_searched_at ON searched_companies(searched_at);

-- Vector indexes for similarity search (HNSW for fast approximate nearest neighbor)
CREATE INDEX IF NOT EXISTS idx_searched_companies_embedding ON searched_companies
  USING hnsw (website_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_seed_profiles_embedding ON seed_profiles
  USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_leads_embedding ON leads
  USING hnsw (company_embedding vector_cosine_ops);

-- Row Level Security (optional - enable if using Supabase Auth)
-- ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE searched_companies ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE seed_profiles ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE sent_emails ENABLE ROW LEVEL SECURITY;
```

**Step 2: Create the scripts directory if needed**

Run: `mkdir -p scripts`
Expected: Directory created or exists

**Step 3: Commit**

```bash
git add scripts/setup_supabase.sql
git commit -m "db: add Supabase schema with vector indexes"
```

---

### Task 4: Create Embedding Service

**Files:**
- Create: `src/services/embedding_service.py`
- Test: `tests/test_embedding_service.py`

**Step 1: Write the failing test**

```python
# tests/test_embedding_service.py
"""Tests for embedding service."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.mark.asyncio
async def test_generate_embedding_returns_list():
    """generate_embedding should return list of floats."""
    with patch("src.services.embedding_service.AsyncOpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        from src.services.embedding_service import EmbeddingService
        service = EmbeddingService()
        result = await service.generate_embedding("test text")

        assert isinstance(result, list)
        assert len(result) == 1536
        assert all(isinstance(x, float) for x in result)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_embedding_service.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# src/services/embedding_service.py
"""Embedding generation service using OpenAI."""

import os
from typing import Optional

from openai import AsyncOpenAI
import structlog

log = structlog.get_logger()

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


class EmbeddingService:
    """Service for generating text embeddings."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            log.warning("openai_api_key_not_set", message="Embeddings will not work")
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            List of floats (1536 dimensions)
        """
        if not self.client:
            log.warning("embedding_skipped", reason="no_api_key")
            return [0.0] * EMBEDDING_DIMENSIONS

        try:
            response = await self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text,
            )
            embedding = response.data[0].embedding
            log.info("embedding_generated", text_length=len(text))
            return embedding
        except Exception as e:
            log.error("embedding_error", error=str(e))
            return [0.0] * EMBEDDING_DIMENSIONS

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings
        """
        if not self.client:
            return [[0.0] * EMBEDDING_DIMENSIONS for _ in texts]

        try:
            response = await self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts,
            )
            embeddings = [item.embedding for item in response.data]
            log.info("embeddings_generated", count=len(texts))
            return embeddings
        except Exception as e:
            log.error("embeddings_error", error=str(e))
            return [[0.0] * EMBEDDING_DIMENSIONS for _ in texts]
```

**Step 4: Create services directory**

Run: `mkdir -p src/services && touch src/services/__init__.py`
Expected: Directory and __init__.py created

**Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_embedding_service.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/services/ tests/test_embedding_service.py
git commit -m "feat: add embedding service for vector similarity"
```

---

## Phase 2: MCP Servers

### Task 5: Create FB Ads MCP Server

**Files:**
- Create: `src/mcp_servers/fb_ads_server.py`
- Test: `tests/mcp/test_fb_ads_server.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/mcp/test_fb_ads_server.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
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
```

**Step 4: Create mcp_servers directory**

Run: `mkdir -p src/mcp_servers tests/mcp && touch src/mcp_servers/__init__.py tests/mcp/__init__.py`
Expected: Directories and __init__.py files created

**Step 5: Run test to verify it passes**

Run: `python -m pytest tests/mcp/test_fb_ads_server.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/mcp_servers/ tests/mcp/
git commit -m "feat: add FB Ads MCP server"
```

---

### Task 6: Create Apollo MCP Server

**Files:**
- Create: `src/mcp_servers/apollo_server.py`
- Test: `tests/mcp/test_apollo_server.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/mcp/test_apollo_server.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
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
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/mcp/test_apollo_server.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/mcp_servers/apollo_server.py tests/mcp/test_apollo_server.py
git commit -m "feat: add Apollo MCP server with contact check and lead finder"
```

---

### Task 7: Create Supabase MCP Server

**Files:**
- Create: `src/mcp_servers/supabase_server.py`
- Test: `tests/mcp/test_supabase_server.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/mcp/test_supabase_server.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
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
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/mcp/test_supabase_server.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/mcp_servers/supabase_server.py tests/mcp/test_supabase_server.py
git commit -m "feat: add Supabase MCP server for lead and company tracking"
```

---

### Task 8: Create Web MCP Server

**Files:**
- Create: `src/mcp_servers/web_server.py`
- Test: `tests/mcp/test_web_server.py`

**Step 1: Write the failing test**

```python
# tests/mcp/test_web_server.py
"""Tests for Web MCP server."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_fetch_company_page_returns_content():
    """fetch_company_page should return page content as markdown."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
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
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/mcp/test_web_server.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# src/mcp_servers/web_server.py
"""Web fetching as MCP server for Claude Agent SDK.

Tools:
- fetch_company_page: Fetch and convert company website to markdown for ICP analysis
"""

import json
import re
from typing import Any
from html.parser import HTMLParser

import httpx
from claude_agent_sdk import SdkMcpTool, McpSdkServerConfig, create_sdk_mcp_server
import structlog

log = structlog.get_logger()

_tool_handlers: dict[str, Any] = {}


def get_tool_handlers() -> dict[str, Any]:
    """Get the current tool handlers for testing."""
    return _tool_handlers


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
        # Clean up whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        return text.strip()


def html_to_markdown(html: str) -> str:
    """Convert HTML to simple markdown."""
    parser = SimpleHTMLToMarkdown()
    parser.feed(html)
    return parser.get_markdown()


def create_web_mcp_server() -> McpSdkServerConfig:
    """Create an MCP server with web fetching tools.

    Returns:
        McpSdkServerConfig for the MCP server.
    """
    global _tool_handlers

    async def fetch_company_page_handler(args: dict[str, Any]) -> dict[str, Any]:
        """Fetch company website and return as markdown.

        Used for Gate 2 - ICP analysis. Agent compares content against seed profiles.

        Args:
            args: Dict with keys:
                - url (str): Company website URL

        Returns:
            MCP response with page content as markdown.
        """
        url = args.get("url")
        if not url:
            return {
                "content": [{"type": "text", "text": json.dumps({"error": "url is required"})}],
                "isError": True,
            }

        # Ensure URL has protocol
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; OutreachBot/1.0)",
                    }
                )

                if response.status_code != 200:
                    return {
                        "content": [{"type": "text", "text": json.dumps({
                            "error": f"HTTP {response.status_code}",
                            "url": url,
                        })}],
                        "isError": True,
                    }

                html = response.text
                markdown = html_to_markdown(html)

                # Truncate if too long (keep first 8000 chars for context window)
                if len(markdown) > 8000:
                    markdown = markdown[:8000] + "\n\n[Content truncated...]"

                result = {
                    "url": url,
                    "content": markdown,
                    "content_length": len(markdown),
                }
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

    _tool_handlers = {
        "fetch_company_page": fetch_company_page_handler,
    }

    fetch_page_tool = SdkMcpTool(
        name="fetch_company_page",
        description="Fetch company website and convert to markdown for ICP analysis (Gate 2)",
        input_schema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Company website URL (e.g., 'example.com' or 'https://example.com')",
                },
            },
            "required": ["url"],
        },
        handler=fetch_company_page_handler,
    )

    return create_sdk_mcp_server(
        name="web",
        version="1.0.0",
        tools=[fetch_page_tool],
    )
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/mcp/test_web_server.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/mcp_servers/web_server.py tests/mcp/test_web_server.py
git commit -m "feat: add Web MCP server for company website analysis"
```

---

## Phase 3: Discovery Agent

### Task 9: Create Seed Analyzer Service

**Files:**
- Create: `src/services/seed_analyzer.py`
- Test: `tests/test_seed_analyzer.py`

**Step 1: Write the failing test**

```python
# tests/test_seed_analyzer.py
"""Tests for seed analyzer service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_analyze_seed_returns_markdown():
    """analyze_seed should return markdown analysis."""
    with patch("src.services.seed_analyzer.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "<html><body><h1>Collagen Brand</h1></body></html>"
        mock_response.status_code = 200
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        with patch("src.services.seed_analyzer.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_claude = MagicMock()
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text="# Analysis\n\nThis is a collagen brand.")]
            mock_claude.messages.create = AsyncMock(return_value=mock_message)
            mock_anthropic.return_value = mock_claude

            from src.services.seed_analyzer import SeedAnalyzer
            analyzer = SeedAnalyzer()
            result = await analyzer.analyze_seed("https://example.com")

            assert isinstance(result, str)
            assert len(result) > 0
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_seed_analyzer.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# src/services/seed_analyzer.py
"""Seed customer analyzer using Claude."""

import os
from pathlib import Path
from urllib.parse import urlparse

import anthropic
import httpx
import structlog

from src.mcp_servers.web_server import html_to_markdown

log = structlog.get_logger()

ANALYSIS_PROMPT = """Analyze this company website and create a detailed ICP (Ideal Customer Profile) analysis.

Website URL: {url}
Website Content:
{content}

Create a markdown document with these sections:

# {domain}

## Company Profile
- Category: (e.g., Beauty/Wellness DTC, SaaS, E-commerce)
- Product: What do they sell?
- Market: Primary geographic markets
- Price point: (Budget, Mid-range, Premium)
- Business model: (One-time purchase, Subscription, etc.)

## ICP Signals
List 5-7 signals that indicate a company is similar to this one:
- (Signal 1)
- (Signal 2)
- etc.

## Search Terms That Would Find Similar
List 4-6 Facebook Ad Library search terms that would find similar companies:
- "term 1"
- "term 2"
- etc.

## Decision Maker Profile
- Primary target role (e.g., CMO, Head of Growth)
- What they're likely interested in (e.g., influencer marketing, UGC, performance creative)

Be specific and actionable. The goal is to help an AI agent find similar companies."""


class SeedAnalyzer:
    """Service for analyzing seed customer websites."""

    def __init__(self):
        """Initialize with Anthropic client."""
        self.client = anthropic.AsyncAnthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )

    async def fetch_website(self, url: str) -> str:
        """Fetch website content as markdown."""
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; OutreachBot/1.0)"},
            )
            response.raise_for_status()
            return html_to_markdown(response.text)

    async def analyze_seed(self, url: str) -> str:
        """Analyze a seed customer website.

        Args:
            url: Website URL to analyze

        Returns:
            Markdown analysis of the company
        """
        # Extract domain for the title
        parsed = urlparse(url if url.startswith('http') else f"https://{url}")
        domain = parsed.netloc.replace('www.', '')

        # Fetch website content
        content = await self.fetch_website(url)

        # Truncate if too long
        if len(content) > 10000:
            content = content[:10000] + "\n\n[Content truncated...]"

        # Generate analysis with Claude
        prompt = ANALYSIS_PROMPT.format(url=url, content=content, domain=domain)

        message = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        analysis = message.content[0].text
        log.info("seed_analyzed", url=url, domain=domain)
        return analysis

    async def analyze_and_save(self, url: str, output_dir: Path) -> Path:
        """Analyze a seed and save to file.

        Args:
            url: Website URL to analyze
            output_dir: Directory to save analysis

        Returns:
            Path to saved file
        """
        # Extract domain for filename
        parsed = urlparse(url if url.startswith('http') else f"https://{url}")
        domain = parsed.netloc.replace('www.', '')
        filename = domain.replace('.', '_') + '.md'

        # Analyze
        analysis = await self.analyze_seed(url)

        # Save
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename
        output_path.write_text(analysis)

        log.info("seed_analysis_saved", path=str(output_path))
        return output_path
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_seed_analyzer.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/seed_analyzer.py tests/test_seed_analyzer.py
git commit -m "feat: add seed analyzer service for ICP profile generation"
```

---

### Task 10: Create Discovery Agent Orchestrator

**Files:**
- Create: `src/agents/discovery_agent.py`
- Test: `tests/test_discovery_agent.py`

**Step 1: Write the failing test**

```python
# tests/test_discovery_agent.py
"""Tests for discovery agent orchestrator."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


def test_discovery_agent_init():
    """Agent should initialize with MCP servers."""
    with patch("src.agents.discovery_agent.SupabaseClient"):
        with patch("src.agents.discovery_agent.create_fb_ads_mcp_server") as mock_fb:
            with patch("src.agents.discovery_agent.create_apollo_mcp_server") as mock_apollo:
                with patch("src.agents.discovery_agent.create_supabase_mcp_server") as mock_supa:
                    with patch("src.agents.discovery_agent.create_web_mcp_server") as mock_web:
                        mock_fb.return_value = MagicMock()
                        mock_apollo.return_value = MagicMock()
                        mock_supa.return_value = MagicMock()
                        mock_web.return_value = MagicMock()

                        from src.agents.discovery_agent import DiscoveryAgent
                        agent = DiscoveryAgent()

                        assert "fb_ads" in agent.mcp_servers
                        assert "apollo" in agent.mcp_servers
                        assert "supabase" in agent.mcp_servers
                        assert "web" in agent.mcp_servers
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_discovery_agent.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# src/agents/discovery_agent.py
"""Discovery agent orchestrator using Claude Agent SDK.

This agent autonomously discovers and qualifies companies similar to
seed customers, hitting a daily quota of 10 new companies.
"""

import os
from pathlib import Path
from typing import AsyncIterator, Optional

from claude_agent_sdk import query, ClaudeAgentOptions
import structlog

from src.supabase_client import SupabaseClient
from src.mcp_servers.fb_ads_server import create_fb_ads_mcp_server
from src.mcp_servers.apollo_server import create_apollo_mcp_server
from src.mcp_servers.supabase_server import create_supabase_mcp_server
from src.mcp_servers.web_server import create_web_mcp_server

log = structlog.get_logger()

# Default paths
CONFIG_DIR = Path("config")
SEED_PROFILES_DIR = CONFIG_DIR / "seed_profiles"
SEARCH_JOURNAL_PATH = Path("data/search_journal.md")
LEAD_GEN_CONFIG_PATH = CONFIG_DIR / "lead_gen.yaml"


class DiscoveryAgent:
    """Agent for discovering and qualifying leads.

    Uses Claude Agent SDK with MCP servers for:
    - FB Ads: Search for companies by keyword
    - Apollo: Check contacts and enrich leads
    - Supabase: Track companies and store leads
    - Web: Fetch company websites for ICP analysis
    """

    def __init__(
        self,
        supabase_client: Optional[SupabaseClient] = None,
        seed_profiles_dir: Path = SEED_PROFILES_DIR,
        search_journal_path: Path = SEARCH_JOURNAL_PATH,
        lead_gen_config_path: Path = LEAD_GEN_CONFIG_PATH,
    ):
        """Initialize the discovery agent.

        Args:
            supabase_client: Supabase client (creates default if not provided)
            seed_profiles_dir: Directory containing seed profile .md files
            search_journal_path: Path to search journal markdown file
            lead_gen_config_path: Path to lead_gen.yaml config
        """
        self.supabase = supabase_client or SupabaseClient()
        self.seed_profiles_dir = seed_profiles_dir
        self.search_journal_path = search_journal_path
        self.lead_gen_config_path = lead_gen_config_path

        # Create MCP servers
        self.mcp_servers = {
            "fb_ads": create_fb_ads_mcp_server(),
            "apollo": create_apollo_mcp_server(),
            "supabase": create_supabase_mcp_server(supabase_client=self.supabase),
            "web": create_web_mcp_server(),
        }

    def _load_seed_profiles(self) -> str:
        """Load all seed profile markdown files."""
        profiles = []
        if self.seed_profiles_dir.exists():
            for profile_path in self.seed_profiles_dir.glob("*.md"):
                content = profile_path.read_text()
                profiles.append(f"## Seed Profile: {profile_path.stem}\n\n{content}")

        return "\n\n---\n\n".join(profiles) if profiles else "No seed profiles found."

    def _load_search_journal(self) -> str:
        """Load search journal if it exists."""
        if self.search_journal_path.exists():
            return self.search_journal_path.read_text()
        return "No previous searches recorded."

    def _load_lead_gen_config(self) -> str:
        """Load lead gen config as string."""
        if self.lead_gen_config_path.exists():
            return self.lead_gen_config_path.read_text()
        return "No config found."

    def _build_system_prompt(self, daily_target: int = 10) -> str:
        """Build the system prompt with all context."""
        seed_profiles = self._load_seed_profiles()
        search_journal = self._load_search_journal()
        lead_gen_config = self._load_lead_gen_config()

        return f"""You are an autonomous lead discovery agent. Your goal is to find {daily_target} companies similar to our seed customers and generate leads from them.

## Your Tools

You have access to these MCP tools:

### FB Ads (mcp__fb_ads__)
- search_advertisers: Search FB Ad Library for companies by keyword

### Apollo (mcp__apollo__)
- check_company_contacts: Quick check if decision-makers exist (Gate 1)
- find_leads: Full enrichment to get email addresses

### Supabase (mcp__supabase__)
- check_company_searched: Check if we already processed a domain
- mark_company_searched: Record company with gate results
- insert_lead: Add new lead to database
- get_quota_status: Check progress toward daily target

### Web (mcp__web__)
- fetch_company_page: Get company website for ICP analysis (Gate 2)

## Workflow

1. Check quota status - if met, stop
2. Pick a search keyword (prioritize higher-weighted ones)
3. Search FB Ads for companies
4. For each company:
   a. Skip if already searched (check_company_searched)
   b. Gate 1: Check if contacts exist (check_company_contacts)
   c. Gate 2: Fetch website, analyze against seed profiles for ICP fit
   d. If passes both gates: find_leads and insert_lead
   e. Mark company as searched with results
5. Continue until quota met or searches exhausted

## Contact Priority (Marketing First)
1. CMO
2. VP Marketing
3. Head of Marketing
4. Marketing Director
5. Founder
6. CEO

## Seed Customer Profiles

{seed_profiles}

## Search Journal (What Worked Before)

{search_journal}

## Configuration

{lead_gen_config}

## Important Rules

1. ALWAYS check if company is already searched before processing
2. ALWAYS run Gate 1 before Gate 2 (cheaper first)
3. Compare website content against seed profiles for ICP fit
4. Record detailed fit_notes explaining why company does/doesn't fit
5. Stop when quota is met
6. Be methodical - process one company at a time"""

    async def run(
        self,
        daily_target: int = 10,
        dry_run: bool = False,
    ) -> AsyncIterator:
        """Run the discovery agent.

        Args:
            daily_target: Number of companies to find (default: 10)
            dry_run: If True, don't write to database

        Yields:
            SDK messages as they arrive
        """
        system_prompt = self._build_system_prompt(daily_target)

        user_prompt = f"""Start discovering leads. Target: {daily_target} companies.

{"DRY RUN MODE: Do not actually insert leads or mark companies as searched." if dry_run else ""}

Begin by checking your current quota status, then start searching."""

        log.info("discovery_agent_starting", daily_target=daily_target, dry_run=dry_run)

        async for message in query(
            prompt=self._make_prompt(user_prompt),
            options=ClaudeAgentOptions(
                cwd=os.environ.get("PROJECT_DIR", os.getcwd()),
                permission_mode="acceptEdits",
                system_prompt=system_prompt,
                allowed_tools=[
                    "mcp__fb_ads__*",
                    "mcp__apollo__*",
                    "mcp__supabase__*",
                    "mcp__web__*",
                ],
                disallowed_tools=[
                    "Bash", "Read", "Write", "Task", "Grep", "Glob", "Edit",
                ],
                mcp_servers=self.mcp_servers,
            )
        ):
            yield message

    async def _make_prompt(self, content: str):
        """Create async generator prompt (workaround for SDK bug)."""
        yield {"type": "user", "message": {"role": "user", "content": content}}
```

**Step 4: Create agents directory**

Run: `mkdir -p src/agents && touch src/agents/__init__.py`
Expected: Directory and __init__.py created

**Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_discovery_agent.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/agents/ tests/test_discovery_agent.py
git commit -m "feat: add discovery agent orchestrator with MCP servers"
```

---

## Phase 4: CLI Integration

### Task 11: Add Agent CLI Commands

**Files:**
- Modify: `src/cli.py`
- Test: `tests/test_cli.py` (add new tests)

**Step 1: Read current cli.py**

Run: Read `src/cli.py` to understand current structure

**Step 2: Write the failing test**

```python
# Add to tests/test_cli.py

def test_agent_command_exists():
    """CLI should have agent command."""
    from click.testing import CliRunner
    from src.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ['agent', '--help'])
    assert result.exit_code == 0
    assert 'discovery agent' in result.output.lower()


def test_analyze_seeds_command_exists():
    """CLI should have analyze-seeds command."""
    from click.testing import CliRunner
    from src.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ['analyze-seeds', '--help'])
    assert result.exit_code == 0
```

**Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py::test_agent_command_exists -v`
Expected: FAIL

**Step 4: Add new commands to cli.py**

Add these commands to `src/cli.py`:

```python
@main.command()
@click.option('--target', default=10, help='Daily company target')
@click.option('--dry-run', is_flag=True, help='Preview without writing to DB')
def agent(target: int, dry_run: bool):
    """Run the discovery agent to find and qualify leads."""
    import asyncio
    from src.agents.discovery_agent import DiscoveryAgent

    click.echo(f"Starting discovery agent (target: {target} companies)")
    if dry_run:
        click.echo("DRY RUN - no database writes")

    async def run_agent():
        agent = DiscoveryAgent()
        async for message in agent.run(daily_target=target, dry_run=dry_run):
            if hasattr(message, 'result'):
                click.echo(message.result)

    asyncio.run(run_agent())
    click.echo("Discovery agent complete")


@main.command('analyze-seeds')
@click.argument('urls', nargs=-1, required=True)
@click.option('--output', '-o', default='config/seed_profiles', help='Output directory')
def analyze_seeds(urls: tuple, output: str):
    """Analyze seed customer websites and save ICP profiles.

    URLS: One or more website URLs to analyze
    """
    import asyncio
    from pathlib import Path
    from src.services.seed_analyzer import SeedAnalyzer

    output_dir = Path(output)

    async def run_analysis():
        analyzer = SeedAnalyzer()
        for url in urls:
            click.echo(f"Analyzing {url}...")
            path = await analyzer.analyze_and_save(url, output_dir)
            click.echo(f"  Saved to {path}")

    asyncio.run(run_analysis())
    click.echo(f"\nSeed profiles saved to {output_dir}/")
```

**Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/cli.py tests/test_cli.py
git commit -m "feat: add agent and analyze-seeds CLI commands"
```

---

### Task 12: Update lead_gen.yaml with Weights

**Files:**
- Modify: `config/lead_gen.yaml`

**Step 1: Update config with weighted keywords**

```yaml
# config/lead_gen.yaml
search:
  keywords:
    # Keyword: weight (0.0-1.0, higher = prioritize)
    "collagen supplement": 0.8
    "beauty supplement": 0.7
    "wellness subscription": 0.6
    "anti-aging skincare": 0.5
  countries: ["US", "GB", "AU"]
  status: "ACTIVE"
  excluded_domains:
    - amazon.com
    - facebook.com
    - meta.com
    - instagram.com
    - google.com
    - youtube.com
    - tiktok.com
    - pinterest.com
    - twitter.com
    - linkedin.com
    - walmart.com
    - target.com
    - ebay.com
    - etsy.com
    - shopify.com

targeting:
  title_priority:
    - CMO
    - VP Marketing
    - Head of Marketing
    - Marketing Director
    - Founder
    - CEO
    - COO
  max_contacts_per_company: 1

quotas:
  companies_per_day: 10
  max_searches_per_run: 50

slack:
  webhook_url: ${SLACK_WEBHOOK_URL}
  channel: "#outreach-alerts"
```

**Step 2: Commit**

```bash
git add config/lead_gen.yaml
git commit -m "config: add weighted keywords and slack settings"
```

---

### Task 13: Create Initial Search Journal

**Files:**
- Create: `data/search_journal.md`

**Step 1: Create initial journal**

```markdown
# Search Journal

This file tracks search results and learnings for the discovery agent.
The agent updates this after each run.

---

## Template Entry

### Search: "[keyword]" ([country])
- Date: YYYY-MM-DD
- Companies found: N
- Passed Gate 1 (has contacts): N
- Passed Gate 2 (ICP fit): N
- Leads generated: N
- Quality notes: [observations about this search]
- Weight adjustment: X.X → Y.Y

---

## Entries

(Agent will add entries here)
```

**Step 2: Create data directory if needed**

Run: `mkdir -p data`
Expected: Directory exists

**Step 3: Commit**

```bash
git add data/search_journal.md
git commit -m "docs: add initial search journal template"
```

---

### Task 14: Add Slack Notification Service

**Files:**
- Create: `src/services/slack_notifier.py`
- Test: `tests/test_slack_notifier.py`

**Step 1: Write the failing test**

```python
# tests/test_slack_notifier.py
"""Tests for Slack notifier service."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_send_summary_makes_request():
    """send_summary should POST to webhook URL."""
    with patch("src.services.slack_notifier.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        from src.services.slack_notifier import SlackNotifier
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        await notifier.send_summary(
            companies_found=10,
            leads_added=12,
            quota_met=True,
        )

        mock_client.post.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_slack_notifier.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# src/services/slack_notifier.py
"""Slack notification service for discovery agent."""

import os
from typing import Optional

import httpx
import structlog

log = structlog.get_logger()


class SlackNotifier:
    """Service for sending Slack notifications."""

    def __init__(self, webhook_url: Optional[str] = None):
        """Initialize with webhook URL."""
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")

    async def send_summary(
        self,
        companies_found: int,
        leads_added: int,
        quota_met: bool,
        errors: Optional[list[str]] = None,
    ) -> bool:
        """Send end-of-run summary to Slack.

        Args:
            companies_found: Number of companies discovered
            leads_added: Number of leads added to database
            quota_met: Whether daily quota was achieved
            errors: List of any errors encountered

        Returns:
            True if sent successfully
        """
        if not self.webhook_url:
            log.warning("slack_webhook_not_configured")
            return False

        # Build message
        status_emoji = "✅" if quota_met else "⚠️"
        status_text = "Quota met!" if quota_met else "Quota not met"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} Daily Outreach Complete",
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Companies Found:*\n{companies_found}"},
                    {"type": "mrkdwn", "text": f"*Leads Added:*\n{leads_added}"},
                    {"type": "mrkdwn", "text": f"*Status:*\n{status_text}"},
                ]
            }
        ]

        if errors:
            error_text = "\n".join(f"• {e}" for e in errors[:5])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Issues:*\n{error_text}"}
            })

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.webhook_url,
                    json={"blocks": blocks},
                )
                response.raise_for_status()
                log.info("slack_summary_sent", companies=companies_found, leads=leads_added)
                return True

        except Exception as e:
            log.error("slack_send_error", error=str(e))
            return False
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_slack_notifier.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/slack_notifier.py tests/test_slack_notifier.py
git commit -m "feat: add Slack notifier for end-of-run summaries"
```

---

### Task 15: Create Run Script for Cron

**Files:**
- Create: `run_agent.py`

**Step 1: Create the run script**

```python
#!/usr/bin/env python
"""Run the discovery agent (for cron scheduling)."""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import structlog
from src.agents.discovery_agent import DiscoveryAgent
from src.services.slack_notifier import SlackNotifier

log = structlog.get_logger()


async def main():
    """Run the discovery agent and send Slack summary."""
    # Skip weekends
    if datetime.now().weekday() >= 5:
        log.info("skipping_weekend")
        return

    daily_target = int(os.getenv("DAILY_TARGET", "10"))

    log.info("discovery_agent_starting", target=daily_target)

    companies_found = 0
    leads_added = 0
    errors = []

    try:
        agent = DiscoveryAgent()

        async for message in agent.run(daily_target=daily_target):
            if hasattr(message, 'result'):
                result = message.result
                log.info("agent_progress", result=result[:200] if isinstance(result, str) else result)

        # Get final stats from Supabase
        stats = agent.supabase.get_daily_stats()
        companies_found = stats.get("companies_checked_today", 0)
        leads_added = stats.get("leads_generated_today", 0)

    except Exception as e:
        log.error("agent_error", error=str(e))
        errors.append(str(e))

    # Send Slack summary
    notifier = SlackNotifier()
    await notifier.send_summary(
        companies_found=companies_found,
        leads_added=leads_added,
        quota_met=leads_added >= daily_target,
        errors=errors if errors else None,
    )

    log.info("discovery_agent_complete", companies=companies_found, leads=leads_added)


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 2: Make executable**

Run: `chmod +x run_agent.py`
Expected: File is executable

**Step 3: Commit**

```bash
git add run_agent.py
git commit -m "feat: add cron-compatible run script for discovery agent"
```

---

## Phase 5: Environment & Documentation

### Task 16: Update Environment Template

**Files:**
- Modify: `.env.example`

**Step 1: Update .env.example**

```bash
# .env.example - Copy to .env and fill in values

# Anthropic (for email generation + seed analysis)
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI (for embeddings)
OPENAI_API_KEY=sk-...

# Supabase (database)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJ...

# Composio (Gmail)
COMPOSIO_API_KEY=...

# ScrapeCreators (FB Ad Library)
SCRAPECREATORS_API_KEY=...

# Apollo (people search)
APOLLO_API_KEY=...

# Apify (LinkedIn enrichment)
APIFY_API_KEY=...

# Slack (notifications)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Agent settings
DAILY_TARGET=10
```

**Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: update env template with Supabase and OpenAI keys"
```

---

### Task 17: Final Integration Test

**Files:**
- Create: `tests/integration/test_discovery_flow.py`

**Step 1: Write integration test**

```python
# tests/integration/test_discovery_flow.py
"""Integration test for discovery agent flow."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.mark.asyncio
async def test_full_discovery_flow_dry_run():
    """Test the full discovery flow in dry run mode."""
    # Mock all external services
    with patch("src.agents.discovery_agent.SupabaseClient") as mock_supa_class:
        mock_supa = MagicMock()
        mock_supa.check_company_searched.return_value = False
        mock_supa.get_quota_status.return_value = {
            "leads_today": 0,
            "target": 10,
            "remaining": 10,
            "quota_met": False,
        }
        mock_supa_class.return_value = mock_supa

        with patch("src.agents.discovery_agent.query") as mock_query:
            # Simulate agent completing
            async def mock_query_gen(*args, **kwargs):
                yield MagicMock(result="Discovery complete: 10 companies found")

            mock_query.return_value = mock_query_gen()

            from src.agents.discovery_agent import DiscoveryAgent
            agent = DiscoveryAgent(supabase_client=mock_supa)

            results = []
            async for message in agent.run(daily_target=10, dry_run=True):
                if hasattr(message, 'result'):
                    results.append(message.result)

            assert len(results) > 0
```

**Step 2: Create integration test directory**

Run: `mkdir -p tests/integration && touch tests/integration/__init__.py`
Expected: Directory created

**Step 3: Run test**

Run: `python -m pytest tests/integration/ -v`
Expected: PASS

**Step 4: Commit**

```bash
git add tests/integration/
git commit -m "test: add integration test for discovery flow"
```

---

## Summary

This plan implements the agentic lead discovery system in 17 tasks across 5 phases:

**Phase 1: Foundation (Tasks 1-4)**
- Add dependencies
- Create Supabase client
- Create database schema
- Create embedding service

**Phase 2: MCP Servers (Tasks 5-8)**
- FB Ads MCP server
- Apollo MCP server
- Supabase MCP server
- Web MCP server

**Phase 3: Discovery Agent (Tasks 9-10)**
- Seed analyzer service
- Discovery agent orchestrator

**Phase 4: CLI Integration (Tasks 11-15)**
- CLI commands
- Config updates
- Search journal
- Slack notifications
- Cron run script

**Phase 5: Environment & Documentation (Tasks 16-17)**
- Environment template
- Integration tests

Each task follows TDD with explicit file paths, code, and test commands.
