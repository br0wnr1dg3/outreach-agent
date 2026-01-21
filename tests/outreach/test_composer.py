import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.outreach.composer import generate_email_1, build_system_prompt


def test_build_system_prompt():
    context = "## Company\nTest Corp\n\n## Value Prop\nWe do things."
    email_template = "Hey {{first_name}},\n\n{{generated_joke_opener}}\n\nSincerely,\nChris"

    prompt = build_system_prompt(context, email_template)

    assert "Test Corp" in prompt
    assert "humor" in prompt.lower() or "joke" in prompt.lower()
    assert "personalized" in prompt.lower()


@pytest.mark.asyncio
async def test_generate_email_1():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir)

        # Create config files
        (config_path / "context.md").write_text("## Company\nTest Corp")
        (config_path / "templates.md").write_text(
            "---\n"
            "template: email_1\n"
            "delay_days: 0\n"
            "---\n\n"
            "subject: {{generated_subject}}\n\n"
            "Hey {{first_name}},\n\n"
            "{{generated_joke_opener}}\n\n"
            "Rest of email.\n\nChris"
        )

        lead = {
            "first_name": "Sarah",
            "last_name": "Chen",
            "company": "Glossy",
            "title": "Marketing Director",
            "email": "sarah@glossy.com",
        }

        posts = ["Just survived another Q4 planning session!"]

        mock_response = MagicMock()
        # API returns JSON with "subject" and "body" fields
        mock_response.content = [
            MagicMock(text='{"subject": "surviving q4 together", "body": "Your post about Q4 planning made me feel seen. Here I am adding to your inbox chaos."}')
        ]

        with patch("src.outreach.composer.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            subject, body = await generate_email_1(lead, posts, {}, config_path)

            assert "q4" in subject.lower()
            assert "Sarah" in body
            assert "Q4" in body or "inbox" in body
