from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.sender import send_new_email, send_reply_email


@pytest.mark.asyncio
async def test_send_new_email():
    mock_result = {
        "data": {
            "threadId": "thread_123",
            "id": "msg_456"
        }
    }

    with patch("src.sender.ComposioToolSet") as mock_toolset:
        mock_instance = MagicMock()
        mock_instance.execute_action.return_value = mock_result
        mock_toolset.return_value = mock_instance

        result = await send_new_email(
            to="test@example.com",
            subject="Test subject",
            body="Test body",
            from_name="Chris"
        )

        assert result["thread_id"] == "thread_123"
        assert result["message_id"] == "msg_456"


@pytest.mark.asyncio
async def test_send_reply_email():
    mock_result = {
        "data": {
            "threadId": "thread_123",
            "id": "msg_789"
        }
    }

    with patch("src.sender.ComposioToolSet") as mock_toolset:
        mock_instance = MagicMock()
        mock_instance.execute_action.return_value = mock_result
        mock_toolset.return_value = mock_instance

        result = await send_reply_email(
            to="test@example.com",
            subject="Re: Test subject",
            body="Follow up body",
            thread_id="thread_123",
            message_id="msg_456",
            from_name="Chris"
        )

        assert result["thread_id"] == "thread_123"
        assert result["message_id"] == "msg_789"
