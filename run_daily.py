#!/usr/bin/env python3
"""Daily automation wrapper: discovery → outreach.

Both pipelines now use SQLite (data/outreach.db) so no sync needed.
"""

import asyncio
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import structlog

from src.core.db import DEFAULT_DB_PATH, init_db

log = structlog.get_logger()


async def main():
    start_time = datetime.now()
    log.info("daily_run_started", time=start_time.isoformat())

    # Ensure SQLite database exists
    init_db(DEFAULT_DB_PATH)

    # Step 1: Run discovery to find new leads (stores to SQLite)
    log.info("step_1_discovery", status="starting")
    try:
        from run_agent import main as run_discovery
        await run_discovery()
        log.info("step_1_discovery", status="completed")
    except Exception as e:
        log.error("step_1_discovery", status="failed", error=str(e))
        # Continue - we may have existing leads to process

    # Step 2: Run outreach to send emails (reads from SQLite)
    log.info("step_2_outreach", status="starting")
    try:
        from src.outreach.scheduler import run_send_cycle
        results = await run_send_cycle()
        log.info("step_2_outreach", status="completed", **results)
    except Exception as e:
        log.error("step_2_outreach", status="failed", error=str(e))

    elapsed = (datetime.now() - start_time).total_seconds()
    log.info("daily_run_completed", elapsed_seconds=elapsed)


if __name__ == "__main__":
    asyncio.run(main())
