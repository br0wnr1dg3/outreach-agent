# src/supabase_client.py
"""Supabase client for leads and companies."""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import uuid4

from supabase import create_client, Client
import structlog

log = structlog.get_logger()


@dataclass
class Lead:
    """Lead record from Supabase."""
    id: str
    email: str
    first_name: str
    last_name: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    linkedin_url: Optional[str] = None
    status: str = "new"
    current_step: int = 0
    source: str = "import"
    source_keyword: Optional[str] = None
    company_fit_score: Optional[int] = None
    company_fit_notes: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class SearchedCompany:
    """Searched company record from Supabase."""
    id: str
    domain: str
    company_name: Optional[str] = None
    source_keyword: Optional[str] = None
    passed_gate_1: Optional[bool] = None
    passed_gate_2: Optional[bool] = None
    leads_found: int = 0
    fit_score: Optional[int] = None
    fit_notes: Optional[str] = None
    searched_at: Optional[datetime] = None


class SupabaseClient:
    """Client for Supabase database operations."""

    def __init__(self):
        """Initialize Supabase client from environment variables."""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url:
            raise ValueError("SUPABASE_URL environment variable is required")
        if not key:
            raise ValueError("SUPABASE_KEY environment variable is required")

        self.client: Client = create_client(url, key)

    def check_company_searched(self, domain: str) -> bool:
        """Check if a company domain has been searched."""
        result = (
            self.client.table("searched_companies")
            .select("id")
            .eq("domain", domain)
            .execute()
        )
        return len(result.data) > 0

    def mark_company_searched(
        self,
        domain: str,
        company_name: Optional[str] = None,
        source_keyword: Optional[str] = None,
        passed_gate_1: Optional[bool] = None,
        passed_gate_2: Optional[bool] = None,
        fit_score: Optional[int] = None,
        fit_notes: Optional[str] = None,
    ) -> SearchedCompany:
        """Mark a company as searched."""
        data = {
            "id": str(uuid4()),
            "domain": domain,
            "company_name": company_name,
            "source_keyword": source_keyword,
            "passed_gate_1": passed_gate_1,
            "passed_gate_2": passed_gate_2,
            "fit_score": fit_score,
            "fit_notes": fit_notes,
            "searched_at": datetime.utcnow().isoformat(),
        }

        result = self.client.table("searched_companies").upsert(data).execute()
        row = result.data[0]

        log.info("company_marked_searched", domain=domain, source_keyword=source_keyword)
        return SearchedCompany(**row)

    def update_company_leads_found(self, domain: str, count: int) -> None:
        """Update the leads_found count for a searched company."""
        self.client.table("searched_companies").update(
            {"leads_found": count}
        ).eq("domain", domain).execute()

    def insert_lead(
        self,
        email: str,
        first_name: str,
        last_name: Optional[str] = None,
        company: Optional[str] = None,
        title: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        source: str = "agent",
        source_keyword: Optional[str] = None,
        company_fit_score: Optional[int] = None,
        company_fit_notes: Optional[str] = None,
    ) -> Optional[Lead]:
        """Insert a lead. Returns Lead or None if duplicate."""
        data = {
            "id": str(uuid4()),
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "company": company,
            "title": title,
            "linkedin_url": linkedin_url,
            "status": "new",
            "current_step": 0,
            "source": source,
            "source_keyword": source_keyword,
            "company_fit_score": company_fit_score,
            "company_fit_notes": company_fit_notes,
            "created_at": datetime.utcnow().isoformat(),
        }

        try:
            result = self.client.table("leads").insert(data).execute()
            row = result.data[0]
            log.info("lead_inserted", email=email, source=source)
            return Lead(**row)
        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                log.info("lead_duplicate_skipped", email=email)
                return None
            raise

    def get_leads_by_status(self, status: str) -> list[Lead]:
        """Get all leads with a given status."""
        result = (
            self.client.table("leads")
            .select("*")
            .eq("status", status)
            .execute()
        )
        return [Lead(**row) for row in result.data]

    def count_leads_generated_today(self) -> int:
        """Count leads generated today."""
        today = datetime.utcnow().date().isoformat()
        result = (
            self.client.table("leads")
            .select("id", count="exact")
            .gte("created_at", f"{today}T00:00:00")
            .lt("created_at", f"{today}T23:59:59")
            .execute()
        )
        return result.count or 0

    def count_companies_checked_today(self) -> int:
        """Count companies checked today."""
        today = datetime.utcnow().date().isoformat()
        result = (
            self.client.table("searched_companies")
            .select("id", count="exact")
            .gte("searched_at", f"{today}T00:00:00")
            .lt("searched_at", f"{today}T23:59:59")
            .execute()
        )
        return result.count or 0

    def get_daily_stats(self) -> dict:
        """Get daily statistics."""
        return {
            "leads_generated_today": self.count_leads_generated_today(),
            "companies_checked_today": self.count_companies_checked_today(),
        }

    def get_quota_status(self, daily_target: int = 10) -> dict:
        """Get quota status for today."""
        leads_today = self.count_leads_generated_today()
        return {
            "leads_today": leads_today,
            "target": daily_target,
            "remaining": max(0, daily_target - leads_today),
            "quota_met": leads_today >= daily_target,
        }
