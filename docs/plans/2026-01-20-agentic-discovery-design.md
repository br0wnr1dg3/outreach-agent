# Agentic Lead Discovery System Design

**Date:** 2026-01-20
**Status:** Approved

## Overview

Transform the outreach pipeline from a simple sequential flow into an agentic system where a Claude Agent SDK-powered discovery agent autonomously finds and qualifies companies similar to seed customers, hitting a daily target of 10 new companies contacted per weekday.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DISCOVERY AGENT                          │
│  (Claude Agent SDK + MCP Servers)                          │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ FB Ads MCP  │  │ Apollo MCP  │  │ Supabase MCP│        │
│  │ Server      │  │ Server      │  │ Server      │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│         │                │                │                │
│  ┌─────────────┐         │                │                │
│  │ Web MCP     │         │                │                │
│  │ Server      │─────────┴────────────────┘                │
│  └─────────────┘                                           │
│                          │                                  │
│              ┌───────────▼───────────┐                     │
│              │   Claude Orchestrator │                     │
│              │   (decides strategy)  │                     │
│              └───────────────────────┘                     │
│                          │                                  │
│              Reads: seed_profiles/*.md                     │
│              Reads/Writes: search_journal.md               │
│              Updates: lead_gen.yaml weights                │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼ Outputs leads to Supabase
┌─────────────────────────────────────────────────────────────┐
│                 EXISTING PIPELINE                           │
│  enricher.py → composer.py → sender.py → scheduler.py      │
└─────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | Claude Agent SDK + MCP Servers | Full autonomy, dynamic tool selection |
| Autonomy Level | Full autonomy | No human checkpoints during run |
| Seed Analysis | One-time, saved to .md files | Cost efficient, manually refinable |
| Daily Trigger | Scheduled cron (8am weekdays) | Hands-off operation |
| Search Learning | Journal + Weights hybrid | Auditability + efficiency |
| Lead Quality Gates | Apollo check → ICP analysis | Cheapest filter first |
| Contact Priority | Marketing-first title hierarchy | CMO > VP Marketing > Founder > CEO |
| Notifications | End-of-run Slack summary only | Clean, not noisy |
| Failure Handling | Best effort + report | Pragmatic, no complex retries |
| Agent Scope | Discovery only | Existing pipeline handles execution |
| Database | Supabase | Vector search, cloud-hosted, scalable |

## MCP Servers

### 1. `fb_ads_server`
```python
Tools:
- search_advertisers(keyword, country, status) → list of companies
- get_advertiser_details(page_id) → company info, ad count, domain
```

### 2. `apollo_server`
```python
Tools:
- check_company_contacts(domain, job_titles) → bool + count
  # Quick check if anyone reachable exists (Gate 1)
- find_leads_at_company(domain, job_titles, limit) → leads with emails
  # Full enrichment for qualified companies
```

### 3. `supabase_server`
```python
Tools:
- check_company_searched(domain) → bool
- mark_company_searched(domain, source_keyword, leads_found)
- insert_lead(lead_data) → lead_id
- get_daily_stats() → companies_checked, leads_added today
- get_quota_status() → remaining vs target
- search_similar_companies(embedding, limit) → similar companies
```

### 4. `web_server`
```python
Tools:
- fetch_company_page(url) → page content (markdown)
  # Agent analyzes this against seed profiles for ICP fit
```

## Agent Workflow

```
START (8am weekday via cron)
    │
    ▼
Load Context
    ├── Read seed_profiles/*.md (ICP patterns)
    ├── Read search_journal.md (what worked before)
    ├── Read lead_gen.yaml (weighted search terms)
    └── Check quota_status() (how many left today)
    │
    ▼
Select Search Strategy
    │   Agent picks highest-weighted keyword not yet exhausted
    │
    ▼
Search FB Ads ──────────────────────────────────┐
    │                                            │
    ▼                                            │
For each company found:                          │
    │                                            │
    ├─► Already searched? ──YES──► Skip          │
    │                                            │
    ├─► Gate 1: Apollo contacts exist? ──NO──► Skip
    │                                            │
    ├─► Gate 2: Fetch website, compare to ICP    │
    │   └─► Poor fit? ──► Skip, log reasoning    │
    │                                            │
    ├─► Generate leads (top marketing contact)   │
    │   └─► Insert to Supabase, mark searched    │
    │                                            │
    └─► Quota met? ──YES──► Exit loop ───────────┘
    │
    ▼
End of Run
    ├── Update search_journal.md with results
    ├── Recalculate weights in lead_gen.yaml
    └── Send Slack summary
```

## Persistent Memory Files

### Seed Profiles (`config/seed_profiles/*.md`)

Analyzed once, referenced every run:

```markdown
# absolutecollagen.com

## Company Profile
- Category: Beauty/Wellness DTC
- Product: Collagen supplements (subscription)
- Market: UK-primary, expanding US
- Price point: Premium ($50+/month)

## ICP Signals
- Running FB ads (active advertiser)
- Subscription model
- Female 25-45 demographic
- Health/beauty positioning
- Founder-led brand story

## Search Terms That Would Find Similar
- "collagen supplement"
- "beauty subscription box"
- "wellness DTC"
- "anti-aging skincare"

## Decision Maker Profile
- Marketing-focused (CMO, Head of Growth)
- Likely interested in: influencer, UGC, performance creative
```

### Search Journal (`data/search_journal.md`)

```markdown
# Search Journal

## 2026-01-20

### Search: "collagen supplement" (US)
- Companies found: 12
- Passed Gate 1 (has contacts): 8
- Passed Gate 2 (ICP fit): 5
- Leads generated: 5
- Quality notes: Strong category, founders responsive
- Weight adjustment: 0.7 → 0.85

### Search: "beauty DTC"
- Companies found: 25
- Passed Gate 1: 18
- Passed Gate 2: 3
- Leads generated: 3
- Quality notes: Too broad, many non-supplement brands
- Weight adjustment: 0.6 → 0.4
```

## Supabase Schema

```sql
-- Leads (migrated from SQLite + new fields)
CREATE TABLE leads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  first_name TEXT NOT NULL,
  last_name TEXT,
  company TEXT,
  title TEXT,
  linkedin_url TEXT,

  -- Enrichment
  linkedin_posts JSONB,
  enriched_at TIMESTAMPTZ,

  -- Email state
  status TEXT DEFAULT 'new',  -- new, active, replied, completed
  current_step INT DEFAULT 0,
  thread_id TEXT,
  last_message_id TEXT,
  email_1_subject TEXT,
  email_1_body TEXT,

  -- Agent metadata
  source TEXT DEFAULT 'import',  -- 'agent' | 'import'
  source_keyword TEXT,
  company_fit_score INT,
  company_fit_notes TEXT,
  company_embedding VECTOR(1536),

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  imported_at TIMESTAMPTZ DEFAULT NOW(),
  last_sent_at TIMESTAMPTZ,
  next_send_at TIMESTAMPTZ
);

-- Companies searched (prevents re-scraping)
CREATE TABLE searched_companies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain TEXT UNIQUE NOT NULL,
  company_name TEXT,
  source_keyword TEXT,
  passed_gate_1 BOOLEAN,
  passed_gate_2 BOOLEAN,
  leads_found INT DEFAULT 0,
  fit_score INT,
  fit_notes TEXT,
  website_embedding VECTOR(1536),
  searched_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed profiles (for vector similarity matching)
CREATE TABLE seed_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain TEXT UNIQUE NOT NULL,
  name TEXT,
  analysis JSONB,
  embedding VECTOR(1536),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sent emails audit log
CREATE TABLE sent_emails (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID REFERENCES leads(id),
  step INT NOT NULL,
  subject TEXT,
  body TEXT,
  gmail_message_id TEXT,
  sent_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable vector similarity search
CREATE INDEX ON searched_companies USING hnsw (website_embedding vector_cosine_ops);
CREATE INDEX ON seed_profiles USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON leads USING hnsw (company_embedding vector_cosine_ops);
```

## Integration with Existing Pipeline

### Handoff Point

Agent inserts leads into `leads` table with `status='new'`. Existing pipeline takes over.

### Daily Schedule

```
08:00  Agent runs → discovers 10 companies → inserts ~10-15 leads
09:00  Existing pipeline runs → enriches, composes, sends
```

### CLI Commands

```bash
python run.py analyze-seeds <url> [url...]  # One-time: analyze seed customers
python run.py agent                          # Run discovery agent
python run.py agent --dry-run               # Preview without DB writes
python run.py send                          # Existing: enrich + send
python run.py                               # Both: agent then send
```

## Implementation Components

### New Components

| Component | Purpose | Based On |
|-----------|---------|----------|
| `agents/discovery_agent.py` | Main agent orchestrator | granola-tools pattern |
| `mcp_servers/fb_ads_server.py` | FB Ads search tools | existing fb_ads.py |
| `mcp_servers/apollo_server.py` | Apollo search tools | existing apollo.py |
| `mcp_servers/supabase_server.py` | Database operations | granola-tools pattern |
| `mcp_servers/web_server.py` | Website fetching/analysis | new |
| `services/seed_analyzer.py` | One-time seed profile generation | new |
| `services/embedding_service.py` | Generate embeddings for similarity | new |

### Modified Components

| Component | Changes |
|-----------|---------|
| `composer.py` | Add self-evaluation quality gate |
| `db.py` | Migrate to Supabase client |
| `cli.py` | Add `agent` and `analyze-seeds` commands |
| `config/lead_gen.yaml` | Add search term weights |

### New Files

```
config/
├── seed_profiles/          # Agent-generated ICP analyses
│   ├── absolutecollagen.md
│   ├── prfct.md
│   └── mothersearth.md
data/
└── search_journal.md       # Agent's learning log
```

## Quality Gate in Composer

```python
async def generate_email_1(lead, posts, profile, config_path):
    # Generate email with joke
    response = await claude.generate(...)

    # Self-evaluate in same call
    quality_score = response.quality_rating  # 1-10

    if quality_score < 7:
        # Regenerate once
        response = await claude.generate(..., feedback="previous attempt weak")

    if quality_score < 5:
        # Use safe fallback
        return fallback_template(lead)

    return response.subject, response.body
```

## Configuration Updates

### `config/lead_gen.yaml` (updated)

```yaml
search:
  keywords:
    "collagen supplement": 0.85
    "beauty subscription box": 0.7
    "wellness DTC": 0.6
    "anti-aging skincare": 0.5
  countries: ["US", "GB", "AU"]
  status: "ACTIVE"
  excluded_domains:
    - amazon.com
    - facebook.com
    - instagram.com

targeting:
  title_priority:
    - CMO
    - VP Marketing
    - Head of Marketing
    - Marketing Director
    - Founder
    - CEO
    - COO
  max_contacts_per_company: 1

quotas:
  companies_per_day: 10
  max_searches_per_run: 50

slack:
  webhook_url: ${SLACK_WEBHOOK_URL}
  channel: "#outreach-alerts"
```

## Success Metrics

- **Daily quota hit rate:** % of weekdays reaching 10 companies
- **Gate 1 pass rate:** % of companies with reachable contacts
- **Gate 2 pass rate:** % of contactable companies that fit ICP
- **Lead quality:** Response rate from agent-sourced vs imported leads
- **Search efficiency:** Leads generated per API call
