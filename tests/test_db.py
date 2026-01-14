import tempfile
from pathlib import Path

from src.db import (
    init_db, get_connection,
    insert_lead, get_lead_by_email, get_leads_by_status,
    update_lead_status, count_sent_today
)


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
