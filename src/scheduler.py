"""Scheduling logic for email sequences."""

import asyncio
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import structlog

from src.config import DEFAULT_CONFIG_PATH, Settings, load_settings, load_template, render_template
from src.db import (
    DEFAULT_DB_PATH,
    get_leads_by_status,
    get_leads_due_for_followup,
    get_lead_by_id,
    update_lead_status,
    update_lead_email_sent,
    count_sent_today,
)
from src.enricher import enrich_lead
from src.composer import generate_email_1
from src.sender import send_new_email, send_reply_email, check_for_reply

log = structlog.get_logger()


async def check_replies(
    db_path: Path = DEFAULT_DB_PATH,
    connected_account_id: Optional[str] = None
) -> list[str]:
    """Check all active leads for replies.

    Returns list of emails that replied.
    """
    active_leads = get_leads_by_status(db_path, "active")
    replied = []

    for lead in active_leads:
        if not lead["thread_id"]:
            continue

        try:
            has_reply = await check_for_reply(
                lead["thread_id"],
                lead["current_step"],
                connected_account_id
            )

            if has_reply:
                log.info("reply_detected", email=lead["email"])
                update_lead_status(db_path, lead["id"], "replied")
                replied.append(lead["email"])

        except Exception as e:
            log.error("reply_check_failed", email=lead["email"], error=str(e))

    return replied


def get_due_leads(db_path: Path = DEFAULT_DB_PATH) -> list:
    """Get leads due for follow-up."""
    return get_leads_due_for_followup(db_path)


def get_new_leads(db_path: Path = DEFAULT_DB_PATH) -> list:
    """Get leads that haven't been processed yet."""
    return get_leads_by_status(db_path, "new")


async def process_lead(
    lead_id: int,
    settings: Settings,
    db_path: Path = DEFAULT_DB_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH
) -> bool:
    """Process a new lead: enrich, generate email, send.

    Returns True if successful.
    """
    return await process_new_lead(lead_id, settings, db_path, config_path)


async def process_new_lead(
    lead_id: int,
    settings: Settings,
    db_path: Path = DEFAULT_DB_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH
) -> bool:
    """Process a new lead: enrich, generate email, send.

    Returns True if successful.
    """
    lead = get_lead_by_id(db_path, lead_id)
    if not lead:
        return False

    log.info("processing_new_lead", email=lead["email"])

    # Enrich
    enrichment = await enrich_lead(lead_id, db_path)
    posts = enrichment.get("posts", [])

    # Generate email 1
    lead_dict = dict(lead)
    subject, body = await generate_email_1(lead_dict, posts, config_path)

    # Send
    try:
        result = await send_new_email(
            to=lead["email"],
            subject=subject,
            body=body,
            from_name=settings.gmail.from_name,
            connected_account_id=settings.gmail.connected_account_id or None
        )

        # Calculate next send time
        next_send = datetime.utcnow() + timedelta(days=settings.sequence.email_2_delay_days)

        # Update database
        update_lead_email_sent(
            db_path, lead_id, step=1,
            subject=subject, body=body,
            thread_id=result["thread_id"],
            message_id=result["message_id"],
            next_send_at=next_send
        )

        log.info("email_1_sent", email=lead["email"], thread_id=result["thread_id"])
        return True

    except Exception as e:
        log.error("send_failed", email=lead["email"], error=str(e))
        return False


async def process_followup(
    lead_id: int,
    settings: Settings,
    db_path: Path = DEFAULT_DB_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH
) -> bool:
    """Send follow-up email to a lead.

    Returns True if successful.
    """
    lead = get_lead_by_id(db_path, lead_id)
    if not lead:
        return False

    current_step = lead["current_step"]
    next_step = current_step + 1

    if next_step > 3:
        log.info("sequence_complete", email=lead["email"])
        update_lead_status(db_path, lead_id, "completed")
        return True

    log.info("processing_followup", email=lead["email"], step=next_step)

    # Load appropriate template
    template_name = f"followup_{next_step - 1}.md"
    try:
        template = load_template(config_path, template_name)
    except FileNotFoundError:
        log.error("template_not_found", template=template_name)
        return False

    # Render template
    variables = {
        "first_name": lead["first_name"],
        "original_subject": lead["email_1_subject"],
    }
    body = render_template(template, variables)

    # Extract subject
    lines = body.strip().split("\n")
    if lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip()
        body = "\n".join(lines[1:]).strip()
    else:
        subject = f"re: {lead['email_1_subject']}"

    # Send
    try:
        result = await send_reply_email(
            to=lead["email"],
            subject=subject,
            body=body,
            thread_id=lead["thread_id"],
            message_id=lead["last_message_id"],
            from_name=settings.gmail.from_name,
            connected_account_id=settings.gmail.connected_account_id or None
        )

        # Calculate next send time (or None if sequence done)
        if next_step < 3:
            next_send = datetime.utcnow() + timedelta(days=settings.sequence.email_3_delay_days)
        else:
            next_send = None

        update_lead_email_sent(
            db_path, lead_id, step=next_step,
            subject=subject, body=body,
            thread_id=result["thread_id"],
            message_id=result["message_id"],
            next_send_at=next_send
        )

        log.info(f"email_{next_step}_sent", email=lead["email"])
        return True

    except Exception as e:
        log.error("followup_send_failed", email=lead["email"], error=str(e))
        return False


async def run_send_cycle(
    db_path: Path = DEFAULT_DB_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH
) -> dict:
    """Run a complete send cycle.

    1. Check for replies
    2. Process new leads
    3. Send follow-ups

    Returns summary dict.
    """
    settings = load_settings(config_path)

    # Check daily limit
    sent_today = count_sent_today(db_path)
    remaining = settings.sending.daily_limit - sent_today

    if remaining <= 0:
        log.info("daily_limit_reached", sent=sent_today, limit=settings.sending.daily_limit)
        return {
            "replied": [],
            "new_sent": 0,
            "followups_sent": 0,
            "daily_limit_reached": True,
            "sent_today": sent_today,
        }

    results = {
        "replied": [],
        "new_sent": 0,
        "followups_sent": 0,
        "daily_limit_reached": False,
        "sent_today": sent_today,
    }

    # 1. Check for replies
    results["replied"] = await check_replies(
        db_path,
        settings.gmail.connected_account_id or None
    )

    # 2. Process new leads
    new_leads = get_new_leads(db_path)
    for lead in new_leads:
        if remaining <= 0:
            results["daily_limit_reached"] = True
            break

        success = await process_new_lead(lead["id"], settings, db_path, config_path)
        if success:
            results["new_sent"] += 1
            remaining -= 1
            results["sent_today"] += 1

            # Random delay
            delay = random.randint(
                settings.sending.min_delay_seconds,
                settings.sending.max_delay_seconds
            )
            await asyncio.sleep(delay)

    # 3. Send follow-ups
    due_leads = get_due_leads(db_path)
    for lead in due_leads:
        if remaining <= 0:
            results["daily_limit_reached"] = True
            break

        success = await process_followup(lead["id"], settings, db_path, config_path)
        if success:
            results["followups_sent"] += 1
            remaining -= 1
            results["sent_today"] += 1

            # Random delay
            delay = random.randint(
                settings.sending.min_delay_seconds,
                settings.sending.max_delay_seconds
            )
            await asyncio.sleep(delay)

    return results
