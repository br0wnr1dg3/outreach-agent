# tests/clients/test_supabase.py
"""Tests for Supabase client."""

import pytest
from unittest.mock import MagicMock, patch


def test_supabase_client_init_requires_env_vars():
    """Client should raise if SUPABASE_URL not set."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="SUPABASE_URL"):
            from src.clients.supabase import SupabaseClient
            SupabaseClient()


def test_check_company_searched_returns_bool():
    """check_company_searched should return boolean."""
    with patch("src.clients.supabase.create_client") as mock_create:
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_create.return_value = mock_client

        with patch.dict("os.environ", {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_KEY": "test-key"}):
            from src.clients.supabase import SupabaseClient
            client = SupabaseClient()
            result = client.check_company_searched("example.com")
            assert isinstance(result, bool)
            assert result is False
