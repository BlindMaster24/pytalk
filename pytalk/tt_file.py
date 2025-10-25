"""Teamtalk file object."""

from typing import TYPE_CHECKING

from ._utils import _get_tt_obj_attribute

if TYPE_CHECKING:
    from .instance import TeamTalkInstance


class RemoteFile:
    """Represents a file on a TeamTalk server. Should not be instantiated directly."""

    def __init__(self, teamtalk_instance: "TeamTalkInstance", payload: object) -> None:
        """Initialize the RemoteFile instance.

        Args:
            teamtalk_instance: The pytalk.TeamTalkInstance instance.
            payload: An instance of sdk.RemoteFile.

        """
        self.teamtalk = teamtalk_instance
        self.channel = lambda self: self.teamtalk.get_channel(payload.nChannelID)
        self.server = lambda self: self.teamtalk.server
        self.payload = payload

    def __str__(self) -> str:
        """Return a string representation of the RemoteFile instance.

        Returns:
            A string representation of the RemoteFile instance.

        """
        return f"Pytalk.RemoteFile(file_name={self.file_name}, file_id={self.file_id}, file_size={self.file_size}, username={self.username}, upload_time={self.upload_time})"  # noqa: E501

    def __getattr__(self, name: str) -> object:
        """Return the value of the specified attribute of the remote file.

        Args:
            name: The name of the attribute.

        Returns:
            The value of the specified attribute.

        Raises:
            AttributeError: If the specified attribute is not found. # noqa

        """
        if name in dir(self):
            return self.__dict__[name]
        return _get_tt_obj_attribute(self.payload, name)
