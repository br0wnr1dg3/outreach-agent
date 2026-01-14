"""Command-line interface for outreach boilerplate."""

import asyncio
from pathlib import Path
from typing import Optional

import click
import structlog

from src.db import DEFAULT_DB_PATH, init_db, get_pipeline_stats, get_lead_by_email
from src.config import DEFAULT_CONFIG_PATH, load_settings
from src.importer import import_leads
from src.scheduler import run_send_cycle

# Configure structlog for CLI output
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ]
)

log = structlog.get_logger()


@click.group()
def cli():
    """Outreach Boilerplate - Humor-first cold email CLI."""
    pass


@cli.command(name="import")
@click.argument("excel_path", type=click.Path(exists=True))
@click.option("--db", "db_path", type=click.Path(), default=str(DEFAULT_DB_PATH),
              help="Database path")
def import_cmd(excel_path: str, db_path: str):
    """Import leads from an Excel file."""
    db = Path(db_path)
    init_db(db)

    click.echo(f"Importing leads from {excel_path}...")

    result = import_leads(Path(excel_path), db)

    click.echo(f"\nImported {result['imported']} new leads")
    if result['skipped'] > 0:
        click.echo(f"Skipped {result['skipped']} duplicates")


@cli.command()
@click.option("--db", "db_path", type=click.Path(), default=str(DEFAULT_DB_PATH),
              help="Database path")
@click.option("--config", "config_path", type=click.Path(), default=str(DEFAULT_CONFIG_PATH),
              help="Config directory path")
def send(db_path: str, config_path: str):
    """Send emails (process new leads and follow-ups)."""
    db = Path(db_path)
    config = Path(config_path)

    init_db(db)
    settings = load_settings(config)

    click.echo("Starting send cycle...\n")

    result = asyncio.run(run_send_cycle(db, config))

    # Print results
    if result["replied"]:
        click.echo("Replies detected:")
        for email in result["replied"]:
            click.echo(f"  ✓ {email} replied - sequence stopped")
        click.echo()

    if result["new_sent"] > 0:
        click.echo(f"New leads processed: {result['new_sent']}")

    if result["followups_sent"] > 0:
        click.echo(f"Follow-ups sent: {result['followups_sent']}")

    total_sent = result["new_sent"] + result["followups_sent"]
    click.echo(f"\nTotal sent: {total_sent}")
    click.echo(f"Daily sends: {result['sent_today']}/{settings.sending.daily_limit}")

    if result["daily_limit_reached"]:
        click.echo("\n⚠️  Daily limit reached. Run again tomorrow.")


@cli.command()
@click.option("--db", "db_path", type=click.Path(), default=str(DEFAULT_DB_PATH),
              help="Database path")
@click.option("--lead", "lead_email", type=str, default=None,
              help="Check specific lead by email")
@click.option("--config", "config_path", type=click.Path(), default=str(DEFAULT_CONFIG_PATH),
              help="Config directory path")
def status(db_path: str, lead_email: Optional[str], config_path: str):
    """Show pipeline status."""
    db = Path(db_path)
    config = Path(config_path)

    init_db(db)
    settings = load_settings(config)

    if lead_email:
        # Show specific lead
        lead = get_lead_by_email(db, lead_email)
        if not lead:
            click.echo(f"Lead not found: {lead_email}")
            return

        click.echo(f"\nLead: {lead['email']}")
        click.echo(f"  Name: {lead['first_name']} {lead['last_name'] or ''}")
        click.echo(f"  Company: {lead['company'] or 'N/A'}")
        click.echo(f"  Status: {lead['status']}")
        click.echo(f"  Current step: {lead['current_step']}")
        click.echo(f"  Imported: {lead['imported_at']}")
        if lead['last_sent_at']:
            click.echo(f"  Last sent: {lead['last_sent_at']}")
        if lead['next_send_at']:
            click.echo(f"  Next send: {lead['next_send_at']}")
        return

    # Show overall stats
    stats = get_pipeline_stats(db)

    click.echo("\nPipeline Status")
    click.echo("───────────────")
    click.echo(f"New (pending):         {stats.get('new', 0)}")
    click.echo(f"Active sequences:      {stats.get('active', 0)}")
    click.echo(f"  - Due for follow-up: {stats.get('due_for_followup', 0)}")
    click.echo(f"Replied:               {stats.get('replied', 0)}")
    click.echo(f"Completed:             {stats.get('completed', 0)}")
    click.echo("───────────────")
    click.echo(f"Daily sends: {stats.get('sent_today', 0)}/{settings.sending.daily_limit}")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
