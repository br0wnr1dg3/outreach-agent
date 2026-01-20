"""Tests for lead generation orchestrator."""

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
