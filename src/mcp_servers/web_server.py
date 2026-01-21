# src/mcp_servers/web_server.py
"""Web fetching as MCP server for Claude Agent SDK.

Tools:
- fetch_company_page: Fetch and convert company website to markdown for ICP analysis
"""

import json
import re
from typing import Any
from html.parser import HTMLParser

import httpx
from claude_agent_sdk import SdkMcpTool, McpSdkServerConfig, create_sdk_mcp_server
import structlog

log = structlog.get_logger()

_tool_handlers: dict[str, Any] = {}


def get_tool_handlers() -> dict[str, Any]:
    """Get the current tool handlers for testing."""
    return _tool_handlers


class SimpleHTMLToMarkdown(HTMLParser):
    """Simple HTML to Markdown converter."""

    def __init__(self):
        super().__init__()
        self.result = []
        self.current_tag = None
        self.skip_content = False

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        if tag in ('script', 'style', 'nav', 'footer', 'header'):
            self.skip_content = True
        elif tag == 'h1':
            self.result.append('\n# ')
        elif tag == 'h2':
            self.result.append('\n## ')
        elif tag == 'h3':
            self.result.append('\n### ')
        elif tag == 'p':
            self.result.append('\n\n')
        elif tag == 'li':
            self.result.append('\n- ')
        elif tag == 'a':
            href = dict(attrs).get('href', '')
            if href and not href.startswith('#'):
                self.result.append('[')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'nav', 'footer', 'header'):
            self.skip_content = False
        elif tag in ('h1', 'h2', 'h3'):
            self.result.append('\n')
        self.current_tag = None

    def handle_data(self, data):
        if not self.skip_content:
            text = data.strip()
            if text:
                self.result.append(text + ' ')

    def get_markdown(self) -> str:
        text = ''.join(self.result)
        # Clean up whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        return text.strip()


def html_to_markdown(html: str) -> str:
    """Convert HTML to simple markdown."""
    parser = SimpleHTMLToMarkdown()
    parser.feed(html)
    return parser.get_markdown()


def create_web_mcp_server() -> McpSdkServerConfig:
    """Create an MCP server with web fetching tools.

    Returns:
        McpSdkServerConfig for the MCP server.
    """
    global _tool_handlers

    async def fetch_company_page_handler(args: dict[str, Any]) -> dict[str, Any]:
        """Fetch company website and return as markdown.

        Used for Gate 2 - ICP analysis. Agent compares content against seed profiles.

        Args:
            args: Dict with keys:
                - url (str): Company website URL

        Returns:
            MCP response with page content as markdown.
        """
        url = args.get("url")
        if not url:
            return {
                "content": [{"type": "text", "text": json.dumps({"error": "url is required"})}],
                "isError": True,
            }

        # Ensure URL has protocol
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; OutreachBot/1.0)",
                    }
                )

                if response.status_code != 200:
                    return {
                        "content": [{"type": "text", "text": json.dumps({
                            "error": f"HTTP {response.status_code}",
                            "url": url,
                        })}],
                        "isError": True,
                    }

                html = response.text
                markdown = html_to_markdown(html)

                # Truncate if too long (keep first 8000 chars for context window)
                if len(markdown) > 8000:
                    markdown = markdown[:8000] + "\n\n[Content truncated...]"

                result = {
                    "url": url,
                    "content": markdown,
                    "content_length": len(markdown),
                }
                return {"content": [{"type": "text", "text": json.dumps(result)}]}

        except httpx.TimeoutException:
            return {
                "content": [{"type": "text", "text": json.dumps({"error": "Timeout", "url": url})}],
                "isError": True,
            }
        except Exception as e:
            log.error("web_fetch_error", error=str(e), url=url)
            return {
                "content": [{"type": "text", "text": json.dumps({"error": str(e), "url": url})}],
                "isError": True,
            }

    _tool_handlers = {
        "fetch_company_page": fetch_company_page_handler,
    }

    fetch_page_tool = SdkMcpTool(
        name="fetch_company_page",
        description="Fetch company website and convert to markdown for ICP analysis (Gate 2)",
        input_schema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Company website URL (e.g., 'example.com' or 'https://example.com')",
                },
            },
            "required": ["url"],
        },
        handler=fetch_company_page_handler,
    )

    return create_sdk_mcp_server(
        name="web",
        version="1.0.0",
        tools=[fetch_page_tool],
    )
