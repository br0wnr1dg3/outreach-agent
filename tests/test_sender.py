from unittest.mock import MagicMock, patch

import pytest

from src.sender import send_new_email, send_reply_email


@pytest.mark.asyncio
async def test_send_new_email():
    # Mock result object with attributes (new SDK style)
    mock_result = MagicMock()
    mock_result.successful = True
    mock_result.data = {
        "threadId": "thread_123",
        "id": "msg_456"
    }
    mock_result.error = None

    with patch("src.sender._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.tools.execute.return_value = mock_result
        mock_get_client.return_value = mock_client

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
    mock_result = MagicMock()
    mock_result.successful = True
    mock_result.data = {
        "threadId": "thread_123",
        "id": "msg_789"
    }
    mock_result.error = None

    with patch("src.sender._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.tools.execute.return_value = mock_result
        mock_get_client.return_value = mock_client

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
