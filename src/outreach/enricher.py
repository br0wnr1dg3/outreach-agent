"""LinkedIn profile enrichment via Apify."""

import asyncio
import os
import re
from pathlib import Path
from typing import Optional

import httpx
import structlog

from src.core.db import DEFAULT_DB_PATH, get_lead_by_id, update_lead_enrichment

log = structlog.get_logger()

APIFY_API_KEY = os.getenv("APIFY_API_KEY", "")
APIFY_BASE_URL = "https://api.apify.com/v2"

# Working actor IDs (both from apimaestro)
PROFILE_ACTOR = "apimaestro~linkedin-profile-detail"
POSTS_ACTOR = "apimaestro~linkedin-profile-posts"


def _extract_username(linkedin_url: str) -> str:
    """Extract username from LinkedIn URL.

    Examples:
        https://linkedin.com/in/satyanadella -> satyanadella
        http://www.linkedin.com/in/john-doe-123 -> john-doe-123
    """
    match = re.search(r"/in/([^/?]+)", linkedin_url)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract username from LinkedIn URL: {linkedin_url}")


async def _run_actor(client: httpx.AsyncClient, actor_id: str, input_data: dict) -> list[dict]:
    """Run an Apify actor and wait for results."""
    # Start the actor run
    url = f"{APIFY_BASE_URL}/acts/{actor_id}/runs"
    response = await client.post(
        url,
        params={"token": APIFY_API_KEY},
        json=input_data,
    )
    response.raise_for_status()
    run_data = response.json()

    run_id = run_data["data"]["id"]
    dataset_id = run_data["data"]["defaultDatasetId"]

    log.info("apify_run_started", actor=actor_id, run_id=run_id)

    # Poll for completion (up to 60 seconds)
    run_url = f"{APIFY_BASE_URL}/actor-runs/{run_id}"
    for _ in range(60):
        await asyncio.sleep(1)
        status_response = await client.get(
            run_url,
            params={"token": APIFY_API_KEY},
        )
        status_data = status_response.json()
        status = status_data.get("data", {}).get("status")

        if status == "SUCCEEDED":
            break
        elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
            raise RuntimeError(f"Apify actor run failed with status: {status}")

    # Fetch results from dataset
    dataset_url = f"{APIFY_BASE_URL}/datasets/{dataset_id}/items"
    results_response = await client.get(
        dataset_url,
        params={"token": APIFY_API_KEY},
    )
    results_response.raise_for_status()
    return results_response.json()


async def scrape_linkedin_profile(linkedin_url: str) -> dict:
    """Scrape LinkedIn profile data using Apify.

    Returns profile dict with firstName, lastName, headline, summary, etc.
    """
    if not APIFY_API_KEY:
        log.warning("apify_api_key_not_set")
        return {}

    try:
        username = _extract_username(linkedin_url)
    except ValueError as e:
        log.error("linkedin_url_parse_error", error=str(e))
        return {}

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            results = await _run_actor(
                client,
                PROFILE_ACTOR,
                {"username": username, "includeEmail": False},
            )

            if not results:
                log.warning("apify_profile_empty", url=linkedin_url)
                return {}

            # Profile data is in basic_info
            data = results[0]
            basic_info = data.get("basic_info", {})

            # Extract location string
            location_data = basic_info.get("location", {})
            location = location_data.get("full", "") if isinstance(location_data, dict) else ""

            return {
                "firstName": basic_info.get("first_name", ""),
                "lastName": basic_info.get("last_name", ""),
                "fullName": basic_info.get("fullname", ""),
                "headline": basic_info.get("headline", ""),
                "summary": basic_info.get("about", ""),
                "companyName": basic_info.get("current_company", ""),
                "location": location,
            }

    except Exception as e:
        log.error("apify_profile_error", error=str(e), url=linkedin_url)
        return {}


async def scrape_linkedin_posts(linkedin_url: str) -> list[str]:
    """Scrape recent posts from a LinkedIn profile using Apify.

    Returns list of post text content.
    """
    if not APIFY_API_KEY:
        log.warning("apify_api_key_not_set")
        return []

    try:
        username = _extract_username(linkedin_url)
    except ValueError as e:
        log.error("linkedin_url_parse_error", error=str(e))
        return []

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            results = await _run_actor(
                client,
                POSTS_ACTOR,
                {"username": username},
            )

            # Extract post text
            posts = []
            for item in results:
                text = item.get("text") or item.get("postText") or item.get("content")
                if text:
                    posts.append(text)

            log.info("apify_posts_complete", count=len(posts))
            return posts

    except Exception as e:
        log.error("apify_posts_error", error=str(e), url=linkedin_url)
        return []


async def enrich_lead(lead_id: int, db_path: Path = DEFAULT_DB_PATH) -> dict:
    """Enrich a lead with LinkedIn data.

    Returns dict with success status, posts, and profile.
    """
    lead = get_lead_by_id(db_path, lead_id)

    if not lead:
        log.error("lead_not_found", lead_id=lead_id)
        return {"success": False, "posts": [], "profile": {}, "error": "Lead not found"}

    linkedin_url = lead["linkedin_url"]

    if not linkedin_url:
        log.info("no_linkedin_url", lead_id=lead_id, email=lead["email"])
        update_lead_enrichment(db_path, lead_id, [], success=True)
        return {"success": True, "posts": [], "profile": {}, "note": "No LinkedIn URL"}

    log.info("enriching_lead", lead_id=lead_id, email=lead["email"])

    try:
        # Scrape both profile and posts in parallel
        profile_task = scrape_linkedin_profile(linkedin_url)
        posts_task = scrape_linkedin_posts(linkedin_url)

        profile, posts = await asyncio.gather(profile_task, posts_task)

        update_lead_enrichment(db_path, lead_id, posts, success=True)

        log.info("enrichment_complete", lead_id=lead_id, post_count=len(posts), has_profile=bool(profile))
        return {"success": True, "posts": posts, "profile": profile}

    except Exception as e:
        log.error("enrichment_failed", lead_id=lead_id, error=str(e))
        update_lead_enrichment(db_path, lead_id, [], success=False)
        return {"success": False, "posts": [], "profile": {}, "error": str(e)}
