"""Email composition using Claude Opus 4.5."""

import json
import os
from pathlib import Path
from typing import Optional

import anthropic
import structlog

from src.core.config import DEFAULT_CONFIG_PATH, get_template_by_name, load_template, render_template

log = structlog.get_logger()

MODEL = "claude-opus-4-5-20251101"


def build_system_prompt(context: str, email_template: str) -> str:
    """Build the system prompt for Claude."""
    return f"""You are writing cold outreach emails. Your job is to write the FULL email using the template as a guide, with a personalized, genuinely funny opening based on their LinkedIn profile.

## Context about the sender:
{context}

## Email template (use as a guide, adjust for natural flow including transition from joke to ask):
```
{email_template}
```

## Your mission:
1. Find something specific from their recent posts to reference and riff on
2. Write an actual JOKE (1-2 lines max) - sharp, unexpected, memorable
3. Write a natural transition from joke to the ask (does not always have to be "Anyway, terrible jokes aside...")
4. Keep the core ask/CTA from the template but adjust wording slightly if needed for flow

## How jokes work in these emails:

STRUCTURE: [Specific reference to recent content] + [Sharp or absurdist punchline]

The reference proves you read their stuff. The punchline should surprise or delight.

## Recency rule:
- ONLY reference posts/content if they're from the last 2 weeks
- If no recent posts, use pure cold-email situational humor instead
- Never reference stale content—it's worse than no reference at all

## What makes a joke land:

1. **Riff on what they actually said** - Don't just compliment it, play with it
   - "You called out the 'comment TRENDS for the report' move as cringe. So I'm cold emailing you instead—much classier."
   - "Your take on brands needing to give up control was sharp. Somewhere a VP of Marketing just felt a chill."

2. **Absurdist angles** - Unexpected comparisons, playful escalation
   - "Your post on Gen Alpha shaping purchase decisions was eye-opening. I'm now convinced my 8-year-old nephew has more market influence than I do."
   - "Read your breakdown on creator attribution. I understood about 80% of it, which puts me ahead of most CMOs I've talked to."

3. **Meta cold-email humor** (fallback when no recent content)
   - "The playbook says I should pretend we have a mutual connection. We don't. So here's me just... asking."
   - "I could manufacture some fake rapport here but honestly, let's skip to the part where I pitch you something."

## What's OFF-LIMITS:
- Implying their content confused, bored, or overwhelmed you
- Backhanded compliments disguised as self-deprecation ("questioning my career", "not smart enough")
- Their job title, career path, or company as punchline
- Anything that makes them the butt of the joke
- Political humor (elections, politicians, government, DOGE, etc.)
- Jokes about appearance or personal life
- Generic humor that could apply to anyone
- Absolutely NO em-dashes (—)

The target is always: the situation, the industry, yourself, or a playful observation about what they said. Never them personally.

## If their LinkedIn is empty or no recent posts:
- Use pure cold-email meta humor
- Example: "I looked for something clever to reference on your profile. LinkedIn gave me nothing. So here's the pitch without the pretense."

## Output format:
Return a JSON object with exactly two fields:
- "subject": A 3-6 word subject line, lowercase, curiosity-inducing
- "body": The FULL email body (everything after "Hey [Name],")

Example output:
{{"subject": "your gen alpha take was spot on", "body": "Your post on Gen Alpha shaping purchase decisions was eye-opening. I'm now convinced my 8-year-old nephew has more market influence than I do.\\n\\nAnyway—I'm researching how marketers leverage creators to build a content machine for paid media. I'd love to ask your advice to help round out my research & can share some of what I've learned so far. Do you have 10min for a short interview in the next few days?\\n\\nChris"}}
"""


async def generate_email_1(
    lead: dict,
    posts: list[str],
    profile: dict = None,
    config_path: Path = DEFAULT_CONFIG_PATH
) -> tuple[str, str]:
    """Generate personalized email 1 using Claude.

    Returns (subject, body) tuple.
    """
    profile = profile or {}
    context = load_template(config_path, "context.md")
    email_1 = get_template_by_name(config_path, "email_1")
    email_template = f"subject: {email_1.subject}\n\n{email_1.body}"

    # Build the user message with lead info
    posts_text = "\n".join(f"- {post}" for post in posts) if posts else "No recent posts found."

    # Use scraped profile data if available, fallback to lead dict (from Excel)
    first_name = profile.get("firstName") or lead.get('first_name', '')
    name = profile.get("fullName") or f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
    company = profile.get("companyName") or lead.get('company', 'Unknown')
    title = profile.get("headline") or lead.get('title', 'Unknown')
    about = profile.get("summary") or ""
    location = profile.get("location") or ""

    # Build profile section
    profile_section = f"""Name: {name}
Company: {company}
Title/Headline: {title}"""

    if about:
        # Truncate about to avoid token bloat
        about_preview = about[:500] + "..." if len(about) > 500 else about
        profile_section += f"\nAbout: {about_preview}"

    if location:
        profile_section += f"\nLocation: {location}"

    user_message = f"""Write a personalized cold email for this lead:

{profile_section}

Their recent LinkedIn posts:
{posts_text}

Remember: Return valid JSON with "subject" and "body" fields. The body should be the FULL email after "Hey {first_name},"."""

    system_prompt = build_system_prompt(context, email_template)

    log.info("generating_email", email=lead.get("email"))

    try:
        client = anthropic.AsyncAnthropic()

        response = await client.messages.create(
            model=MODEL,
            max_tokens=800,
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
        body = result.get("body", "")

        # Prepend greeting
        full_body = f"Hey {first_name},\n\n{body}"

        log.info("email_generated", email=lead.get("email"), subject=subject)

        return subject, full_body

    except json.JSONDecodeError as e:
        log.error("json_parse_error", error=str(e), response=response_text[:200])
        # Fallback
        return generate_fallback_email(lead, config_path)
    except Exception as e:
        log.error("claude_error", error=str(e))
        return generate_fallback_email(lead, config_path)


def generate_fallback_email(lead: dict, config_path: Path) -> tuple[str, str]:
    """Generate a fallback email when Claude fails."""
    email_1 = get_template_by_name(config_path, "email_1")

    variables = {
        "generated_subject": "cold email but make it honest",
        "generated_joke_opener": "I'd make a clever joke about your LinkedIn but honestly I'm just here to talk about creators. No fake rapport, just a pitch.",
        "first_name": lead.get("first_name", ""),
        "last_name": lead.get("last_name", ""),
        "company": lead.get("company", "your company"),
    }

    subject = render_template(email_1.subject, variables)
    body = render_template(email_1.body, variables)

    return subject, body
