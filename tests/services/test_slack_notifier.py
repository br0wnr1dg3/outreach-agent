# tests/services/test_slack_notifier.py
"""Tests for Slack notifier service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_send_summary_posts_with_stats():
    """send_summary should POST formatted stats to webhook URL."""
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

        weekly_stats = {"leads_found": 12, "leads_contacted": 8, "leads_replied": 2}
        all_time_stats = {"leads_found": 247, "leads_contacted": 189, "leads_replied": 31, "reply_rate": 16.4}

        result = await notifier.send_summary(
            weekly_stats=weekly_stats,
            all_time_stats=all_time_stats,
        )

        assert result is True
        mock_client.post.assert_called_once()

        # Verify blocks structure
        call_kwargs = mock_client.post.call_args[1]
        blocks = call_kwargs["json"]["blocks"]

        # Should have header, stats section, and reply rate section
        assert len(blocks) >= 3
        assert blocks[0]["type"] == "header"


@pytest.mark.asyncio
async def test_send_summary_includes_errors_when_provided():
    """send_summary should include errors section when errors provided."""
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

        weekly_stats = {"leads_found": 5, "leads_contacted": 3, "leads_replied": 0}
        all_time_stats = {"leads_found": 100, "leads_contacted": 80, "leads_replied": 10, "reply_rate": 12.5}

        await notifier.send_summary(
            weekly_stats=weekly_stats,
            all_time_stats=all_time_stats,
            errors=["API timeout", "Rate limited"],
        )

        call_kwargs = mock_client.post.call_args[1]
        blocks = call_kwargs["json"]["blocks"]

        # Find errors section
        error_block = [b for b in blocks if b.get("type") == "section" and "Issues" in str(b)]
        assert len(error_block) == 1
