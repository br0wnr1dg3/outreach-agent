# Slack Notification Redesign

## Problem

The current Slack notification only shows "Companies Found" and "Leads Added" for the current run. This provides limited visibility into pipeline health and trends.

## Solution

Replace the current daily notification with a comprehensive report showing weekly and all-time metrics.

## New Metrics

| Metric | Definition |
|--------|------------|
| Leads Found | Total leads in database |
| Leads Contacted | Leads with `current_step >= 1` (received first email) |
| Leads Replied | Leads with `status = 'replied'` |
| Reply Rate | `leads_replied / leads_contacted * 100` |

## Schema Change

Add `replied_at` timestamp to the `leads` table:

```sql
ALTER TABLE leads ADD COLUMN replied_at TIMESTAMP;
```

Set when `status` changes to `'replied'`.

## Slack Message Format

```
✅ Daily Outreach Complete

This Week                    All Time
─────────────────────────────────────────
Leads Found:      12         Leads Found:      247
Contacted:         8         Contacted:        189
Replied:           2         Replied:           31

📊 Reply Rate: 16.4%

Issues: (only if errors occurred)
• Error message 1
```

Two-column layout using Slack `fields`. Week boundary is Monday (ISO standard).

## Files to Modify

### 1. `src/core/db.py`

- Add `replied_at` column in `init_db()` schema
- Add `get_weekly_stats(db_path) -> dict`
- Add `get_all_time_stats(db_path) -> dict`
- Update reply status setters to include `replied_at`

### 2. `src/services/slack_notifier.py`

- Update `send_summary()` to accept stats dict
- Build two-column Slack blocks layout
- Add reply rate section

### 3. `src/outreach/scheduler.py`

- Set `replied_at = datetime.utcnow()` when marking lead as replied

## Out of Scope

- Supabase migration (SQLite only for now)
- Weekly digest (single daily report only)
