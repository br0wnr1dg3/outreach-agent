# Outreach Boilerplate

Humor-first cold email outreach CLI. Clone, configure, upload leads, hit go.

## What It Does

1. **Import leads** from Excel (email, name, company, LinkedIn URL)
2. **Scrape LinkedIn** for personalization context (via Apify)
3. **Generate personalized jokes** using Claude Opus 4.5 as email openers
4. **Send via Gmail** with proper threading (via Composio)
5. **Automate follow-ups** via cron (self-aware templated humor)
6. **Stop sequences** when replies detected

## Setup (5 minutes)

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/outreach-boilerplate
cd outreach-boilerplate
uv sync
```

### 2. Add API Keys

```bash
cp .env.example .env
```

Edit `.env` with your keys:
- `ANTHROPIC_API_KEY` - Get from [Anthropic Console](https://console.anthropic.com/)
- `COMPOSIO_API_KEY` - Get from [Composio](https://composio.dev/)
- `APIFY_API_KEY` - Get from [Apify](https://apify.com/)

### 3. Connect Gmail

```bash
composio login
composio add gmail
```

### 4. Configure Your Messaging

Edit the files in `config/`:

- `context.md` - Who you are, what you offer, tone guidelines
- `email_1.md` - Base template for first email (Claude personalizes the opener)
- `followup_1.md` - Template for email 2 (3 days later)
- `followup_2.md` - Template for email 3 (7 days later)
- `settings.yaml` - Timing and rate limits

### 5. Set Up Cron (Optional)

For automated follow-ups:

```bash
crontab -e
```

Add:
```
0 * * * * cd /path/to/outreach-boilerplate && uv run python run.py send >> /tmp/outreach.log 2>&1
```

## Usage

### Import Leads

```bash
python run.py import leads.xlsx
```

Excel format:

| email | first_name | last_name | company | title | linkedin_url |
|-------|------------|-----------|---------|-------|--------------|
| sarah@brand.com | Sarah | Chen | Brand Co | Marketing Director | https://linkedin.com/in/sarahchen |

### Send Emails

```bash
python run.py send
```

This will:
1. Check for replies (stop sequences for those who replied)
2. Process new leads (enrich → generate → send)
3. Send follow-ups that are due

### Check Status

```bash
# Overall pipeline status
python run.py status

# Specific lead
python run.py status --lead sarah@brand.com
```

## How It Works

### Email 1: Personalized Joke

Claude reads their LinkedIn and generates a genuinely funny opener:

```
subject: your linkedin is suspiciously clean

Hey Sarah,

Scrolled your whole profile looking for something clever to
reference and you've given me nothing. No hot takes, no humble
brags. I respect the mystery.

I'm with Cheerful - we help brands like Brand Co turn creators
into affiliates without the usual headaches...
```

### Emails 2 & 3: Self-Aware Follow-ups

Templates with built-in humor about following up:

```
subject: re: your linkedin is suspiciously clean

Hey Sarah,

Following up on my own cold email. The audacity continues.

Genuinely curious if creator/affiliate stuff is on your radar
or if I should take the hint.

Chris
```

## Configuration

### settings.yaml

```yaml
sequence:
  email_2_delay_days: 3    # Days after email 1
  email_3_delay_days: 4    # Days after email 2

sending:
  daily_limit: 50          # Max emails per day
  min_delay_seconds: 20    # Min gap between sends
  max_delay_seconds: 60    # Max gap between sends

gmail:
  from_name: "Chris"
```

## Requirements

- Python 3.11+
- Gmail account
- API keys: Anthropic, Composio, Apify

## License

MIT
