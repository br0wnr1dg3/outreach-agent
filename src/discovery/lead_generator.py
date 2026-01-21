"""Lead generation orchestrator."""

import asyncio
from datetime import datetime
from pathlib import Path

import openpyxl
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

LEADS_FOLDER = Path("leads")


def export_leads_to_xlsx(leads: list[dict]) -> Path | None:
    """Export leads to xlsx file in /leads folder.

    Returns path to created file, or None if no leads.
    """
    if not leads:
        return None

    # Ensure leads folder exists
    LEADS_FOLDER.mkdir(exist_ok=True)

    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = LEADS_FOLDER / f"leads_{timestamp}.xlsx"

    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active

    # Header row
    headers = ["email", "first_name", "last_name", "company", "title", "linkedin_url"]
    ws.append(headers)

    # Data rows
    for lead in leads:
        ws.append([
            lead.get("email"),
            lead.get("first_name"),
            lead.get("last_name"),
            lead.get("company"),
            lead.get("title"),
            lead.get("linkedin_url"),
        ])

    wb.save(filename)
    log.info("leads_exported_to_xlsx", filename=str(filename), count=len(leads))
    return filename


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
        "dry_run": dry_run,
        "export_file": None,
    }

    # Track leads for xlsx export
    generated_leads: list[dict] = []

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

            # Skip excluded domains (marketplaces, platforms, etc.)
            if any(excluded in domain for excluded in config.search.excluded_domains):
                results["companies_skipped"] += 1
                continue

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
                    generated_leads.append(lead)
                    log.info("lead_added", email=lead["email"], company=domain)

            # Update company record
            update_company_leads_found(db_path, domain, leads_from_company)

            # Small delay between companies
            await asyncio.sleep(0.1)

    # Export leads to xlsx if any were generated
    if generated_leads and not dry_run:
        export_file = export_leads_to_xlsx(generated_leads)
        results["export_file"] = str(export_file) if export_file else None

    return results
