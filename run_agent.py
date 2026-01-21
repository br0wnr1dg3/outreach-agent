#!/usr/bin/env python
"""Run the discovery agent (for cron scheduling)."""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import structlog
from src.agents.discovery_agent import DiscoveryAgent
from src.services.slack_notifier import SlackNotifier

log = structlog.get_logger()


async def main():
    """Run the discovery agent and send Slack summary."""
    # Skip weekends
    if datetime.now().weekday() >= 5:
        log.info("skipping_weekend")
        return

    daily_target = int(os.getenv("DAILY_TARGET", "10"))

    log.info("discovery_agent_starting", target=daily_target)

    companies_found = 0
    leads_added = 0
    errors = []

    try:
        agent = DiscoveryAgent()

        async for message in agent.run(daily_target=daily_target):
            if hasattr(message, 'result'):
                result = message.result
                log.info("agent_progress", result=result[:200] if isinstance(result, str) else result)

        # Get final stats from Supabase
        stats = agent.supabase.get_daily_stats()
        companies_found = stats.get("companies_checked_today", 0)
        leads_added = stats.get("leads_generated_today", 0)

    except Exception as e:
        log.error("agent_error", error=str(e))
        errors.append(str(e))

    # Send Slack summary
    notifier = SlackNotifier()
    await notifier.send_summary(
        companies_found=companies_found,
        leads_added=leads_added,
        quota_met=leads_added >= daily_target,
        errors=errors if errors else None,
    )

    log.info("discovery_agent_complete", companies=companies_found, leads=leads_added)


if __name__ == "__main__":
    asyncio.run(main())
