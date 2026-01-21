# README & Setup Instructions Redesign

## Overview

Redesign the README and `/outreach-setup` skill to provide a Claude-first onboarding experience with interactive testing and automation setup.

## Key Decisions

- **Claude-first approach**: Primary path uses `claude --dangerously-skip-permissions` + `/outreach-setup`
- **Manual fallback**: Link to SETUP.md for users who prefer manual configuration
- **Interactive testing**: Preview leads and emails in chat before going live
- **Iterative config**: If tests look wrong, update config files and re-test
- **Automation via launchd**: macOS-native scheduling handles sleep/wake properly
- **Slack testing**: Test webhook if configured

---

## README.md Structure

Short, focused quick-start guide:

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
```

Additional brief sections:
- What the system does (two pipelines overview)
- How emails work (joke opener example)
- Requirements (Python 3.11+, API keys list)

---

## `/outreach-setup` Skill Flow

### Existing Steps (Keep As-Is)

1. **Welcome** - Intro to the wizard
2. **Seed Customers** - Collect 5-10 best customers (domain + name)
3. **Targeting** - Job titles, contacts per company
4. **Company Context** - Name, value prop, tone, CTA
5. **Email Templates** - Use defaults or customize
6. **API Keys** - Anthropic, Composio, Apify, optionally Apollo/ScrapeCreators/Slack
7. **Gmail Settings** - From name
8. **Write Config Files + Init Database**

### New Steps (Add After Step 8)

#### Step 9: Test Lead Generation

**What happens:**
1. Run discovery pipeline with limit of 3-5 leads
2. Display results in formatted table:

```
## Sample Leads Found

| Company | Person | Title | Email | LinkedIn |
|---------|--------|-------|-------|----------|
| Acme DTC | Sarah Chen | VP Marketing | sarah@acmedtc.com | linkedin.com/in/sarahchen |
| Brand Co | Mike Johnson | CMO | mike@brandco.com | linkedin.com/in/mikejohnson |
| ShopFlow | Lisa Park | Head of Growth | lisa@shopflow.io | linkedin.com/in/lisapark |

These were found by searching for companies similar to your seed customers.
```

3. Ask: "Do these leads match your ideal customer profile?"

**If no:**
- Ask: "What's off? Too big/small? Wrong industry? Wrong titles?"
- Update `lead_gen.yaml` based on feedback
- Re-run test
- Repeat until confirmed

**Skip condition:**
If Apollo/ScrapeCreators keys missing: "Lead testing skipped - add Apollo and ScrapeCreators keys to test discovery"

#### Step 10: Test Email Generation

**What happens:**
1. Pick first lead from sample set
2. Scrape LinkedIn profile via Apify
3. Generate full email sequence (email 1 + followups)
4. Display in chat:

```
## Sample Email Sequence for Sarah Chen

**Email 1** (sends immediately)
Subject: your linkedin is suspiciously clean

Hey Sarah,

Scrolled your whole profile looking for something clever to reference
and you've given me nothing. No hot takes, no humble brags. I respect
the mystery.

[Pitch from context.md]

---

**Followup 1** (3 days later, no reply)
Subject: re: your linkedin is suspiciously clean

Hey Sarah,

Following up on my own cold email. The audacity.

[Rest of followup]

---

**Followup 2** (7 days later, no reply)
...
```

5. Ask: "Does this email feel right for your brand?"

**If no:**
- Ask what's off (tone? pitch? CTA?)
- Update `context.md` or `templates.md`
- Re-generate and show again

#### Step 11: Test Slack Notifications

**Only if SLACK_WEBHOOK_URL was provided:**

1. Send test notification: "Test notification from Outreach Setup - your Slack integration is working!"
2. Ask: "Did you receive a test message in Slack?"
   - Yes → continue
   - No → troubleshoot (check URL, permissions)
   - Skip → continue without Slack

#### Step 12: Setup Automation

**Prompt:**
"Want to run this automatically on weekdays at 9am?"

**Options (AskUserQuestion):**
- "Yes, set it up now"
- "Yes, but different time" → ask for preferred time
- "No, I'll do it later" → show instructions, continue

**If yes:**

1. Create launchd plist at `~/Library/LaunchAgents/com.outreach.daily.plist`:

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
    <string>/absolute/path/to/outreach-boilerplate</string>
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

2. Load it: `launchctl load ~/Library/LaunchAgents/com.outreach.daily.plist`
3. Confirm: "Automation scheduled. The pipeline will run Monday-Friday at 9am."

**If no:**
Show instructions they can reference later (also add to SETUP.md).

#### Step 13: Completion

```
# Setup Complete!

✓ Added {N} seed customers to config/lead_gen.yaml
✓ Set targeting: {job_titles}
✓ Wrote company context to config/context.md
✓ Saved API keys to .env
✓ Initialized database at data/outreach.db
✓ Tested lead generation - {N} sample leads found
✓ Tested email generation - sequence looks good
✓ Tested Slack notifications (if applicable)
✓ Automation scheduled for weekdays at {time}

Your outreach system is ready to go!

## What happens now

- Monday-Friday at {time}: The pipeline runs automatically
- Checks for replies, sends follow-ups, imports new leads from /leads folder
- Logs at /tmp/outreach.log

## Manual commands

python run.py status          # Check pipeline status
python run.py send            # Run manually anytime
python run_agent.py           # Find more leads via discovery
```

---

## SETUP.md Changes

Add new section: "Setting Up Automation Later"

```markdown
## Setting Up Automation Later

If you skipped automation during setup, you can configure it anytime.

### Using launchd (Recommended for macOS)

launchd is macOS-native and handles sleep/wake properly - if your laptop is asleep at 9am, it runs when it wakes.

1. Create the plist file:
   ```bash
   nano ~/Library/LaunchAgents/com.outreach.daily.plist
   ```

2. Paste this content (update paths):
   [plist content here]

3. Load it:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.outreach.daily.plist
   ```

4. Verify it's loaded:
   ```bash
   launchctl list | grep outreach
   ```

### Managing the schedule

- **Stop automation:** `launchctl unload ~/Library/LaunchAgents/com.outreach.daily.plist`
- **Change time:** Edit the plist, unload, reload
- **Check logs:** `tail -f /tmp/outreach.log`

### Using cron (Alternative)

If you prefer cron (note: doesn't handle sleep/wake):

```bash
crontab -e
```

Add:
```
0 9 * * 1-5 cd /path/to/outreach-boilerplate && uv run python run.py send >> /tmp/outreach.log 2>&1
```
```

---

## Files to Modify

1. **README.md** - Rewrite with Claude-first quick start
2. **.claude/skills/outreach-setup/SKILL.md** - Add steps 9-13
3. **SETUP.md** - Add "Setting Up Automation Later" section

## Implementation Notes

- Lead generation test requires calling actual discovery code with a limit
- Email generation test requires calling enricher + composer
- Slack test uses existing `services/slack_notifier.py`
- launchd plist needs absolute paths resolved at runtime (use `pwd` and `which uv`)
- Store automation preference so completion message is accurate
