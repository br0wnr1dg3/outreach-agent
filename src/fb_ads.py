"""Facebook Ad Library client using ScrapeCreators API."""

import os
from urllib.parse import urlparse

import httpx
import structlog

SCRAPECREATORS_API_KEY = os.getenv("SCRAPECREATORS_API_KEY", "")
BASE_URL = "https://api.scrapecreators.com/v1/facebook/adLibrary/search/ads"

log = structlog.get_logger()


def extract_domain(url: str) -> str | None:
    """Extract clean domain from URL (e.g., 'glossybrand.com').

    Removes 'www.' prefix if present.
    Returns None for invalid URLs.
    """
    if not url:
        return None
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if not domain:
            return None
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return None


async def search_ads(
    keyword: str,
    country: str = "US",
    status: str = "ACTIVE",
    limit: int = 50
) -> list[dict]:
    """Search FB Ad Library for ads matching keyword.

    Returns list of ad dicts with page_id, page_name, link_url, etc.
    """
    if not SCRAPECREATORS_API_KEY:
        log.warning("scrapecreators_api_key_not_set")
        return []

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                BASE_URL,
                params={
                    "query": keyword,
                    "country": country,
                    "status": status,
                    "trim": "true",
                },
                headers={
                    "x-api-key": SCRAPECREATORS_API_KEY,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("searchResults", [])

    except Exception as e:
        log.error("scrapecreators_search_error", error=str(e), keyword=keyword)
        return []


async def get_advertiser_domains(
    keyword: str,
    country: str = "US",
    status: str = "ACTIVE",
    limit: int = 50
) -> list[dict]:
    """Search ads and return unique advertiser domains.

    Returns: [{"domain": "glossybrand.com", "page_id": "123", "company_name": "Glossy Brand"}, ...]
    """
    ads = await search_ads(keyword, country, status, limit)

    seen_domains: set[str] = set()
    results: list[dict] = []

    for ad in ads:
        # link_url can be at root level or in snapshot
        link_url = ad.get("link_url") or ""
        if not link_url:
            snapshot = ad.get("snapshot", {})
            link_url = snapshot.get("link_url") or ""

        domain = extract_domain(link_url)

        if not domain or domain in seen_domains:
            continue

        seen_domains.add(domain)
        results.append({
            "domain": domain,
            "page_id": ad.get("page_id"),
            "company_name": ad.get("page_name"),
        })

    log.info("get_advertiser_domains_complete", keyword=keyword, count=len(results))
    return results
