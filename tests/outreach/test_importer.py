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
