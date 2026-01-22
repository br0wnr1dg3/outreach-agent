"""Gmail sending via Composio."""

import asyncio
from typing import Optional

import structlog
from composio.sdk import Composio

log = structlog.get_logger()

# Cache for user_id lookups
_user_id_cache: dict[str, str] = {}


def _get_client() -> Composio:
    """Get Composio client (uses COMPOSIO_API_KEY env var)."""
    return Composio()


def _get_user_id_for_account(client: Composio, connected_account_id: str) -> Optional[str]:
    """Look up user_id for a connected account."""
    if connected_account_id in _user_id_cache:
        return _user_id_cache[connected_account_id]

    try:
        accounts = client.connected_accounts.list()
        for item in accounts.items:
            if item.id == connected_account_id:
                _user_id_cache[connected_account_id] = item.user_id
                return item.user_id
    except Exception as e:
        log.warning("failed_to_get_user_id", error=str(e))

    return None


async def send_new_email(
    to: str,
    subject: str,
    body: str,
    from_name: str = "Chris",
    connected_account_id: Optional[str] = None
) -> dict:
    """Send a new email (not a reply).

    Returns dict with thread_id and message_id.
    """
    log.info("sending_new_email", to=to, subject=subject, connected_account_id=connected_account_id)

    client = _get_client()

    params = {
        "recipient_email": to,
        "subject": subject,
        "body": body,
    }

    execute_kwargs = {
        "slug": "GMAIL_SEND_EMAIL",
        "arguments": params,
        "dangerously_skip_version_check": True,
    }
    if connected_account_id:
        execute_kwargs["connected_account_id"] = connected_account_id
        user_id = _get_user_id_for_account(client, connected_account_id)
        if user_id:
            execute_kwargs["user_id"] = user_id

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: client.tools.execute(**execute_kwargs)
    )

    # Handle both object and dict responses
    successful = result.successful if hasattr(result, 'successful') else result.get("successful", False)
    data = result.data if hasattr(result, 'data') else result.get("data", {})
    error = result.error if hasattr(result, 'error') else result.get("error")

    if successful:
        data = data or {}
        return {
            "thread_id": data.get("threadId"),
            "message_id": data.get("id"),
        }
    else:
        error_msg = error or "Unknown error"
        log.error("send_failed", error=error_msg)
        raise Exception(f"Failed to send email: {error_msg}")


async def send_reply_email(
    to: str,
    subject: str,
    body: str,
    thread_id: str,
    message_id: str,
    from_name: str = "Chris",
    connected_account_id: Optional[str] = None
) -> dict:
    """Send a reply email (in existing thread).

    Returns dict with thread_id and message_id.
    """
    log.info("sending_reply_email", to=to, subject=subject, thread_id=thread_id)

    client = _get_client()

    params = {
        "thread_id": thread_id,
        "message_id": message_id,
        "to": to,
        "subject": subject,
        "body": body,
        "from_name": from_name,
    }

    execute_kwargs = {
        "slug": "GMAIL_REPLY_TO_THREAD",
        "arguments": params,
        "dangerously_skip_version_check": True,
    }
    if connected_account_id:
        execute_kwargs["connected_account_id"] = connected_account_id
        user_id = _get_user_id_for_account(client, connected_account_id)
        if user_id:
            execute_kwargs["user_id"] = user_id

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: client.tools.execute(**execute_kwargs)
    )

    # Handle both object and dict responses
    successful = result.successful if hasattr(result, 'successful') else result.get("successful", False)
    data = result.data if hasattr(result, 'data') else result.get("data", {})
    error = result.error if hasattr(result, 'error') else result.get("error")

    if successful:
        data = data or {}
        return {
            "thread_id": data.get("threadId"),
            "message_id": data.get("id"),
        }
    else:
        error_msg = error or "Unknown error"
        log.error("reply_failed", error=error_msg)
        raise Exception(f"Failed to send reply: {error_msg}")


async def get_thread_messages(
    thread_id: str,
    connected_account_id: Optional[str] = None
) -> list[dict]:
    """Get all messages in a thread.

    Returns list of message dicts.
    """
    log.info("fetching_thread", thread_id=thread_id)

    client = _get_client()

    execute_kwargs = {
        "slug": "GMAIL_FETCH_MESSAGE_BY_THREAD_ID",
        "arguments": {"thread_id": thread_id},
        "dangerously_skip_version_check": True,
    }
    if connected_account_id:
        execute_kwargs["connected_account_id"] = connected_account_id
        user_id = _get_user_id_for_account(client, connected_account_id)
        if user_id:
            execute_kwargs["user_id"] = user_id

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: client.tools.execute(**execute_kwargs)
    )

    # Handle both object and dict responses
    successful = result.successful if hasattr(result, 'successful') else result.get("successful", False)
    data = result.data if hasattr(result, 'data') else result.get("data", {})
    error = result.error if hasattr(result, 'error') else result.get("error")

    if successful:
        data = data or {}
        # Handle different response formats
        if isinstance(data, list):
            return data
        return data.get("messages", data.get("items", []))
    else:
        error_msg = error or "Unknown error"
        log.error("fetch_thread_failed", error=error_msg)
        raise Exception(f"Failed to fetch thread: {error_msg}")


async def check_for_reply(
    thread_id: str,
    our_message_count: int,
    connected_account_id: Optional[str] = None
) -> bool:
    """Check if there are more messages in thread than we sent.

    Returns True if recipient replied.
    """
    messages = await get_thread_messages(thread_id, connected_account_id)

    # If there are more messages than we sent, they replied
    return len(messages) > our_message_count
