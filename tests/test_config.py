import tempfile
from pathlib import Path

from src.config import load_settings, load_template, Settings, LeadGenConfig


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
