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

## Step 10: Completion

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
