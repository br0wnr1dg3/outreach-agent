import tempfile
from pathlib import Path

from src.db import (
    init_db, get_connection,
    insert_lead, get_lead_by_email, get_leads_by_status,
    update_lead_status, count_sent_today,
    insert_searched_company, is_company_searched,
    update_company_leads_found, count_leads_generated_today
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


def test_is_company_searched():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        assert is_company_searched(db_path, "unknown.com") is False

        insert_searched_company(db_path, "known.com", "Known", "keyword", "123")

        assert is_company_searched(db_path, "known.com") is True
        assert is_company_searched(db_path, "unknown.com") is False


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
