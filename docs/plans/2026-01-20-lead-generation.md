# Lead Generation Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add automated lead generation that searches Facebook Ad Library for advertisers, then finds decision-makers using Apollo API.

**Architecture:** FB Ad Library (via ScrapeCreators API) → Extract company domains → Apollo People Search → Bulk email enrichment → Insert to leads table. Config-driven search keywords, job titles, and daily quotas.

**Tech Stack:** Python 3.11+, httpx (async HTTP), Pydantic (config models), SQLite, pytest-asyncio

---

## Data Flow

```
FB Ad Library (ScrapeCreators)  →  Extract domains  →  Apollo People Search
         ↓                              ↓                       ↓
  "collagen supplement"         glossybrand.com         title: "Founder"
                                                               ↓
                        Insert to leads table  ←  Apollo Bulk Enrich
                           (status: 'new')            (get emails)
```

---

## Files Overview

| File | Action | Purpose |
|------|--------|---------|
| `src/db.py` | **Modify** | Add `searched_companies` table + CRUD |
| `tests/test_db.py` | **Modify** | Tests for new DB functions |
| `src/config.py` | **Modify** | Add `LeadGenConfig` model |
| `tests/test_config.py` | **Modify** | Tests for config loading |
| `config/lead_gen.yaml` | **Create** | Keywords, job titles, quotas |
| `src/fb_ads.py` | **Create** | ScrapeCreators API client |
| `tests/test_fb_ads.py` | **Create** | Tests for FB Ads client |
| `src/apollo.py` | **Create** | Apollo search + enrich client |
| `tests/test_apollo.py` | **Create** | Tests for Apollo client |
| `src/lead_generator.py` | **Create** | Orchestration logic |
| `tests/test_lead_generator.py` | **Create** | Tests for orchestrator |
| `src/cli.py` | **Modify** | Add `generate` command |
| `tests/test_cli.py` | **Modify** | Tests for CLI command |

---

## Task 1: Database Schema - searched_companies Table

**Files:**
- Modify: `src/db.py:20-72` (init_db function)
- Test: `tests/test_db.py`

### Step 1: Write failing test for init_db creating searched_companies table

Add to `tests/test_db.py`:

```python
def test_init_db_creates_searched_companies_table():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        conn = get_connection(db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='searched_companies'"
        )
        tables = cursor.fetchall()
        conn.close()

        assert len(tables) == 1
```

### Step 2: Run test to verify it fails

Run: `python -m pytest tests/test_db.py::test_init_db_creates_searched_companies_table -v`

Expected: FAIL with `AssertionError: assert 0 == 1`

### Step 3: Add searched_companies table to init_db

In `src/db.py`, inside `init_db()` function, add after the existing `CREATE INDEX` statements:

```python
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

### Step 4: Run test to verify it passes

Run: `python -m pytest tests/test_db.py::test_init_db_creates_searched_companies_table -v`

Expected: PASS

### Step 5: Commit

```bash
git add src/db.py tests/test_db.py
git commit -m "feat(db): add searched_companies table schema"
```

---

## Task 2: Database CRUD - insert_searched_company

**Files:**
- Modify: `src/db.py`
- Test: `tests/test_db.py`

### Step 1: Write failing test for insert_searched_company

Add to `tests/test_db.py`:

```python
from src.db import (
    init_db, get_connection,
    insert_lead, get_lead_by_email, get_leads_by_status,
    update_lead_status, count_sent_today,
    insert_searched_company  # Add this import
)


def test_insert_searched_company():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        result = insert_searched_company(
            db_path=db_path,
            domain="glossybrand.com",
            company_name="Glossy Brand",
            source_keyword="collagen supplement",
            fb_page_id="123456"
        )

        assert result is True

        conn = get_connection(db_path)
        cursor = conn.execute(
            "SELECT * FROM searched_companies WHERE domain = ?",
            ("glossybrand.com",)
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row["company_name"] == "Glossy Brand"
        assert row["source_keyword"] == "collagen supplement"


def test_insert_searched_company_duplicate_returns_false():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        result1 = insert_searched_company(db_path, "test.com", "Test", "keyword", "123")
        result2 = insert_searched_company(db_path, "test.com", "Test Again", "other", "456")

        assert result1 is True
        assert result2 is False
```

### Step 2: Run test to verify it fails

Run: `python -m pytest tests/test_db.py::test_insert_searched_company -v`

Expected: FAIL with `ImportError: cannot import name 'insert_searched_company'`

### Step 3: Implement insert_searched_company

Add to `src/db.py` after `insert_lead`:

```python
def insert_searched_company(
    db_path: Path,
    domain: str,
    company_name: Optional[str],
    source_keyword: Optional[str],
    fb_page_id: Optional[str],
) -> bool:
    """Insert a searched company. Returns True if inserted, False if duplicate."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO searched_companies (domain, company_name, source_keyword, fb_page_id)
            VALUES (?, ?, ?, ?)
            """,
            (domain, company_name, source_keyword, fb_page_id)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
```

### Step 4: Run tests to verify they pass

Run: `python -m pytest tests/test_db.py::test_insert_searched_company tests/test_db.py::test_insert_searched_company_duplicate_returns_false -v`

Expected: PASS

### Step 5: Commit

```bash
git add src/db.py tests/test_db.py
git commit -m "feat(db): add insert_searched_company function"
```

---

## Task 3: Database CRUD - is_company_searched

**Files:**
- Modify: `src/db.py`
- Test: `tests/test_db.py`

### Step 1: Write failing test for is_company_searched

Add to `tests/test_db.py` imports:

```python
from src.db import (
    init_db, get_connection,
    insert_lead, get_lead_by_email, get_leads_by_status,
    update_lead_status, count_sent_today,
    insert_searched_company, is_company_searched  # Add is_company_searched
)
```

Add test:

```python
def test_is_company_searched():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        assert is_company_searched(db_path, "unknown.com") is False

        insert_searched_company(db_path, "known.com", "Known", "keyword", "123")

        assert is_company_searched(db_path, "known.com") is True
        assert is_company_searched(db_path, "unknown.com") is False
```

### Step 2: Run test to verify it fails

Run: `python -m pytest tests/test_db.py::test_is_company_searched -v`

Expected: FAIL with `ImportError: cannot import name 'is_company_searched'`

### Step 3: Implement is_company_searched

Add to `src/db.py` after `insert_searched_company`:

```python
def is_company_searched(db_path: Path, domain: str) -> bool:
    """Check if a company domain has been searched."""
    conn = get_connection(db_path)
    cursor = conn.execute(
        "SELECT 1 FROM searched_companies WHERE domain = ?",
        (domain,)
    )
    exists = cursor.fetchone() is not None
    conn.close()
    return exists
```

### Step 4: Run test to verify it passes

Run: `python -m pytest tests/test_db.py::test_is_company_searched -v`

Expected: PASS

### Step 5: Commit

```bash
git add src/db.py tests/test_db.py
git commit -m "feat(db): add is_company_searched function"
```

---

## Task 4: Database CRUD - update_company_leads_found

**Files:**
- Modify: `src/db.py`
- Test: `tests/test_db.py`

### Step 1: Write failing test

Add import and test to `tests/test_db.py`:

```python
from src.db import (
    init_db, get_connection,
    insert_lead, get_lead_by_email, get_leads_by_status,
    update_lead_status, count_sent_today,
    insert_searched_company, is_company_searched, update_company_leads_found
)


def test_update_company_leads_found():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        insert_searched_company(db_path, "test.com", "Test", "keyword", "123")
        update_company_leads_found(db_path, "test.com", 5)

        conn = get_connection(db_path)
        cursor = conn.execute(
            "SELECT leads_found FROM searched_companies WHERE domain = ?",
            ("test.com",)
        )
        row = cursor.fetchone()
        conn.close()

        assert row["leads_found"] == 5
```

### Step 2: Run test to verify it fails

Run: `python -m pytest tests/test_db.py::test_update_company_leads_found -v`

Expected: FAIL with `ImportError: cannot import name 'update_company_leads_found'`

### Step 3: Implement update_company_leads_found

Add to `src/db.py`:

```python
def update_company_leads_found(db_path: Path, domain: str, count: int) -> None:
    """Update the leads_found count for a searched company."""
    conn = get_connection(db_path)
    conn.execute(
        "UPDATE searched_companies SET leads_found = ? WHERE domain = ?",
        (count, domain)
    )
    conn.commit()
    conn.close()
```

### Step 4: Run test to verify it passes

Run: `python -m pytest tests/test_db.py::test_update_company_leads_found -v`

Expected: PASS

### Step 5: Commit

```bash
git add src/db.py tests/test_db.py
git commit -m "feat(db): add update_company_leads_found function"
```

---

## Task 5: Database CRUD - count_leads_generated_today

**Files:**
- Modify: `src/db.py`
- Test: `tests/test_db.py`

### Step 1: Write failing test

Add import and test:

```python
from src.db import (
    init_db, get_connection,
    insert_lead, get_lead_by_email, get_leads_by_status,
    update_lead_status, count_sent_today,
    insert_searched_company, is_company_searched, update_company_leads_found,
    count_leads_generated_today
)


def test_count_leads_generated_today():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        # No leads yet
        assert count_leads_generated_today(db_path) == 0

        # Add leads today
        insert_lead(db_path, "lead1@test.com", "One", None, None, None, None)
        insert_lead(db_path, "lead2@test.com", "Two", None, None, None, None)

        assert count_leads_generated_today(db_path) == 2
```

### Step 2: Run test to verify it fails

Run: `python -m pytest tests/test_db.py::test_count_leads_generated_today -v`

Expected: FAIL with `ImportError: cannot import name 'count_leads_generated_today'`

### Step 3: Implement count_leads_generated_today

Add to `src/db.py`:

```python
def count_leads_generated_today(db_path: Path) -> int:
    """Count leads imported/generated today."""
    conn = get_connection(db_path)
    today = datetime.utcnow().date().isoformat()
    cursor = conn.execute(
        "SELECT COUNT(*) FROM leads WHERE date(imported_at) = ?",
        (today,)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count
```

### Step 4: Run test to verify it passes

Run: `python -m pytest tests/test_db.py::test_count_leads_generated_today -v`

Expected: PASS

### Step 5: Commit

```bash
git add src/db.py tests/test_db.py
git commit -m "feat(db): add count_leads_generated_today function"
```

---

## Task 6: Configuration - LeadGenConfig Models

**Files:**
- Modify: `src/config.py`
- Test: `tests/test_config.py`

### Step 1: Write failing test for LeadGenConfig

Add to `tests/test_config.py`:

```python
from src.config import load_settings, load_template, Settings, LeadGenConfig


def test_lead_gen_config_defaults():
    config = LeadGenConfig()

    assert config.search.keywords == ["collagen supplement"]
    assert config.search.countries == ["US"]
    assert config.search.status == "ACTIVE"
    assert "Founder" in config.targeting.job_titles
    assert config.quotas.leads_per_day == 20
    assert config.quotas.max_companies_to_check == 50
```

### Step 2: Run test to verify it fails

Run: `python -m pytest tests/test_config.py::test_lead_gen_config_defaults -v`

Expected: FAIL with `ImportError: cannot import name 'LeadGenConfig'`

### Step 3: Implement LeadGenConfig models

Add to `src/config.py` after existing models:

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

### Step 4: Run test to verify it passes

Run: `python -m pytest tests/test_config.py::test_lead_gen_config_defaults -v`

Expected: PASS

### Step 5: Commit

```bash
git add src/config.py tests/test_config.py
git commit -m "feat(config): add LeadGenConfig Pydantic models"
```

---

## Task 7: Configuration - load_lead_gen_config Function

**Files:**
- Modify: `src/config.py`
- Test: `tests/test_config.py`

### Step 1: Write failing test for load_lead_gen_config

Add to `tests/test_config.py`:

```python
from src.config import load_settings, load_template, Settings, LeadGenConfig, load_lead_gen_config


def test_load_lead_gen_config_from_yaml():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir)
        config_file = config_path / "lead_gen.yaml"
        config_file.write_text("""
search:
  keywords:
    - "test product"
    - "another product"
  countries: ["US", "GB"]
  status: "ACTIVE"

targeting:
  job_titles:
    - "CEO"
    - "CTO"

quotas:
  leads_per_day: 10
  max_companies_to_check: 25
""")

        config = load_lead_gen_config(config_path)

        assert config.search.keywords == ["test product", "another product"]
        assert config.search.countries == ["US", "GB"]
        assert config.targeting.job_titles == ["CEO", "CTO"]
        assert config.quotas.leads_per_day == 10


def test_load_lead_gen_config_missing_file_returns_defaults():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir)
        # No file exists

        config = load_lead_gen_config(config_path)

        assert config.search.keywords == ["collagen supplement"]
        assert config.quotas.leads_per_day == 20
```

### Step 2: Run test to verify it fails

Run: `python -m pytest tests/test_config.py::test_load_lead_gen_config_from_yaml -v`

Expected: FAIL with `ImportError: cannot import name 'load_lead_gen_config'`

### Step 3: Implement load_lead_gen_config

Add to `src/config.py`:

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

### Step 4: Run tests to verify they pass

Run: `python -m pytest tests/test_config.py::test_load_lead_gen_config_from_yaml tests/test_config.py::test_load_lead_gen_config_missing_file_returns_defaults -v`

Expected: PASS

### Step 5: Commit

```bash
git add src/config.py tests/test_config.py
git commit -m "feat(config): add load_lead_gen_config function"
```

---

## Task 8: Create config/lead_gen.yaml

**Files:**
- Create: `config/lead_gen.yaml`

### Step 1: Create the config file

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

### Step 2: Verify config loads correctly

Run: `python -c "from src.config import load_lead_gen_config; c = load_lead_gen_config(); print(c.search.keywords)"`

Expected: `['collagen supplement', 'beauty supplement']`

### Step 3: Commit

```bash
git add config/lead_gen.yaml
git commit -m "feat(config): add lead_gen.yaml configuration file"
```

---

## Task 9: ScrapeCreators Client - extract_domain

**Files:**
- Create: `src/fb_ads.py`
- Create: `tests/test_fb_ads.py`

### Step 1: Write failing test for extract_domain

Create `tests/test_fb_ads.py`:

```python
import pytest

from src.fb_ads import extract_domain


def test_extract_domain_simple():
    assert extract_domain("https://glossybrand.com/shop") == "glossybrand.com"


def test_extract_domain_with_www():
    assert extract_domain("https://www.example.com/page") == "example.com"


def test_extract_domain_with_subdomain():
    assert extract_domain("https://shop.mystore.com/products") == "shop.mystore.com"


def test_extract_domain_invalid_url():
    assert extract_domain("not a url") is None
    assert extract_domain("") is None
```

### Step 2: Run test to verify it fails

Run: `python -m pytest tests/test_fb_ads.py::test_extract_domain_simple -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'src.fb_ads'`

### Step 3: Create src/fb_ads.py with extract_domain

Create `src/fb_ads.py`:

```python
"""Facebook Ad Library client using ScrapeCreators API."""

import os
from urllib.parse import urlparse

import httpx
import structlog

SCRAPECREATORS_API_KEY = os.getenv("SCRAPECREATORS_API_KEY", "")
BASE_URL = "https://api.scrapecreators.com/v1/facebook/adLibrary"

log = structlog.get_logger()


def extract_domain(url: str) -> str | None:
    """Extract clean domain from URL (e.g., 'glossybrand.com').

    Removes 'www.' prefix if present.
    Returns None for invalid URLs.
    """
    if not url:
        return None
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if not domain:
            return None
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return None
```

### Step 4: Run tests to verify they pass

Run: `python -m pytest tests/test_fb_ads.py -v`

Expected: PASS

### Step 5: Commit

```bash
git add src/fb_ads.py tests/test_fb_ads.py
git commit -m "feat(fb_ads): add extract_domain utility function"
```

---

## Task 10: ScrapeCreators Client - search_ads

**Files:**
- Modify: `src/fb_ads.py`
- Modify: `tests/test_fb_ads.py`

### Step 1: Write failing test for search_ads

Add to `tests/test_fb_ads.py`:

```python
from unittest.mock import patch, AsyncMock

from src.fb_ads import extract_domain, search_ads


@pytest.mark.asyncio
async def test_search_ads_returns_results():
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "data": [
            {
                "page_id": "123",
                "page_name": "Glossy Brand",
                "link_url": "https://glossybrand.com/shop"
            },
            {
                "page_id": "456",
                "page_name": "Beauty Co",
                "link_url": "https://beautyco.com/products"
            }
        ]
    }
    mock_response.raise_for_status = lambda: None

    with patch("src.fb_ads.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        results = await search_ads("collagen supplement", country="US", limit=10)

        assert len(results) == 2
        assert results[0]["page_id"] == "123"
        assert results[0]["link_url"] == "https://glossybrand.com/shop"


@pytest.mark.asyncio
async def test_search_ads_no_api_key_returns_empty():
    with patch("src.fb_ads.SCRAPECREATORS_API_KEY", ""):
        results = await search_ads("test keyword")
        assert results == []
```

### Step 2: Run test to verify it fails

Run: `python -m pytest tests/test_fb_ads.py::test_search_ads_returns_results -v`

Expected: FAIL with `ImportError: cannot import name 'search_ads'`

### Step 3: Implement search_ads

Add to `src/fb_ads.py`:

```python
async def search_ads(
    keyword: str,
    country: str = "US",
    status: str = "ACTIVE",
    limit: int = 50
) -> list[dict]:
    """Search FB Ad Library for ads matching keyword.

    Returns list of ad dicts with page_id, page_name, link_url, etc.
    """
    if not SCRAPECREATORS_API_KEY:
        log.warning("scrapecreators_api_key_not_set")
        return []

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                BASE_URL,
                params={
                    "query": keyword,
                    "country": country,
                    "ad_status": status,
                    "limit": limit,
                },
                headers={
                    "Authorization": f"Bearer {SCRAPECREATORS_API_KEY}",
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])

    except Exception as e:
        log.error("scrapecreators_search_error", error=str(e), keyword=keyword)
        return []
```

### Step 4: Run tests to verify they pass

Run: `python -m pytest tests/test_fb_ads.py::test_search_ads_returns_results tests/test_fb_ads.py::test_search_ads_no_api_key_returns_empty -v`

Expected: PASS

### Step 5: Commit

```bash
git add src/fb_ads.py tests/test_fb_ads.py
git commit -m "feat(fb_ads): add search_ads function"
```

---

## Task 11: ScrapeCreators Client - get_advertiser_domains

**Files:**
- Modify: `src/fb_ads.py`
- Modify: `tests/test_fb_ads.py`

### Step 1: Write failing test for get_advertiser_domains

Add to `tests/test_fb_ads.py`:

```python
from src.fb_ads import extract_domain, search_ads, get_advertiser_domains


@pytest.mark.asyncio
async def test_get_advertiser_domains_dedupes_by_domain():
    with patch("src.fb_ads.search_ads") as mock_search:
        mock_search.return_value = [
            {"page_id": "123", "page_name": "Brand A", "link_url": "https://brand-a.com/page1"},
            {"page_id": "123", "page_name": "Brand A", "link_url": "https://brand-a.com/page2"},
            {"page_id": "456", "page_name": "Brand B", "link_url": "https://brand-b.com/shop"},
        ]

        results = await get_advertiser_domains("test", country="US", limit=10)

        assert len(results) == 2
        domains = [r["domain"] for r in results]
        assert "brand-a.com" in domains
        assert "brand-b.com" in domains


@pytest.mark.asyncio
async def test_get_advertiser_domains_skips_invalid_urls():
    with patch("src.fb_ads.search_ads") as mock_search:
        mock_search.return_value = [
            {"page_id": "123", "page_name": "Valid", "link_url": "https://valid.com"},
            {"page_id": "456", "page_name": "Invalid", "link_url": ""},
            {"page_id": "789", "page_name": "None", "link_url": None},
        ]

        results = await get_advertiser_domains("test")

        assert len(results) == 1
        assert results[0]["domain"] == "valid.com"
```

### Step 2: Run test to verify it fails

Run: `python -m pytest tests/test_fb_ads.py::test_get_advertiser_domains_dedupes_by_domain -v`

Expected: FAIL with `ImportError: cannot import name 'get_advertiser_domains'`

### Step 3: Implement get_advertiser_domains

Add to `src/fb_ads.py`:

```python
async def get_advertiser_domains(
    keyword: str,
    country: str = "US",
    status: str = "ACTIVE",
    limit: int = 50
) -> list[dict]:
    """Search ads and return unique advertiser domains.

    Returns: [{"domain": "glossybrand.com", "page_id": "123", "company_name": "Glossy Brand"}, ...]
    """
    ads = await search_ads(keyword, country, status, limit)

    seen_domains: set[str] = set()
    results: list[dict] = []

    for ad in ads:
        link_url = ad.get("link_url") or ""
        domain = extract_domain(link_url)

        if not domain or domain in seen_domains:
            continue

        seen_domains.add(domain)
        results.append({
            "domain": domain,
            "page_id": ad.get("page_id"),
            "company_name": ad.get("page_name"),
        })

    log.info("get_advertiser_domains_complete", keyword=keyword, count=len(results))
    return results
```

### Step 4: Run tests to verify they pass

Run: `python -m pytest tests/test_fb_ads.py::test_get_advertiser_domains_dedupes_by_domain tests/test_fb_ads.py::test_get_advertiser_domains_skips_invalid_urls -v`

Expected: PASS

### Step 5: Commit

```bash
git add src/fb_ads.py tests/test_fb_ads.py
git commit -m "feat(fb_ads): add get_advertiser_domains function"
```

---

## Task 12: Apollo Client - search_people

**Files:**
- Create: `src/apollo.py`
- Create: `tests/test_apollo.py`

### Step 1: Write failing test for search_people

Create `tests/test_apollo.py`:

```python
import pytest
from unittest.mock import patch, AsyncMock

from src.apollo import search_people


@pytest.mark.asyncio
async def test_search_people_returns_results():
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "people": [
            {
                "id": "abc123",
                "first_name": "John",
                "last_name": "Doe",
                "title": "CEO",
                "organization": {"name": "Acme Inc"},
                "linkedin_url": "https://linkedin.com/in/johndoe"
            }
        ]
    }
    mock_response.raise_for_status = lambda: None

    with patch("src.apollo.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        results = await search_people("acme.com", ["CEO", "Founder"], limit=5)

        assert len(results) == 1
        assert results[0]["first_name"] == "John"
        assert results[0]["title"] == "CEO"


@pytest.mark.asyncio
async def test_search_people_no_api_key_returns_empty():
    with patch("src.apollo.APOLLO_API_KEY", ""):
        results = await search_people("test.com", ["CEO"])
        assert results == []
```

### Step 2: Run test to verify it fails

Run: `python -m pytest tests/test_apollo.py::test_search_people_returns_results -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'src.apollo'`

### Step 3: Create src/apollo.py with search_people

Create `src/apollo.py`:

```python
"""Apollo.io API client for people search and enrichment."""

import os

import httpx
import structlog

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")
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
    if not APOLLO_API_KEY:
        log.warning("apollo_api_key_not_set")
        return []

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{BASE_URL}/mixed_people/search",
                headers={
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache",
                },
                json={
                    "api_key": APOLLO_API_KEY,
                    "q_organization_domains": domain,
                    "person_titles": job_titles,
                    "per_page": limit,
                },
            )
            response.raise_for_status()
            data = response.json()

            people = data.get("people", [])
            log.info("apollo_search_complete", domain=domain, count=len(people))
            return people

    except Exception as e:
        log.error("apollo_search_error", error=str(e), domain=domain)
        return []
```

### Step 4: Run tests to verify they pass

Run: `python -m pytest tests/test_apollo.py -v`

Expected: PASS

### Step 5: Commit

```bash
git add src/apollo.py tests/test_apollo.py
git commit -m "feat(apollo): add search_people function"
```

---

## Task 13: Apollo Client - enrich_people

**Files:**
- Modify: `src/apollo.py`
- Modify: `tests/test_apollo.py`

### Step 1: Write failing test for enrich_people

Add to `tests/test_apollo.py`:

```python
from src.apollo import search_people, enrich_people


@pytest.mark.asyncio
async def test_enrich_people_returns_emails():
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "matches": [
            {
                "id": "abc123",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@acme.com",
                "title": "CEO",
                "organization": {"name": "Acme Inc"},
                "linkedin_url": "https://linkedin.com/in/johndoe"
            }
        ]
    }
    mock_response.raise_for_status = lambda: None

    with patch("src.apollo.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        people = [{"id": "abc123", "first_name": "John", "last_name": "Doe"}]
        results = await enrich_people(people)

        assert len(results) == 1
        assert results[0]["email"] == "john@acme.com"


@pytest.mark.asyncio
async def test_enrich_people_empty_list():
    results = await enrich_people([])
    assert results == []
```

### Step 2: Run test to verify it fails

Run: `python -m pytest tests/test_apollo.py::test_enrich_people_returns_emails -v`

Expected: FAIL with `ImportError: cannot import name 'enrich_people'`

### Step 3: Implement enrich_people

Add to `src/apollo.py`:

```python
async def enrich_people(people: list[dict]) -> list[dict]:
    """Bulk enrich people to get email addresses.

    Accepts up to 10 people per call.
    Returns enriched person dicts with email field.
    """
    if not people:
        return []

    if not APOLLO_API_KEY:
        log.warning("apollo_api_key_not_set")
        return []

    try:
        # Build match requests from people data
        details = []
        for person in people[:10]:  # Max 10 per call
            org = person.get("organization", {})
            details.append({
                "first_name": person.get("first_name"),
                "last_name": person.get("last_name"),
                "organization_name": org.get("name") if isinstance(org, dict) else None,
                "linkedin_url": person.get("linkedin_url"),
            })

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{BASE_URL}/people/bulk_match",
                headers={
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache",
                },
                json={
                    "api_key": APOLLO_API_KEY,
                    "details": details,
                },
            )
            response.raise_for_status()
            data = response.json()

            matches = data.get("matches", [])
            log.info("apollo_enrich_complete", requested=len(people), matched=len(matches))
            return matches

    except Exception as e:
        log.error("apollo_enrich_error", error=str(e))
        return []
```

### Step 4: Run tests to verify they pass

Run: `python -m pytest tests/test_apollo.py::test_enrich_people_returns_emails tests/test_apollo.py::test_enrich_people_empty_list -v`

Expected: PASS

### Step 5: Commit

```bash
git add src/apollo.py tests/test_apollo.py
git commit -m "feat(apollo): add enrich_people function"
```

---

## Task 14: Apollo Client - find_leads_at_company

**Files:**
- Modify: `src/apollo.py`
- Modify: `tests/test_apollo.py`

### Step 1: Write failing test for find_leads_at_company

Add to `tests/test_apollo.py`:

```python
from src.apollo import search_people, enrich_people, find_leads_at_company


@pytest.mark.asyncio
async def test_find_leads_at_company_returns_leads_with_email():
    with patch("src.apollo.search_people") as mock_search:
        with patch("src.apollo.enrich_people") as mock_enrich:
            mock_search.return_value = [
                {"id": "1", "first_name": "John", "last_name": "Doe", "title": "CEO",
                 "organization": {"name": "Acme"}, "linkedin_url": "https://linkedin.com/in/john"}
            ]
            mock_enrich.return_value = [
                {"id": "1", "first_name": "John", "last_name": "Doe", "email": "john@acme.com",
                 "title": "CEO", "organization": {"name": "Acme"}, "linkedin_url": "https://linkedin.com/in/john"}
            ]

            results = await find_leads_at_company("acme.com", ["CEO"], max_leads=3)

            assert len(results) == 1
            assert results[0]["email"] == "john@acme.com"
            assert results[0]["first_name"] == "John"
            assert results[0]["company"] == "Acme"


@pytest.mark.asyncio
async def test_find_leads_at_company_filters_no_email():
    with patch("src.apollo.search_people") as mock_search:
        with patch("src.apollo.enrich_people") as mock_enrich:
            mock_search.return_value = [{"id": "1", "first_name": "John"}]
            mock_enrich.return_value = [
                {"id": "1", "first_name": "John", "email": None},  # No email
            ]

            results = await find_leads_at_company("acme.com", ["CEO"])

            assert len(results) == 0
```

### Step 2: Run test to verify it fails

Run: `python -m pytest tests/test_apollo.py::test_find_leads_at_company_returns_leads_with_email -v`

Expected: FAIL with `ImportError: cannot import name 'find_leads_at_company'`

### Step 3: Implement find_leads_at_company

Add to `src/apollo.py`:

```python
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

    # Format results and filter out those without email
    results = []
    for person in enriched:
        email = person.get("email")
        if not email:
            continue

        org = person.get("organization", {})
        company_name = org.get("name") if isinstance(org, dict) else None

        results.append({
            "email": email,
            "first_name": person.get("first_name"),
            "last_name": person.get("last_name"),
            "company": company_name,
            "title": person.get("title"),
            "linkedin_url": person.get("linkedin_url"),
        })

    return results
```

### Step 4: Run tests to verify they pass

Run: `python -m pytest tests/test_apollo.py::test_find_leads_at_company_returns_leads_with_email tests/test_apollo.py::test_find_leads_at_company_filters_no_email -v`

Expected: PASS

### Step 5: Commit

```bash
git add src/apollo.py tests/test_apollo.py
git commit -m "feat(apollo): add find_leads_at_company function"
```

---

## Task 15: Lead Generator - generate_leads Dry Run

**Files:**
- Create: `src/lead_generator.py`
- Create: `tests/test_lead_generator.py`

### Step 1: Write failing test for generate_leads dry run

Create `tests/test_lead_generator.py`:

```python
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock

from src.db import init_db, is_company_searched
from src.lead_generator import generate_leads


@pytest.mark.asyncio
async def test_generate_leads_dry_run():
    """Test dry run doesn't insert records."""
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

            assert result["dry_run"] is True
            assert result["companies_checked"] == 1
            assert result["leads_added"] == 0

            # Company should NOT be marked as searched in dry run
            assert not is_company_searched(db_path, "test.com")
```

### Step 2: Run test to verify it fails

Run: `python -m pytest tests/test_lead_generator.py::test_generate_leads_dry_run -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'src.lead_generator'`

### Step 3: Create src/lead_generator.py

Create `src/lead_generator.py`:

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
        return {"leads_added": 0, "companies_checked": 0, "quota_reached": True, "dry_run": dry_run}

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
            country=config.search.countries[0],
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
            await asyncio.sleep(0.1)

    return results
```

### Step 4: Run test to verify it passes

Run: `python -m pytest tests/test_lead_generator.py::test_generate_leads_dry_run -v`

Expected: PASS

### Step 5: Commit

```bash
git add src/lead_generator.py tests/test_lead_generator.py
git commit -m "feat(lead_generator): add generate_leads orchestrator"
```

---

## Task 16: Lead Generator - Skip Already Searched Companies

**Files:**
- Modify: `tests/test_lead_generator.py`

### Step 1: Write test for skipping searched companies

Add to `tests/test_lead_generator.py`:

```python
from src.db import init_db, is_company_searched, insert_searched_company


@pytest.mark.asyncio
async def test_generate_leads_skips_searched_companies():
    """Test that already-searched companies are skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        config_path = Path(tmpdir)

        init_db(db_path)

        # Pre-mark a company as searched
        insert_searched_company(db_path, "already-searched.com", "Already", "test", "111")

        (config_path / "lead_gen.yaml").write_text("""
search:
  keywords: ["test"]
targeting:
  job_titles: ["CEO"]
quotas:
  leads_per_day: 10
  max_companies_to_check: 10
""")

        with patch("src.lead_generator.get_advertiser_domains") as mock_fb:
            with patch("src.lead_generator.find_leads_at_company") as mock_apollo:
                mock_fb.return_value = [
                    {"domain": "already-searched.com", "page_id": "111", "company_name": "Already"},
                    {"domain": "new-company.com", "page_id": "222", "company_name": "New"},
                ]
                mock_apollo.return_value = [
                    {"email": "lead@new.com", "first_name": "New", "last_name": "Lead",
                     "company": "New", "title": "CEO", "linkedin_url": None}
                ]

                result = await generate_leads(db_path=db_path, config_path=config_path)

                assert result["companies_skipped"] == 1
                assert result["companies_checked"] == 1
                assert result["leads_added"] == 1
```

### Step 2: Run test to verify it passes

Run: `python -m pytest tests/test_lead_generator.py::test_generate_leads_skips_searched_companies -v`

Expected: PASS (already implemented)

### Step 3: Commit

```bash
git add tests/test_lead_generator.py
git commit -m "test(lead_generator): add test for skipping searched companies"
```

---

## Task 17: Lead Generator - Respect Daily Quota

**Files:**
- Modify: `tests/test_lead_generator.py`

### Step 1: Write test for daily quota enforcement

Add to `tests/test_lead_generator.py`:

```python
from src.db import init_db, is_company_searched, insert_searched_company, insert_lead


@pytest.mark.asyncio
async def test_generate_leads_respects_daily_quota():
    """Test daily quota enforcement."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        config_path = Path(tmpdir)

        init_db(db_path)

        # Pre-add leads to hit quota
        insert_lead(db_path, "existing1@test.com", "One", None, None, None, None)
        insert_lead(db_path, "existing2@test.com", "Two", None, None, None, None)

        # Set quota to 2 (already at quota)
        (config_path / "lead_gen.yaml").write_text("""
search:
  keywords: ["test"]
targeting:
  job_titles: ["CEO"]
quotas:
  leads_per_day: 2
  max_companies_to_check: 10
""")

        result = await generate_leads(db_path=db_path, config_path=config_path)

        assert result["quota_reached"] is True
        assert result["leads_added"] == 0
```

### Step 2: Run test to verify it passes

Run: `python -m pytest tests/test_lead_generator.py::test_generate_leads_respects_daily_quota -v`

Expected: PASS

### Step 3: Commit

```bash
git add tests/test_lead_generator.py
git commit -m "test(lead_generator): add test for daily quota enforcement"
```

---

## Task 18: CLI - Add generate Command

**Files:**
- Modify: `src/cli.py`
- Modify: `tests/test_cli.py`

### Step 1: Write failing test for generate command

Add to `tests/test_cli.py`:

```python
from click.testing import CliRunner

from src.cli import cli


def test_generate_command_dry_run(tmp_path, monkeypatch):
    """Test generate command with --dry-run flag."""
    from unittest.mock import patch, AsyncMock

    db_path = tmp_path / "test.db"
    config_path = tmp_path

    # Create config
    (config_path / "lead_gen.yaml").write_text("""
search:
  keywords: ["test"]
targeting:
  job_titles: ["CEO"]
quotas:
  leads_per_day: 5
  max_companies_to_check: 10
""")

    with patch("src.cli.generate_leads") as mock_generate:
        mock_generate.return_value = {
            "leads_added": 0,
            "companies_checked": 3,
            "companies_skipped": 1,
            "quota_reached": False,
            "dry_run": True
        }

        runner = CliRunner()
        result = runner.invoke(cli, [
            "generate",
            "--db", str(db_path),
            "--config", str(config_path),
            "--dry-run"
        ])

        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "Leads added: 0" in result.output
        assert "Companies checked: 3" in result.output
```

### Step 2: Run test to verify it fails

Run: `python -m pytest tests/test_cli.py::test_generate_command_dry_run -v`

Expected: FAIL with error about missing `generate` command

### Step 3: Add generate command to cli.py

Add to `src/cli.py` after imports:

```python
from src.lead_generator import generate_leads
```

Add the command after the `status` command:

```python
@cli.command()
@click.option("--db", "db_path", type=click.Path(), default=str(DEFAULT_DB_PATH),
              help="Database path")
@click.option("--config", "config_path", type=click.Path(), default=str(DEFAULT_CONFIG_PATH),
              help="Config directory path")
@click.option("--dry-run", is_flag=True, help="Show what would be generated without making API calls")
@click.option("--keyword", help="Override search keyword for this run")
def generate(db_path: str, config_path: str, dry_run: bool, keyword: str):
    """Generate new leads from FB Ad Library + Apollo."""
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

### Step 4: Run test to verify it passes

Run: `python -m pytest tests/test_cli.py::test_generate_command_dry_run -v`

Expected: PASS

### Step 5: Commit

```bash
git add src/cli.py tests/test_cli.py
git commit -m "feat(cli): add generate command for lead generation"
```

---

## Task 19: Update .env Template

**Files:**
- Modify: `.env.example` (if exists) or document in README

### Step 1: Document required environment variables

Ensure `.env` includes (or `.env.example` documents):

```
ANTHROPIC_API_KEY=...
COMPOSIO_API_KEY=...
APIFY_API_KEY=...
SCRAPECREATORS_API_KEY=...   # NEW - for FB Ad Library
APOLLO_API_KEY=...            # NEW - for people search
```

### Step 2: Commit

```bash
git add .env.example 2>/dev/null || true
git commit -m "docs: add SCRAPECREATORS and APOLLO API keys to env template" --allow-empty
```

---

## Task 20: Run All Tests

**Verification:**

### Step 1: Run full test suite

Run: `python -m pytest -v`

Expected: All tests pass

### Step 2: Run linting (if configured)

Run: `python -m ruff check src/ tests/`

Expected: No errors (or fix any that appear)

### Step 3: Final commit

```bash
git add -A
git commit -m "chore: final cleanup for lead generation feature"
```

---

## Verification Checklist

After implementation, verify with:

1. **Unit tests:**
   ```bash
   python -m pytest tests/test_lead_generator.py tests/test_fb_ads.py tests/test_apollo.py -v
   ```

2. **Dry run:**
   ```bash
   python run.py generate --dry-run
   ```

3. **Single keyword test (requires API keys):**
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

## Summary

**20 tasks total**, each with TDD workflow:
1. Write failing test
2. Run test (verify failure)
3. Implement minimal code
4. Run test (verify pass)
5. Commit

**Files created:**
- `src/fb_ads.py`
- `src/apollo.py`
- `src/lead_generator.py`
- `tests/test_fb_ads.py`
- `tests/test_apollo.py`
- `tests/test_lead_generator.py`
- `config/lead_gen.yaml`

**Files modified:**
- `src/db.py`
- `src/config.py`
- `src/cli.py`
- `tests/test_db.py`
- `tests/test_config.py`
- `tests/test_cli.py`
