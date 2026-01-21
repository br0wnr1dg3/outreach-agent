# Lead Generation Agent - Implementation Plan

## Overview

Add automated lead generation that searches Facebook Ad Library for advertisers in specific product categories, then finds decision-makers at those companies using Apollo API.

**Data Flow:**
```
FB Ad Library (ScrapeCreators)  →  Extract domains  →  Apollo People Search
         ↓                              ↓                       ↓
  "collagen supplement"         glossybrand.com         title: "Founder"
                                                               ↓
                        Insert to leads table  ←  Apollo Bulk Enrich
                           (status: 'new')            (get emails)
```

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/fb_ads.py` | **Create** | ScrapeCreators API client |
| `src/apollo.py` | **Create** | Apollo search + enrich client |
| `src/lead_generator.py` | **Create** | Orchestration logic |
| `src/db.py` | **Modify** | Add `searched_companies` table |
| `src/cli.py` | **Modify** | Add `generate` command |
| `src/config.py` | **Modify** | Add `LeadGenConfig` model |
| `config/lead_gen.yaml` | **Create** | Keywords, job titles, quotas |
| `tests/test_lead_generator.py` | **Create** | Tests for new functionality |

---

## Step 1: Database Schema Update

**File:** `src/db.py`

Add to `init_db()`:

```sql
CREATE TABLE IF NOT EXISTS searched_companies (
    id INTEGER PRIMARY KEY,
    domain TEXT UNIQUE NOT NULL,
    company_name TEXT,
    source_keyword TEXT,
    fb_page_id TEXT,
    leads_found INTEGER DEFAULT 0,
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_searched_companies_domain ON searched_companies(domain);
```

Add CRUD functions:
- `insert_searched_company(db_path, domain, company_name, source_keyword, fb_page_id) -> bool`
- `is_company_searched(db_path, domain) -> bool`
- `update_company_leads_found(db_path, domain, count)`
- `count_leads_generated_today(db_path) -> int`

---

## Step 2: Configuration

**File:** `src/config.py`

Add Pydantic models:

```python
class LeadGenSearchConfig(BaseModel):
    keywords: list[str] = ["collagen supplement"]
    countries: list[str] = ["US"]
    status: str = "ACTIVE"

class LeadGenTargetingConfig(BaseModel):
    job_titles: list[str] = ["Founder", "CEO", "Head of Marketing", "CMO"]

class LeadGenQuotaConfig(BaseModel):
    leads_per_day: int = 20
    max_companies_to_check: int = 50

class LeadGenConfig(BaseModel):
    search: LeadGenSearchConfig = LeadGenSearchConfig()
    targeting: LeadGenTargetingConfig = LeadGenTargetingConfig()
    quotas: LeadGenQuotaConfig = LeadGenQuotaConfig()
```

Add loader:
```python
def load_lead_gen_config(config_path: Path = DEFAULT_CONFIG_PATH) -> LeadGenConfig:
    """Load lead generation config from YAML file."""
    config_file = config_path / "lead_gen.yaml"
    if not config_file.exists():
        return LeadGenConfig()
    with open(config_file) as f:
        data = yaml.safe_load(f) or {}
    return LeadGenConfig(**data)
```

**File:** `config/lead_gen.yaml`

```yaml
search:
  keywords:
    - "collagen supplement"
    - "beauty supplement"
  countries: ["US", "GB", "AU"]
  status: "ACTIVE"

targeting:
  job_titles:
    - "Founder"
    - "CEO"
    - "Co-Founder"
    - "Head of Marketing"
    - "Marketing Director"
    - "CMO"
    - "VP Marketing"

quotas:
  leads_per_day: 20
  max_companies_to_check: 50
```

---

## Step 3: ScrapeCreators Client

**File:** `src/fb_ads.py`

```python
"""Facebook Ad Library client using ScrapeCreators API."""

import os
import httpx
import structlog
from urllib.parse import urlparse

SCRAPECREATORS_API_KEY = os.getenv("SCRAPECREATORS_API_KEY")
BASE_URL = "https://api.scrapecreators.com/v1/facebook/adLibrary"

log = structlog.get_logger()

async def search_ads(
    keyword: str,
    country: str = "US",
    status: str = "ACTIVE",
    limit: int = 50
) -> list[dict]:
    """Search FB Ad Library for ads matching keyword.

    Returns list of ad dicts with page_id, link_url, etc.
    """
    ...

def extract_domain(url: str) -> str | None:
    """Extract clean domain from URL (e.g., 'glossybrand.com')."""
    ...

async def get_advertiser_domains(
    keyword: str,
    country: str = "US",
    status: str = "ACTIVE",
    limit: int = 50
) -> list[dict]:
    """Search ads and return unique advertiser domains.

    Returns: [{"domain": "glossybrand.com", "page_id": "123", "company_name": "Glossy Brand"}, ...]
    """
    ...
```

**Key implementation details:**
- Use `httpx.AsyncClient` for consistency with existing patterns
- Extract domain from `link_url` field in ad results
- Dedupe by domain before returning
- Handle pagination via `cursor` if needed

---

## Step 4: Apollo Client

**File:** `src/apollo.py`

```python
"""Apollo.io API client for people search and enrichment."""

import os
import httpx
import structlog

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")
BASE_URL = "https://api.apollo.io/api/v1"

log = structlog.get_logger()

async def search_people(
    domain: str,
    job_titles: list[str],
    limit: int = 10
) -> list[dict]:
    """Search for people at a company by domain and job titles.

    Returns list of person dicts (without email yet).
    """
    # POST to /mixed_people/api_search
    ...

async def enrich_people(people: list[dict]) -> list[dict]:
    """Bulk enrich people to get email addresses.

    Accepts up to 10 people per call.
    Returns enriched person dicts with email field.
    """
    # POST to /people/bulk_match
    ...

async def find_leads_at_company(
    domain: str,
    job_titles: list[str],
    max_leads: int = 3
) -> list[dict]:
    """Find and enrich leads at a company.

    Returns list of enriched leads ready for DB insert:
    [{"email": "...", "first_name": "...", "last_name": "...",
      "company": "...", "title": "...", "linkedin_url": "..."}, ...]
    """
    people = await search_people(domain, job_titles, limit=max_leads)
    if not people:
        return []
    enriched = await enrich_people(people)
    return [p for p in enriched if p.get("email")]
```

**Key implementation details:**
- Use bearer token auth: `Authorization: Bearer {API_KEY}`
- Handle rate limits gracefully (429 responses)
- Log credits consumed from response
- Filter out people without valid emails

---

## Step 5: Lead Generator Orchestration

**File:** `src/lead_generator.py`

```python
"""Lead generation orchestrator."""

import asyncio
from pathlib import Path
import structlog

from src.config import load_lead_gen_config, DEFAULT_CONFIG_PATH
from src.db import (
    DEFAULT_DB_PATH, insert_lead, is_company_searched,
    insert_searched_company, update_company_leads_found,
    count_leads_generated_today
)
from src.fb_ads import get_advertiser_domains
from src.apollo import find_leads_at_company

log = structlog.get_logger()

async def generate_leads(
    db_path: Path = DEFAULT_DB_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    dry_run: bool = False,
    keyword_override: str | None = None
) -> dict:
    """Generate new leads from FB Ad Library + Apollo.

    Returns summary dict with stats.
    """
    config = load_lead_gen_config(config_path)

    # Check daily quota
    generated_today = count_leads_generated_today(db_path)
    remaining = config.quotas.leads_per_day - generated_today

    if remaining <= 0:
        log.info("daily_lead_quota_reached", generated=generated_today)
        return {"leads_added": 0, "companies_checked": 0, "quota_reached": True}

    results = {
        "leads_added": 0,
        "companies_checked": 0,
        "companies_skipped": 0,
        "quota_reached": False,
        "dry_run": dry_run
    }

    keywords = [keyword_override] if keyword_override else config.search.keywords

    for keyword in keywords:
        if results["leads_added"] >= remaining:
            results["quota_reached"] = True
            break

        # Get advertiser domains from FB
        advertisers = await get_advertiser_domains(
            keyword=keyword,
            country=config.search.countries[0],  # Primary country
            status=config.search.status,
            limit=config.quotas.max_companies_to_check
        )

        for advertiser in advertisers:
            if results["leads_added"] >= remaining:
                results["quota_reached"] = True
                break

            domain = advertiser["domain"]

            # Skip if already searched
            if is_company_searched(db_path, domain):
                results["companies_skipped"] += 1
                continue

            results["companies_checked"] += 1

            if dry_run:
                log.info("dry_run_would_search", domain=domain, keyword=keyword)
                continue

            # Mark as searched
            insert_searched_company(
                db_path, domain,
                company_name=advertiser.get("company_name"),
                source_keyword=keyword,
                fb_page_id=advertiser.get("page_id")
            )

            # Find leads at this company
            leads = await find_leads_at_company(
                domain=domain,
                job_titles=config.targeting.job_titles,
                max_leads=min(3, remaining - results["leads_added"])
            )

            leads_from_company = 0
            for lead in leads:
                lead_id = insert_lead(
                    db_path=db_path,
                    email=lead["email"],
                    first_name=lead["first_name"],
                    last_name=lead.get("last_name"),
                    company=lead.get("company"),
                    title=lead.get("title"),
                    linkedin_url=lead.get("linkedin_url")
                )

                if lead_id:
                    results["leads_added"] += 1
                    leads_from_company += 1
                    log.info("lead_added", email=lead["email"], company=domain)

            # Update company record
            update_company_leads_found(db_path, domain, leads_from_company)

            # Small delay between companies
            await asyncio.sleep(1)

    return results
```

---

## Step 6: CLI Integration

**File:** `src/cli.py`

Add new command:

```python
@cli.command()
@click.option("--db", "db_path", type=click.Path(), default=str(DEFAULT_DB_PATH))
@click.option("--config", "config_path", type=click.Path(), default=str(DEFAULT_CONFIG_PATH))
@click.option("--dry-run", is_flag=True, help="Show what would be generated without making API calls")
@click.option("--keyword", help="Override search keyword for this run")
def generate(db_path: str, config_path: str, dry_run: bool, keyword: str):
    """Generate new leads from FB Ad Library + Apollo."""
    from src.lead_generator import generate_leads

    db = Path(db_path)
    config = Path(config_path)

    init_db(db)

    if dry_run:
        click.echo("DRY RUN - No API calls will be made\n")

    click.echo("=" * 40)
    click.echo("Generating leads...")
    click.echo("=" * 40 + "\n")

    result = asyncio.run(generate_leads(
        db_path=db,
        config_path=config,
        dry_run=dry_run,
        keyword_override=keyword
    ))

    click.echo(f"\nResults:")
    click.echo(f"  Leads added: {result['leads_added']}")
    click.echo(f"  Companies checked: {result['companies_checked']}")
    click.echo(f"  Companies skipped (already searched): {result['companies_skipped']}")

    if result.get("quota_reached"):
        click.echo(f"\n  Daily quota reached!")
```

---

## Step 7: Environment Variables

**File:** `.env` (update)

```
ANTHROPIC_API_KEY=...
COMPOSIO_API_KEY=...
APIFY_API_KEY=...
SCRAPECREATORS_API_KEY=...   # NEW
APOLLO_API_KEY=...            # NEW
```

---

## Step 8: Tests

**File:** `tests/test_lead_generator.py`

```python
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock

from src.db import init_db, get_lead_by_email, is_company_searched
from src.lead_generator import generate_leads

@pytest.mark.asyncio
async def test_generate_leads_dry_run():
    """Test dry run doesn't make API calls or insert records."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        config_path = Path(tmpdir)

        init_db(db_path)

        # Create minimal config
        (config_path / "lead_gen.yaml").write_text("""
search:
  keywords: ["test product"]
targeting:
  job_titles: ["CEO"]
quotas:
  leads_per_day: 5
  max_companies_to_check: 10
""")

        with patch("src.lead_generator.get_advertiser_domains") as mock_fb:
            mock_fb.return_value = [
                {"domain": "test.com", "page_id": "123", "company_name": "Test Co"}
            ]

            result = await generate_leads(
                db_path=db_path,
                config_path=config_path,
                dry_run=True
            )

            assert result["dry_run"] == True
            assert result["companies_checked"] == 1
            assert result["leads_added"] == 0

            # Company should NOT be marked as searched in dry run
            assert not is_company_searched(db_path, "test.com")

@pytest.mark.asyncio
async def test_generate_leads_skips_searched_companies():
    """Test that already-searched companies are skipped."""
    ...

@pytest.mark.asyncio
async def test_generate_leads_respects_daily_quota():
    """Test daily quota enforcement."""
    ...
```

---

## Verification Steps

After implementation, verify with:

1. **Unit tests:**
   ```bash
   python -m pytest tests/test_lead_generator.py -v
   ```

2. **Dry run:**
   ```bash
   python run.py generate --dry-run
   ```

3. **Single keyword test:**
   ```bash
   python run.py generate --keyword "collagen supplement"
   ```

4. **Check database:**
   ```bash
   python run.py status
   sqlite3 data/outreach.db "SELECT * FROM searched_companies LIMIT 5"
   sqlite3 data/outreach.db "SELECT * FROM leads WHERE status='new' LIMIT 5"
   ```

5. **Full integration:**
   ```bash
   python run.py generate
   python run.py send
   ```

---

## Implementation Order

1. `src/db.py` - Add searched_companies table + CRUD
2. `src/config.py` - Add LeadGenConfig models
3. `config/lead_gen.yaml` - Create config file
4. `src/fb_ads.py` - ScrapeCreators client
5. `src/apollo.py` - Apollo client
6. `src/lead_generator.py` - Orchestration
7. `src/cli.py` - Add generate command
8. `tests/test_lead_generator.py` - Tests
9. Verify end-to-end
