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
                f"{BASE_URL}/mixed_people/api_search",
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
    """Enrich people to get email addresses using their Apollo IDs.

    Returns enriched person dicts with email field.
    """
    if not people:
        return []

    if not APOLLO_API_KEY:
        log.warning("apollo_api_key_not_set")
        return []

    enriched = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for person in people:
            person_id = person.get("id")
            if not person_id:
                continue

            try:
                response = await client.post(
                    f"{BASE_URL}/people/match",
                    headers={
                        "Content-Type": "application/json",
                        "Cache-Control": "no-cache",
                    },
                    json={
                        "api_key": APOLLO_API_KEY,
                        "id": person_id,
                    },
                )
                response.raise_for_status()
                data = response.json()
                matched_person = data.get("person")
                if matched_person:
                    enriched.append(matched_person)

            except Exception as e:
                log.error("apollo_enrich_error", error=str(e), person_id=person_id)
                continue

    log.info("apollo_enrich_complete", requested=len(people), matched=len(enriched))
    return enriched


async def find_leads_at_company(
    domain: str,
    job_titles: list[str],
    max_leads: int = 3
) -> list[dict]:
    """Find and enrich leads at a company.

    Args:
        domain: Company domain (e.g., "acme.com")
        job_titles: List of job titles to search for
        max_leads: Maximum number of leads to return

    Returns:
        List of enriched leads ready for DB insert:
        [{"email": "...", "first_name": "...", "last_name": "...",
          "company": "...", "title": "...", "linkedin_url": "..."}, ...]
    """
    people = await search_people(domain, job_titles, limit=max_leads)
    if not people:
        return []

    enriched = await enrich_people(people)

    # Format results and filter out those without email
    results = []
    for person in enriched:
        if not person:
            continue
        email = person.get("email")
        if not email:
            continue

        org = person.get("organization", {})
        company_name = org.get("name") if isinstance(org, dict) else None

        results.append({
            "email": email,
            "first_name": person.get("first_name"),
            "last_name": person.get("last_name"),
            "company": company_name,
            "title": person.get("title"),
            "linkedin_url": person.get("linkedin_url"),
        })

    return results
