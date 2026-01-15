# Outreach Boilerplate

Humor-first cold email outreach CLI. Clone, configure, upload leads, hit go.

## What It Does

1. **Import leads** from Excel (email, name, company, LinkedIn URL)
2. **Scrape LinkedIn** for personalization context (via Apify)
3. **Generate personalized jokes** using Claude Opus 4.5 as email openers
4. **Send via Gmail** with proper threading (via Composio)
5. **Automate follow-ups** via cron (self-aware templated humor)
6. **Stop sequences** when replies detected

---

## Running a Campaign

Once setup is complete, here's how to run a campaign:

### Step 1: Prepare Your Lead List

Create an Excel file with these columns:

| email | first_name | last_name | company | title | linkedin_url |
|-------|------------|-----------|---------|-------|--------------|
| sarah@brand.com | Sarah | Chen | Brand Co | Marketing Director | https://linkedin.com/in/sarahchen |

Save it anywhere (e.g., `leads.xlsx` in the project folder).

### Step 2: Import Leads

```bash
python run.py import leads.xlsx
```

This adds leads to the database and marks them as "new".

### Step 3: Send Emails

```bash
python run.py send
```

This will:
- Scrape each lead's LinkedIn for recent posts
- Generate a personalized joke opener using Claude
- Send the email via Gmail
- Schedule follow-ups automatically

### Step 4: Check Progress

```bash
python run.py status
```

Shows how many leads are new, active, replied, or completed.

### Step 5: Run Daily (or set up cron)

Run `python run.py send` daily to:
- Detect replies and stop those sequences
- Send scheduled follow-ups
- Process any new leads you've imported

---

## One-Time Setup

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
- `ANTHROPIC_API_KEY` - [Anthropic Console](https://console.anthropic.com/)
- `COMPOSIO_API_KEY` - [Composio](https://composio.dev/)
- `APIFY_API_KEY` - [Apify](https://apify.com/)

### 3. Connect Gmail

1. Go to [composio.dev](https://composio.dev) dashboard
2. Connect your Gmail account
3. Copy the connected account ID
4. Paste it in `config/settings.yaml` under `gmail.connected_account_id`

### 4. Configure Your Messaging

Edit files in `config/`:

| File | Purpose |
|------|---------|
| `context.md` | Who you are, what you offer, tone guidelines |
| `email_1.md` | First email template (Claude fills in the joke) |
| `followup_1.md` | Second email (sent 3 days later) |
| `followup_2.md` | Third email (sent 7 days later) |
| `settings.yaml` | Timing, rate limits, Gmail account |

### 5. Automate with Cron (Optional)

To run automatically every hour:

```bash
crontab -e
```

Add:
```
0 * * * * cd /path/to/outreach-boilerplate && uv run python run.py send >> /tmp/outreach.log 2>&1
```

---

## How the Emails Work

### Email 1: Personalized Joke Opener

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

Following up on my own cold email. The audacity.

Genuinely curious if creator/affiliate stuff is on your radar
or if I should take the hint.

Chris
```

---

## Configuration Reference

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
  connected_account_id: "ca_xxx"  # From Composio dashboard
```

---

## Requirements

- Python 3.11+
- Gmail account
- API keys: Anthropic, Composio, Apify

## License

MIT
