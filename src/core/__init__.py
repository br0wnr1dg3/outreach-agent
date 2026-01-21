"""Core infrastructure: CLI, config, database."""

from src.core.config import (
    Settings,
    SequenceConfig,
    SendingConfig,
    GmailConfig,
    LeadGenConfig,
    load_settings,
    load_template,
    render_template,
    load_lead_gen_config,
)
from src.core.db import (
    init_db,
    get_lead_by_email,
    get_lead_by_id,
    get_leads_by_status,
    insert_lead,
    update_lead_status,
    update_lead_enrichment,
    update_lead_email_sent,
    get_leads_due_for_followup,
    count_sent_today,
    get_pipeline_stats,
)
