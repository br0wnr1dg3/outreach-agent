"""Apollo.io API client for people search and enrichment."""

import os

import httpx
import structlog

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")
BASE_URL = "https://api.apollo.io/api/v1"

log = structlog.get_logger()


async def search_people(
    domain: str,
    job_titles: list[str],
    limit: int = 10
) -> list[dict]:
    """Search for people at a company by domain and job titles.

    Args:
        domain: Company domain (e.g., "acme.com")
        job_titles: List of job titles to search for (e.g., ["CEO", "Founder"])
        limit: Maximum number of results to return

    Returns:
        List of person dicts (without email yet).
    """
    if not APOLLO_API_KEY:
        log.warning("apollo_api_key_not_set")
        return []

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{BASE_URL}/mixed_people/search",
                headers={
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache",
                },
                json={
                    "api_key": APOLLO_API_KEY,
                    "q_organization_domains": domain,
                    "person_titles": job_titles,
                    "per_page": limit,
                },
            )
            response.raise_for_status()
            data = response.json()

            people = data.get("people", [])
            log.info("apollo_search_complete", domain=domain, count=len(people))
            return people

    except Exception as e:
        log.error("apollo_search_error", error=str(e), domain=domain)
        return []
