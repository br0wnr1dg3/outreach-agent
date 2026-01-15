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
