# src/services/seed_analyzer.py
"""Seed customer analyzer using Claude."""

import os
from pathlib import Path
from urllib.parse import urlparse

import anthropic
import httpx
import structlog

from src.discovery.mcp_tools import html_to_markdown

log = structlog.get_logger()

ANALYSIS_PROMPT = """Analyze this company website and create a detailed ICP (Ideal Customer Profile) analysis.

Website URL: {url}
Website Content:
{content}

Create a markdown document with these sections:

# {domain}

## Company Profile
- Category: (e.g., Beauty/Wellness DTC, SaaS, E-commerce)
- Product: What do they sell?
- Market: Primary geographic markets
- Price point: (Budget, Mid-range, Premium)
- Business model: (One-time purchase, Subscription, etc.)

## ICP Signals
List 5-7 signals that indicate a company is similar to this one:
- (Signal 1)
- (Signal 2)
- etc.

## Search Terms That Would Find Similar
List 4-6 Facebook Ad Library search terms that would find similar companies:
- "term 1"
- "term 2"
- etc.

## Decision Maker Profile
- Primary target role (e.g., CMO, Head of Growth)
- What they're likely interested in (e.g., influencer marketing, UGC, performance creative)

Be specific and actionable. The goal is to help an AI agent find similar companies."""


class SeedAnalyzer:
    """Service for analyzing seed customer websites."""

    def __init__(self):
        """Initialize with Anthropic client."""
        self.client = anthropic.AsyncAnthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )

    async def fetch_website(self, url: str) -> str:
        """Fetch website content as markdown."""
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; OutreachBot/1.0)"},
            )
            response.raise_for_status()
            return html_to_markdown(response.text)

    async def analyze_seed(self, url: str) -> str:
        """Analyze a seed customer website.

        Args:
            url: Website URL to analyze

        Returns:
            Markdown analysis of the company
        """
        # Extract domain for the title
        parsed = urlparse(url if url.startswith('http') else f"https://{url}")
        domain = parsed.netloc.replace('www.', '')

        # Fetch website content
        content = await self.fetch_website(url)

        # Truncate if too long
        if len(content) > 10000:
            content = content[:10000] + "\n\n[Content truncated...]"

        # Generate analysis with Claude
        prompt = ANALYSIS_PROMPT.format(url=url, content=content, domain=domain)

        message = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        analysis = message.content[0].text
        log.info("seed_analyzed", url=url, domain=domain)
        return analysis

    async def analyze_and_save(self, url: str, output_dir: Path) -> Path:
        """Analyze a seed and save to file.

        Args:
            url: Website URL to analyze
            output_dir: Directory to save analysis

        Returns:
            Path to saved file
        """
        # Extract domain for filename
        parsed = urlparse(url if url.startswith('http') else f"https://{url}")
        domain = parsed.netloc.replace('www.', '')
        filename = domain.replace('.', '_') + '.md'

        # Analyze
        analysis = await self.analyze_seed(url)

        # Save
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename
        output_path.write_text(analysis)

        log.info("seed_analysis_saved", path=str(output_path))
        return output_path
