"""Email composition using Claude Opus 4.5."""

import json
import os
from pathlib import Path
from typing import Optional

import anthropic
import structlog

from src.config import DEFAULT_CONFIG_PATH, load_template, render_template

log = structlog.get_logger()

MODEL = "claude-opus-4-5-20251101"


def build_system_prompt(context: str) -> str:
    """Build the system prompt for Claude."""
    return f"""You are writing cold outreach emails. Your job is to generate a personalized, genuinely funny opening line based on their LinkedIn profile and posts.

## Context about the sender:
{context}

## Your mission:
1. Find something to riff on - a post, their title, their company, anything
2. Write a SHORT joke or witty observation (1-2 lines max)
3. Self-deprecating > clever. Warm > edgy. Never mean.
4. It's okay if it's not hilarious - aim for a smile, not a laugh track

## Examples of what works:
- Light teasing about their industry
- Self-aware jokes about cold emails
- Observational humor about something on their profile
- Playful takes on their job title

## What to avoid:
- Anything that could be read as insulting
- Jokes about appearance or personal life
- Trying too hard (desperation isn't funny)
- Generic humor that could apply to anyone

## If their LinkedIn is empty or you can't find anything:
- Make a joke about how clean/empty their profile is
- Or be self-aware about having nothing to reference

## Output format:
Return a JSON object with exactly two fields:
- "subject": A 3-6 word subject line, lowercase, curiosity-inducing
- "joke_opener": Your 1-2 sentence personalized joke opening

Example output:
{{"subject": "your linkedin is suspiciously clean", "joke_opener": "Scrolled your whole profile looking for something clever to reference and you've given me nothing. No hot takes, no humble brags. I respect the mystery."}}
"""


async def generate_email_1(
    lead: dict,
    posts: list[str],
    config_path: Path = DEFAULT_CONFIG_PATH
) -> tuple[str, str]:
    """Generate personalized email 1 using Claude.

    Returns (subject, body) tuple.
    """
    context = load_template(config_path, "context.md")
    email_template = load_template(config_path, "email_1.md")

    # Build the user message with lead info
    posts_text = "\n".join(f"- {post}" for post in posts) if posts else "No recent posts found."

    user_message = f"""Generate a personalized joke opener for this lead:

Name: {lead.get('first_name', '')} {lead.get('last_name', '')}
Company: {lead.get('company', 'Unknown')}
Title: {lead.get('title', 'Unknown')}

Their recent LinkedIn posts:
{posts_text}

Remember: Return valid JSON with "subject" and "joke_opener" fields only."""

    system_prompt = build_system_prompt(context)

    log.info("generating_email", email=lead.get("email"))

    try:
        client = anthropic.AsyncAnthropic()

        response = await client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )

        response_text = response.content[0].text.strip()

        # Parse JSON response
        # Handle potential markdown code blocks
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        result = json.loads(response_text)

        subject = result.get("subject", "quick question")
        joke_opener = result.get("joke_opener", "")

        # Render the template
        variables = {
            "generated_subject": subject,
            "generated_joke_opener": joke_opener,
            "first_name": lead.get("first_name", ""),
            "last_name": lead.get("last_name", ""),
            "company": lead.get("company", "your company"),
        }

        body = render_template(email_template, variables)

        # Extract subject from body if template has it
        lines = body.strip().split("\n")
        if lines[0].lower().startswith("subject:"):
            subject = lines[0].split(":", 1)[1].strip()
            body = "\n".join(lines[1:]).strip()

        log.info("email_generated", email=lead.get("email"), subject=subject)

        return subject, body

    except json.JSONDecodeError as e:
        log.error("json_parse_error", error=str(e), response=response_text[:200])
        # Fallback
        return generate_fallback_email(lead, config_path)
    except Exception as e:
        log.error("claude_error", error=str(e))
        return generate_fallback_email(lead, config_path)


def generate_fallback_email(lead: dict, config_path: Path) -> tuple[str, str]:
    """Generate a fallback email when Claude fails."""
    email_template = load_template(config_path, "email_1.md")

    variables = {
        "generated_subject": "cold email but make it honest",
        "generated_joke_opener": "I'd make a clever joke about your LinkedIn but honestly I'm just here to talk about creators. No fake rapport, just a pitch.",
        "first_name": lead.get("first_name", ""),
        "last_name": lead.get("last_name", ""),
        "company": lead.get("company", "your company"),
    }

    body = render_template(email_template, variables)

    lines = body.strip().split("\n")
    if lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip()
        body = "\n".join(lines[1:]).strip()
    else:
        subject = "cold email but make it honest"

    return subject, body
