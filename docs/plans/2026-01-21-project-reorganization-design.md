# Project Reorganization Design

**Date:** 2026-01-21
**Status:** Approved

## Overview

Reorganize the outreach-boilerplate project for clarity and reduced file count. Group code by business domain (outreach vs discovery) rather than technical layer. Consolidate config files and MCP servers.

## Goals

1. Reduce cognitive load - fewer files, clearer organization
2. Group related code by what problem it solves
3. Consolidate MCP servers into single file
4. Consolidate email templates with timing metadata
5. Add seed customers to lead generation config

## Directory Structure

### Before

```
src/
├── cli.py
├── config.py
├── db.py
├── importer.py
├── enricher.py
├── composer.py
├── sender.py
├── scheduler.py
├── lead_generator.py
├── apollo.py
├── fb_ads.py
├── supabase_client.py
├── agents/
│   └── discovery_agent.py
├── mcp_servers/
│   ├── apollo_server.py
│   ├── fb_ads_server.py
│   ├── supabase_server.py
│   └── web_server.py
└── services/
    ├── slack_notifier.py
    ├── seed_analyzer.py
    └── embedding_service.py

config/
├── settings.yaml
├── lead_gen.yaml
├── context.md
├── email_1.md
├── followup_1.md
└── followup_2.md
```

### After

```
src/
├── core/
│   ├── __init__.py
│   ├── cli.py           # Click CLI entry point
│   ├── config.py        # Pydantic models, template loading
│   └── db.py            # SQLite CRUD
│
├── outreach/            # Email sending pipeline
│   ├── __init__.py
│   ├── importer.py      # Excel → DB
│   ├── enricher.py      # LinkedIn via Apify
│   ├── composer.py      # Email generation via Claude
│   ├── sender.py        # Gmail via Composio
│   └── scheduler.py     # Orchestrates send cycle
│
├── discovery/           # Lead finding pipeline
│   ├── __init__.py
│   ├── agent.py         # Claude Agent SDK orchestrator
│   ├── lead_generator.py # FB Ads → Apollo flow
│   └── mcp_tools.py     # All MCP tool definitions
│
├── clients/             # External API clients
│   ├── __init__.py
│   ├── apollo.py        # Apollo.io API
│   ├── fb_ads.py        # Facebook Ad Library
│   └── supabase.py      # Supabase client
│
└── services/            # Shared services
    ├── __init__.py
    ├── slack_notifier.py
    ├── seed_analyzer.py
    └── embedding_service.py

config/
├── settings.yaml      # Operational: rate limits, Gmail, Slack
├── lead_gen.yaml      # Discovery: keywords, quotas, seeds
├── context.md         # Brand voice for Claude
└── templates.md       # All email templates + timing
```

## Config Changes

### Seed Customers in lead_gen.yaml

```yaml
# Existing content...
keywords:
  - term: "collagen"
    weight: 0.9

# NEW section
seed_customers:
  - domain: "glossier.com"
    name: "Glossier"
  - domain: "drmartens.com"
    name: "Dr. Martens"
  - domain: "athleticgreens.com"
    name: "AG1"
```

### Consolidated templates.md

```markdown
---
template: email_1
delay_days: 0
---

Subject: Quick question about {{company_name}}

Hey {{first_name}},

{{generated_joke_opener}}

...

---
template: followup_1
delay_days: 3
---

Subject: Re: Quick question about {{company_name}}

Hey {{first_name}},

Bumping this up...

---
template: followup_2
delay_days: 7
---

Subject: Re: Quick question about {{company_name}}

Last one, I promise...
```

## Code Changes

### Template Parser (core/config.py)

```python
def load_templates(path: str = "config/templates.md") -> list[EmailTemplate]:
    """Parse templates.md into list of EmailTemplate objects."""
    content = Path(path).read_text()

    # Split on frontmatter delimiters
    sections = re.split(r'^---\s*$', content, flags=re.MULTILINE)

    templates = []
    for i in range(1, len(sections), 2):  # pairs of (frontmatter, body)
        meta = yaml.safe_load(sections[i])
        body = sections[i + 1].strip()
        templates.append(EmailTemplate(
            name=meta["template"],
            delay_days=meta["delay_days"],
            body=body,
        ))
    return templates
```

### Import Path Updates

```python
# Before
from src.apollo import ApolloClient
from src.composer import generate_email
from src.db import get_lead

# After
from src.clients.apollo import ApolloClient
from src.outreach.composer import generate_email
from src.core.db import get_lead
```

### Files Requiring Import Updates

- `run.py`
- `run_agent.py`
- `discovery/agent.py`
- `discovery/lead_generator.py`
- `outreach/scheduler.py`
- All test files

## Test Organization

```
tests/
├── core/
│   ├── test_cli.py
│   ├── test_config.py
│   └── test_db.py
├── outreach/
│   ├── test_composer.py
│   ├── test_enricher.py
│   └── test_sender.py
├── discovery/
│   ├── test_agent.py
│   ├── test_lead_generator.py
│   └── test_mcp_tools.py
├── clients/
│   ├── test_apollo.py
│   ├── test_fb_ads.py
│   └── test_supabase.py
├── services/
│   └── test_slack_notifier.py
└── integration/
    └── test_discovery_flow.py
```

## Data Flow

### Outreach Pipeline

```
Excel file
    → core/db.py (store lead)
    → outreach/importer.py
    → outreach/enricher.py (LinkedIn via Apify)
    → outreach/composer.py (Claude generates joke)
    → outreach/sender.py (Gmail via Composio)
    → outreach/scheduler.py (orchestrates follow-ups)
```

### Discovery Pipeline

```
config/lead_gen.yaml (seeds, keywords)
    → discovery/agent.py (Claude Agent SDK)
    → discovery/mcp_tools.py (tool definitions)
    → clients/fb_ads.py (search advertisers)
    → clients/apollo.py (find contacts)
    → clients/supabase.py (store leads)
    → services/slack_notifier.py (summary)
```

## Summary

| Metric | Before | After |
|--------|--------|-------|
| Config files | 6 | 4 |
| MCP server files | 4 | 1 |
| src/ top-level items | 15+ files | 5 folders |
| Test organization | Mixed | Mirrors src/ |

## Implementation Notes

- Create `__init__.py` files for each new package
- Update all imports across codebase
- Consolidate MCP tools with proper imports from clients
- Add template parser to config.py
- Delete old files after migration complete
