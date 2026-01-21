"""Tests for config module."""

import tempfile
from pathlib import Path

from src.core.config import (
    load_settings,
    load_template,
    Settings,
    LeadGenConfig,
    load_lead_gen_config,
    load_templates,
)


def test_load_settings():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir)
        settings_file = config_path / "settings.yaml"
        settings_file.write_text("""
sequence:
  email_2_delay_days: 3
  email_3_delay_days: 4

sending:
  daily_limit: 50
  min_delay_seconds: 20
  max_delay_seconds: 60

gmail:
  from_name: "Test"
""")

        settings = load_settings(config_path)

        assert settings.sequence.email_2_delay_days == 3
        assert settings.sending.daily_limit == 50
        assert settings.gmail.from_name == "Test"


def test_load_template():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir)
        template_file = config_path / "test_template.md"
        template_file.write_text("Hello {{first_name}}!")

        content = load_template(config_path, "test_template.md")

        assert content == "Hello {{first_name}}!"


def test_lead_gen_config_defaults():
    config = LeadGenConfig()

    assert config.search.keywords == ["collagen supplement"]
    assert config.search.countries == ["US"]
    assert config.search.status == "ACTIVE"
    assert "Founder" in config.targeting.job_titles
    assert config.quotas.leads_per_day == 20
    assert config.quotas.max_companies_to_check == 50


def test_load_lead_gen_config_from_yaml():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir)
        config_file = config_path / "lead_gen.yaml"
        config_file.write_text("""
search:
  keywords:
    - "test product"
    - "another product"
  countries: ["US", "GB"]
  status: "ACTIVE"

targeting:
  job_titles:
    - "CEO"
    - "CTO"

quotas:
  leads_per_day: 10
  max_companies_to_check: 25
""")

        config = load_lead_gen_config(config_path)

        assert config.search.keywords == ["test product", "another product"]
        assert config.search.countries == ["US", "GB"]
        assert config.targeting.job_titles == ["CEO", "CTO"]
        assert config.quotas.leads_per_day == 10


def test_load_lead_gen_config_missing_file_returns_defaults():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir)
        # No file exists

        config = load_lead_gen_config(config_path)

        assert config.search.keywords == ["collagen supplement"]
        assert config.quotas.leads_per_day == 20


def test_load_templates():
    """Test loading templates from templates.md."""
    templates = load_templates()

    assert len(templates) == 3
    assert templates[0].name == "email_1"
    assert templates[0].delay_days == 0
    assert "{{generated_subject}}" in templates[0].subject or templates[0].subject

    assert templates[1].name == "followup_1"
    assert templates[1].delay_days == 3

    assert templates[2].name == "followup_2"
    assert templates[2].delay_days == 7
