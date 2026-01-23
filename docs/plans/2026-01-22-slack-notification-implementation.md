# Slack Notification Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace basic Slack notification with a comprehensive weekly/all-time metrics dashboard including reply rate.

**Architecture:** Add `replied_at` column to track reply timestamps, create query functions for weekly/all-time stats, and update SlackNotifier to render two-column Slack blocks layout.

**Tech Stack:** SQLite, httpx, Slack Block Kit

---

### Task 1: Add replied_at Column to Database Schema

**Files:**
- Modify: `src/core/db.py:24-55` (init_db schema)
- Test: `tests/core/test_db.py`

**Step 1: Write the failing test**

Add to `tests/core/test_db.py`:

```python
def test_leads_table_has_replied_at_column():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        conn = get_connection(db_path)
        cursor = conn.execute("PRAGMA table_info(leads)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        assert "replied_at" in columns
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/test_db.py::test_leads_table_has_replied_at_column -v`
Expected: FAIL with `AssertionError`

**Step 3: Write minimal implementation**

In `src/core/db.py`, add to the leads table schema in `init_db()` after line 50 (`next_send_at TIMESTAMP,`):

```python
            replied_at TIMESTAMP,
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/core/test_db.py::test_leads_table_has_replied_at_column -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/db.py tests/core/test_db.py
git commit -m "feat(db): add replied_at column to leads table"
```

---

### Task 2: Create mark_lead_replied Function

**Files:**
- Modify: `src/core/db.py`
- Test: `tests/core/test_db.py`

**Step 1: Write the failing test**

Add to `tests/core/test_db.py`:

```python
from datetime import datetime

def test_mark_lead_replied_sets_status_and_timestamp():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        lead_id = insert_lead(db_path, "reply@test.com", "Reply", None, None, None, None)

        from src.core.db import mark_lead_replied
        mark_lead_replied(db_path, lead_id)

        lead = get_lead_by_email(db_path, "reply@test.com")
        assert lead["status"] == "replied"
        assert lead["replied_at"] is not None
```

Update the import at top of file:

```python
from src.core.db import (
    init_db, get_connection,
    insert_lead, get_lead_by_email, get_leads_by_status,
    update_lead_status, count_sent_today,
    insert_searched_company, is_company_searched,
    update_company_leads_found, count_leads_generated_today,
    mark_lead_replied
)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/test_db.py::test_mark_lead_replied_sets_status_and_timestamp -v`
Expected: FAIL with `ImportError: cannot import name 'mark_lead_replied'`

**Step 3: Write minimal implementation**

Add to `src/core/db.py` after `update_lead_status` function:

```python
def mark_lead_replied(db_path: Path, lead_id: int) -> None:
    """Mark a lead as replied with timestamp."""
    conn = get_connection(db_path)
    conn.execute(
        "UPDATE leads SET status = 'replied', replied_at = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), lead_id)
    )
    conn.commit()
    conn.close()
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/core/test_db.py::test_mark_lead_replied_sets_status_and_timestamp -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/db.py tests/core/test_db.py
git commit -m "feat(db): add mark_lead_replied function"
```

---

### Task 3: Create get_weekly_stats Function

**Files:**
- Modify: `src/core/db.py`
- Test: `tests/core/test_db.py`

**Step 1: Write the failing test**

Add to `tests/core/test_db.py`:

```python
def test_get_weekly_stats_returns_correct_counts():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        # Add leads (all created "today" which is within the week)
        insert_lead(db_path, "lead1@test.com", "One", None, None, None, None)
        insert_lead(db_path, "lead2@test.com", "Two", None, None, None, None)
        insert_lead(db_path, "lead3@test.com", "Three", None, None, None, None)

        # Simulate one contacted (current_step >= 1)
        conn = get_connection(db_path)
        conn.execute("UPDATE leads SET current_step = 1 WHERE email = ?", ("lead1@test.com",))
        conn.commit()
        conn.close()

        # Simulate one replied
        mark_lead_replied(db_path, 2)  # lead2

        from src.core.db import get_weekly_stats
        stats = get_weekly_stats(db_path)

        assert stats["leads_found"] == 3
        assert stats["leads_contacted"] == 1
        assert stats["leads_replied"] == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/test_db.py::test_get_weekly_stats_returns_correct_counts -v`
Expected: FAIL with `ImportError: cannot import name 'get_weekly_stats'`

**Step 3: Write minimal implementation**

Add to `src/core/db.py`:

```python
def get_weekly_stats(db_path: Path) -> dict:
    """Get stats for the current week (Monday-Sunday)."""
    conn = get_connection(db_path)

    # Calculate Monday of current week
    today = datetime.utcnow().date()
    monday = today - timedelta(days=today.weekday())
    monday_str = monday.isoformat()

    # Leads found this week
    cursor = conn.execute(
        "SELECT COUNT(*) FROM leads WHERE date(imported_at) >= ?",
        (monday_str,)
    )
    leads_found = cursor.fetchone()[0]

    # Leads contacted this week (first email sent this week)
    cursor = conn.execute(
        """SELECT COUNT(*) FROM leads
           WHERE current_step >= 1
           AND date(last_sent_at) >= ?""",
        (monday_str,)
    )
    leads_contacted = cursor.fetchone()[0]

    # Leads replied this week
    cursor = conn.execute(
        "SELECT COUNT(*) FROM leads WHERE status = 'replied' AND date(replied_at) >= ?",
        (monday_str,)
    )
    leads_replied = cursor.fetchone()[0]

    conn.close()

    return {
        "leads_found": leads_found,
        "leads_contacted": leads_contacted,
        "leads_replied": leads_replied,
    }
```

Add `timedelta` to the imports at top of file:

```python
from datetime import datetime, timedelta
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/core/test_db.py::test_get_weekly_stats_returns_correct_counts -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/db.py tests/core/test_db.py
git commit -m "feat(db): add get_weekly_stats function"
```

---

### Task 4: Create get_all_time_stats Function

**Files:**
- Modify: `src/core/db.py`
- Test: `tests/core/test_db.py`

**Step 1: Write the failing test**

Add to `tests/core/test_db.py`:

```python
def test_get_all_time_stats_returns_counts_and_reply_rate():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        # Add 4 leads
        for i in range(4):
            insert_lead(db_path, f"lead{i}@test.com", f"Lead{i}", None, None, None, None)

        # Mark 2 as contacted
        conn = get_connection(db_path)
        conn.execute("UPDATE leads SET current_step = 1 WHERE email IN (?, ?)",
                     ("lead0@test.com", "lead1@test.com"))
        conn.commit()
        conn.close()

        # Mark 1 as replied
        mark_lead_replied(db_path, 1)  # lead0

        from src.core.db import get_all_time_stats
        stats = get_all_time_stats(db_path)

        assert stats["leads_found"] == 4
        assert stats["leads_contacted"] == 2
        assert stats["leads_replied"] == 1
        assert stats["reply_rate"] == 50.0  # 1/2 * 100
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/test_db.py::test_get_all_time_stats_returns_counts_and_reply_rate -v`
Expected: FAIL with `ImportError: cannot import name 'get_all_time_stats'`

**Step 3: Write minimal implementation**

Add to `src/core/db.py`:

```python
def get_all_time_stats(db_path: Path) -> dict:
    """Get all-time stats."""
    conn = get_connection(db_path)

    # Total leads found
    cursor = conn.execute("SELECT COUNT(*) FROM leads")
    leads_found = cursor.fetchone()[0]

    # Total leads contacted (received first email)
    cursor = conn.execute("SELECT COUNT(*) FROM leads WHERE current_step >= 1")
    leads_contacted = cursor.fetchone()[0]

    # Total leads replied
    cursor = conn.execute("SELECT COUNT(*) FROM leads WHERE status = 'replied'")
    leads_replied = cursor.fetchone()[0]

    conn.close()

    # Calculate reply rate
    reply_rate = (leads_replied / leads_contacted * 100) if leads_contacted > 0 else 0.0

    return {
        "leads_found": leads_found,
        "leads_contacted": leads_contacted,
        "leads_replied": leads_replied,
        "reply_rate": round(reply_rate, 1),
    }
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/core/test_db.py::test_get_all_time_stats_returns_counts_and_reply_rate -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/db.py tests/core/test_db.py
git commit -m "feat(db): add get_all_time_stats function"
```

---

### Task 5: Update SlackNotifier.send_summary Method

**Files:**
- Modify: `src/services/slack_notifier.py`
- Test: `tests/services/test_slack_notifier.py`

**Step 1: Write the failing test**

Replace the existing test in `tests/services/test_slack_notifier.py`:

```python
# tests/services/test_slack_notifier.py
"""Tests for Slack notifier service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_send_summary_posts_with_stats():
    """send_summary should POST formatted stats to webhook URL."""
    with patch("src.services.slack_notifier.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        from src.services.slack_notifier import SlackNotifier
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        weekly_stats = {"leads_found": 12, "leads_contacted": 8, "leads_replied": 2}
        all_time_stats = {"leads_found": 247, "leads_contacted": 189, "leads_replied": 31, "reply_rate": 16.4}

        result = await notifier.send_summary(
            weekly_stats=weekly_stats,
            all_time_stats=all_time_stats,
        )

        assert result is True
        mock_client.post.assert_called_once()

        # Verify blocks structure
        call_kwargs = mock_client.post.call_args[1]
        blocks = call_kwargs["json"]["blocks"]

        # Should have header, stats section, and reply rate section
        assert len(blocks) >= 3
        assert blocks[0]["type"] == "header"


@pytest.mark.asyncio
async def test_send_summary_includes_errors_when_provided():
    """send_summary should include errors section when errors provided."""
    with patch("src.services.slack_notifier.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        from src.services.slack_notifier import SlackNotifier
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        weekly_stats = {"leads_found": 5, "leads_contacted": 3, "leads_replied": 0}
        all_time_stats = {"leads_found": 100, "leads_contacted": 80, "leads_replied": 10, "reply_rate": 12.5}

        await notifier.send_summary(
            weekly_stats=weekly_stats,
            all_time_stats=all_time_stats,
            errors=["API timeout", "Rate limited"],
        )

        call_kwargs = mock_client.post.call_args[1]
        blocks = call_kwargs["json"]["blocks"]

        # Find errors section
        error_block = [b for b in blocks if b.get("type") == "section" and "Issues" in str(b)]
        assert len(error_block) == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/services/test_slack_notifier.py -v`
Expected: FAIL with `TypeError` (wrong arguments)

**Step 3: Write minimal implementation**

Replace `src/services/slack_notifier.py`:

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
        weekly_stats: dict,
        all_time_stats: dict,
        errors: Optional[list[str]] = None,
    ) -> bool:
        """Send end-of-run summary to Slack.

        Args:
            weekly_stats: Dict with leads_found, leads_contacted, leads_replied
            all_time_stats: Dict with leads_found, leads_contacted, leads_replied, reply_rate
            errors: List of any errors encountered

        Returns:
            True if sent successfully
        """
        if not self.webhook_url:
            log.warning("slack_webhook_not_configured")
            return False

        # Build message blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Daily Outreach Complete",
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": "*This Week*"},
                    {"type": "mrkdwn", "text": "*All Time*"},
                    {"type": "mrkdwn", "text": f"Leads Found: {weekly_stats['leads_found']}"},
                    {"type": "mrkdwn", "text": f"Leads Found: {all_time_stats['leads_found']}"},
                    {"type": "mrkdwn", "text": f"Contacted: {weekly_stats['leads_contacted']}"},
                    {"type": "mrkdwn", "text": f"Contacted: {all_time_stats['leads_contacted']}"},
                    {"type": "mrkdwn", "text": f"Replied: {weekly_stats['leads_replied']}"},
                    {"type": "mrkdwn", "text": f"Replied: {all_time_stats['leads_replied']}"},
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Reply Rate:* {all_time_stats['reply_rate']}%"
                }
            }
        ]

        if errors:
            error_text = "\n".join(f"* {e}" for e in errors[:5])
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
                log.info(
                    "slack_summary_sent",
                    weekly_found=weekly_stats["leads_found"],
                    all_time_found=all_time_stats["leads_found"],
                    reply_rate=all_time_stats["reply_rate"],
                )
                return True

        except Exception as e:
            log.error("slack_send_error", error=str(e))
            return False
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/services/test_slack_notifier.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/slack_notifier.py tests/services/test_slack_notifier.py
git commit -m "feat(slack): redesign send_summary with weekly/all-time stats"
```

---

### Task 6: Update Scheduler to Use mark_lead_replied

**Files:**
- Modify: `src/outreach/scheduler.py:52-53`

**Step 1: Update the import**

In `src/outreach/scheduler.py`, change the imports from `src.core.db`:

```python
from src.core.db import (
    DEFAULT_DB_PATH,
    get_leads_by_status,
    get_leads_due_for_followup,
    get_lead_by_id,
    mark_lead_replied,
    update_lead_email_sent,
    count_sent_today,
)
```

**Step 2: Replace update_lead_status call**

In `check_replies` function, replace line 53:

```python
                update_lead_status(db_path, lead["id"], "replied")
```

with:

```python
                mark_lead_replied(db_path, lead["id"])
```

**Step 3: Run tests to verify nothing broke**

Run: `uv run pytest tests/core/test_db.py -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add src/outreach/scheduler.py
git commit -m "refactor(scheduler): use mark_lead_replied for timestamp tracking"
```

---

### Task 7: Integration - Wire Up Stats in Caller

**Files:**
- Identify caller of `SlackNotifier.send_summary()` and update

**Step 1: Find the caller**

Run: `grep -r "send_summary" src/`

This will likely be in `src/discovery/agent.py` or `run_agent.py`. Update that file to:
1. Import `get_weekly_stats` and `get_all_time_stats` from `src.core.db`
2. Call both functions before calling `notifier.send_summary()`
3. Pass the stats dicts to `send_summary()`

**Step 2: Update the caller**

Example pattern (adapt to actual file):

```python
from src.core.db import get_weekly_stats, get_all_time_stats, DEFAULT_DB_PATH

# ... in the function that calls send_summary:
weekly_stats = get_weekly_stats(DEFAULT_DB_PATH)
all_time_stats = get_all_time_stats(DEFAULT_DB_PATH)

await notifier.send_summary(
    weekly_stats=weekly_stats,
    all_time_stats=all_time_stats,
    errors=errors if errors else None,
)
```

**Step 3: Run full test suite**

Run: `uv run pytest tests/core/test_db.py tests/services/test_slack_notifier.py -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add <modified-caller-file>
git commit -m "feat: wire up weekly/all-time stats to slack notification"
```

---

### Task 8: Final Verification

**Step 1: Run all relevant tests**

Run: `uv run pytest tests/core/test_db.py tests/services/test_slack_notifier.py -v`
Expected: All PASS

**Step 2: Verify schema works with fresh DB**

```bash
rm -f data/outreach.db
uv run python -c "from src.core.db import init_db, DEFAULT_DB_PATH; init_db(DEFAULT_DB_PATH); print('DB initialized')"
```

**Step 3: Commit any final changes**

If all looks good, no commit needed.

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Add replied_at column | db.py |
| 2 | Create mark_lead_replied | db.py |
| 3 | Create get_weekly_stats | db.py |
| 4 | Create get_all_time_stats | db.py |
| 5 | Redesign send_summary | slack_notifier.py |
| 6 | Update scheduler | scheduler.py |
| 7 | Wire up in caller | TBD |
| 8 | Final verification | - |
