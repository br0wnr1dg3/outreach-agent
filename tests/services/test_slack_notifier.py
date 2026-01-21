# tests/test_slack_notifier.py
"""Tests for Slack notifier service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_send_summary_makes_request():
    """send_summary should POST to webhook URL."""
    with patch("src.services.slack_notifier.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        from src.services.slack_notifier import SlackNotifier
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")

        await notifier.send_summary(
            companies_found=10,
            leads_added=12,
            quota_met=True,
        )

        mock_client.post.assert_called_once()
