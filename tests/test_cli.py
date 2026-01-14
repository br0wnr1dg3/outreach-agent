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
