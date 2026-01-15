"""Gmail sending via Composio."""

import asyncio
from typing import Optional

import structlog
from composio import ComposioToolSet, Action

log = structlog.get_logger()


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
    log.info("sending_new_email", to=to, subject=subject)

    toolset = ComposioToolSet()

    # Build execute_action kwargs
    execute_kwargs = {
        "action": Action.GMAIL_SEND_EMAIL,
        "params": {
            "to": to,
            "subject": subject,
            "body": body,
            "from_name": from_name,
        }
    }
    if connected_account_id:
        execute_kwargs["connected_account_id"] = connected_account_id

    # Run in executor since Composio is sync
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: toolset.execute_action(**execute_kwargs)
    )

    data = result.get("data", {})

    return {
        "thread_id": data.get("threadId"),
        "message_id": data.get("id"),
    }


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

    toolset = ComposioToolSet()

    execute_kwargs = {
        "action": Action.GMAIL_REPLY_TO_THREAD,
        "params": {
            "thread_id": thread_id,
            "message_id": message_id,
            "to": to,
            "subject": subject,
            "body": body,
            "from_name": from_name,
        }
    }
    if connected_account_id:
        execute_kwargs["connected_account_id"] = connected_account_id

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: toolset.execute_action(**execute_kwargs)
    )

    data = result.get("data", {})

    return {
        "thread_id": data.get("threadId"),
        "message_id": data.get("id"),
    }


async def get_thread_messages(
    thread_id: str,
    connected_account_id: Optional[str] = None
) -> list[dict]:
    """Get all messages in a thread.

    Returns list of message dicts.
    """
    log.info("fetching_thread", thread_id=thread_id)

    toolset = ComposioToolSet()

    execute_kwargs = {
        "action": Action.GMAIL_GET_THREAD,
        "params": {"thread_id": thread_id}
    }
    if connected_account_id:
        execute_kwargs["connected_account_id"] = connected_account_id

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: toolset.execute_action(**execute_kwargs)
    )

    data = result.get("data", {})
    messages = data.get("messages", [])

    return messages


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
