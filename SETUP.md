# Setup Guide

This guide walks you through setting up the outreach system for your own use.

> **Using Claude Code?** Run `/outreach-setup` for an interactive setup wizard that walks you through everything step by step.

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Gmail account (for sending emails)
- API keys for external services (see below)

## Quick Start

```bash
# 1. Clone and install
git clone <repo-url>
cd outreach-boilerplate
uv sync

# 2. Copy environment template
cp .env.example .env

# 3. Edit .env with your API keys (see "API Keys" section below)

# 4. Customize your config files (see "Configuration" section below)

# 5. Test the setup
python run.py status
```

---

## API Keys

Edit `.env` with your API keys. Here's what each one does:

### Required for Outreach Pipeline

| Key | Service | Purpose | Get it at |
|-----|---------|---------|-----------|
| `ANTHROPIC_API_KEY` | Anthropic | Generates personalized email openers using Claude | [console.anthropic.com](https://console.anthropic.com) |
| `COMPOSIO_API_KEY` | Composio | Sends emails via Gmail API | [composio.dev](https://composio.dev) |
| `APIFY_API_KEY` | Apify | Scrapes LinkedIn posts for personalization | [apify.com](https://apify.com) |

### Required for Discovery Pipeline (Lead Finding)

| Key | Service | Purpose | Get it at |
|-----|---------|---------|-----------|
| `SCRAPECREATORS_API_KEY` | ScrapeCreators | Searches Facebook Ad Library for advertisers | [scrapecreators.com](https://scrapecreators.com) |
| `APOLLO_API_KEY` | Apollo.io | Finds people at companies + gets emails | [apollo.io](https://apollo.io) |

### Optional

| Key | Service | Purpose | Get it at |
|-----|---------|---------|-----------|
| `OPENAI_API_KEY` | OpenAI | Embeddings for ICP similarity matching | [platform.openai.com](https://platform.openai.com) |
| `SUPABASE_URL` / `SUPABASE_KEY` | Supabase | Cloud database (if not using local SQLite) | [supabase.com](https://supabase.com) |
| `SLACK_WEBHOOK_URL` | Slack | Get notifications when runs complete | Slack app settings |

---

## Configuration

All config files are in the `config/` directory.

### 1. Set Up Your Company Context (`config/context.md`)

This tells Claude about your company so it can write relevant emails.

```markdown
## Company
[Your company name] - [one-line description of what you do]

## Value Prop
[What problem you solve and for whom]

## Tone
[How you want emails to sound - casual, professional, humor-first, etc.]

## CTA
[What you want the recipient to do - book a call, reply, etc.]
```

**Example:**
```markdown
## Company
Acme Analytics - real-time dashboard platform for e-commerce brands

## Value Prop
Help DTC brands understand their customer data without hiring a data team

## Tone
Friendly, curious, slightly self-deprecating. Not salesy.

## CTA
Quick 15-min call to see if we can help
```

### 2. Configure Email Templates (`config/templates.md`)

The system sends a sequence of emails. Each template has:
- `template`: Name (email_1, followup_1, followup_2)
- `delay_days`: Days to wait before sending (0 = immediate, 3 = 3 days after previous)

**Variables you can use:**
- `{{first_name}}` - Recipient's first name
- `{{last_name}}` - Recipient's last name
- `{{company}}` - Recipient's company
- `{{generated_subject}}` - AI-generated subject line (email_1 only)
- `{{generated_joke_opener}}` - AI-generated personalized opener (email_1 only)
- `{{original_subject}}` - Subject from email_1 (for follow-ups)

**The first email** is AI-personalized based on their LinkedIn. Follow-ups are static templates.

### 3. Configure Settings (`config/settings.yaml`)

Controls sending behavior:

```yaml
# How long to wait between emails in the sequence
sequence:
  email_2_delay_days: 3    # Days after email 1
  email_3_delay_days: 4    # Days after email 2

# Rate limiting (to avoid Gmail issues)
sending:
  daily_limit: 50          # Max emails per day
  min_delay_seconds: 20    # Min gap between sends
  max_delay_seconds: 60    # Max gap between sends

# Your Gmail identity
gmail:
  from_name: "Your Name"
  connected_account_id: "" # Leave empty for default, or get from Composio dashboard
```

### 4. Configure Lead Discovery (`config/lead_gen.yaml`)

If using the discovery pipeline to find leads automatically.

**The main thing you need to configure is your seed customers** - your best existing customers. The agent analyzes these to understand your ICP and automatically generates search keywords.

```yaml
# START HERE - Add your best customers
# The agent analyzes these to generate search keywords automatically
seed_customers:
  - domain: "bestcustomer1.com"
    name: "Best Customer 1"
  - domain: "bestcustomer2.com"
    name: "Best Customer 2"
  # Add 5-10 of your best customers

# Who to find at each company
targeting:
  title_priority:          # Job titles to target, in order of preference
    - CMO
    - VP Marketing
    - Founder
    # ... add more

  max_contacts_per_company: 1

# Search filters
search:
  countries: ["US", "GB"]  # Which countries to search

  excluded_domains:        # Domains to skip (big platforms, competitors)
    - amazon.com
    - facebook.com
    # ... add more

# Rate limits
quotas:
  companies_per_day: 10    # How many companies to find per day
  max_searches_per_run: 50 # Max API calls per run
```

**How it works:**
1. You add your best customers as seeds
2. The agent visits their websites, analyzes their ads and positioning
3. It identifies patterns (industry, products, company size, etc.)
4. It generates search keywords based on those patterns
5. It finds similar companies and scores them by ICP fit

---

## Database

The system uses **local SQLite** by default at `data/outreach.db`. No setup needed - it's created automatically.

**Optional: Using Supabase**

If you want cloud persistence (useful for running the discovery agent on a server):

1. Create a project at [supabase.com](https://supabase.com)
2. Add `SUPABASE_URL` and `SUPABASE_KEY` to your `.env`
3. The discovery agent will use Supabase; the outreach pipeline still uses local SQLite

---

## Gmail Setup (Composio)

1. Sign up at [composio.dev](https://composio.dev)
2. Connect your Gmail account in the Composio dashboard
3. Copy your API key to `COMPOSIO_API_KEY` in `.env`
4. (Optional) Copy the `connected_account_id` to `config/settings.yaml` if you have multiple Gmail accounts

---

## Running the System

### Outreach Pipeline (Send Emails)

```bash
# Import leads from Excel
python run.py import leads/my_leads.xlsx

# Check pipeline status
python run.py status

# Send emails (handles new leads + follow-ups)
python run.py send

# Check a specific lead
python run.py status --lead someone@company.com
```

### Discovery Pipeline (Find Leads)

```bash
# Find new leads via FB Ads + Apollo
python run_agent.py

# Dry run (see what would happen without making changes)
python run.py generate --dry-run
```

---

## Lead Excel Format

When importing leads manually, use this format:

| email | first_name | last_name | company | title | linkedin_url |
|-------|------------|-----------|---------|-------|--------------|
| john@acme.com | John | Doe | Acme Inc | CEO | https://linkedin.com/in/johndoe |

Only `email` and `first_name` are required. The `linkedin_url` is used for personalization.

---

## Troubleshooting

**"No API key" errors**
- Check your `.env` file has the right keys
- Make sure there are no extra spaces or quotes around values

**Emails not sending**
- Verify Composio is connected to your Gmail
- Check `python run.py status` to see lead states
- Look for rate limiting (daily_limit in settings.yaml)

**LinkedIn enrichment failing**
- Apify may be rate limited or the profile is private
- Check `enrichment_attempts` in status - it retries automatically

**Discovery not finding leads**
- Check your keywords in lead_gen.yaml match what companies advertise
- Try broader keywords or different countries
