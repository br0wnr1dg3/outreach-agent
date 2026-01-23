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
            replied_at TIMESTAMP,

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

        CREATE TABLE IF NOT EXISTS searched_companies (
            id INTEGER PRIMARY KEY,
            domain TEXT UNIQUE NOT NULL,
            company_name TEXT,
            source_keyword TEXT,
            fb_page_id TEXT,
            passed_gate_1 INTEGER,
            passed_gate_2 INTEGER,
            fit_score INTEGER,
            fit_notes TEXT,
            leads_found INTEGER DEFAULT 0,
            searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_searched_companies_domain ON searched_companies(domain);
    """)

    conn.commit()
    conn.close()


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


def insert_searched_company(
    db_path: Path,
    domain: str,
    company_name: Optional[str] = None,
    source_keyword: Optional[str] = None,
    fb_page_id: Optional[str] = None,
    passed_gate_1: Optional[bool] = None,
    passed_gate_2: Optional[bool] = None,
    fit_score: Optional[int] = None,
    fit_notes: Optional[str] = None,
) -> bool:
    """Insert a searched company. Returns True if inserted, False if duplicate."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO searched_companies
            (domain, company_name, source_keyword, fb_page_id, passed_gate_1, passed_gate_2, fit_score, fit_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (domain, company_name, source_keyword, fb_page_id,
             1 if passed_gate_1 else (0 if passed_gate_1 is False else None),
             1 if passed_gate_2 else (0 if passed_gate_2 is False else None),
             fit_score, fit_notes)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def count_companies_searched_today(db_path: Path) -> int:
    """Count companies searched today."""
    conn = get_connection(db_path)
    today = datetime.utcnow().date().isoformat()
    cursor = conn.execute(
        "SELECT COUNT(*) FROM searched_companies WHERE date(searched_at) = ?",
        (today,)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_quota_status(db_path: Path, daily_target: int = 10) -> dict:
    """Get quota status for today."""
    leads_today = count_leads_generated_today(db_path)
    return {
        "leads_today": leads_today,
        "target": daily_target,
        "remaining": max(0, daily_target - leads_today),
        "quota_met": leads_today >= daily_target,
    }


def get_daily_stats(db_path: Path) -> dict:
    """Get daily statistics."""
    return {
        "leads_generated_today": count_leads_generated_today(db_path),
        "companies_checked_today": count_companies_searched_today(db_path),
    }


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


def update_company_leads_found(db_path: Path, domain: str, count: int) -> None:
    """Update the leads_found count for a searched company."""
    conn = get_connection(db_path)
    conn.execute(
        "UPDATE searched_companies SET leads_found = ? WHERE domain = ?",
        (count, domain)
    )
    conn.commit()
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
