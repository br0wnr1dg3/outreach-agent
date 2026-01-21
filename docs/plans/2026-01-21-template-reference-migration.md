# Template Reference Migration

## Problem

Code still references old individual template files (`email_1.md`, `followup_1.md`, `followup_2.md`) which no longer exist. All templates are now consolidated in `templates.md`, and `config.py` has a `load_templates()` function to parse it—but nothing uses it.

## Solution

Add a `get_template_by_name()` helper and update `composer.py` and `scheduler.py` to use it.

## Changes

### 1. `src/core/config.py`

Add after `load_templates()`:

```python
def get_template_by_name(config_path: Path, name: str) -> EmailTemplate:
    """Get a specific email template by name from templates.md."""
    templates = load_templates(config_path)
    for t in templates:
        if t.name == name:
            return t
    raise ValueError(f"Template '{name}' not found in templates.md")
```

### 2. `src/outreach/composer.py`

- Update import to include `get_template_by_name`
- Line 103: Replace `load_template(config_path, "email_1.md")` with `get_template_by_name()` call
- Line 185: Same change in `generate_fallback_email()`
- Keep `load_template` import for `context.md`

### 3. `src/outreach/scheduler.py`

- Update import to use `get_template_by_name` instead of `load_template`
- Lines 165-167: Use `get_template_by_name(config_path, f"followup_{next_step - 1}")`
- Lines 173-185: Simplify by using `template_obj.subject` and `template_obj.body` directly with `render_template()`

## What stays the same

- `load_template()` still exists for `context.md`
- `load_templates()` unchanged
- `templates.md` format unchanged

## Out of scope

- Removing `email_2_delay_days` / `email_3_delay_days` from `settings.yaml` (templates have `delay_days` but settings still used for scheduling)
- Deleting `load_template()` function
