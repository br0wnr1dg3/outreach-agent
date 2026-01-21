"""Command-line interface for outreach boilerplate."""

import asyncio
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import structlog

from src.core.db import DEFAULT_DB_PATH, init_db, get_pipeline_stats, get_lead_by_email
from src.core.config import DEFAULT_CONFIG_PATH, load_settings
from src.outreach.importer import import_leads
from src.outreach.scheduler import run_send_cycle
from src.discovery.lead_generator import generate_leads

# Configure structlog for CLI output
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ]
)

log = structlog.get_logger()

LEADS_FOLDER = Path("leads")
PROCESSED_FOLDER = LEADS_FOLDER / "processed"


def import_from_leads_folder(db_path: Path) -> dict:
    """Import all Excel files from /leads folder and move to /processed."""
    LEADS_FOLDER.mkdir(exist_ok=True)
    PROCESSED_FOLDER.mkdir(exist_ok=True)

    total_imported = 0
    total_skipped = 0
    files_processed = []

    # Find all Excel files
    excel_files = list(LEADS_FOLDER.glob("*.xlsx")) + list(LEADS_FOLDER.glob("*.xls"))

    for excel_path in excel_files:
        if excel_path.parent == PROCESSED_FOLDER:
            continue  # Skip files already in processed folder

        click.echo(f"Importing {excel_path.name}...")

        try:
            result = import_leads(excel_path, db_path)
            total_imported += result["imported"]
            total_skipped += result["skipped"]

            # Move to processed folder with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_name = f"{excel_path.stem}_{timestamp}{excel_path.suffix}"
            dest = PROCESSED_FOLDER / new_name
            shutil.move(str(excel_path), str(dest))

            files_processed.append(excel_path.name)
            click.echo(f"  → Imported {result['imported']}, skipped {result['skipped']}")

        except Exception as e:
            click.echo(f"  ✗ Error: {e}")

    return {
        "imported": total_imported,
        "skipped": total_skipped,
        "files": files_processed,
    }


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Outreach Boilerplate - Humor-first cold email CLI.

    Just run 'python run.py' to import leads and send emails.
    """
    if ctx.invoked_subcommand is None:
        # Default behavior: run the full cycle
        ctx.invoke(run)


@cli.command()
@click.option("--db", "db_path", type=click.Path(), default=str(DEFAULT_DB_PATH),
              help="Database path")
@click.option("--config", "config_path", type=click.Path(), default=str(DEFAULT_CONFIG_PATH),
              help="Config directory path")
def run(db_path: str, config_path: str):
    """Import new leads from /leads folder and send emails."""
    db = Path(db_path)
    config = Path(config_path)

    init_db(db)
    settings = load_settings(config)

    # Step 1: Import any new leads
    click.echo("=" * 40)
    click.echo("STEP 1: Checking for new leads...")
    click.echo("=" * 40)

    import_result = import_from_leads_folder(db)

    if import_result["files"]:
        click.echo(f"\nImported {import_result['imported']} leads from {len(import_result['files'])} file(s)")
        click.echo("Files moved to leads/processed/")
    else:
        click.echo("No new files in /leads folder")

    # Step 2: Send emails
    click.echo("\n" + "=" * 40)
    click.echo("STEP 2: Sending emails...")
    click.echo("=" * 40 + "\n")

    result = asyncio.run(run_send_cycle(db, config))

    # Print results
    if result["replied"]:
        click.echo("Replies detected:")
        for email in result["replied"]:
            click.echo(f"  ✓ {email} replied - sequence stopped")
        click.echo()

    if result["new_sent"] > 0:
        click.echo(f"New leads emailed: {result['new_sent']}")

    if result["followups_sent"] > 0:
        click.echo(f"Follow-ups sent: {result['followups_sent']}")

    total_sent = result["new_sent"] + result["followups_sent"]

    # Summary
    click.echo("\n" + "=" * 40)
    click.echo("SUMMARY")
    click.echo("=" * 40)
    click.echo(f"Emails sent this run: {total_sent}")
    click.echo(f"Daily total: {result['sent_today']}/{settings.sending.daily_limit}")

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


@cli.command()
@click.option("--db", "db_path", type=click.Path(), default=str(DEFAULT_DB_PATH),
              help="Database path")
@click.option("--config", "config_path", type=click.Path(), default=str(DEFAULT_CONFIG_PATH),
              help="Config directory path")
@click.option("--dry-run", is_flag=True, help="Show what would be generated without making API calls")
@click.option("--keyword", help="Override search keyword for this run")
def generate(db_path: str, config_path: str, dry_run: bool, keyword: str):
    """Generate new leads from FB Ad Library + Apollo."""
    db = Path(db_path)
    config = Path(config_path)

    init_db(db)

    if dry_run:
        click.echo("DRY RUN - No API calls will be made\n")

    click.echo("=" * 40)
    click.echo("Generating leads...")
    click.echo("=" * 40 + "\n")

    result = asyncio.run(generate_leads(
        db_path=db,
        config_path=config,
        dry_run=dry_run,
        keyword_override=keyword
    ))

    click.echo(f"\nResults:")
    click.echo(f"  Leads added: {result['leads_added']}")
    click.echo(f"  Companies checked: {result['companies_checked']}")
    click.echo(f"  Companies skipped (already searched): {result['companies_skipped']}")

    if result.get("export_file"):
        click.echo(f"\n  Exported to: {result['export_file']}")

    if result.get("quota_reached"):
        click.echo(f"\n  Daily quota reached!")


@cli.command()
@click.option('--target', default=10, help='Daily company target')
@click.option('--dry-run', is_flag=True, help='Preview without writing to DB')
def agent(target: int, dry_run: bool):
    """Run the discovery agent to find and qualify leads."""
    from src.discovery.agent import DiscoveryAgent

    click.echo(f"Starting discovery agent (target: {target} companies)")
    if dry_run:
        click.echo("DRY RUN - no database writes")

    async def run_agent():
        agent = DiscoveryAgent()
        async for message in agent.run(daily_target=target, dry_run=dry_run):
            if hasattr(message, 'result'):
                click.echo(message.result)

    asyncio.run(run_agent())
    click.echo("Discovery agent complete")


@cli.command('analyze-seeds')
@click.argument('urls', nargs=-1, required=True)
@click.option('--output', '-o', default='config/seed_profiles', help='Output directory')
def analyze_seeds(urls: tuple, output: str):
    """Analyze seed customer websites and save ICP profiles.

    URLS: One or more website URLs to analyze
    """
    from pathlib import Path
    from src.services.seed_analyzer import SeedAnalyzer

    output_dir = Path(output)

    async def run_analysis():
        analyzer = SeedAnalyzer()
        for url in urls:
            click.echo(f"Analyzing {url}...")
            path = await analyzer.analyze_and_save(url, output_dir)
            click.echo(f"  Saved to {path}")

    asyncio.run(run_analysis())
    click.echo(f"\nSeed profiles saved to {output_dir}/")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
