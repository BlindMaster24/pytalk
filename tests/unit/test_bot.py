import asyncio
import pytest
from unittest.mock import AsyncMock

from pytalk.bot import TeamTalkBot


@pytest.mark.asyncio
async def test_event_dispatch():
    """Test that the bot correctly dispatches an event to a registered handler."""
    bot = TeamTalkBot("!")
    mock_handler = AsyncMock()
    mock_handler.__name__ = "test_event"

    # Register the handler
    bot.event(mock_handler)

    # Dispatch the event
    bot.dispatch("test_event", "arg1", kwarg="kwarg1")

    # Yield control to the event loop to allow the task to run
    await asyncio.sleep(0)

    # Assert the handler was called
    mock_handler.assert_called_once_with("arg1", kwarg="kwarg1")


def test_dispatch_unknown_event():
    """Test that dispatching an unknown event does not raise an error."""
    bot = TeamTalkBot("!")
    try:
        bot.dispatch("non_existent_event")
    except Exception as e:
        pytest.fail(f"Dispatching an unknown event raised an exception: {e}")