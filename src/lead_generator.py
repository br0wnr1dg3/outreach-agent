"""Lead generation orchestrator."""

import asyncio
from pathlib import Path

import structlog

from src.config import load_lead_gen_config, DEFAULT_CONFIG_PATH
from src.db import (
    DEFAULT_DB_PATH, insert_lead, is_company_searched,
    insert_searched_company, update_company_leads_found,
    count_leads_generated_today
)
from src.fb_ads import get_advertiser_domains
from src.apollo import find_leads_at_company

log = structlog.get_logger()


async def generate_leads(
    db_path: Path = DEFAULT_DB_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    dry_run: bool = False,
    keyword_override: str | None = None
) -> dict:
    """Generate new leads from FB Ad Library + Apollo.

    Returns summary dict with stats.
    """
    config = load_lead_gen_config(config_path)

    # Check daily quota
    generated_today = count_leads_generated_today(db_path)
    remaining = config.quotas.leads_per_day - generated_today

    if remaining <= 0:
        log.info("daily_lead_quota_reached", generated=generated_today)
        return {"leads_added": 0, "companies_checked": 0, "quota_reached": True, "dry_run": dry_run}

    results = {
        "leads_added": 0,
        "companies_checked": 0,
        "companies_skipped": 0,
        "quota_reached": False,
        "dry_run": dry_run
    }

    keywords = [keyword_override] if keyword_override else config.search.keywords

    for keyword in keywords:
        if results["leads_added"] >= remaining:
            results["quota_reached"] = True
            break

        # Get advertiser domains from FB
        advertisers = await get_advertiser_domains(
            keyword=keyword,
            country=config.search.countries[0],
            status=config.search.status,
            limit=config.quotas.max_companies_to_check
        )

        for advertiser in advertisers:
            if results["leads_added"] >= remaining:
                results["quota_reached"] = True
                break

            domain = advertiser["domain"]

            # Skip if already searched
            if is_company_searched(db_path, domain):
                results["companies_skipped"] += 1
                continue

            results["companies_checked"] += 1

            if dry_run:
                log.info("dry_run_would_search", domain=domain, keyword=keyword)
                continue

            # Mark as searched
            insert_searched_company(
                db_path, domain,
                company_name=advertiser.get("company_name"),
                source_keyword=keyword,
                fb_page_id=advertiser.get("page_id")
            )

            # Find leads at this company
            leads = await find_leads_at_company(
                domain=domain,
                job_titles=config.targeting.job_titles,
                max_leads=min(3, remaining - results["leads_added"])
            )

            leads_from_company = 0
            for lead in leads:
                lead_id = insert_lead(
                    db_path=db_path,
                    email=lead["email"],
                    first_name=lead["first_name"],
                    last_name=lead.get("last_name"),
                    company=lead.get("company"),
                    title=lead.get("title"),
                    linkedin_url=lead.get("linkedin_url")
                )

                if lead_id:
                    results["leads_added"] += 1
                    leads_from_company += 1
                    log.info("lead_added", email=lead["email"], company=domain)

            # Update company record
            update_company_leads_found(db_path, domain, leads_from_company)

            # Small delay between companies
            await asyncio.sleep(0.1)

    return results
