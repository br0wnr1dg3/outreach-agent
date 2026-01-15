import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock
import os

from click.testing import CliRunner

from src.cli import cli, import_from_leads_folder
from src.db import init_db, get_leads_by_status


def test_cli_status_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--db", str(db_path)])

        assert result.exit_code == 0
        assert "Pipeline Status" in result.output


def test_import_from_leads_folder():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Change to temp directory so leads folder is created there
        old_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            tmpdir = Path(tmpdir)
            db_path = tmpdir / "test.db"
            leads_folder = tmpdir / "leads"
            leads_folder.mkdir()

            # Create test Excel in leads folder
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.append(["email", "first_name", "last_name", "company", "title", "linkedin_url"])
            ws.append(["test@example.com", "Test", "User", "Acme", "CEO", "https://linkedin.com/in/test"])
            wb.save(leads_folder / "test_leads.xlsx")

            init_db(db_path)

            result = import_from_leads_folder(db_path)

            assert result["imported"] == 1
            assert len(result["files"]) == 1

            # Check file was moved to processed
            assert not (leads_folder / "test_leads.xlsx").exists()
            assert (leads_folder / "processed").exists()

            # Check lead was imported
            leads = get_leads_by_status(db_path, "new")
            assert len(leads) == 1
            assert leads[0]["email"] == "test@example.com"

        finally:
            os.chdir(old_cwd)


def test_cli_run_no_leads():
    """Test run command with no leads to process."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            db_path = Path(tmpdir) / "test.db"
            config_path = Path(tmpdir) / "config"
            config_path.mkdir()

            # Create minimal config
            (config_path / "settings.yaml").write_text("""
sequence:
  email_2_delay_days: 3
  email_3_delay_days: 4
sending:
  daily_limit: 50
gmail:
  from_name: "Test"
  connected_account_id: ""
""")

            runner = CliRunner()
            result = runner.invoke(cli, ["run", "--db", str(db_path), "--config", str(config_path)])

            assert result.exit_code == 0
            assert "No new files" in result.output
            assert "STEP 1" in result.output
            assert "STEP 2" in result.output

        finally:
            os.chdir(old_cwd)
