# tests/integration/test_discovery_flow.py
"""Integration test for discovery agent flow."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.mark.asyncio
async def test_full_discovery_flow_dry_run():
    """Test the full discovery flow in dry run mode."""
    # Mock all external services
    with patch("src.agents.discovery_agent.SupabaseClient") as mock_supa_class:
        mock_supa = MagicMock()
        mock_supa.check_company_searched.return_value = False
        mock_supa.get_quota_status.return_value = {
            "leads_today": 0,
            "target": 10,
            "remaining": 10,
            "quota_met": False,
        }
        mock_supa_class.return_value = mock_supa

        with patch("src.agents.discovery_agent.query") as mock_query:
            # Simulate agent completing
            async def mock_query_gen(*args, **kwargs):
                yield MagicMock(result="Discovery complete: 10 companies found")

            mock_query.return_value = mock_query_gen()

            from src.agents.discovery_agent import DiscoveryAgent
            agent = DiscoveryAgent(supabase_client=mock_supa)

            results = []
            async for message in agent.run(daily_target=10, dry_run=True):
                if hasattr(message, 'result'):
                    results.append(message.result)

            assert len(results) > 0
