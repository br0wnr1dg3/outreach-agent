"""Email composition using Claude Opus 4.5."""

import json
import os
from pathlib import Path
from typing import Optional

import anthropic
import structlog

from src.core.config import DEFAULT_CONFIG_PATH, load_template, render_template

log = structlog.get_logger()

MODEL = "claude-opus-4-5-20251101"


def build_system_prompt(context: str, email_template: str) -> str:
    """Build the system prompt for Claude."""
    return f"""You are writing cold outreach emails. Your job is to write the FULL email using the template as a guide, with a personalized, genuinely funny opening based on their LinkedIn profile.

## Context about the sender:
{context}

## Email template (use as a guide, adjust for natural flow):
```
{email_template}
```

## Your mission:
1. Find something specific to riff on - a post, a phrase they used, a quirky detail, anything with texture
2. Write an actual JOKE or witty observation (1-2 lines max) - not just a compliment
3. Write a natural transition from joke to the ask
4. Keep the core ask/CTA from the template but adjust wording slightly if needed for flow
5. Self-deprecating > clever. Warm > edgy. Never mean.

## What counts as a joke vs. flattery:
FLATTERY (boring): "You manage a huge team and that's intimidating" - just restating their accomplishments
JOKE (good): Comedic contrast between their success and your struggles, or a specific self-aware observation
FLATTERY (boring): "Your career is impressive and I'm questioning my life choices" - vague self-deprecation
JOKE (good): Reference something specific they said/did and make a witty observation about it

The key: jokes have SURPRISE or CONTRAST. Flattery is just "you're great, I'm not."

## Examples of what works:
- Light teasing about their industry
- Self-aware jokes about cold emails
- Observational humor about something on their profile
- Playful takes on their job title

## What to avoid:
- Political humor (no references to elections, politicians, government, DOGE, etc.)
- Mocking their career path, job changes, or work history
- Judgmental observations about their company or role
- Jokes about appearance or personal life
- Trying too hard (desperation isn't funny)
- Generic humor that could apply to anyone

## Where the joke should land:
- On YOU (the sender) - "I stalked your LinkedIn for 20 minutes and this is the best I've got"
- On the SITUATION (cold emailing is awkward) - "This is the part where I pretend we have mutual context"
- On YOUR REACTION to them - "Your post made me feel inadequate" / "I read your headline three times and I'm still confused (that's on me)"
- NEVER on THEM - their choices, career, company, brand, or work are off-limits for humor

## Critical rule:
If you notice something interesting/confusing/unusual about their profile, DO NOT comment on it directly. Instead, make the joke about YOUR confused reaction or YOUR inadequacy.
BAD: "I can't tell if you're building a cult or an agency" (judges them)
GOOD: "I've read your headline four times and I'm still not smart enough to summarize what you do" (judges yourself)

When referencing their accomplishments, be clearly IMPRESSED, not ambiguously tired/bored.
NEVER use "tired", "nap", "lie down", "exhausted", "sleepy" - these read as "you bored me"
BAD: "I scrolled your deals and need a nap" (sounds dismissive)
GOOD: "I scrolled your deals and now I'm questioning my entire career" (clearly impressed/intimidated)

## If their LinkedIn is empty or you can't find anything:
- Make a joke about how clean/empty their profile is
- Or be self-aware about having nothing to reference

## Output format:
Return a JSON object with exactly two fields:
- "subject": A 3-6 word subject line, lowercase, curiosity-inducing
- "body": The FULL email body (everything after "Hey [Name],")

Example output:
{{"subject": "i read your whole linkedin", "body": "Spent way too long scrolling your profile trying to find something clever to say. This is apparently the best I could do.\\n\\nI'm researching how marketers leverage affiliates and creators to create a content machine for paid media campaigns. I'd love to ask your advice to help round out my research & can share some of what I've learned so far. Do you have 10min for a short interview in the next few days?\\n\\nChris"}}
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
    email_template = load_template(config_path, "email_1.md")

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
