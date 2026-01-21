"""Configuration loading and models."""

import os
import re
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel


class SequenceConfig(BaseModel):
    email_2_delay_days: int = 3
    email_3_delay_days: int = 4


class SendingConfig(BaseModel):
    daily_limit: int = 50
    min_delay_seconds: int = 20
    max_delay_seconds: int = 60


class GmailConfig(BaseModel):
    from_name: str = "Chris"
    connected_account_id: str = ""  # Composio connected account ID


class Settings(BaseModel):
    sequence: SequenceConfig = SequenceConfig()
    sending: SendingConfig = SendingConfig()
    gmail: GmailConfig = GmailConfig()


class LeadGenSearchConfig(BaseModel):
    keywords: list[str] = ["collagen supplement"]
    countries: list[str] = ["US"]
    status: str = "ACTIVE"
    excluded_domains: list[str] = []


class LeadGenTargetingConfig(BaseModel):
    job_titles: list[str] = ["Founder", "CEO", "Head of Marketing", "CMO"]


class LeadGenQuotaConfig(BaseModel):
    leads_per_day: int = 20
    max_companies_to_check: int = 50


class LeadGenConfig(BaseModel):
    search: LeadGenSearchConfig = LeadGenSearchConfig()
    targeting: LeadGenTargetingConfig = LeadGenTargetingConfig()
    quotas: LeadGenQuotaConfig = LeadGenQuotaConfig()


DEFAULT_CONFIG_PATH = Path("config")


def load_settings(config_path: Path = DEFAULT_CONFIG_PATH) -> Settings:
    """Load settings from YAML file."""
    settings_file = config_path / "settings.yaml"

    if not settings_file.exists():
        return Settings()

    with open(settings_file) as f:
        data = yaml.safe_load(f) or {}

    settings = Settings(**data)

    # Check env var for connected_account_id if not set in YAML
    if not settings.gmail.connected_account_id:
        env_account_id = os.environ.get("COMPOSIO_CONNECTED_ACCOUNT_ID", "")
        if env_account_id:
            settings.gmail.connected_account_id = env_account_id

    return settings


def load_template(config_path: Path, template_name: str) -> str:
    """Load a template file."""
    template_file = config_path / template_name
    return template_file.read_text()


def render_template(template: str, variables: dict) -> str:
    """Render a template with variable substitution."""
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", str(value) if value else "")
    return result


def load_lead_gen_config(config_path: Path = DEFAULT_CONFIG_PATH) -> LeadGenConfig:
    """Load lead generation config from YAML file."""
    config_file = config_path / "lead_gen.yaml"
    if not config_file.exists():
        return LeadGenConfig()
    with open(config_file) as f:
        data = yaml.safe_load(f) or {}
    return LeadGenConfig(**data)


class EmailTemplate(BaseModel):
    """Email template with timing metadata."""
    name: str
    delay_days: int
    subject: str
    body: str


def load_templates(config_path: Path = DEFAULT_CONFIG_PATH) -> list[EmailTemplate]:
    """Load and parse templates.md into list of EmailTemplate objects."""
    templates_file = config_path / "templates.md"

    if not templates_file.exists():
        return []

    content = templates_file.read_text()

    # Split on frontmatter delimiters (---)
    sections = re.split(r'^---\s*$', content, flags=re.MULTILINE)

    templates = []
    # Process pairs of (frontmatter, body)
    i = 1
    while i < len(sections) - 1:
        frontmatter = sections[i].strip()
        body = sections[i + 1].strip()

        if not frontmatter:
            i += 2
            continue

        # Parse YAML frontmatter
        meta = yaml.safe_load(frontmatter)
        if not meta or "template" not in meta:
            i += 2
            continue

        # Extract subject from body
        lines = body.split('\n')
        subject = ""
        body_start = 0
        for idx, line in enumerate(lines):
            if line.startswith('subject:'):
                subject = line.replace('subject:', '').strip()
                body_start = idx + 1
                break

        body_content = '\n'.join(lines[body_start:]).strip()

        templates.append(EmailTemplate(
            name=meta["template"],
            delay_days=meta.get("delay_days", 0),
            subject=subject,
            body=body_content,
        ))

        i += 2

    return templates


def get_template_by_name(config_path: Path, name: str) -> EmailTemplate:
    """Get a specific email template by name from templates.md."""
    templates = load_templates(config_path)
    for t in templates:
        if t.name == name:
            return t
    raise ValueError(f"Template '{name}' not found in templates.md")
