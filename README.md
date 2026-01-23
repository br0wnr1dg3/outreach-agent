# Outreach Boilerplate

Humor-first cold email outreach. Clone, configure with Claude, run.

Designed to work for companies selling to anyone that would be advertising on Facebook (raw lead gen comes from Facebook Ad Library)

## Quick Start

1. Clone and install:
   ```bash
   git clone https://github.com/br0wnr1dg3/outreach-agent
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

## Stopping Automation
```
launchctl unload ~/Library/LaunchAgents/com.outreach.daily.plist
```

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
