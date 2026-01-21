---
name: outreach-setup
description: Interactive setup wizard for configuring the outreach system. Walk users through seed customers, targeting, company context, email templates, and API keys.
---

# Outreach Setup Wizard

You are running an interactive setup wizard to help the user configure their outreach system. Walk them through each step, gathering information and writing config files at the end.

## How to Run This Wizard

Guide the user through these steps IN ORDER. Use AskUserQuestion for structured choices and direct conversation for open-ended inputs. Be conversational and helpful.

**IMPORTANT:** Collect ALL information first, then write ALL config files at the end. Don't write files mid-wizard.

---

## Step 1: Welcome

Start with:
```
# Outreach Setup Wizard

I'll walk you through setting up your outreach system. This takes about 5-10 minutes.

We'll configure:
1. **Seed Customers** - Your best customers (so the agent knows who to find)
2. **Targeting** - Job titles to look for
3. **Company Context** - About your company (for personalized emails)
4. **Email Templates** - Customize or use defaults
5. **API Keys** - Connect external services
6. **Gmail Settings** - Your sending identity
7. **Database** - Initialize SQLite for storing leads

Then we'll test everything:
8. **Test Lead Generation** - Preview sample leads before going live
9. **Test Email Generation** - Preview a sample email sequence
10. **Test Slack** - Verify notifications work (if configured)
11. **Setup Automation** - Schedule weekday runs

Let's start!
```

---

## Step 2: Seed Customers

This is the most important step. The discovery agent analyzes these to find similar companies.

Ask:
```
## Step 1: Seed Customers

The discovery agent analyzes your best customers to understand your ICP and find similar companies.

**Add 5-10 of your best customers.** These should be:
- High lifetime value
- Easy to close
- Love your product
- Represent your ideal buyer

For each customer, I need:
- **Domain** (e.g., `acmecorp.com`)
- **Company name** (e.g., `Acme Corporation`)

Let's start with your first seed customer. What's their domain and company name?
```

After they provide one, ask "Got it! Want to add another seed customer? (You can add up to 10, aim for at least 5)"

Keep collecting until they say they're done or reach 10.

Store as a list: `seed_customers = [{domain: "...", name: "..."}, ...]`

---

## Step 3: Targeting

Ask:
```
## Step 2: Targeting

What job titles should we look for at companies? I'll search for these in order of priority.

**Default titles:**
1. Influencer Marketing
2. Marketing
3. CMO
4. Founder
5. CEO
6. COO
```

Use AskUserQuestion:
- "Use defaults" - Keep the default list
- "Customize" - Let them specify their own list

If they customize, ask them to list their preferred job titles in order of priority.

Also ask: "How many contacts per company? (Default: 3, usually 1-3 is good)"

Store: `job_titles = [...]` and `max_contacts_per_company = N`

---

## Step 4: Company Context

This is used by Claude to write personalized emails.

Ask each of these:

```
## Step 3: Company Context

Now tell me about YOUR company so I can write personalized emails.

**What's your company name and what do you do?**
(One line, e.g., "Acme Analytics - real-time dashboards for e-commerce brands")
```

Then:
```
**What's your value prop?**
What problem do you solve and for whom?
(e.g., "Help DTC brands understand their customer data without hiring a data team")
```

Then:
```
**What tone should emails have?**
(e.g., "Friendly, curious, slightly self-deprecating. Not salesy.")
```

Then:
```
**What's your CTA (call-to-action)?**
What do you want recipients to do?
(e.g., "Quick 15-min call to see if we can help")
```

Store: `company_name`, `value_prop`, `tone`, `cta`

---

## Step 5: Email Templates

Ask:
```
## Step 4: Email Templates

The system sends a 3-email sequence:
1. **Email 1** - Personalized with AI-generated opener based on their LinkedIn
2. **Followup 1** - Sent 3 days later if no reply
3. **Followup 2** - Sent 7 days after email 1 if no reply
```

Use AskUserQuestion:
- "Use defaults" - Keep the existing templates (recommended for most users)
- "Show me the templates" - Display current templates so they can review
- "Customize" - Let them edit templates

If they choose "Show me the templates", read and display `config/templates.md`, then ask if they want to customize or keep as-is.

If they customize, walk them through editing each template.

Store: `use_default_templates = true/false` and optionally `custom_templates`

---

## Step 6: API Keys

```
## Step 5: API Keys

Let's set up your API keys. I'll walk you through each one.

**Required for sending emails:**
```

Walk through EACH key one at a time:

### 6a. Anthropic (Required)
```
**Anthropic API Key** (for AI-generated email openers)
- Get it at: https://console.anthropic.com
- Starts with: `sk-ant-...`

Paste your Anthropic API key:
```

### 6b. Composio (Required)
```
**Composio API Key** (for sending emails via Gmail)
- Get it at: https://composio.dev
- You'll need to connect your Gmail account in their dashboard

Paste your Composio API key:
```

Then:
```
**Composio Connected Account ID** (identifies which Gmail account to use)
- Find it at: https://app.composio.dev/connected_accounts
- Click on your Gmail connection and copy the ID

Paste your Composio Connected Account ID:
```

### 6c. Apify (Required for outreach)
```
**Apify API Key** (for LinkedIn profile scraping)
- Get it at: https://apify.com
- Used to find LinkedIn posts for personalization

Paste your Apify API key (or type 'skip' to set up later):
```

### 6d. Discovery Pipeline Keys (Optional)

Ask first:
```
**Discovery Pipeline**

Do you want to set up the discovery pipeline? This automatically finds new leads by:
- Searching Facebook Ad Library for advertisers like your seed customers
- Looking up decision makers via Apollo.io

This requires additional API keys.
```

Use AskUserQuestion:
- "Yes, set it up" - Continue with ScrapeCreators and Apollo keys
- "Skip for now" - Skip these keys

If yes:

```
**ScrapeCreators API Key** (for Facebook Ad Library search)
- Get it at: https://scrapecreators.com

Paste your ScrapeCreators API key:
```

```
**Apollo API Key** (for finding people at companies)
- Get it at: https://apollo.io

Paste your Apollo API key:
```

### 6e. Optional Keys

```
**Optional: Slack Notifications**

Want to get Slack notifications when the discovery agent runs?
```

Use AskUserQuestion:
- "Yes" - Ask for webhook URL
- "No" - Skip

Store all keys in a dict: `api_keys = {ANTHROPIC_API_KEY: "...", ...}`

---

## Step 7: Gmail Settings

```
## Step 6: Gmail Settings

**What name should appear in the "From" field?**
(e.g., "Chris" shows as "Chris <your-email@gmail.com>")
```

Store: `from_name`

---

## Step 8: Write Config Files

Now write all the config files:

### 8a. Write `config/lead_gen.yaml`

Use the collected `seed_customers`, `job_titles`, `max_contacts_per_company`.

Keep the existing structure but update:
- `seed_customers` section with their customers
- `targeting.title_priority` with their job titles
- `targeting.max_contacts_per_company` with their value

### 8b. Write `config/context.md`

```markdown
## Company
{company_name}

## Value Prop
{value_prop}

## Tone
{tone}

## CTA
{cta}
```

### 8c. Write `config/settings.yaml`

Update `gmail.from_name` with their value. Keep other settings as defaults.

### 8d. Write `.env`

Create or update `.env` with their API keys:

```
# API Keys (generated by /outreach-setup)

ANTHROPIC_API_KEY={key}
COMPOSIO_API_KEY={key}
COMPOSIO_CONNECTED_ACCOUNT_ID={id}
APIFY_API_KEY={key}
# ... etc
```

**IMPORTANT:** Only write keys they provided. Don't overwrite existing keys they skipped.

### 8e. Optionally update `config/templates.md`

Only if they customized templates.

### 8f. Initialize the Database

Run the database initialization to create the SQLite database and tables:

```bash
uv run python -c "from src.core.db import init_db; init_db(); print('Database initialized at data/outreach.db')"
```

This creates:
- `data/outreach.db` - The SQLite database
- `leads` table - For storing lead information
- `sent_emails` table - For tracking sent emails
- `searched_companies` table - For tracking companies already processed by discovery

---

## Step 9: Test Lead Generation

If Apollo and ScrapeCreators API keys were provided, test the discovery pipeline.

**Skip condition:** If keys are missing, say:
```
## Lead Generation Test

Skipping lead generation test - Apollo and ScrapeCreators API keys not configured.

You can test this later by running:
   python run_agent.py
```

**If keys are configured:**

Run the discovery pipeline with a limit of 3-5 leads using bash:

```bash
uv run python -c "
import asyncio
from src.discovery.lead_generator import generate_leads
from pathlib import Path

async def test():
    # Run with a small limit
    result = await generate_leads(dry_run=False)
    return result

result = asyncio.run(test())
print(f'Leads found: {result[\"leads_added\"]}')
print(f'Companies checked: {result[\"companies_checked\"]}')
"
```

Then query the database to get the leads:

```bash
uv run python -c "
import sqlite3
conn = sqlite3.connect('data/outreach.db')
conn.row_factory = sqlite3.Row
cursor = conn.execute('SELECT email, first_name, last_name, company, title, linkedin_url FROM leads ORDER BY created_at DESC LIMIT 5')
leads = [dict(row) for row in cursor.fetchall()]
for lead in leads:
    print(f\"{lead['company']} | {lead['first_name']} {lead['last_name']} | {lead['title']} | {lead['email']} | {lead['linkedin_url']}\")
"
```

Display the results to the user:

```
## Sample Leads Found

| Company | Person | Title | Email | LinkedIn |
|---------|--------|-------|-------|----------|
| Acme DTC | Sarah Chen | VP Marketing | sarah@acmedtc.com | linkedin.com/in/sarahchen |
| Brand Co | Mike Johnson | CMO | mike@brandco.com | linkedin.com/in/mikejohnson |
...

These were found by searching for companies similar to your seed customers.
```

Ask: "Do these leads match your ideal customer profile?"

Use AskUserQuestion:
- "Yes, looks good" - Continue to email testing
- "No, needs adjustment" - Ask what's wrong

**If needs adjustment:**
- Ask: "What's off? Too big/small? Wrong industry? Wrong titles?"
- Based on feedback, update `config/lead_gen.yaml`:
  - Wrong titles → update `targeting.title_priority`
  - Wrong industry → update `search.keywords` or `search.excluded_domains`
  - Companies too big/small → add size filters or excluded domains
- Re-run the test
- Repeat until confirmed

---

## Step 10: Test Email Generation

Test email generation using one of the sample leads (or a mock lead if no leads were generated).

**Get a lead to test with:**

If leads were generated in Step 9, use the first one. Otherwise, create a mock lead:

```python
test_lead = {
    "email": "test@example.com",
    "first_name": "Sarah",
    "last_name": "Chen",
    "company": "Acme DTC",
    "title": "VP Marketing",
    "linkedin_url": "https://linkedin.com/in/sarahchen"
}
```

**Run enrichment and email generation:**

```bash
uv run python -c "
import asyncio
from src.outreach.enricher import scrape_linkedin_profile, scrape_linkedin_posts
from src.outreach.composer import generate_email_1
from src.core.config import get_template_by_name, render_template, DEFAULT_CONFIG_PATH

async def test():
    # Test lead
    lead = {
        'email': 'sarah@acmedtc.com',
        'first_name': 'Sarah',
        'last_name': 'Chen',
        'company': 'Acme DTC',
        'title': 'VP Marketing',
        'linkedin_url': 'https://linkedin.com/in/sarahchen'
    }

    # Scrape LinkedIn
    print('Scraping LinkedIn profile...')
    profile = await scrape_linkedin_profile(lead['linkedin_url'])
    posts = await scrape_linkedin_posts(lead['linkedin_url'])

    print(f'Found {len(posts)} recent posts')

    # Generate email 1
    print('Generating email 1...')
    subject, body = await generate_email_1(lead, posts, profile)

    print('---EMAIL 1---')
    print(f'Subject: {subject}')
    print(body)
    print('---END---')

    # Generate followups from templates
    email_1_template = get_template_by_name(DEFAULT_CONFIG_PATH, 'email_1')
    followup_1 = get_template_by_name(DEFAULT_CONFIG_PATH, 'followup_1')
    followup_2 = get_template_by_name(DEFAULT_CONFIG_PATH, 'followup_2')

    vars = {
        'first_name': lead['first_name'],
        'original_subject': subject
    }

    print('---FOLLOWUP 1 (3 days later)---')
    print(f'Subject: {render_template(followup_1.subject, vars)}')
    print(render_template(followup_1.body, vars))
    print('---END---')

    print('---FOLLOWUP 2 (7 days later)---')
    print(f'Subject: {render_template(followup_2.subject, vars)}')
    print(render_template(followup_2.body, vars))
    print('---END---')

asyncio.run(test())
"
```

Display the output to the user in a formatted way:

```
## Sample Email Sequence for Sarah Chen

**Email 1** (sends immediately)
Subject: your linkedin is suspiciously clean

Hey Sarah,

Scrolled your whole profile looking for something clever to reference
and you've given me nothing. No hot takes, no humble brags. I respect
the mystery.

Anyway, terrible jokes aside...

[Rest of email]

---

**Followup 1** (3 days later, no reply)
Subject: re: your linkedin is suspiciously clean

Hey Sarah,

Following up on my own cold email. The audacity.

[Rest of followup]

---

**Followup 2** (7 days later, no reply)
Subject: re: your linkedin is suspiciously clean

Hey Sarah,

Last one, I promise...

[Rest of followup]
```

Ask: "Does this email feel right for your brand?"

Use AskUserQuestion:
- "Yes, looks good" - Continue
- "No, needs adjustment" - Ask what's wrong

**If needs adjustment:**
- Ask: "What's off? (tone too casual? pitch unclear? CTA weak?)"
- Based on feedback, update the appropriate file:
  - Tone issues → update `config/context.md`
  - Template wording → update `config/templates.md`
- Re-run the email generation test
- Repeat until confirmed

---

## Step 11: Test Slack Notifications

Only run this step if `SLACK_WEBHOOK_URL` was provided in the API keys step.

**Skip condition:** If Slack webhook not configured, skip silently and continue to Step 12.

**If configured:**

Send a test notification:

```bash
uv run python -c "
import asyncio
import httpx
import os

async def test_slack():
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    if not webhook_url:
        print('No Slack webhook configured')
        return False

    message = {
        'text': '🧪 Test notification from Outreach Setup - your Slack integration is working!'
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(webhook_url, json=message)
        if response.status_code == 200:
            print('Test message sent successfully!')
            return True
        else:
            print(f'Failed to send: {response.status_code}')
            return False

asyncio.run(test_slack())
"
```

Ask: "Did you receive a test message in Slack?"

Use AskUserQuestion:
- "Yes, it worked" - Continue to automation setup
- "No, didn't receive it" - Troubleshoot
- "Skip Slack for now" - Continue without Slack

**If troubleshooting:**
- Ask them to verify the webhook URL is correct
- Check channel permissions
- Offer to re-enter the webhook URL and retry

---

## Step 12: Setup Automation

Offer to set up weekday automation using launchd.

```
## Automation Setup

Want to run the outreach pipeline automatically on weekdays?

This will:
- Run Monday-Friday at 9am (or your preferred time)
- Check for replies, send follow-ups, import new leads
- Log output to /tmp/outreach.log
- Handle laptop sleep/wake properly (runs when you wake up if asleep at 9am)
```

Use AskUserQuestion:
- "Yes, set it up at 9am" - Create and load launchd plist
- "Yes, but different time" - Ask for preferred time, then create plist
- "No, I'll do it later" - Show instructions and continue

**If yes (any time):**

Get the required paths:

```bash
UV_PATH=$(which uv)
PROJECT_PATH=$(pwd)
```

Create the launchd plist. The hour value should be the user's chosen hour (default 9):

```bash
HOUR=9  # Or user's chosen hour

cat > ~/Library/LaunchAgents/com.outreach.daily.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.outreach.daily</string>
    <key>ProgramArguments</key>
    <array>
        <string>${UV_PATH}</string>
        <string>run</string>
        <string>python</string>
        <string>run.py</string>
        <string>send</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${PROJECT_PATH}</string>
    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Weekday</key><integer>1</integer>
            <key>Hour</key><integer>${HOUR}</integer>
            <key>Minute</key><integer>0</integer>
        </dict>
        <dict>
            <key>Weekday</key><integer>2</integer>
            <key>Hour</key><integer>${HOUR}</integer>
            <key>Minute</key><integer>0</integer>
        </dict>
        <dict>
            <key>Weekday</key><integer>3</integer>
            <key>Hour</key><integer>${HOUR}</integer>
            <key>Minute</key><integer>0</integer>
        </dict>
        <dict>
            <key>Weekday</key><integer>4</integer>
            <key>Hour</key><integer>${HOUR}</integer>
            <key>Minute</key><integer>0</integer>
        </dict>
        <dict>
            <key>Weekday</key><integer>5</integer>
            <key>Hour</key><integer>${HOUR}</integer>
            <key>Minute</key><integer>0</integer>
        </dict>
    </array>
    <key>StandardOutPath</key>
    <string>/tmp/outreach.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/outreach-error.log</string>
</dict>
</plist>
EOF
```

Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.outreach.daily.plist
```

Verify:

```bash
launchctl list | grep outreach
```

Tell the user:
```
Automation scheduled! The pipeline will run Monday-Friday at {HOUR}:00.

Logs: /tmp/outreach.log
Stop: launchctl unload ~/Library/LaunchAgents/com.outreach.daily.plist
```

Store: `automation_enabled = true/false`, `automation_hour = N`

**If no (do it later):**

Tell the user:
```
No problem! When you're ready, see the "Setting Up Automation Later" section in SETUP.md.

Or run `/outreach-setup` again and choose automation at the end.
```

---

## Step 13: Completion

```
# Setup Complete!

I've configured your outreach system:

✓ Added {N} seed customers to `config/lead_gen.yaml`
✓ Set targeting to look for: {job_titles}
✓ Wrote company context to `config/context.md`
✓ Set Gmail from name to "{from_name}" in `config/settings.yaml`
✓ Saved API keys to `.env`
✓ Initialized database at `data/outreach.db`

## Next Steps

1. **Test the setup:**
   ```bash
   python run.py status
   ```

2. **Import some leads:**
   ```bash
   python run.py import leads/my_leads.xlsx
   ```

3. **Or run the discovery agent to find leads automatically:**
   ```bash
   python run_agent.py
   ```

See `SETUP.md` for more details on running the system.
```

---

## Error Handling

- If user provides invalid input, gently ask them to try again
- If they want to skip a step, note what won't be configured
- If they want to quit mid-wizard, offer to save progress or start over next time
- Be encouraging and helpful throughout

## Important Notes

- Never display API keys back to the user after they enter them (security)
- Validate domains look like domains (contain a dot, no spaces)
- Keep the conversation flowing naturally - don't be robotic
- If they seem confused, offer more explanation
