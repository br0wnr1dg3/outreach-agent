# Outreach Boilerplate Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a CLI tool for humor-first cold email outreach with LinkedIn personalization.

**Architecture:** CLI commands (import, send, status) backed by SQLite for state, Apify for LinkedIn scraping, Claude Opus 4.5 for joke generation, and Composio for Gmail threading.

**Tech Stack:** Python 3.11+, uv, SQLite, anthropic, composio-core, httpx, openpyxl, pydantic, structlog

---

## Task 1: Project Setup

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `src/__init__.py`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "outreach-boilerplate"
version = "0.1.0"
description = "Humor-first cold email outreach CLI"
requires-python = ">=3.11"

dependencies = [
    "anthropic>=0.40.0",
    "composio-core>=0.5.0",
    "openpyxl>=3.1.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0.0",
    "httpx>=0.27.0",
    "structlog>=24.0.0",
]

[project.scripts]
outreach = "src.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Step 2: Create .env.example**

```bash
# Required API Keys
ANTHROPIC_API_KEY=sk-ant-...
COMPOSIO_API_KEY=...
APIFY_API_KEY=...

# Optional
LOG_LEVEL=INFO
```

**Step 3: Create .gitignore**

```
# Environment
.env
.venv/
__pycache__/

# Data
data/outreach.db

# IDE
.idea/
.vscode/

# OS
.DS_Store
```

**Step 4: Create src/__init__.py**

```python
"""Outreach boilerplate - humor-first cold email CLI."""
```

**Step 5: Install dependencies**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv sync`
Expected: Dependencies installed successfully

**Step 6: Commit**

```bash
git add -A
git commit -m "chore: project setup with dependencies"
```

---

## Task 2: Database Schema

**Files:**
- Create: `src/db.py`
- Create: `tests/__init__.py`
- Create: `tests/test_db.py`

**Step 1: Write failing test for database initialization**

Create `tests/__init__.py`:
```python
"""Tests for outreach boilerplate."""
```

Create `tests/test_db.py`:
```python
import tempfile
from pathlib import Path

from src.db import init_db, get_connection


def test_init_db_creates_tables():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        conn = get_connection(db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "leads" in tables
        assert "sent_emails" in tables
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv run pytest tests/test_db.py -v`
Expected: FAIL with "ModuleNotFoundError" or "cannot import name 'init_db'"

**Step 3: Write database implementation**

Create `src/db.py`:
```python
"""SQLite database operations."""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional
import json

DEFAULT_DB_PATH = Path("data/outreach.db")


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Get a database connection with row factory."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    """Initialize database with schema."""
    conn = get_connection(db_path)

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT,
            company TEXT,
            title TEXT,
            linkedin_url TEXT,

            -- Enrichment data
            linkedin_posts TEXT,
            enriched_at TIMESTAMP,
            enrichment_attempts INTEGER DEFAULT 0,

            -- Sequence state
            status TEXT DEFAULT 'new',
            current_step INTEGER DEFAULT 0,

            -- Gmail threading
            thread_id TEXT,
            last_message_id TEXT,

            -- Timing
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_sent_at TIMESTAMP,
            next_send_at TIMESTAMP,

            -- Generated content
            email_1_subject TEXT,
            email_1_body TEXT
        );

        CREATE TABLE IF NOT EXISTS sent_emails (
            id INTEGER PRIMARY KEY,
            lead_id INTEGER REFERENCES leads(id),
            step INTEGER NOT NULL,
            subject TEXT,
            body TEXT,
            gmail_message_id TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
        CREATE INDEX IF NOT EXISTS idx_leads_next_send ON leads(next_send_at);
    """)

    conn.commit()
    conn.close()
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv run pytest tests/test_db.py -v`
Expected: PASS

**Step 5: Add tests for lead CRUD operations**

Add to `tests/test_db.py`:
```python
from src.db import (
    init_db, get_connection,
    insert_lead, get_lead_by_email, get_leads_by_status,
    update_lead_status, count_sent_today
)


def test_insert_and_get_lead():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        lead_id = insert_lead(
            db_path=db_path,
            email="test@example.com",
            first_name="Test",
            last_name="User",
            company="Acme Inc",
            title="CEO",
            linkedin_url="https://linkedin.com/in/testuser"
        )

        assert lead_id is not None

        lead = get_lead_by_email(db_path, "test@example.com")
        assert lead is not None
        assert lead["first_name"] == "Test"
        assert lead["company"] == "Acme Inc"
        assert lead["status"] == "new"


def test_insert_duplicate_returns_none():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        lead_id1 = insert_lead(db_path, "dupe@example.com", "First", None, None, None, None)
        lead_id2 = insert_lead(db_path, "dupe@example.com", "Second", None, None, None, None)

        assert lead_id1 is not None
        assert lead_id2 is None  # Duplicate


def test_get_leads_by_status():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        insert_lead(db_path, "new1@test.com", "One", None, None, None, None)
        insert_lead(db_path, "new2@test.com", "Two", None, None, None, None)

        leads = get_leads_by_status(db_path, "new")
        assert len(leads) == 2


def test_count_sent_today():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        count = count_sent_today(db_path)
        assert count == 0
```

**Step 6: Run tests to verify they fail**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv run pytest tests/test_db.py -v`
Expected: FAIL with "cannot import name 'insert_lead'"

**Step 7: Implement CRUD operations**

Add to `src/db.py`:
```python
def insert_lead(
    db_path: Path,
    email: str,
    first_name: str,
    last_name: Optional[str],
    company: Optional[str],
    title: Optional[str],
    linkedin_url: Optional[str],
) -> Optional[int]:
    """Insert a lead. Returns lead_id or None if duplicate."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            INSERT INTO leads (email, first_name, last_name, company, title, linkedin_url)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (email, first_name, last_name, company, title, linkedin_url)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_lead_by_email(db_path: Path, email: str) -> Optional[sqlite3.Row]:
    """Get a lead by email."""
    conn = get_connection(db_path)
    cursor = conn.execute("SELECT * FROM leads WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_lead_by_id(db_path: Path, lead_id: int) -> Optional[sqlite3.Row]:
    """Get a lead by ID."""
    conn = get_connection(db_path)
    cursor = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_leads_by_status(db_path: Path, status: str) -> list[sqlite3.Row]:
    """Get all leads with a given status."""
    conn = get_connection(db_path)
    cursor = conn.execute("SELECT * FROM leads WHERE status = ?", (status,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def update_lead_status(db_path: Path, lead_id: int, status: str) -> None:
    """Update a lead's status."""
    conn = get_connection(db_path)
    conn.execute("UPDATE leads SET status = ? WHERE id = ?", (status, lead_id))
    conn.commit()
    conn.close()


def update_lead_enrichment(
    db_path: Path,
    lead_id: int,
    linkedin_posts: list[str],
    success: bool
) -> None:
    """Update lead with enrichment data."""
    conn = get_connection(db_path)
    posts_json = json.dumps(linkedin_posts) if linkedin_posts else None

    if success:
        conn.execute(
            """
            UPDATE leads
            SET linkedin_posts = ?, enriched_at = ?, enrichment_attempts = enrichment_attempts + 1
            WHERE id = ?
            """,
            (posts_json, datetime.utcnow().isoformat(), lead_id)
        )
    else:
        conn.execute(
            "UPDATE leads SET enrichment_attempts = enrichment_attempts + 1 WHERE id = ?",
            (lead_id,)
        )

    conn.commit()
    conn.close()


def update_lead_email_sent(
    db_path: Path,
    lead_id: int,
    step: int,
    subject: str,
    body: str,
    thread_id: str,
    message_id: str,
    next_send_at: Optional[datetime]
) -> None:
    """Update lead after sending an email."""
    conn = get_connection(db_path)

    # Update lead record
    if step == 1:
        conn.execute(
            """
            UPDATE leads
            SET status = 'active', current_step = ?, thread_id = ?, last_message_id = ?,
                last_sent_at = ?, next_send_at = ?, email_1_subject = ?, email_1_body = ?
            WHERE id = ?
            """,
            (step, thread_id, message_id, datetime.utcnow().isoformat(),
             next_send_at.isoformat() if next_send_at else None, subject, body, lead_id)
        )
    else:
        new_status = 'completed' if step == 3 else 'active'
        conn.execute(
            """
            UPDATE leads
            SET status = ?, current_step = ?, last_message_id = ?,
                last_sent_at = ?, next_send_at = ?
            WHERE id = ?
            """,
            (new_status, step, message_id, datetime.utcnow().isoformat(),
             next_send_at.isoformat() if next_send_at else None, lead_id)
        )

    # Record in sent_emails
    conn.execute(
        """
        INSERT INTO sent_emails (lead_id, step, subject, body, gmail_message_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (lead_id, step, subject, body, message_id)
    )

    conn.commit()
    conn.close()


def get_leads_due_for_followup(db_path: Path) -> list[sqlite3.Row]:
    """Get active leads due for follow-up."""
    conn = get_connection(db_path)
    cursor = conn.execute(
        """
        SELECT * FROM leads
        WHERE status = 'active'
        AND next_send_at <= ?
        AND current_step < 3
        """,
        (datetime.utcnow().isoformat(),)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def count_sent_today(db_path: Path) -> int:
    """Count emails sent today."""
    conn = get_connection(db_path)
    today = datetime.utcnow().date().isoformat()
    cursor = conn.execute(
        "SELECT COUNT(*) FROM sent_emails WHERE date(sent_at) = ?",
        (today,)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_pipeline_stats(db_path: Path) -> dict:
    """Get pipeline statistics."""
    conn = get_connection(db_path)

    stats = {}

    # Count by status
    cursor = conn.execute(
        "SELECT status, COUNT(*) as count FROM leads GROUP BY status"
    )
    for row in cursor.fetchall():
        stats[row["status"]] = row["count"]

    # Count due for follow-up
    cursor = conn.execute(
        """
        SELECT COUNT(*) FROM leads
        WHERE status = 'active' AND next_send_at <= ? AND current_step < 3
        """,
        (datetime.utcnow().isoformat(),)
    )
    stats["due_for_followup"] = cursor.fetchone()[0]

    # Count sent today
    stats["sent_today"] = count_sent_today(db_path)

    conn.close()
    return stats
```

**Step 8: Run all tests**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv run pytest tests/test_db.py -v`
Expected: All PASS

**Step 9: Commit**

```bash
git add -A
git commit -m "feat: add database schema and CRUD operations"
```

---

## Task 3: Configuration Loading

**Files:**
- Create: `src/config.py`
- Create: `config/settings.yaml`
- Create: `config/context.md`
- Create: `config/email_1.md`
- Create: `config/followup_1.md`
- Create: `config/followup_2.md`
- Create: `tests/test_config.py`

**Step 1: Write failing test for config loading**

Create `tests/test_config.py`:
```python
import tempfile
from pathlib import Path

from src.config import load_settings, load_template, Settings


def test_load_settings():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir)
        settings_file = config_path / "settings.yaml"
        settings_file.write_text("""
sequence:
  email_2_delay_days: 3
  email_3_delay_days: 4

sending:
  daily_limit: 50
  min_delay_seconds: 20
  max_delay_seconds: 60

gmail:
  from_name: "Test"
""")

        settings = load_settings(config_path)

        assert settings.sequence.email_2_delay_days == 3
        assert settings.sending.daily_limit == 50
        assert settings.gmail.from_name == "Test"


def test_load_template():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir)
        template_file = config_path / "test_template.md"
        template_file.write_text("Hello {{first_name}}!")

        content = load_template(config_path, "test_template.md")

        assert content == "Hello {{first_name}}!"
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv run pytest tests/test_config.py -v`
Expected: FAIL with "cannot import name 'load_settings'"

**Step 3: Implement config loading**

Create `src/config.py`:
```python
"""Configuration loading and models."""

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel


class SequenceConfig(BaseModel):
    email_2_delay_days: int = 3
    email_3_delay_days: int = 4


class SendingConfig(BaseModel):
    daily_limit: int = 50
    min_delay_seconds: int = 20
    max_delay_seconds: int = 60


class GmailConfig(BaseModel):
    from_name: str = "Chris"


class Settings(BaseModel):
    sequence: SequenceConfig = SequenceConfig()
    sending: SendingConfig = SendingConfig()
    gmail: GmailConfig = GmailConfig()


DEFAULT_CONFIG_PATH = Path("config")


def load_settings(config_path: Path = DEFAULT_CONFIG_PATH) -> Settings:
    """Load settings from YAML file."""
    settings_file = config_path / "settings.yaml"

    if not settings_file.exists():
        return Settings()

    with open(settings_file) as f:
        data = yaml.safe_load(f) or {}

    return Settings(**data)


def load_template(config_path: Path, template_name: str) -> str:
    """Load a template file."""
    template_file = config_path / template_name
    return template_file.read_text()


def render_template(template: str, variables: dict) -> str:
    """Render a template with variable substitution."""
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", str(value) if value else "")
    return result
```

**Step 4: Run tests**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv run pytest tests/test_config.py -v`
Expected: All PASS

**Step 5: Create default config files**

Create `config/settings.yaml`:
```yaml
# Sequence timing
sequence:
  email_2_delay_days: 3
  email_3_delay_days: 4    # Days after email 2 (7 total from email 1)

# Rate limiting
sending:
  daily_limit: 50          # Max emails per day
  min_delay_seconds: 20    # Min gap between sends
  max_delay_seconds: 60    # Max gap between sends

# Gmail account
gmail:
  from_name: "Chris"
```

Create `config/context.md`:
```markdown
## Company
Cheerful - creator affiliate platform

## Value Prop
Help brands turn creators into affiliates without the usual chaos.

## Tone
Curious, casual, not salesy. Self-aware about cold emailing. Humor-first.

## CTA
Quick call to learn about their creator strategy
```

Create `config/email_1.md`:
```markdown
subject: {{generated_subject}}

Hey {{first_name}},

{{generated_joke_opener}}

I'm with Cheerful - we help brands like {{company}} turn creators into affiliates without the usual headaches.

Curious if you're exploring anything on the creator/affiliate side right now?

Either way, happy to share what's working for similar brands.

Chris
```

Create `config/followup_1.md`:
```markdown
subject: re: {{original_subject}}

Hey {{first_name}},

Following up on my own cold email. The audacity continues.

Genuinely curious if creator/affiliate stuff is on your radar or if I should take the hint.

Chris
```

Create `config/followup_2.md`:
```markdown
subject: re: {{original_subject}}

Hey {{first_name}},

Last one, I promise. After this I'll quietly accept defeat and move on with my life.

If timing's just bad, happy to reconnect later. If it's a "not interested" - totally get it, no hard feelings.

Chris
```

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: add configuration loading and default templates"
```

---

## Task 4: Excel Importer

**Files:**
- Create: `src/importer.py`
- Create: `data/leads_example.xlsx`
- Create: `tests/test_importer.py`

**Step 1: Write failing test**

Create `tests/test_importer.py`:
```python
import tempfile
from pathlib import Path

from openpyxl import Workbook

from src.db import init_db, get_leads_by_status
from src.importer import import_leads


def test_import_leads_from_excel():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "test.db"
        excel_path = tmpdir / "leads.xlsx"

        # Create test Excel file
        wb = Workbook()
        ws = wb.active
        ws.append(["email", "first_name", "last_name", "company", "title", "linkedin_url"])
        ws.append(["alice@test.com", "Alice", "Smith", "Acme", "CEO", "https://linkedin.com/in/alice"])
        ws.append(["bob@test.com", "Bob", "Jones", "Beta Inc", "CTO", "https://linkedin.com/in/bob"])
        wb.save(excel_path)

        # Initialize DB and import
        init_db(db_path)
        result = import_leads(excel_path, db_path)

        assert result["imported"] == 2
        assert result["skipped"] == 0

        leads = get_leads_by_status(db_path, "new")
        assert len(leads) == 2


def test_import_skips_duplicates():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "test.db"
        excel_path = tmpdir / "leads.xlsx"

        wb = Workbook()
        ws = wb.active
        ws.append(["email", "first_name", "last_name", "company", "title", "linkedin_url"])
        ws.append(["same@test.com", "First", "", "", "", ""])
        ws.append(["same@test.com", "Second", "", "", "", ""])  # Duplicate
        wb.save(excel_path)

        init_db(db_path)
        result = import_leads(excel_path, db_path)

        assert result["imported"] == 1
        assert result["skipped"] == 1
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv run pytest tests/test_importer.py -v`
Expected: FAIL with "cannot import name 'import_leads'"

**Step 3: Implement importer**

Create `src/importer.py`:
```python
"""Excel lead importer."""

from pathlib import Path

import structlog
from openpyxl import Workbook, load_workbook

from src.db import DEFAULT_DB_PATH, insert_lead

log = structlog.get_logger()


def import_leads(excel_path: Path, db_path: Path = DEFAULT_DB_PATH) -> dict:
    """Import leads from Excel file.

    Expected columns: email, first_name, last_name, company, title, linkedin_url

    Returns dict with imported and skipped counts.
    """
    wb = load_workbook(excel_path)
    ws = wb.active

    # Get header row
    headers = [cell.value.lower().strip() if cell.value else "" for cell in ws[1]]

    required = {"email", "first_name"}
    if not required.issubset(set(headers)):
        raise ValueError(f"Excel must have columns: {required}. Found: {headers}")

    # Map column indices
    col_map = {name: idx for idx, name in enumerate(headers)}

    imported = 0
    skipped = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        email = row[col_map["email"]]
        if not email:
            continue

        email = email.strip().lower()
        first_name = row[col_map["first_name"]]

        if not first_name:
            log.warning("skipping_row_no_first_name", email=email)
            skipped += 1
            continue

        lead_id = insert_lead(
            db_path=db_path,
            email=email,
            first_name=first_name.strip(),
            last_name=row[col_map.get("last_name", -1)] if col_map.get("last_name") is not None and col_map["last_name"] < len(row) else None,
            company=row[col_map.get("company", -1)] if col_map.get("company") is not None and col_map["company"] < len(row) else None,
            title=row[col_map.get("title", -1)] if col_map.get("title") is not None and col_map["title"] < len(row) else None,
            linkedin_url=row[col_map.get("linkedin_url", -1)] if col_map.get("linkedin_url") is not None and col_map["linkedin_url"] < len(row) else None,
        )

        if lead_id:
            log.info("lead_imported", email=email, lead_id=lead_id)
            imported += 1
        else:
            log.info("lead_skipped_duplicate", email=email)
            skipped += 1

    return {"imported": imported, "skipped": skipped}


def create_example_excel(output_path: Path) -> None:
    """Create an example Excel file showing expected format."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Leads"

    # Headers
    ws.append(["email", "first_name", "last_name", "company", "title", "linkedin_url"])

    # Example rows
    ws.append([
        "sarah@glossybrand.com",
        "Sarah",
        "Chen",
        "Glossy Brand",
        "Marketing Director",
        "https://linkedin.com/in/sarahchen"
    ])
    ws.append([
        "mike@acmeco.com",
        "Mike",
        "Johnson",
        "Acme Co",
        "Head of Growth",
        "https://linkedin.com/in/mikej"
    ])

    wb.save(output_path)
```

**Step 4: Run tests**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv run pytest tests/test_importer.py -v`
Expected: All PASS

**Step 5: Create example Excel file**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && mkdir -p data && uv run python -c "from src.importer import create_example_excel; from pathlib import Path; create_example_excel(Path('data/leads_example.xlsx'))"`
Expected: File created at data/leads_example.xlsx

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: add Excel lead importer"
```

---

## Task 5: LinkedIn Enricher (Apify)

**Files:**
- Create: `src/enricher.py`
- Create: `tests/test_enricher.py`

**Step 1: Write failing test with mock**

Create `tests/test_enricher.py`:
```python
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.db import init_db, insert_lead, get_lead_by_id
from src.enricher import enrich_lead, scrape_linkedin_posts


@pytest.mark.asyncio
async def test_scrape_linkedin_posts_success():
    mock_response = {
        "recentPosts": [
            {"text": "Excited about our new product launch!"},
            {"text": "Q4 is always organized chaos."},
        ]
    }

    with patch("src.enricher.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value.json.return_value = mock_response
        mock_instance.get.return_value.status_code = 200
        mock_client.return_value.__aenter__.return_value = mock_instance

        posts = await scrape_linkedin_posts("https://linkedin.com/in/test")

        assert len(posts) == 2
        assert "new product launch" in posts[0]


@pytest.mark.asyncio
async def test_scrape_linkedin_posts_empty():
    mock_response = {"recentPosts": []}

    with patch("src.enricher.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value.json.return_value = mock_response
        mock_instance.get.return_value.status_code = 200
        mock_client.return_value.__aenter__.return_value = mock_instance

        posts = await scrape_linkedin_posts("https://linkedin.com/in/test")

        assert posts == []


@pytest.mark.asyncio
async def test_enrich_lead_updates_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        lead_id = insert_lead(
            db_path, "test@example.com", "Test", None, "Acme", None,
            "https://linkedin.com/in/test"
        )

        mock_posts = ["Post about marketing", "Another post"]

        with patch("src.enricher.scrape_linkedin_posts", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = mock_posts

            result = await enrich_lead(lead_id, db_path)

            assert result["success"] is True
            assert result["posts"] == mock_posts

            lead = get_lead_by_id(db_path, lead_id)
            assert lead["enriched_at"] is not None
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv run pytest tests/test_enricher.py -v`
Expected: FAIL with "cannot import name 'enrich_lead'"

**Step 3: Implement enricher**

Create `src/enricher.py`:
```python
"""LinkedIn profile enrichment via Apify."""

import os
from pathlib import Path
from typing import Optional

import httpx
import structlog

from src.db import DEFAULT_DB_PATH, get_lead_by_id, update_lead_enrichment

log = structlog.get_logger()

APIFY_API_KEY = os.getenv("APIFY_API_KEY", "")
APIFY_ACTOR_ID = "curious_coder/linkedin-profile-scraper"
APIFY_BASE_URL = "https://api.apify.com/v2"


async def scrape_linkedin_posts(linkedin_url: str) -> list[str]:
    """Scrape recent posts from a LinkedIn profile using Apify.

    Returns list of post text content.
    """
    if not APIFY_API_KEY:
        log.warning("apify_api_key_not_set")
        return []

    # Run the actor synchronously
    run_url = f"{APIFY_BASE_URL}/acts/{APIFY_ACTOR_ID}/run-sync-get-dataset-items"

    payload = {
        "startUrls": [{"url": linkedin_url}],
        "includeRecentPosts": True,
        "maxPosts": 5,
    }

    headers = {
        "Authorization": f"Bearer {APIFY_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(run_url, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()

            if not data or len(data) == 0:
                return []

            profile = data[0]
            posts = profile.get("recentPosts", [])

            return [post.get("text", "") for post in posts if post.get("text")]

    except httpx.HTTPError as e:
        log.error("apify_request_failed", error=str(e))
        return []
    except Exception as e:
        log.error("apify_unexpected_error", error=str(e))
        return []


async def enrich_lead(lead_id: int, db_path: Path = DEFAULT_DB_PATH) -> dict:
    """Enrich a lead with LinkedIn data.

    Returns dict with success status and posts.
    """
    lead = get_lead_by_id(db_path, lead_id)

    if not lead:
        log.error("lead_not_found", lead_id=lead_id)
        return {"success": False, "posts": [], "error": "Lead not found"}

    linkedin_url = lead["linkedin_url"]

    if not linkedin_url:
        log.info("no_linkedin_url", lead_id=lead_id, email=lead["email"])
        update_lead_enrichment(db_path, lead_id, [], success=True)
        return {"success": True, "posts": [], "note": "No LinkedIn URL"}

    log.info("enriching_lead", lead_id=lead_id, email=lead["email"])

    try:
        posts = await scrape_linkedin_posts(linkedin_url)
        update_lead_enrichment(db_path, lead_id, posts, success=True)

        log.info("enrichment_complete", lead_id=lead_id, post_count=len(posts))
        return {"success": True, "posts": posts}

    except Exception as e:
        log.error("enrichment_failed", lead_id=lead_id, error=str(e))
        update_lead_enrichment(db_path, lead_id, [], success=False)
        return {"success": False, "posts": [], "error": str(e)}
```

**Step 4: Run tests**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv run pytest tests/test_enricher.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: add LinkedIn enricher via Apify"
```

---

## Task 6: Email Composer (Claude)

**Files:**
- Create: `src/composer.py`
- Create: `tests/test_composer.py`

**Step 1: Write failing test with mock**

Create `tests/test_composer.py`:
```python
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.composer import generate_email_1, build_system_prompt


def test_build_system_prompt():
    context = "## Company\nTest Corp\n\n## Value Prop\nWe do things."

    prompt = build_system_prompt(context)

    assert "Test Corp" in prompt
    assert "humor" in prompt.lower() or "joke" in prompt.lower()
    assert "personalized" in prompt.lower()


@pytest.mark.asyncio
async def test_generate_email_1():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir)

        # Create config files
        (config_path / "context.md").write_text("## Company\nTest Corp")
        (config_path / "email_1.md").write_text(
            "subject: {{generated_subject}}\n\n"
            "Hey {{first_name}},\n\n"
            "{{generated_joke_opener}}\n\n"
            "Rest of email.\n\nChris"
        )

        lead = {
            "first_name": "Sarah",
            "last_name": "Chen",
            "company": "Glossy",
            "title": "Marketing Director",
            "email": "sarah@glossy.com",
        }

        posts = ["Just survived another Q4 planning session!"]

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text='{"subject": "surviving q4 together", "joke_opener": "Your post about Q4 planning made me feel seen. Here I am adding to your inbox chaos."}')
        ]

        with patch("src.composer.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            subject, body = await generate_email_1(lead, posts, config_path)

            assert "q4" in subject.lower()
            assert "Sarah" in body
            assert "Q4" in body or "inbox" in body
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv run pytest tests/test_composer.py -v`
Expected: FAIL with "cannot import name 'generate_email_1'"

**Step 3: Implement composer**

Create `src/composer.py`:
```python
"""Email composition using Claude Opus 4.5."""

import json
import os
from pathlib import Path
from typing import Optional

import anthropic
import structlog

from src.config import DEFAULT_CONFIG_PATH, load_template, render_template

log = structlog.get_logger()

MODEL = "claude-opus-4-5-20250514"


def build_system_prompt(context: str) -> str:
    """Build the system prompt for Claude."""
    return f"""You are writing cold outreach emails. Your job is to generate a personalized, genuinely funny opening line based on their LinkedIn profile and posts.

## Context about the sender:
{context}

## Your mission:
1. Find something to riff on - a post, their title, their company, anything
2. Write a SHORT joke or witty observation (1-2 lines max)
3. Self-deprecating > clever. Warm > edgy. Never mean.
4. It's okay if it's not hilarious - aim for a smile, not a laugh track

## Examples of what works:
- Light teasing about their industry
- Self-aware jokes about cold emails
- Observational humor about something on their profile
- Playful takes on their job title

## What to avoid:
- Anything that could be read as insulting
- Jokes about appearance or personal life
- Trying too hard (desperation isn't funny)
- Generic humor that could apply to anyone

## If their LinkedIn is empty or you can't find anything:
- Make a joke about how clean/empty their profile is
- Or be self-aware about having nothing to reference

## Output format:
Return a JSON object with exactly two fields:
- "subject": A 3-6 word subject line, lowercase, curiosity-inducing
- "joke_opener": Your 1-2 sentence personalized joke opening

Example output:
{{"subject": "your linkedin is suspiciously clean", "joke_opener": "Scrolled your whole profile looking for something clever to reference and you've given me nothing. No hot takes, no humble brags. I respect the mystery."}}
"""


async def generate_email_1(
    lead: dict,
    posts: list[str],
    config_path: Path = DEFAULT_CONFIG_PATH
) -> tuple[str, str]:
    """Generate personalized email 1 using Claude.

    Returns (subject, body) tuple.
    """
    context = load_template(config_path, "context.md")
    email_template = load_template(config_path, "email_1.md")

    # Build the user message with lead info
    posts_text = "\n".join(f"- {post}" for post in posts) if posts else "No recent posts found."

    user_message = f"""Generate a personalized joke opener for this lead:

Name: {lead.get('first_name', '')} {lead.get('last_name', '')}
Company: {lead.get('company', 'Unknown')}
Title: {lead.get('title', 'Unknown')}

Their recent LinkedIn posts:
{posts_text}

Remember: Return valid JSON with "subject" and "joke_opener" fields only."""

    system_prompt = build_system_prompt(context)

    log.info("generating_email", email=lead.get("email"))

    try:
        client = anthropic.AsyncAnthropic()

        response = await client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )

        response_text = response.content[0].text.strip()

        # Parse JSON response
        # Handle potential markdown code blocks
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        result = json.loads(response_text)

        subject = result.get("subject", "quick question")
        joke_opener = result.get("joke_opener", "")

        # Render the template
        variables = {
            "generated_subject": subject,
            "generated_joke_opener": joke_opener,
            "first_name": lead.get("first_name", ""),
            "last_name": lead.get("last_name", ""),
            "company": lead.get("company", "your company"),
        }

        body = render_template(email_template, variables)

        # Extract subject from body if template has it
        lines = body.strip().split("\n")
        if lines[0].lower().startswith("subject:"):
            subject = lines[0].split(":", 1)[1].strip()
            body = "\n".join(lines[1:]).strip()

        log.info("email_generated", email=lead.get("email"), subject=subject)

        return subject, body

    except json.JSONDecodeError as e:
        log.error("json_parse_error", error=str(e), response=response_text[:200])
        # Fallback
        return generate_fallback_email(lead, config_path)
    except Exception as e:
        log.error("claude_error", error=str(e))
        return generate_fallback_email(lead, config_path)


def generate_fallback_email(lead: dict, config_path: Path) -> tuple[str, str]:
    """Generate a fallback email when Claude fails."""
    email_template = load_template(config_path, "email_1.md")

    variables = {
        "generated_subject": "cold email but make it honest",
        "generated_joke_opener": "I'd make a clever joke about your LinkedIn but honestly I'm just here to talk about creators. No fake rapport, just a pitch.",
        "first_name": lead.get("first_name", ""),
        "last_name": lead.get("last_name", ""),
        "company": lead.get("company", "your company"),
    }

    body = render_template(email_template, variables)

    lines = body.strip().split("\n")
    if lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip()
        body = "\n".join(lines[1:]).strip()
    else:
        subject = "cold email but make it honest"

    return subject, body
```

**Step 4: Run tests**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv run pytest tests/test_composer.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: add email composer with Claude Opus 4.5"
```

---

## Task 7: Gmail Sender (Composio)

**Files:**
- Create: `src/sender.py`
- Create: `tests/test_sender.py`

**Step 1: Write failing test with mock**

Create `tests/test_sender.py`:
```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.sender import send_new_email, send_reply_email


@pytest.mark.asyncio
async def test_send_new_email():
    mock_result = {
        "data": {
            "threadId": "thread_123",
            "id": "msg_456"
        }
    }

    with patch("src.sender.ComposioToolSet") as mock_toolset:
        mock_instance = MagicMock()
        mock_instance.execute_action.return_value = mock_result
        mock_toolset.return_value = mock_instance

        result = await send_new_email(
            to="test@example.com",
            subject="Test subject",
            body="Test body",
            from_name="Chris"
        )

        assert result["thread_id"] == "thread_123"
        assert result["message_id"] == "msg_456"


@pytest.mark.asyncio
async def test_send_reply_email():
    mock_result = {
        "data": {
            "threadId": "thread_123",
            "id": "msg_789"
        }
    }

    with patch("src.sender.ComposioToolSet") as mock_toolset:
        mock_instance = MagicMock()
        mock_instance.execute_action.return_value = mock_result
        mock_toolset.return_value = mock_instance

        result = await send_reply_email(
            to="test@example.com",
            subject="Re: Test subject",
            body="Follow up body",
            thread_id="thread_123",
            message_id="msg_456",
            from_name="Chris"
        )

        assert result["thread_id"] == "thread_123"
        assert result["message_id"] == "msg_789"
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv run pytest tests/test_sender.py -v`
Expected: FAIL with "cannot import name 'send_new_email'"

**Step 3: Implement sender**

Create `src/sender.py`:
```python
"""Gmail sending via Composio."""

import asyncio
from typing import Optional

import structlog
from composio import ComposioToolSet, Action

log = structlog.get_logger()


async def send_new_email(
    to: str,
    subject: str,
    body: str,
    from_name: str = "Chris"
) -> dict:
    """Send a new email (not a reply).

    Returns dict with thread_id and message_id.
    """
    log.info("sending_new_email", to=to, subject=subject)

    toolset = ComposioToolSet()

    # Run in executor since Composio is sync
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: toolset.execute_action(
            action=Action.GMAIL_SEND_EMAIL,
            params={
                "to": to,
                "subject": subject,
                "body": body,
                "from_name": from_name,
            }
        )
    )

    data = result.get("data", {})

    return {
        "thread_id": data.get("threadId"),
        "message_id": data.get("id"),
    }


async def send_reply_email(
    to: str,
    subject: str,
    body: str,
    thread_id: str,
    message_id: str,
    from_name: str = "Chris"
) -> dict:
    """Send a reply email (in existing thread).

    Returns dict with thread_id and message_id.
    """
    log.info("sending_reply_email", to=to, subject=subject, thread_id=thread_id)

    toolset = ComposioToolSet()

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: toolset.execute_action(
            action=Action.GMAIL_REPLY_TO_THREAD,
            params={
                "thread_id": thread_id,
                "message_id": message_id,
                "to": to,
                "subject": subject,
                "body": body,
                "from_name": from_name,
            }
        )
    )

    data = result.get("data", {})

    return {
        "thread_id": data.get("threadId"),
        "message_id": data.get("id"),
    }


async def get_thread_messages(thread_id: str) -> list[dict]:
    """Get all messages in a thread.

    Returns list of message dicts.
    """
    log.info("fetching_thread", thread_id=thread_id)

    toolset = ComposioToolSet()

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: toolset.execute_action(
            action=Action.GMAIL_GET_THREAD,
            params={"thread_id": thread_id}
        )
    )

    data = result.get("data", {})
    messages = data.get("messages", [])

    return messages


async def check_for_reply(thread_id: str, our_message_count: int) -> bool:
    """Check if there are more messages in thread than we sent.

    Returns True if recipient replied.
    """
    messages = await get_thread_messages(thread_id)

    # If there are more messages than we sent, they replied
    return len(messages) > our_message_count
```

**Step 4: Run tests**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv run pytest tests/test_sender.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: add Gmail sender via Composio"
```

---

## Task 8: Scheduler (Reply Detection & Due Emails)

**Files:**
- Create: `src/scheduler.py`
- Create: `tests/test_scheduler.py`

**Step 1: Write failing test**

Create `tests/test_scheduler.py`:
```python
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.db import init_db, insert_lead, update_lead_email_sent, get_lead_by_id
from src.config import Settings
from src.scheduler import check_replies, get_due_leads, process_lead


@pytest.mark.asyncio
async def test_check_replies_marks_replied():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        lead_id = insert_lead(db_path, "test@example.com", "Test", None, None, None, None)

        # Simulate email 1 sent
        update_lead_email_sent(
            db_path, lead_id, step=1,
            subject="test", body="body",
            thread_id="thread_123", message_id="msg_1",
            next_send_at=datetime.utcnow() + timedelta(days=3)
        )

        # Mock reply detection
        with patch("src.scheduler.check_for_reply", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True  # They replied

            replied = await check_replies(db_path)

            assert len(replied) == 1
            assert replied[0] == "test@example.com"

            lead = get_lead_by_id(db_path, lead_id)
            assert lead["status"] == "replied"


@pytest.mark.asyncio
async def test_get_due_leads():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        lead_id = insert_lead(db_path, "due@example.com", "Due", None, None, None, None)

        # Set as active with past next_send_at
        update_lead_email_sent(
            db_path, lead_id, step=1,
            subject="test", body="body",
            thread_id="thread_123", message_id="msg_1",
            next_send_at=datetime.utcnow() - timedelta(hours=1)  # Due
        )

        due = get_due_leads(db_path)

        assert len(due) == 1
        assert due[0]["email"] == "due@example.com"
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv run pytest tests/test_scheduler.py -v`
Expected: FAIL with "cannot import name 'check_replies'"

**Step 3: Implement scheduler**

Create `src/scheduler.py`:
```python
"""Scheduling logic for email sequences."""

import asyncio
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import structlog

from src.config import DEFAULT_CONFIG_PATH, Settings, load_settings, load_template, render_template
from src.db import (
    DEFAULT_DB_PATH,
    get_leads_by_status,
    get_leads_due_for_followup,
    get_lead_by_id,
    update_lead_status,
    update_lead_email_sent,
    count_sent_today,
)
from src.enricher import enrich_lead
from src.composer import generate_email_1
from src.sender import send_new_email, send_reply_email, check_for_reply

log = structlog.get_logger()


async def check_replies(db_path: Path = DEFAULT_DB_PATH) -> list[str]:
    """Check all active leads for replies.

    Returns list of emails that replied.
    """
    active_leads = get_leads_by_status(db_path, "active")
    replied = []

    for lead in active_leads:
        if not lead["thread_id"]:
            continue

        try:
            has_reply = await check_for_reply(lead["thread_id"], lead["current_step"])

            if has_reply:
                log.info("reply_detected", email=lead["email"])
                update_lead_status(db_path, lead["id"], "replied")
                replied.append(lead["email"])

        except Exception as e:
            log.error("reply_check_failed", email=lead["email"], error=str(e))

    return replied


def get_due_leads(db_path: Path = DEFAULT_DB_PATH) -> list:
    """Get leads due for follow-up."""
    return get_leads_due_for_followup(db_path)


def get_new_leads(db_path: Path = DEFAULT_DB_PATH) -> list:
    """Get leads that haven't been processed yet."""
    return get_leads_by_status(db_path, "new")


async def process_new_lead(
    lead_id: int,
    settings: Settings,
    db_path: Path = DEFAULT_DB_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH
) -> bool:
    """Process a new lead: enrich, generate email, send.

    Returns True if successful.
    """
    lead = get_lead_by_id(db_path, lead_id)
    if not lead:
        return False

    log.info("processing_new_lead", email=lead["email"])

    # Enrich
    enrichment = await enrich_lead(lead_id, db_path)
    posts = enrichment.get("posts", [])

    # Generate email 1
    lead_dict = dict(lead)
    subject, body = await generate_email_1(lead_dict, posts, config_path)

    # Send
    try:
        result = await send_new_email(
            to=lead["email"],
            subject=subject,
            body=body,
            from_name=settings.gmail.from_name
        )

        # Calculate next send time
        next_send = datetime.utcnow() + timedelta(days=settings.sequence.email_2_delay_days)

        # Update database
        update_lead_email_sent(
            db_path, lead_id, step=1,
            subject=subject, body=body,
            thread_id=result["thread_id"],
            message_id=result["message_id"],
            next_send_at=next_send
        )

        log.info("email_1_sent", email=lead["email"], thread_id=result["thread_id"])
        return True

    except Exception as e:
        log.error("send_failed", email=lead["email"], error=str(e))
        return False


async def process_followup(
    lead_id: int,
    settings: Settings,
    db_path: Path = DEFAULT_DB_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH
) -> bool:
    """Send follow-up email to a lead.

    Returns True if successful.
    """
    lead = get_lead_by_id(db_path, lead_id)
    if not lead:
        return False

    current_step = lead["current_step"]
    next_step = current_step + 1

    if next_step > 3:
        log.info("sequence_complete", email=lead["email"])
        update_lead_status(db_path, lead_id, "completed")
        return True

    log.info("processing_followup", email=lead["email"], step=next_step)

    # Load appropriate template
    template_name = f"followup_{next_step - 1}.md"
    try:
        template = load_template(config_path, template_name)
    except FileNotFoundError:
        log.error("template_not_found", template=template_name)
        return False

    # Render template
    variables = {
        "first_name": lead["first_name"],
        "original_subject": lead["email_1_subject"],
    }
    body = render_template(template, variables)

    # Extract subject
    lines = body.strip().split("\n")
    if lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip()
        body = "\n".join(lines[1:]).strip()
    else:
        subject = f"re: {lead['email_1_subject']}"

    # Send
    try:
        result = await send_reply_email(
            to=lead["email"],
            subject=subject,
            body=body,
            thread_id=lead["thread_id"],
            message_id=lead["last_message_id"],
            from_name=settings.gmail.from_name
        )

        # Calculate next send time (or None if sequence done)
        if next_step < 3:
            next_send = datetime.utcnow() + timedelta(days=settings.sequence.email_3_delay_days)
        else:
            next_send = None

        update_lead_email_sent(
            db_path, lead_id, step=next_step,
            subject=subject, body=body,
            thread_id=result["thread_id"],
            message_id=result["message_id"],
            next_send_at=next_send
        )

        log.info(f"email_{next_step}_sent", email=lead["email"])
        return True

    except Exception as e:
        log.error("followup_send_failed", email=lead["email"], error=str(e))
        return False


async def run_send_cycle(
    db_path: Path = DEFAULT_DB_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH
) -> dict:
    """Run a complete send cycle.

    1. Check for replies
    2. Process new leads
    3. Send follow-ups

    Returns summary dict.
    """
    settings = load_settings(config_path)

    # Check daily limit
    sent_today = count_sent_today(db_path)
    remaining = settings.sending.daily_limit - sent_today

    if remaining <= 0:
        log.info("daily_limit_reached", sent=sent_today, limit=settings.sending.daily_limit)
        return {
            "replied": [],
            "new_sent": 0,
            "followups_sent": 0,
            "daily_limit_reached": True,
            "sent_today": sent_today,
        }

    results = {
        "replied": [],
        "new_sent": 0,
        "followups_sent": 0,
        "daily_limit_reached": False,
        "sent_today": sent_today,
    }

    # 1. Check for replies
    results["replied"] = await check_replies(db_path)

    # 2. Process new leads
    new_leads = get_new_leads(db_path)
    for lead in new_leads:
        if remaining <= 0:
            results["daily_limit_reached"] = True
            break

        success = await process_new_lead(lead["id"], settings, db_path, config_path)
        if success:
            results["new_sent"] += 1
            remaining -= 1
            results["sent_today"] += 1

            # Random delay
            delay = random.randint(
                settings.sending.min_delay_seconds,
                settings.sending.max_delay_seconds
            )
            await asyncio.sleep(delay)

    # 3. Send follow-ups
    due_leads = get_due_leads(db_path)
    for lead in due_leads:
        if remaining <= 0:
            results["daily_limit_reached"] = True
            break

        success = await process_followup(lead["id"], settings, db_path, config_path)
        if success:
            results["followups_sent"] += 1
            remaining -= 1
            results["sent_today"] += 1

            # Random delay
            delay = random.randint(
                settings.sending.min_delay_seconds,
                settings.sending.max_delay_seconds
            )
            await asyncio.sleep(delay)

    return results
```

**Step 4: Run tests**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv run pytest tests/test_scheduler.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: add scheduler for reply detection and follow-ups"
```

---

## Task 9: CLI Entry Point

**Files:**
- Create: `src/cli.py`
- Create: `run.py`
- Create: `tests/test_cli.py`

**Step 1: Write failing test**

Create `tests/test_cli.py`:
```python
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock

from click.testing import CliRunner

from src.cli import cli
from src.db import init_db


def test_cli_status_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--db", str(db_path)])

        assert result.exit_code == 0
        assert "Pipeline Status" in result.output


def test_cli_import_command():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "test.db"
        excel_path = tmpdir / "leads.xlsx"

        # Create test Excel
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append(["email", "first_name", "last_name", "company", "title", "linkedin_url"])
        ws.append(["test@example.com", "Test", "User", "Acme", "CEO", "https://linkedin.com/in/test"])
        wb.save(excel_path)

        init_db(db_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["import", str(excel_path), "--db", str(db_path)])

        assert result.exit_code == 0
        assert "Imported 1" in result.output or "imported" in result.output.lower()
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv run pytest tests/test_cli.py -v`
Expected: FAIL with "cannot import name 'cli'"

**Step 3: Implement CLI**

Create `src/cli.py`:
```python
"""Command-line interface for outreach boilerplate."""

import asyncio
from pathlib import Path
from typing import Optional

import click
import structlog

from src.db import DEFAULT_DB_PATH, init_db, get_pipeline_stats, get_lead_by_email
from src.config import DEFAULT_CONFIG_PATH, load_settings
from src.importer import import_leads
from src.scheduler import run_send_cycle

# Configure structlog for CLI output
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ]
)

log = structlog.get_logger()


@click.group()
def cli():
    """Outreach Boilerplate - Humor-first cold email CLI."""
    pass


@cli.command()
@click.argument("excel_path", type=click.Path(exists=True))
@click.option("--db", "db_path", type=click.Path(), default=str(DEFAULT_DB_PATH),
              help="Database path")
def import_(excel_path: str, db_path: str):
    """Import leads from an Excel file."""
    db = Path(db_path)
    init_db(db)

    click.echo(f"Importing leads from {excel_path}...")

    result = import_leads(Path(excel_path), db)

    click.echo(f"\nImported {result['imported']} new leads")
    if result['skipped'] > 0:
        click.echo(f"Skipped {result['skipped']} duplicates")


# Rename 'import' command since it's a reserved word
cli.add_command(import_, name="import")


@cli.command()
@click.option("--db", "db_path", type=click.Path(), default=str(DEFAULT_DB_PATH),
              help="Database path")
@click.option("--config", "config_path", type=click.Path(), default=str(DEFAULT_CONFIG_PATH),
              help="Config directory path")
def send(db_path: str, config_path: str):
    """Send emails (process new leads and follow-ups)."""
    db = Path(db_path)
    config = Path(config_path)

    init_db(db)
    settings = load_settings(config)

    click.echo("Starting send cycle...\n")

    result = asyncio.run(run_send_cycle(db, config))

    # Print results
    if result["replied"]:
        click.echo("Replies detected:")
        for email in result["replied"]:
            click.echo(f"  ✓ {email} replied - sequence stopped")
        click.echo()

    if result["new_sent"] > 0:
        click.echo(f"New leads processed: {result['new_sent']}")

    if result["followups_sent"] > 0:
        click.echo(f"Follow-ups sent: {result['followups_sent']}")

    total_sent = result["new_sent"] + result["followups_sent"]
    click.echo(f"\nTotal sent: {total_sent}")
    click.echo(f"Daily sends: {result['sent_today']}/{settings.sending.daily_limit}")

    if result["daily_limit_reached"]:
        click.echo("\n⚠️  Daily limit reached. Run again tomorrow.")


@cli.command()
@click.option("--db", "db_path", type=click.Path(), default=str(DEFAULT_DB_PATH),
              help="Database path")
@click.option("--lead", "lead_email", type=str, default=None,
              help="Check specific lead by email")
@click.option("--config", "config_path", type=click.Path(), default=str(DEFAULT_CONFIG_PATH),
              help="Config directory path")
def status(db_path: str, lead_email: Optional[str], config_path: str):
    """Show pipeline status."""
    db = Path(db_path)
    config = Path(config_path)

    init_db(db)
    settings = load_settings(config)

    if lead_email:
        # Show specific lead
        lead = get_lead_by_email(db, lead_email)
        if not lead:
            click.echo(f"Lead not found: {lead_email}")
            return

        click.echo(f"\nLead: {lead['email']}")
        click.echo(f"  Name: {lead['first_name']} {lead['last_name'] or ''}")
        click.echo(f"  Company: {lead['company'] or 'N/A'}")
        click.echo(f"  Status: {lead['status']}")
        click.echo(f"  Current step: {lead['current_step']}")
        click.echo(f"  Imported: {lead['imported_at']}")
        if lead['last_sent_at']:
            click.echo(f"  Last sent: {lead['last_sent_at']}")
        if lead['next_send_at']:
            click.echo(f"  Next send: {lead['next_send_at']}")
        return

    # Show overall stats
    stats = get_pipeline_stats(db)

    click.echo("\nPipeline Status")
    click.echo("───────────────")
    click.echo(f"New (pending):         {stats.get('new', 0)}")
    click.echo(f"Active sequences:      {stats.get('active', 0)}")
    click.echo(f"  - Due for follow-up: {stats.get('due_for_followup', 0)}")
    click.echo(f"Replied:               {stats.get('replied', 0)}")
    click.echo(f"Completed:             {stats.get('completed', 0)}")
    click.echo("───────────────")
    click.echo(f"Daily sends: {stats.get('sent_today', 0)}/{settings.sending.daily_limit}")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
```

Create `run.py`:
```python
#!/usr/bin/env python
"""Entry point for outreach CLI."""

from src.cli import main

if __name__ == "__main__":
    main()
```

**Step 4: Run tests**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv run pytest tests/test_cli.py -v`
Expected: All PASS

**Step 5: Test CLI manually**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv run python run.py --help`
Expected: Shows help with import, send, status commands

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv run python run.py status`
Expected: Shows pipeline status (all zeros)

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: add CLI entry point with import, send, status commands"
```

---

## Task 10: README and Final Polish

**Files:**
- Create: `README.md`
- Update: `.gitignore`

**Step 1: Create README**

Create `README.md`:
```markdown
# Outreach Boilerplate

Humor-first cold email outreach CLI. Clone, configure, upload leads, hit go.

## What It Does

1. **Import leads** from Excel (email, name, company, LinkedIn URL)
2. **Scrape LinkedIn** for personalization context (via Apify)
3. **Generate personalized jokes** using Claude Opus 4.5 as email openers
4. **Send via Gmail** with proper threading (via Composio)
5. **Automate follow-ups** via cron (self-aware templated humor)
6. **Stop sequences** when replies detected

## Setup (5 minutes)

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/outreach-boilerplate
cd outreach-boilerplate
uv sync
```

### 2. Add API Keys

```bash
cp .env.example .env
```

Edit `.env` with your keys:
- `ANTHROPIC_API_KEY` - Get from [Anthropic Console](https://console.anthropic.com/)
- `COMPOSIO_API_KEY` - Get from [Composio](https://composio.dev/)
- `APIFY_API_KEY` - Get from [Apify](https://apify.com/)

### 3. Connect Gmail

```bash
composio login
composio add gmail
```

### 4. Configure Your Messaging

Edit the files in `config/`:

- `context.md` - Who you are, what you offer, tone guidelines
- `email_1.md` - Base template for first email (Claude personalizes the opener)
- `followup_1.md` - Template for email 2 (3 days later)
- `followup_2.md` - Template for email 3 (7 days later)
- `settings.yaml` - Timing and rate limits

### 5. Set Up Cron (Optional)

For automated follow-ups:

```bash
crontab -e
```

Add:
```
0 * * * * cd /path/to/outreach-boilerplate && uv run python run.py send >> /tmp/outreach.log 2>&1
```

## Usage

### Import Leads

```bash
python run.py import leads.xlsx
```

Excel format:

| email | first_name | last_name | company | title | linkedin_url |
|-------|------------|-----------|---------|-------|--------------|
| sarah@brand.com | Sarah | Chen | Brand Co | Marketing Director | https://linkedin.com/in/sarahchen |

### Send Emails

```bash
python run.py send
```

This will:
1. Check for replies (stop sequences for those who replied)
2. Process new leads (enrich → generate → send)
3. Send follow-ups that are due

### Check Status

```bash
# Overall pipeline status
python run.py status

# Specific lead
python run.py status --lead sarah@brand.com
```

## How It Works

### Email 1: Personalized Joke

Claude reads their LinkedIn and generates a genuinely funny opener:

```
subject: your linkedin is suspiciously clean

Hey Sarah,

Scrolled your whole profile looking for something clever to
reference and you've given me nothing. No hot takes, no humble
brags. I respect the mystery.

I'm with Cheerful - we help brands like Brand Co turn creators
into affiliates without the usual headaches...
```

### Emails 2 & 3: Self-Aware Follow-ups

Templates with built-in humor about following up:

```
subject: re: your linkedin is suspiciously clean

Hey Sarah,

Following up on my own cold email. The audacity continues.

Genuinely curious if creator/affiliate stuff is on your radar
or if I should take the hint.

Chris
```

## Configuration

### settings.yaml

```yaml
sequence:
  email_2_delay_days: 3    # Days after email 1
  email_3_delay_days: 4    # Days after email 2

sending:
  daily_limit: 50          # Max emails per day
  min_delay_seconds: 20    # Min gap between sends
  max_delay_seconds: 60    # Max gap between sends

gmail:
  from_name: "Chris"
```

## Requirements

- Python 3.11+
- Gmail account
- API keys: Anthropic, Composio, Apify

## License

MIT
```

**Step 2: Update .gitignore**

Ensure `.gitignore` has:
```
# Environment
.env
.venv/
__pycache__/
*.pyc

# Data
data/outreach.db
data/*.xlsx
!data/leads_example.xlsx

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Test artifacts
.pytest_cache/
.coverage
htmlcov/
```

**Step 3: Create data directory**

Run: `mkdir -p /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate/data`

**Step 4: Run all tests**

Run: `cd /Users/christopherbrownridge/Desktop/projects/outreach-boilerplate && uv run pytest -v`
Expected: All tests pass

**Step 5: Final commit**

```bash
git add -A
git commit -m "docs: add README and finalize project structure"
```

---

## Summary

**Tasks completed:**
1. Project setup (pyproject.toml, .env.example, .gitignore)
2. Database schema and CRUD operations
3. Configuration loading (settings.yaml, templates)
4. Excel importer
5. LinkedIn enricher (Apify)
6. Email composer (Claude Opus 4.5)
7. Gmail sender (Composio)
8. Scheduler (reply detection, follow-ups)
9. CLI entry point (import, send, status)
10. README and documentation

**To use:**
```bash
# One-time setup
cp .env.example .env  # Add your API keys
composio login && composio add gmail
uv sync

# Daily usage
python run.py import leads.xlsx
python run.py send
python run.py status
```
