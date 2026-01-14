# Outreach Boilerplate Design

A local CLI tool for humor-first cold email outreach. Clone, configure, upload leads, hit go.

## Overview

Solo founder tool that:
1. Imports leads from Excel
2. Scrapes LinkedIn for personalization context
3. Uses Claude Opus 4.5 to generate a personalized joke as email opener
4. Sends via Gmail with proper threading
5. Automates follow-ups via cron
6. Stops sequence when replies detected

## Key Decisions

| Aspect | Decision |
|--------|----------|
| Use case | Solo founder, local use |
| Trigger | CLI command (`python run.py send`) |
| Sequence timing | Cron job (hourly) |
| Email 1 | Opus 4.5 generates personalized joke from LinkedIn |
| Emails 2 & 3 | Self-aware templated follow-ups |
| LinkedIn scraping | Apify |
| Email sending | Gmail via Composio (threaded) |
| State tracking | Local SQLite |
| Reply handling | Auto-detect, stops sequence |
| Config | Separate files (context.md, templates, settings.yaml) |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    outreach-boilerplate/                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  CLI Commands:                                               │
│  ├── python run.py import leads.xlsx    # Import new leads  │
│  ├── python run.py send                 # Send what's due   │
│  └── python run.py status               # Check progress    │
│                                                              │
│  Cron Job (hourly):                                         │
│  └── python run.py send                                     │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Data Flow:                                                  │
│                                                              │
│  leads.xlsx ──► Import ──► SQLite DB                        │
│                              │                               │
│                              ▼                               │
│                    ┌─────────────────┐                      │
│                    │  For each lead: │                      │
│                    │  1. Scrape LinkedIn (Apify)            │
│                    │  2. Claude generates Email 1           │
│                    │  3. Send via Gmail (Composio)          │
│                    │  4. Store thread_id, update status     │
│                    └─────────────────┘                      │
│                              │                               │
│                              ▼                               │
│                    ┌─────────────────┐                      │
│                    │  Cron (hourly): │                      │
│                    │  1. Check for replies (stop if found)  │
│                    │  2. Check what's due (delay_days)      │
│                    │  3. Send follow-up templates           │
│                    └─────────────────┘                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
outreach-boilerplate/
├── run.py                     # CLI entry point
├── config/
│   ├── settings.yaml          # Timing, rate limits, operational config
│   ├── context.md             # Who you are, what you offer, tone
│   ├── email_1.md             # Base template for email 1 (Claude personalizes)
│   ├── followup_1.md          # Template: email 2 (self-aware humor)
│   └── followup_2.md          # Template: email 3 (self-aware humor)
├── src/
│   ├── cli.py                 # CLI argument parsing
│   ├── importer.py            # Parse Excel, insert to SQLite
│   ├── enricher.py            # Apify LinkedIn scraping
│   ├── composer.py            # Claude generates email 1
│   ├── sender.py              # Composio Gmail send/reply
│   ├── scheduler.py           # Check what's due, detect replies
│   └── db.py                  # SQLite schema and queries
├── data/
│   ├── outreach.db            # SQLite database (gitignored)
│   └── leads_example.xlsx     # Example file format
├── .env.example               # Required API keys template
├── pyproject.toml             # Dependencies (uv)
└── README.md                  # Setup instructions
```

## Configuration Files

### settings.yaml

```yaml
# Sequence timing
sequence:
  email_2_delay_days: 3
  email_3_delay_days: 4    # Days after email 2 (7 total from email 1)

# Rate limiting
sending:
  daily_limit: 50          # Max emails per day
  min_delay_seconds: 20    # Min gap between sends
  max_delay_seconds: 60    # Max gap between sends

# Gmail account (Composio)
gmail:
  from_name: "Chris"
```

### context.md

```markdown
## Company
Cheerful - creator affiliate platform

## Value Prop
Help brands turn creators into affiliates without the usual chaos.

## Tone
Curious, casual, not salesy. Self-aware about cold emailing.

## CTA
Quick call to learn about their creator strategy
```

### email_1.md

```markdown
subject: {{generated_subject}}

Hey {{first_name}},

{{generated_joke_opener}}

I'm with Cheerful - we help brands like {{company}} turn
creators into affiliates without the usual headaches.

Curious if you're exploring anything on the creator/affiliate
side right now?

Either way, happy to share what's working for similar brands.

Chris
```

### followup_1.md

```markdown
subject: re: {{original_subject}}

Hey {{first_name}},

Following up on my own cold email. The audacity continues.

Genuinely curious if creator/affiliate stuff is on your radar
or if I should take the hint.

Chris
```

### followup_2.md

```markdown
subject: re: {{original_subject}}

Hey {{first_name}},

Last one, I promise. After this I'll quietly accept defeat
and move on with my life.

If timing's just bad, happy to reconnect later. If it's a
"not interested" - totally get it, no hard feelings.

Chris
```

## Database Schema

```sql
CREATE TABLE leads (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT,
    company TEXT,
    title TEXT,
    linkedin_url TEXT,

    -- Enrichment data (from Apify)
    linkedin_posts TEXT,          -- JSON array of recent posts
    enriched_at TIMESTAMP,
    enrichment_attempts INTEGER DEFAULT 0,

    -- Sequence state
    status TEXT DEFAULT 'new',    -- new | enriching | active | replied | completed
    current_step INTEGER DEFAULT 0,

    -- Gmail threading
    thread_id TEXT,               -- Gmail thread ID for replies
    last_message_id TEXT,         -- Last sent message ID

    -- Timing
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_sent_at TIMESTAMP,
    next_send_at TIMESTAMP,

    -- Generated content (stored so we can track what was sent)
    email_1_subject TEXT,
    email_1_body TEXT
);

CREATE TABLE sent_emails (
    id INTEGER PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id),
    step INTEGER NOT NULL,        -- 1, 2, or 3
    subject TEXT,
    body TEXT,
    gmail_message_id TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Status Flow

```
new → enriching → active → completed
                    ↓
                  replied (stops sequence)
```

## Email Generation (Claude)

Claude Opus 4.5 generates personalized joke openers for email 1.

### System Prompt

```markdown
You are writing cold outreach emails. Your job is to generate a
personalized, genuinely funny opening line based on their LinkedIn.

## What you're looking at:
- Their posts, comments, activity
- Their job title and company
- Their profile headline/summary

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
```

### Example Outputs

**Marketing Director at DTC brand:**
```
subject: your inbox called, it's mad at me

Hey Sarah,

I see you're a "Marketing Director" which LinkedIn tells me
means you mass-delete emails like this for sport. Respect.

Anyway, before you archive me...
```

**Posted about Q4 stress:**
```
subject: adding to your q4 chaos

Hey Mike,

Your post about Q4 being "organized panic" made me think
"perfect time to cold email this guy." You're welcome.

Real quick though...
```

**Nothing interesting on profile:**
```
subject: your linkedin is suspiciously clean

Hey Jessica,

Scrolled your whole profile looking for something to joke about
and you've given me nothing. No hot takes, no humble brags,
not even a cringey motivational quote. I'm impressed and mildly
concerned.

Anyway, since I can't pretend we have something in common...
```

**Enrichment failed (fallback - no LinkedIn references):**
```
subject: cold email but make it honest

Hey Alex,

I'd make a joke about your LinkedIn but honestly I'm just
here to talk about creators. No fake rapport, just a pitch.

I'm with Cheerful...
```

## CLI Commands

### Setup (one-time)

```bash
cp .env.example .env           # Add API keys
composio login                 # Auth with Composio
composio add gmail             # Connect Gmail account
uv sync                        # Install dependencies
```

### Daily Usage

```bash
python run.py import leads.xlsx    # Import new leads
python run.py send                 # Process & send what's due
python run.py status               # Show pipeline status
python run.py status --lead "email@example.com"  # Check specific lead
```

### Cron Setup

```bash
crontab -e
# Add: 0 * * * * cd /path/to/outreach-boilerplate && uv run python run.py send
```

## Command Flows

### `import` Command

1. Parse Excel (expects: email, first_name, last_name, company, title, linkedin_url)
2. Skip duplicates (by email)
3. Insert new leads with status `new`
4. Print summary: "Imported 23 new leads, skipped 5 duplicates"

### `send` Command

1. Check for replies on active sequences → mark as `replied`
2. Find leads with status `new` → enrich → generate email 1 → send → set `active`
3. Find leads with status `active` where `next_send_at <= now` → send follow-up
4. Respect daily limit, add random delays between sends
5. Print summary: "Sent 12 emails (8 new, 4 follow-ups). 38 remaining today."

### `status` Command Output

```
Pipeline Status
───────────────
New (pending enrichment):  14
Active sequences:          47
  - Due for follow-up:      8
Replied:                   12
Completed:                 31
───────────────
Daily sends: 23/50
```

## Error Handling

| Scenario | Handling |
|----------|----------|
| LinkedIn scrape fails (API error) | Retry once. If still fails, mark as `enrichment_failed`. Skip for now, retry on next `send` run (up to 3 attempts total). |
| LinkedIn scrape succeeds but empty | Claude knows it's empty → generates "suspiciously clean" style humor. |
| Enrichment failed 3x | Fall back to company/title based humor only. No LinkedIn references. |
| Claude API error | Retry 2x with exponential backoff. If still fails, skip lead, log error, continue. |
| Gmail send fails | Log error, keep lead in queue, will retry next `send` run. |
| Duplicate email in Excel | Skip on import, log as duplicate. |
| Invalid email format | Skip on import, log as invalid. |
| Reply detection fails | Assume no reply, continue sequence. |
| Daily limit reached | Stop sending, print "Daily limit reached." |
| Lead has no LinkedIn URL | Skip enrichment, generate with company/title based humor. |

## Dependencies

```toml
[project]
name = "outreach-boilerplate"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    "anthropic>=0.40.0",       # Claude Opus 4.5
    "composio-core>=0.5.0",    # Gmail integration
    "openpyxl>=3.1.0",         # Excel parsing
    "pydantic>=2.0.0",         # Config validation
    "pyyaml>=6.0.0",           # settings.yaml parsing
    "httpx>=0.27.0",           # Apify API calls
    "structlog>=24.0.0",       # Logging
]
```

## What's NOT Included (Intentionally)

- Lead discovery/scraping (you bring the leads)
- Web UI (CLI only)
- Slack notifications (terminal output)
- Multi-user/team features
- Supabase/cloud DB
- Instantly integration (replaced with direct Gmail)

## References

This design draws from:
- `agent-boilerplate`: Composio Gmail integration pattern
- `cheerful-gtm`: Lead processing and Claude copywriting flow
- `cheerful-engine`: Email sequencing, threading, and rate limiting
