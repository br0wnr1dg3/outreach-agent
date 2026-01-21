import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.core.db import init_db, insert_lead, update_lead_email_sent, get_lead_by_id
from src.core.config import Settings
from src.outreach.scheduler import check_replies, get_due_leads, process_lead


@pytest.mark.asyncio
async def test_check_replies_marks_replied():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        lead_id = insert_lead(db_path, "test@example.com", "Test", None, None, None, None)

        # Simulate email 1 sent
        update_lead_email_sent(
            db_path, lead_id, step=1,
            subject="test", body="body",
            thread_id="thread_123", message_id="msg_1",
            next_send_at=datetime.utcnow() + timedelta(days=3)
        )

        # Mock reply detection
        with patch("src.outreach.scheduler.check_for_reply", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True  # They replied

            replied = await check_replies(db_path)

            assert len(replied) == 1
            assert replied[0] == "test@example.com"

            lead = get_lead_by_id(db_path, lead_id)
            assert lead["status"] == "replied"


@pytest.mark.asyncio
async def test_get_due_leads():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)

        lead_id = insert_lead(db_path, "due@example.com", "Due", None, None, None, None)

        # Set as active with past next_send_at
        update_lead_email_sent(
            db_path, lead_id, step=1,
            subject="test", body="body",
            thread_id="thread_123", message_id="msg_1",
            next_send_at=datetime.utcnow() - timedelta(hours=1)  # Due
        )

        due = get_due_leads(db_path)

        assert len(due) == 1
        assert due[0]["email"] == "due@example.com"
