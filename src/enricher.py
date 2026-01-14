"""LinkedIn profile enrichment via Apify."""

import os
from pathlib import Path
from typing import Optional

import httpx
import structlog

from src.db import DEFAULT_DB_PATH, get_lead_by_id, update_lead_enrichment

log = structlog.get_logger()

APIFY_API_KEY = os.getenv("APIFY_API_KEY", "")
APIFY_ACTOR_ID = "curious_coder/linkedin-profile-scraper"
APIFY_BASE_URL = "https://api.apify.com/v2"


async def scrape_linkedin_posts(linkedin_url: str) -> list[str]:
    """Scrape recent posts from a LinkedIn profile using Apify.

    Returns list of post text content.
    """
    if not APIFY_API_KEY:
        log.warning("apify_api_key_not_set")
        return []

    # Run the actor synchronously
    run_url = f"{APIFY_BASE_URL}/acts/{APIFY_ACTOR_ID}/run-sync-get-dataset-items"

    payload = {
        "startUrls": [{"url": linkedin_url}],
        "includeRecentPosts": True,
        "maxPosts": 5,
    }

    headers = {
        "Authorization": f"Bearer {APIFY_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(run_url, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()

            if not data or len(data) == 0:
                return []

            profile = data[0]
            posts = profile.get("recentPosts", [])

            return [post.get("text", "") for post in posts if post.get("text")]

    except httpx.HTTPError as e:
        log.error("apify_request_failed", error=str(e))
        return []
    except Exception as e:
        log.error("apify_unexpected_error", error=str(e))
        return []


async def enrich_lead(lead_id: int, db_path: Path = DEFAULT_DB_PATH) -> dict:
    """Enrich a lead with LinkedIn data.

    Returns dict with success status and posts.
    """
    lead = get_lead_by_id(db_path, lead_id)

    if not lead:
        log.error("lead_not_found", lead_id=lead_id)
        return {"success": False, "posts": [], "error": "Lead not found"}

    linkedin_url = lead["linkedin_url"]

    if not linkedin_url:
        log.info("no_linkedin_url", lead_id=lead_id, email=lead["email"])
        update_lead_enrichment(db_path, lead_id, [], success=True)
        return {"success": True, "posts": [], "note": "No LinkedIn URL"}

    log.info("enriching_lead", lead_id=lead_id, email=lead["email"])

    try:
        posts = await scrape_linkedin_posts(linkedin_url)
        update_lead_enrichment(db_path, lead_id, posts, success=True)

        log.info("enrichment_complete", lead_id=lead_id, post_count=len(posts))
        return {"success": True, "posts": posts}

    except Exception as e:
        log.error("enrichment_failed", lead_id=lead_id, error=str(e))
        update_lead_enrichment(db_path, lead_id, [], success=False)
        return {"success": False, "posts": [], "error": str(e)}
