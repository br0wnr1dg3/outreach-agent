"""Facebook Ad Library client using ScrapeCreators API."""

import os
from urllib.parse import urlparse

import httpx
import structlog

SCRAPECREATORS_API_KEY = os.getenv("SCRAPECREATORS_API_KEY", "")
BASE_URL = "https://api.scrapecreators.com/v1/facebook/adLibrary"

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
