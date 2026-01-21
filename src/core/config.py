"""Configuration loading and models."""

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

    return Settings(**data)


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
