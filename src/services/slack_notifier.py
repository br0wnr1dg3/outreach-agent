# src/services/slack_notifier.py
"""Slack notification service for discovery agent."""

import os
from typing import Optional

import httpx
import structlog

log = structlog.get_logger()


class SlackNotifier:
    """Service for sending Slack notifications."""

    def __init__(self, webhook_url: Optional[str] = None):
        """Initialize with webhook URL."""
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")

    async def send_summary(
        self,
        weekly_stats: dict,
        all_time_stats: dict,
        errors: Optional[list[str]] = None,
    ) -> bool:
        """Send end-of-run summary to Slack.

        Args:
            weekly_stats: Dict with leads_found, leads_contacted, leads_replied
            all_time_stats: Dict with leads_found, leads_contacted, leads_replied, reply_rate
            errors: List of any errors encountered

        Returns:
            True if sent successfully
        """
        if not self.webhook_url:
            log.warning("slack_webhook_not_configured")
            return False

        # Build message blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Daily Outreach Complete",
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": "*This Week*"},
                    {"type": "mrkdwn", "text": "*All Time*"},
                    {"type": "mrkdwn", "text": f"Leads Found: {weekly_stats['leads_found']}"},
                    {"type": "mrkdwn", "text": f"Leads Found: {all_time_stats['leads_found']}"},
                    {"type": "mrkdwn", "text": f"Contacted: {weekly_stats['leads_contacted']}"},
                    {"type": "mrkdwn", "text": f"Contacted: {all_time_stats['leads_contacted']}"},
                    {"type": "mrkdwn", "text": f"Replied: {weekly_stats['leads_replied']}"},
                    {"type": "mrkdwn", "text": f"Replied: {all_time_stats['leads_replied']}"},
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Reply Rate:* {all_time_stats['reply_rate']}%"
                }
            }
        ]

        if errors:
            error_text = "\n".join(f"* {e}" for e in errors[:5])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Issues:*\n{error_text}"}
            })

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.webhook_url,
                    json={"blocks": blocks},
                )
                response.raise_for_status()
                log.info(
                    "slack_summary_sent",
                    weekly_found=weekly_stats["leads_found"],
                    all_time_found=all_time_stats["leads_found"],
                    reply_rate=all_time_stats["reply_rate"],
                )
                return True

        except Exception as e:
            log.error("slack_send_error", error=str(e))
            return False
