# README & Setup Instructions Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Update README, SETUP.md, and `/outreach-setup` skill to provide Claude-first onboarding with interactive testing and weekday automation.

**Architecture:** Modify existing markdown files and skill definition. No new code files needed - the testing steps call existing functions from `src/discovery/lead_generator.py`, `src/outreach/enricher.py`, `src/outreach/composer.py`, and `src/services/slack_notifier.py`.

**Tech Stack:** Markdown, YAML (skill definition), launchd (macOS automation)

---

## Task 1: Rewrite README.md

**Files:**
- Modify: `README.md`

**Step 1: Replace README with Claude-first quick start**

Replace entire contents of `README.md` with:

```markdown
# Outreach Boilerplate

Humor-first cold email outreach. Clone, configure with Claude, run.

## Quick Start

1. Clone and install:
   ```bash
   git clone <repo-url>
   cd outreach-boilerplate
   uv sync
   ```

2. Start Claude Code:
   ```bash
   claude --dangerously-skip-permissions
   ```

3. Run the setup wizard:
   ```
   /outreach-setup
   ```

This walks you through:
- Adding your seed customers (so the agent knows who to find)
- Configuring your company context and email templates
- Setting up API keys
- Testing lead generation
- Testing email generation
- Setting up weekday automation

## Manual Setup

Prefer to configure things yourself? See [SETUP.md](SETUP.md).

---

## What This Does

**Two pipelines:**

1. **Outreach** - Import leads, scrape LinkedIn for personalization, generate joke openers with Claude, send via Gmail, automate follow-ups

2. **Discovery** - Find new leads by searching Facebook Ad Library for advertisers similar to your seed customers, then enrich via Apollo.io

## How Emails Work

**Email 1** - Claude writes a personalized joke opener based on their LinkedIn:

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
- [uv](https://github.com/astral-sh/uv) package manager
- Claude Code CLI

**API keys needed:**
- Anthropic (email generation)
- Composio (Gmail integration)
- Apify (LinkedIn scraping)
- Apollo.io (lead discovery - optional)
- ScrapeCreators (FB Ad Library - optional)

## License

MIT
```

**Step 2: Verify the file was written correctly**

Run: `head -30 README.md`
Expected: See the new "Outreach Boilerplate" header and Quick Start section

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README with Claude-first quick start"
```

---

## Task 2: Add automation section to SETUP.md

**Files:**
- Modify: `SETUP.md`

**Step 1: Add "Setting Up Automation Later" section at the end of SETUP.md**

Append the following to the end of `SETUP.md`:

```markdown

---

## Setting Up Automation Later

If you skipped automation during `/outreach-setup`, you can configure it anytime.

### Using launchd (Recommended for macOS)

launchd is macOS-native and handles sleep/wake properly - if your laptop is asleep at 9am, it runs when it wakes.

**1. Create the plist file:**

```bash
nano ~/Library/LaunchAgents/com.outreach.daily.plist
```

**2. Paste this content (update the paths):**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.outreach.daily</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/uv</string>
        <string>run</string>
        <string>python</string>
        <string>run.py</string>
        <string>send</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/outreach-boilerplate</string>
    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Weekday</key><integer>1</integer>
            <key>Hour</key><integer>9</integer>
            <key>Minute</key><integer>0</integer>
        </dict>
        <dict>
            <key>Weekday</key><integer>2</integer>
            <key>Hour</key><integer>9</integer>
            <key>Minute</key><integer>0</integer>
        </dict>
        <dict>
            <key>Weekday</key><integer>3</integer>
            <key>Hour</key><integer>9</integer>
            <key>Minute</key><integer>0</integer>
        </dict>
        <dict>
            <key>Weekday</key><integer>4</integer>
            <key>Hour</key><integer>9</integer>
            <key>Minute</key><integer>0</integer>
        </dict>
        <dict>
            <key>Weekday</key><integer>5</integer>
            <key>Hour</key><integer>9</integer>
            <key>Minute</key><integer>0</integer>
        </dict>
    </array>
    <key>StandardOutPath</key>
    <string>/tmp/outreach.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/outreach-error.log</string>
</dict>
</plist>
```

**3. Find your paths:**

```bash
# Get uv path
which uv

# Get project path
pwd
```

**4. Load it:**

```bash
launchctl load ~/Library/LaunchAgents/com.outreach.daily.plist
```

**5. Verify it's loaded:**

```bash
launchctl list | grep outreach
```

### Managing the Schedule

- **Stop automation:** `launchctl unload ~/Library/LaunchAgents/com.outreach.daily.plist`
- **Change time:** Edit the plist, unload, then reload
- **Check logs:** `tail -f /tmp/outreach.log`
- **Run manually:** `python run.py send`

### Using cron (Alternative)

If you prefer cron (note: doesn't handle sleep/wake on macOS):

```bash
crontab -e
```

Add:
```
0 9 * * 1-5 cd /path/to/outreach-boilerplate && uv run python run.py send >> /tmp/outreach.log 2>&1
```
```

**Step 2: Verify the section was added**

Run: `tail -20 SETUP.md`
Expected: See "Using cron (Alternative)" section near the end

**Step 3: Commit**

```bash
git add SETUP.md
git commit -m "docs: add automation setup section to SETUP.md"
```

---

## Task 3: Update /outreach-setup skill - Welcome message

**Files:**
- Modify: `.claude/skills/outreach-setup/SKILL.md`

**Step 1: Update the welcome message to include new steps**

Find and replace the Step 1: Welcome section. Change:

```markdown
We'll configure:
1. **Seed Customers** - Your best customers (so the agent knows who to find)
2. **Targeting** - Job titles to look for
3. **Company Context** - About your company (for personalized emails)
4. **Email Templates** - Customize or use defaults
5. **API Keys** - Connect external services
6. **Gmail Settings** - Your sending identity
7. **Database** - Initialize SQLite for storing leads
```

To:

```markdown
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
```

**Step 2: Verify the change**

Run: `grep -A 15 "We'll configure:" .claude/skills/outreach-setup/SKILL.md`
Expected: See the updated list with steps 8-11

**Step 3: Commit**

```bash
git add .claude/skills/outreach-setup/SKILL.md
git commit -m "feat(skill): update welcome message with testing steps"
```

---

## Task 4: Add Step 9 - Test Lead Generation

**Files:**
- Modify: `.claude/skills/outreach-setup/SKILL.md`

**Step 1: Add Step 9 after Step 8 (Write Config Files)**

Find the section `## Step 9: Completion` and insert the following BEFORE it (renumber existing Step 9 to Step 13):

```markdown
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

```

**Step 2: Verify the section was added**

Run: `grep -A 5 "## Step 9: Test Lead Generation" .claude/skills/outreach-setup/SKILL.md`
Expected: See the new step heading and first few lines

**Step 3: Commit**

```bash
git add .claude/skills/outreach-setup/SKILL.md
git commit -m "feat(skill): add Step 9 - test lead generation"
```

---

## Task 5: Add Step 10 - Test Email Generation

**Files:**
- Modify: `.claude/skills/outreach-setup/SKILL.md`

**Step 1: Add Step 10 after Step 9**

Insert after Step 9:

```markdown
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

```

**Step 2: Verify the section was added**

Run: `grep -A 5 "## Step 10: Test Email Generation" .claude/skills/outreach-setup/SKILL.md`
Expected: See the new step heading and first few lines

**Step 3: Commit**

```bash
git add .claude/skills/outreach-setup/SKILL.md
git commit -m "feat(skill): add Step 10 - test email generation"
```

---

## Task 6: Add Step 11 - Test Slack Notifications

**Files:**
- Modify: `.claude/skills/outreach-setup/SKILL.md`

**Step 1: Add Step 11 after Step 10**

Insert after Step 10:

```markdown
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

```

**Step 2: Verify the section was added**

Run: `grep -A 5 "## Step 11: Test Slack" .claude/skills/outreach-setup/SKILL.md`
Expected: See the new step heading and first few lines

**Step 3: Commit**

```bash
git add .claude/skills/outreach-setup/SKILL.md
git commit -m "feat(skill): add Step 11 - test Slack notifications"
```

---

## Task 7: Add Step 12 - Setup Automation

**Files:**
- Modify: `.claude/skills/outreach-setup/SKILL.md`

**Step 1: Add Step 12 after Step 11**

Insert after Step 11:

```markdown
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

```

**Step 2: Verify the section was added**

Run: `grep -A 5 "## Step 12: Setup Automation" .claude/skills/outreach-setup/SKILL.md`
Expected: See the new step heading and first few lines

**Step 3: Commit**

```bash
git add .claude/skills/outreach-setup/SKILL.md
git commit -m "feat(skill): add Step 12 - setup automation via launchd"
```

---

## Task 8: Update Step 13 - Completion message

**Files:**
- Modify: `.claude/skills/outreach-setup/SKILL.md`

**Step 1: Rename existing Step 9 to Step 13 and update content**

Find the existing `## Step 9: Completion` section and replace it with:

```markdown
---

## Step 13: Completion

Show the final summary based on what was configured:

```
# Setup Complete!

✓ Added {N} seed customers to config/lead_gen.yaml
✓ Set targeting: {job_titles}
✓ Wrote company context to config/context.md
✓ Set Gmail from name to "{from_name}" in config/settings.yaml
✓ Saved API keys to .env
✓ Initialized database at data/outreach.db
```

If lead generation was tested:
```
✓ Tested lead generation - {N} sample leads found
```

If email generation was tested:
```
✓ Tested email generation - sequence looks good
```

If Slack was tested:
```
✓ Tested Slack notifications
```

If automation was set up:
```
✓ Automation scheduled for weekdays at {hour}:00
```

Then show next steps:

```
Your outreach system is ready to go!

## What happens now
```

If automation enabled:
```
- Monday-Friday at {hour}:00: The pipeline runs automatically
- Checks for replies, sends follow-ups, imports new leads from /leads folder
- Logs at /tmp/outreach.log
```

If automation not enabled:
```
- Run `python run.py send` to send emails manually
- Run `python run_agent.py` to find new leads
- See SETUP.md for automation instructions when you're ready
```

Always show:
```
## Manual commands

python run.py status          # Check pipeline status
python run.py send            # Run manually anytime
python run_agent.py           # Find more leads via discovery
```

```

**Step 2: Verify the section was updated**

Run: `grep -A 10 "## Step 13: Completion" .claude/skills/outreach-setup/SKILL.md`
Expected: See the updated completion step

**Step 3: Commit**

```bash
git add .claude/skills/outreach-setup/SKILL.md
git commit -m "feat(skill): update completion message with testing/automation status"
```

---

## Task 9: Final verification

**Files:**
- Verify: `README.md`, `SETUP.md`, `.claude/skills/outreach-setup/SKILL.md`

**Step 1: Verify README structure**

Run: `head -50 README.md`
Expected: See Claude-first quick start with 3 steps

**Step 2: Verify SETUP.md has automation section**

Run: `grep "Setting Up Automation Later" SETUP.md`
Expected: Match found

**Step 3: Verify skill has all 13 steps**

Run: `grep "^## Step" .claude/skills/outreach-setup/SKILL.md`
Expected: See Steps 1-13 listed (Steps 1-8 existing, Steps 9-13 new)

**Step 4: Final commit with summary**

```bash
git add -A
git status
# If any unstaged changes, add them
git commit -m "docs: complete README/setup redesign with testing and automation

- README: Claude-first quick start (clone, claude, /outreach-setup)
- SETUP.md: Added 'Setting Up Automation Later' section with launchd
- Skill: Added Steps 9-13 (test leads, test emails, test Slack, automation, completion)"
```

---

## Summary

| Task | File | Change |
|------|------|--------|
| 1 | README.md | Rewrite with Claude-first quick start |
| 2 | SETUP.md | Add "Setting Up Automation Later" section |
| 3 | SKILL.md | Update welcome message |
| 4 | SKILL.md | Add Step 9 - Test Lead Generation |
| 5 | SKILL.md | Add Step 10 - Test Email Generation |
| 6 | SKILL.md | Add Step 11 - Test Slack Notifications |
| 7 | SKILL.md | Add Step 12 - Setup Automation |
| 8 | SKILL.md | Update Step 13 - Completion message |
| 9 | All | Final verification |
