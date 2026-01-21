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
        companies_found: int,
        leads_added: int,
        quota_met: bool,
        errors: Optional[list[str]] = None,
    ) -> bool:
        """Send end-of-run summary to Slack.

        Args:
            companies_found: Number of companies discovered
            leads_added: Number of leads added to database
            quota_met: Whether daily quota was achieved
            errors: List of any errors encountered

        Returns:
            True if sent successfully
        """
        if not self.webhook_url:
            log.warning("slack_webhook_not_configured")
            return False

        # Build message
        status_emoji = "✅" if quota_met else "⚠️"
        status_text = "Quota met!" if quota_met else "Quota not met"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} Daily Outreach Complete",
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Companies Found:*\n{companies_found}"},
                    {"type": "mrkdwn", "text": f"*Leads Added:*\n{leads_added}"},
                    {"type": "mrkdwn", "text": f"*Status:*\n{status_text}"},
                ]
            }
        ]

        if errors:
            error_text = "\n".join(f"• {e}" for e in errors[:5])
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
                log.info("slack_summary_sent", companies=companies_found, leads=leads_added)
                return True

        except Exception as e:
            log.error("slack_send_error", error=str(e))
            return False
