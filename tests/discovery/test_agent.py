# tests/test_discovery_agent.py
"""Tests for discovery agent orchestrator."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


def test_discovery_agent_init():
    """Agent should initialize with MCP servers."""
    with patch("src.discovery.agent.SupabaseClient"):
        with patch("src.discovery.agent.create_fb_ads_mcp_server") as mock_fb:
            with patch("src.discovery.agent.create_apollo_mcp_server") as mock_apollo:
                with patch("src.discovery.agent.create_supabase_mcp_server") as mock_supa:
                    with patch("src.discovery.agent.create_web_mcp_server") as mock_web:
                        mock_fb.return_value = MagicMock()
                        mock_apollo.return_value = MagicMock()
                        mock_supa.return_value = MagicMock()
                        mock_web.return_value = MagicMock()

                        from src.discovery.agent import DiscoveryAgent
                        agent = DiscoveryAgent()

                        assert "fb_ads" in agent.mcp_servers
                        assert "apollo" in agent.mcp_servers
                        assert "supabase" in agent.mcp_servers
                        assert "web" in agent.mcp_servers
