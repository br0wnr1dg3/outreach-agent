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


async def enrich_people(people: list[dict]) -> list[dict]:
    """Bulk enrich people to get email addresses.

    Accepts up to 10 people per call.
    Returns enriched person dicts with email field.
    """
    if not people:
        return []

    if not APOLLO_API_KEY:
        log.warning("apollo_api_key_not_set")
        return []

    try:
        # Build match requests from people data
        details = []
        for person in people[:10]:  # Max 10 per call
            org = person.get("organization", {})
            details.append({
                "first_name": person.get("first_name"),
                "last_name": person.get("last_name"),
                "organization_name": org.get("name") if isinstance(org, dict) else None,
                "linkedin_url": person.get("linkedin_url"),
            })

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{BASE_URL}/people/bulk_match",
                headers={
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache",
                },
                json={
                    "api_key": APOLLO_API_KEY,
                    "details": details,
                },
            )
            response.raise_for_status()
            data = response.json()

            matches = data.get("matches", [])
            log.info("apollo_enrich_complete", requested=len(people), matched=len(matches))
            return matches

    except Exception as e:
        log.error("apollo_enrich_error", error=str(e))
        return []
