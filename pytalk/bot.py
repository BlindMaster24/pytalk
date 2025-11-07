"""A module that contains the TeamTalkBot class.

The TeamTalkBot class is the main class of the library.
It's used to create a bot,connect to any amount of TeamTalk servers and dispatch events.
"""

import asyncio
import contextlib
import logging
import sys
import types
from collections.abc import Callable, Coroutine
from typing import Any, Self, TypeVar

if sys.platform.startswith("linux"):
    import uvloop

from .enums import TeamTalkServerInfo
from .instance import TeamTalkInstance

T = TypeVar("T")
Coro = Coroutine[Any, Any, T]
CoroT = TypeVar("CoroT", bound=Callable[..., Coro[Any]])


class _LoopSentinel:
    __slots__ = ()

    def __getattr__(self, attr: str) -> None:
        msg = "loop attribute cannot be accessed in non-async contexts. "
        raise AttributeError(msg)


_loop: Any = _LoopSentinel()
_log = logging.getLogger(__name__)


class TeamTalkBot:
    """A class that represents a TeamTalk bot."""

    def __init__(self, client_name: str | None = "PyTalk") -> None:
        """Initialize a TeamTalkBot object.

        Args:
            client_name (Optional[str]): The name of the client. Defaults to
                "Teamtalk.py".

        """
        self.client_name = client_name
        self.loop: asyncio.AbstractEventLoop = _loop
        self.teamtalks: list[TeamTalkInstance] = []
        self._listeners: dict[
            str, list[tuple[asyncio.Future[Any], Callable[..., bool]]]
        ] = {}

    async def add_server(
        self,
        server: TeamTalkServerInfo | dict[str, Any],
        reconnect: bool = True,
        backoff_config: dict[str, Any] | None = None,
        auto_login: bool | None = None,
    ) -> None:
        """Add a server to the bot.

        Args:
            server: A Union[TeamTalkServerInfo, dict] object representing the server to
                add.
                If a dictionary is provided, it will be converted to a
                TeamTalkServerInfo object.
            reconnect (bool): Whether to automatically reconnect to the server if the
                connection is lost. Defaults to True.
            backoff_config (Optional[dict]): Optional dictionary to customize backoff
                behavior.
                Can contain keys: `base`, `exponent`, `max_value`, `max_tries`.
                These settings govern the retry behavior for both the initial
                connection sequence and for reconnections after a connection loss.
            auto_login (Optional[bool]): Whether to automatically log in to the
                server. ``None`` (default) defers to ``server.auto_login``.

        """
        if isinstance(server, dict):
            server = TeamTalkServerInfo.from_dict(server)
        _log.debug("Adding server: %s, %s", self, server)
        tt = TeamTalkInstance(self, server, reconnect, backoff_config, auto_login)
        successful_initial_connection = await tt.initial_connect_loop()
        if not successful_initial_connection:
            _log.error(
                "Failed to establish initial connection to server %s:%s "
                "after multiple retries. "
                "Instance will be added but may not be usable.",
                server.host,
                server.tcp_port,
            )
        self.teamtalks.append(tt)

    def run(self) -> None:
        """Connect to all added servers and handle all events."""
        if sys.platform.startswith("linux"):
            try:
                uvloop.install()
                _log.info("Using uvloop as the event loop policy.")
            except (ImportError, NameError):
                pass

        async def runner() -> None:
            async with self:
                await self._start()

        try:
            asyncio.run(runner())
        except KeyboardInterrupt:
            return

    async def _async_setup_hook(self) -> None:
        loop = asyncio.get_running_loop()
        self.loop = loop

    async def __aenter__(self) -> Self:
        """Get the correct event loop.

        Returns:
            Self: The TeamTalkBot object.

        """
        await self._async_setup_hook()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        """When we exit the program, try to disconnect from all servers.

        Args:
            exc_type (Optional[Type[BaseException]]): The exception type.
            exc_value (Optional[BaseException]): The exception value.
            traceback: The traceback.

        """
        for teamtalk in self.teamtalks:
            teamtalk.disconnect()
            teamtalk.closeTeamTalk()

    def event(self, coro: CoroT, /) -> CoroT:
        """Register an event to listen to.

        The events must be a :ref:`coroutine <coroutine>`, if not,
        :exc:`TypeError` is raised.

        Example:
        -------

        .. code-block:: python3

            @client.event
            async def on_ready():
                print('Ready!')

        See the :doc:`event Reference </events>` for more information
        and a list of all events.


        Args:
            coro (CoroT): The coroutine to register.

        Returns:
            CoroT: The coroutine that was registered.

        Raises:
            TypeError: The coroutine is not a coroutine function.

        """
        _log.debug("Registering event %s", coro.__name__)

        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("event registered must be a coroutine function")

        setattr(self, coro.__name__, coro)
        _log.debug("Registered event %s", coro.__name__)
        return coro

    async def _run_event(
        self,
        coro: Callable[..., Coroutine[Any, Any, Any]],
        event_name: str,
        *args: object,
        **kwargs: object,
    ) -> None:
        try:
            _log.debug("Running event %s", event_name)
            await coro(*args, **kwargs)
        except asyncio.CancelledError:
            _log.debug("Event %s was cancelled", event_name)
        except Exception:  # noqa: BLE001
            with contextlib.suppress(asyncio.CancelledError):
                await self.on_error(event_name, *args, **kwargs)

    def _schedule_event(
        self,
        coro: Callable[..., Coroutine[Any, Any, Any]],
        event_name: str,
        *args: object,
        **kwargs: object,
    ) -> asyncio.Task[Any]:
        wrapped = self._run_event(coro, event_name, *args, **kwargs)
        return self.loop.create_task(wrapped, name=f"teamtalk.py: {event_name}")

    async def on_error(
        self,
        event_method: str,
        /,
        *args: object,  # noqa: ARG002
        **kwargs: object,  # noqa: ARG002
    ) -> None:
        """|coro| .

        The default error handler provided by the client.

        By default this logs to the library logger however it could be
        overridden to have a different implementation.
        The traceback from this exception is logged to the logging module.

        Args:
            event_method (str): The event method that errored.
            *args (Any): The arguments to the event.
            **kwargs (Any): The keyword arguments to the event.

        """
        _log.exception("Ignoring exception in %s", event_method)

    def dispatch(self, event: str, /, *args: object, **kwargs: object) -> None:  # noqa: C901, PLR0912
        """Dispatch an event to all listeners. This is called internally.

        Args:
            event (str): The name of the event to dispatch.
            *args (Any): The arguments to the event.
            **kwargs (Any): The keyword arguments to the event.

        """
        _log.debug("Dispatching event %s", event)
        method = "on_" + event

        listeners = self._listeners.get(event)
        if listeners:
            removed = []
            for i, (future, condition) in enumerate(listeners):
                if future.cancelled():
                    removed.append(i)
                    continue

                try:
                    result = condition(*args)
                except Exception as exc:  # noqa: BLE001
                    future.set_exception(exc)
                    removed.append(i)
                else:
                    if result:
                        if len(args) == 0:
                            future.set_result(None)
                        elif len(args) == 1:
                            future.set_result(args[0])
                        else:
                            future.set_result(args)
                        removed.append(i)

            if len(removed) == len(listeners):
                self._listeners.pop(event)
            else:
                for idx in reversed(removed):
                    del listeners[idx]

        try:
            coro = getattr(self, method)
        except AttributeError:
            pass
        else:
            self._schedule_event(coro, method, *args, **kwargs)

    async def _start(self) -> None:
        self.dispatch("ready")
        try:
            while True:
                for teamtalk in self.teamtalks:
                    await teamtalk._process_events()
                await asyncio.sleep(0.001)
        except KeyboardInterrupt:
            for teamtalk in self.teamtalks:
                teamtalk.doLogout()
                self.dispatch("my_logout", teamtalk.server)
                teamtalk.disconnect()
                self.dispatch("my_disconnect", teamtalk.server)

    async def _do_after_delay(self, delay: float, func: Callable[..., Any]) -> None:  # noqa: ARG002
        await asyncio.sleep(delay)
        print("WORKS")
