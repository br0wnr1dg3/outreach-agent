# src/agents/discovery_agent.py
"""Discovery agent orchestrator using Claude Agent SDK.

This agent autonomously discovers and qualifies companies similar to
seed customers, hitting a daily quota of 10 new companies.
"""

import os
from pathlib import Path
from typing import AsyncIterator, Optional

from claude_agent_sdk import query, ClaudeAgentOptions
import structlog

from src.core.db import DEFAULT_DB_PATH, init_db, get_daily_stats
from src.discovery.mcp_tools import (
    create_apollo_mcp_server,
    create_fb_ads_mcp_server,
    create_sqlite_mcp_server,
    create_web_mcp_server,
)

log = structlog.get_logger()

# Default paths
CONFIG_DIR = Path("config")
SEED_PROFILES_DIR = CONFIG_DIR / "seed_profiles"
SEARCH_JOURNAL_PATH = Path("data/search_journal.md")
LEAD_GEN_CONFIG_PATH = CONFIG_DIR / "lead_gen.yaml"


class DiscoveryAgent:
    """Agent for discovering and qualifying leads.

    Uses Claude Agent SDK with MCP servers for:
    - FB Ads: Search for companies by keyword
    - Apollo: Check contacts and enrich leads
    - SQLite: Track companies and store leads (local database)
    - Web: Fetch company websites for ICP analysis
    """

    def __init__(
        self,
        seed_profiles_dir: Path = SEED_PROFILES_DIR,
        search_journal_path: Path = SEARCH_JOURNAL_PATH,
        lead_gen_config_path: Path = LEAD_GEN_CONFIG_PATH,
    ):
        """Initialize the discovery agent.

        Args:
            seed_profiles_dir: Directory containing seed profile .md files
            search_journal_path: Path to search journal markdown file
            lead_gen_config_path: Path to lead_gen.yaml config
        """
        self.seed_profiles_dir = seed_profiles_dir
        self.search_journal_path = search_journal_path
        self.lead_gen_config_path = lead_gen_config_path

        # Ensure database exists
        init_db(DEFAULT_DB_PATH)

        # Create MCP servers
        self.mcp_servers = {
            "fb_ads": create_fb_ads_mcp_server(),
            "apollo": create_apollo_mcp_server(),
            "sqlite": create_sqlite_mcp_server(),
            "web": create_web_mcp_server(),
        }

    def _load_seed_profiles(self) -> str:
        """Load all seed profile markdown files."""
        profiles = []
        if self.seed_profiles_dir.exists():
            for profile_path in self.seed_profiles_dir.glob("*.md"):
                content = profile_path.read_text()
                profiles.append(f"## Seed Profile: {profile_path.stem}\n\n{content}")

        return "\n\n---\n\n".join(profiles) if profiles else "No seed profiles found."

    def _load_search_journal(self) -> str:
        """Load search journal if it exists."""
        if self.search_journal_path.exists():
            return self.search_journal_path.read_text()
        return "No previous searches recorded."

    def _load_lead_gen_config(self) -> str:
        """Load lead gen config as string."""
        if self.lead_gen_config_path.exists():
            return self.lead_gen_config_path.read_text()
        return "No config found."

    def _build_system_prompt(self, daily_target: int = 10) -> str:
        """Build the system prompt with all context."""
        seed_profiles = self._load_seed_profiles()
        search_journal = self._load_search_journal()
        lead_gen_config = self._load_lead_gen_config()

        return f"""You are an autonomous lead discovery agent. Your goal is to find {daily_target} companies similar to our seed customers and generate leads from them.

## Your Tools

You have access to these MCP tools:

### FB Ads (mcp__fb_ads__)
- search_advertisers: Search FB Ad Library for companies by keyword

### Apollo (mcp__apollo__)
- check_company_contacts: Quick check if decision-makers exist (Gate 1)
- find_leads: Full enrichment to get email addresses

### SQLite (mcp__sqlite__)
- check_company_searched: Check if we already processed a domain
- mark_company_searched: Record company with gate results
- insert_lead: Add new lead to database
- get_quota_status: Check progress toward daily target

### Web (mcp__web__)
- fetch_company_page: Get company website for ICP analysis (Gate 2)

## Workflow

1. Pick a search keyword (prioritize higher-weighted ones)
2. Search FB Ads for companies
3. For each company:
   a. Skip if already searched (check_company_searched)
   b. Gate 1: Check if contacts exist (check_company_contacts)
   c. Gate 2: Fetch website, analyze against seed profiles for ICP fit
   d. If passes both gates: find_leads and insert_lead
   e. Mark company as searched with results
4. Track leads found THIS RUN (not from database) - stop when you hit {daily_target}
5. Continue with new keywords until target met or all keywords exhausted

## Contact Priority (Marketing First)
1. CMO
2. VP Marketing
3. Head of Marketing
4. Marketing Director
5. Founder
6. CEO

## Seed Customer Profiles

{seed_profiles}

## Search Journal (What Worked Before)

{search_journal}

## Configuration

{lead_gen_config}

## Important Rules

1. ALWAYS check if company is already searched before processing
2. ALWAYS run Gate 1 before Gate 2 (cheaper first)
3. Compare website content against seed profiles for ICP fit
4. Record detailed fit_notes explaining why company does/doesn't fit
5. Stop when quota is met
6. Be methodical - process one company at a time"""

    async def run(
        self,
        daily_target: int = 10,
        dry_run: bool = False,
    ) -> AsyncIterator:
        """Run the discovery agent.

        Args:
            daily_target: Number of companies to find (default: 10)
            dry_run: If True, don't write to database

        Yields:
            SDK messages as they arrive
        """
        system_prompt = self._build_system_prompt(daily_target)

        user_prompt = f"""Start discovering leads. Target: {daily_target} new leads THIS RUN.

{"DRY RUN MODE: Do not actually insert leads or mark companies as searched." if dry_run else ""}

Track how many leads you successfully insert during this run. Stop when you reach {daily_target} or exhaust all keywords. Begin searching now."""

        log.info("discovery_agent_starting", daily_target=daily_target, dry_run=dry_run)

        # Use streaming mode (async generator) to enable SDK MCP server communication.
        # String prompts close stdin immediately, preventing MCP control protocol responses.
        async def stream_prompt():
            yield {
                "type": "user",
                "message": {"role": "user", "content": user_prompt},
            }

        async for message in query(
            prompt=stream_prompt(),
            options=ClaudeAgentOptions(
                cwd=os.environ.get("PROJECT_DIR", os.getcwd()),
                permission_mode="acceptEdits",
                system_prompt=system_prompt,
                max_turns=200,  # Allow enough turns to process many companies
                allowed_tools=[
                    "mcp__fb_ads__*",
                    "mcp__apollo__*",
                    "mcp__sqlite__*",
                    "mcp__web__*",
                ],
                disallowed_tools=[
                    "Bash", "Read", "Write", "Task", "Grep", "Glob", "Edit",
                ],
                mcp_servers=self.mcp_servers,
            )
        ):
            yield message
