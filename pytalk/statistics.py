"""Server statistics module for Teamtalk."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._utils import _get_tt_obj_attribute

if TYPE_CHECKING:
    from .implementation.TeamTalkPy import TeamTalk5 as sdk
    from .instance import TeamTalkInstance


class Statistics:
    """represents the statistics of a TeamTalk server."""

    def __init__(
        self, teamtalk: TeamTalkInstance, statistics: sdk.ServerStatistics
    ) -> None:
        """Initialize a statistics object.

        Args:
            teamtalk: The pytalk.TeamTalkInstance instance.
            statistics (sdk.ServerStatistics): The sdk.ServerStatistics object.

        """
        self.teamtalk = teamtalk
        self.server = teamtalk.server
        self._statistics = statistics

    def __getattr__(self, name: str) -> object:
        """Try to get the attribute from the ServerStatistics object.

        Args:
            name: The name of the attribute.

        Returns:
            The value of the specified attribute.

        Raises:
            AttributeError: If the specified attribute is not found. This is the
                default behavior. # noqa

        """
        if name in dir(self):
            return self.__dict__[name]
        return _get_tt_obj_attribute(self._statistics, name)

    def refresh(self) -> None:
        """Refresh the server statistics."""
        self._statistics = self.teamtalk.get_server_statistics()._statistics
