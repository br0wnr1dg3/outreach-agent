# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Humor-first cold email outreach system with two pipelines:
1. **Outreach** - Import leads, enrich with LinkedIn data, generate personalized joke openers via Claude, send via Gmail, automate follow-ups
2. **Discovery** - Claude Agent SDK finds new leads via FB Ad Library and Apollo.io enrichment

## Commands

```bash
# Install dependencies (uses uv, not pip)
uv sync

# Run CLI (outreach pipeline)
python run.py import <excel_file>     # Import leads from Excel
python run.py send                    # Send emails & follow-ups
python run.py status                  # Show pipeline status
python run.py status --lead <email>   # Check specific lead

# Run discovery agent
python run_agent.py                   # Find new leads (cron-compatible)

# Run tests
python -m pytest                      # All tests
python -m pytest tests/core/ -v       # Test specific module
```

## Architecture

```
src/
├── core/                 # Infrastructure
│   ├── cli.py            # Click CLI entry point
│   ├── config.py         # Pydantic models, template loading
│   └── db.py             # SQLite CRUD (leads, sent_emails)
│
├── outreach/             # Email sending pipeline
│   ├── importer.py       # Excel → DB
│   ├── enricher.py       # LinkedIn scraping via Apify (async)
│   ├── composer.py       # Email generation via Claude Opus 4.5 (async)
│   ├── sender.py         # Gmail via Composio (sync, wrapped in executor)
│   └── scheduler.py      # Orchestrates: reply check → new leads → follow-ups
│
├── discovery/            # Lead finding pipeline
│   ├── agent.py          # Claude Agent SDK orchestrator
│   ├── lead_generator.py # FB Ads → Apollo flow
│   └── mcp_tools.py      # MCP tool definitions for agent
│
├── clients/              # External API clients
│   ├── apollo.py         # Apollo.io API (search, enrich)
│   ├── fb_ads.py         # Facebook Ad Library via ScrapeCreators
│   └── supabase.py       # Supabase client (cloud DB + vector search)
│
└── services/             # Shared services
    ├── slack_notifier.py # End-of-run Slack summaries
    ├── seed_analyzer.py  # Analyze seed customers with Claude
    └── embedding_service.py
```

## Data Flow

**Outreach pipeline:**
```
Excel → core/db → outreach/importer → outreach/enricher → outreach/composer → outreach/sender → outreach/scheduler
```

**Discovery pipeline:**
```
config/lead_gen.yaml → discovery/agent → discovery/mcp_tools → clients/* → services/slack_notifier
```

## Key Patterns

- **Async/await** throughout; Composio sync calls wrapped with `loop.run_in_executor()`
- **Pydantic** for config validation (SequenceConfig, SendingConfig, GmailConfig, Settings)
- **Template system**: `config/templates.md` with `{{variable}}` substitution and per-template timing
- **MCP tools**: Consolidated in `discovery/mcp_tools.py`, wrapping clients for agent use
- **Structured logging**: via structlog with ISO timestamps
- **Reply detection**: Compares thread message count vs `current_step`

## Configuration

```
config/
├── settings.yaml      # Operational: rate limits, Gmail, Slack webhook
├── lead_gen.yaml      # Discovery: keywords, quotas, excluded domains, seed_customers
├── context.md         # Brand voice/company context for Claude
└── templates.md       # Email templates with timing (email_1, followup_1, followup_2)
```

**Environment variables** (`.env`):
- `ANTHROPIC_API_KEY` - Claude API
- `COMPOSIO_API_KEY` - Gmail integration
- `APIFY_API_KEY` - LinkedIn scraping
- `APOLLO_API_KEY` - People search/enrichment
- `SCRAPECREATORS_API_KEY` - FB Ad Library
- `SUPABASE_URL`, `SUPABASE_KEY` - Cloud database
- `SLACK_WEBHOOK_URL` - Notifications

## Database

**SQLite** at `data/outreach.db` for local/dev. **Supabase** for production.

Key fields on `leads` table:
- `status`: new → active → replied/completed
- `current_step`: 0-3 (0=new, 1=sent email 1, 2=sent followup 1, 3=done)
- `thread_id`: Gmail thread for reply-in-thread
- `next_send_at`: When next follow-up is due

## External Services

| Service | Purpose | Location |
|---------|---------|----------|
| Anthropic Claude | Email generation, agent orchestration | `outreach/composer.py`, `discovery/agent.py` |
| Apollo.io | People search & enrichment | `clients/apollo.py` |
| ScrapeCreators | Facebook Ad Library search | `clients/fb_ads.py` |
| Composio | Gmail send/reply/threads | `outreach/sender.py` |
| Apify | LinkedIn scraping | `outreach/enricher.py` |
| Supabase | Cloud DB & vector search | `clients/supabase.py` |
| Slack | Run notifications | `services/slack_notifier.py` |

## Testing

Tests mirror src structure:
```
tests/
├── core/           # test_cli.py, test_config.py, test_db.py
├── outreach/       # test_composer.py, test_enricher.py, test_sender.py
├── discovery/      # test_agent.py, test_lead_generator.py, test_mcp_tools.py
├── clients/        # test_apollo.py, test_fb_ads.py, test_supabase.py
├── services/       # test_slack_notifier.py
└── integration/    # test_discovery_flow.py
```
