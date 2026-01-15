# Outreach Boilerplate

Humor-first cold email outreach CLI. Clone, configure, drop leads, run.

---

## Running a Campaign

### Step 1: Drop your lead list into `/leads`

Save your Excel file to the `leads/` folder. Format:

| email | first_name | last_name | company | title | linkedin_url |
|-------|------------|-----------|---------|-------|--------------|
| sarah@brand.com | Sarah | Chen | Brand Co | Marketing Director | https://linkedin.com/in/sarahchen |

### Step 2: Run

```bash
python run.py
```

That's it. This will:
- Import any Excel files from `/leads`
- Move them to `/leads/processed`
- Scrape LinkedIn for personalization
- Generate joke openers with Claude
- Send emails via Gmail
- Schedule follow-ups

### Step 3: Run again tomorrow

```bash
python run.py
```

Each run:
- Checks for replies (stops sequences for responders)
- Sends scheduled follow-ups
- Imports any new lead files you've added

### Check status anytime

```bash
python run.py status
```

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

Edit `.env`:
- `ANTHROPIC_API_KEY` - [console.anthropic.com](https://console.anthropic.com/)
- `COMPOSIO_API_KEY` - [composio.dev](https://composio.dev/)
- `APIFY_API_KEY` - [apify.com](https://apify.com/)

### 3. Connect Gmail

1. Go to [composio.dev](https://composio.dev) dashboard
2. Connect your Gmail account
3. Copy the connected account ID
4. Paste in `config/settings.yaml` under `gmail.connected_account_id`

### 4. Edit Your Messaging

| File | What it does |
|------|--------------|
| `config/context.md` | Who you are, your offer, tone |
| `config/email_1.md` | First email (Claude fills the joke) |
| `config/followup_1.md` | Email 2 (3 days later) |
| `config/followup_2.md` | Email 3 (7 days later) |
| `config/settings.yaml` | Timing, limits, Gmail account |

### 5. Automate (Optional)

Run hourly via cron:

```bash
crontab -e
```

Add:
```
0 * * * * cd /path/to/outreach-boilerplate && uv run python run.py >> /tmp/outreach.log 2>&1
```

---

## How the Emails Work

**Email 1** - Claude reads their LinkedIn and writes a personalized joke opener:

```
subject: your linkedin is suspiciously clean

Hey Sarah,

Scrolled your whole profile looking for something clever to reference
and you've given me nothing. No hot takes, no humble brags. I respect
the mystery.

[Your pitch here]
```

**Emails 2 & 3** - Self-aware follow-up templates:

```
subject: re: your linkedin is suspiciously clean

Hey Sarah,

Following up on my own cold email. The audacity.

[Rest of follow-up]
```

---

## Requirements

- Python 3.11+
- API keys: Anthropic, Composio, Apify

## License

MIT
