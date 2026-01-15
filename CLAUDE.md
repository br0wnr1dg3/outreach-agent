# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Humor-first cold email outreach CLI. Imports leads from Excel, scrapes LinkedIn for context via Apify, generates personalized joke openers using Claude Opus 4.5, sends via Gmail (Composio), and automates follow-up sequences with reply detection.

## Commands

```bash
# Install dependencies (uses uv, not pip)
uv sync

# Run CLI
python run.py import <excel_file>     # Import leads from Excel
python run.py send                    # Send emails & follow-ups
python run.py status                  # Show pipeline status
python run.py status --lead <email>   # Check specific lead

# Run tests
python -m pytest                      # All tests
python -m pytest tests/test_db.py -v  # Single test file
```

## Architecture

```
src/
├── cli.py        # Click CLI with import/send/status commands
├── config.py     # Pydantic models, template loading from config/
├── db.py         # SQLite CRUD (leads, sent_emails tables)
├── importer.py   # Excel import via openpyxl
├── enricher.py   # LinkedIn scraping via Apify API (async)
├── composer.py   # Email generation with Claude Opus 4.5 (async)
├── sender.py     # Gmail via Composio (sync, wrapped in executor)
└── scheduler.py  # Orchestrates: reply check → new leads → follow-ups
```

**Data flow**: `import` → `enrich_lead()` → `generate_email_1()` → `send_new_email()` → follow-ups via `run_send_cycle()`

## Key Patterns

- **Async/await** throughout; Composio sync calls wrapped with `loop.run_in_executor()`
- **Pydantic** for config validation (SequenceConfig, SendingConfig, GmailConfig, Settings)
- **Template system**: Markdown files in `config/` with `{{variable}}` substitution
- **Structured logging**: via structlog with ISO timestamps
- **Reply detection**: Compares thread message count vs `current_step`

## Configuration

- `config/settings.yaml` - Sequence timing, rate limits, Gmail settings
- `config/context.md` - Brand voice/company context for Claude
- `config/email_1.md` - Primary template (has `{{generated_joke_opener}}` placeholder)
- `config/followup_1.md`, `followup_2.md` - Follow-up templates
- `.env` - API keys: `ANTHROPIC_API_KEY`, `COMPOSIO_API_KEY`, `APIFY_API_KEY`

## Database

SQLite at `data/outreach.db`. Key fields on `leads` table:
- `status`: new → active → replied/completed
- `current_step`: 0-3 (0=new, 1=sent email 1, 2=sent followup 1, 3=done)
- `thread_id`: Gmail thread for reply-in-thread
- `next_send_at`: When next follow-up is due

## External Services

| Service | Purpose | File |
|---------|---------|------|
| Anthropic Claude Opus 4.5 | Joke generation | `composer.py` |
| Apify | LinkedIn scraping | `enricher.py` |
| Composio | Gmail send/reply/threads | `sender.py` |
