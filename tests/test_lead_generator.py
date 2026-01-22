"""Tests for lead generation orchestrator."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock

from src.db import init_db, is_company_searched, insert_searched_company, insert_lead
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
"""
        )

        result = await generate_leads(db_path=db_path, config_path=config_path)

        assert result["quota_reached"] is True
        assert result["leads_added"] == 0
