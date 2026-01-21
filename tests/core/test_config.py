"""Tests for config module."""

from src.core.config import load_templates


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
