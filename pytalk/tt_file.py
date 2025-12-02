"""Provides file-related classes for pytalk."""

from typing import TYPE_CHECKING, cast

from ._utils import (
    _get_tt_obj_attribute,
    _set_tt_obj_attribute,
)
from .implementation.TeamTalkPy import TeamTalk5 as sdk

if TYPE_CHECKING:
    from .instance import TeamTalkInstance


class RemoteFile:
    """Represents a remote file on a TeamTalk server."""

    def __init__(self, teamtalk: "TeamTalkInstance", file: sdk.RemoteFile) -> None:
        """Initialize a RemoteFile object.

        Args:
            teamtalk: The pytalk.TeamTalkInstance instance.
            file: The underlying sdk.RemoteFile object.

        """
        self.teamtalk = teamtalk
        self.payload = file
        self.channel_id: int = file.nChannelID
        self.file_id: int = file.nFileID

    def delete(self) -> None:
        """Delete the remote file."""
        self.teamtalk.delete_file_by_id(self.channel_id, self.file_id)

    def download(self, filepath: str) -> None:
        """Download the remote file.

        Args:
            filepath: The path to save the file to.

        """
        self.teamtalk.download_file_by_id(self.channel_id, self.file_id, filepath)

    def __getattr__(self, name: str) -> object:
        """Dynamically retrieve attributes from the underlying SDK payload.

        Args:
            name: The name of the attribute to retrieve.

        Returns:
            The value of the attribute.

        Raises:
            AttributeError: If the attribute does not exist.

        """
        if name in dir(self):
            return self.__dict__[name]
        value = _get_tt_obj_attribute(self.payload, name)
        if isinstance(value, (bytes, sdk.TTCHAR, sdk.TTCHAR_P)):
            return sdk.ttstr(cast("sdk.TTCHAR_P", value))
        return value


class FileTransfer:
    """Represents a file transfer in progress."""

    def __init__(self, teamtalk: "TeamTalkInstance", payload: sdk.FileTransfer) -> None:
        """Initialize a FileTransfer object.

        Args:
            teamtalk: The TeamTalkInstance this transfer belongs to.
            payload: The underlying sdk.FileTransfer object.

        """
        self.teamtalk = teamtalk
        self.payload = payload

    @property
    def transferred(self) -> int:
        """The number of bytes transferred so far."""
        return cast("int", self.payload.nTransferred)

    @property
    def file_size(self) -> int:
        """The total size of the file in bytes."""
        return cast("int", self.payload.nFileSize)

    @property
    def status(self) -> int:
        """The status of the file transfer."""
        return cast("int", self.payload.nStatus)

    @property
    def transfer_id(self) -> int:
        """The ID of the file transfer."""
        return cast("int", self.payload.nTransferID)

    def __repr__(self) -> str:
        """Return a string representation of the FileTransfer object."""
        return (
            f"<FileTransfer id={self.transfer_id} "
            f"status={self.status} "
            f"transferred={self.transferred}/{self.file_size}>"
        )

    def __eq__(self, other: object) -> bool:
        """Check if two FileTransfer objects are equal."""
        if not isinstance(other, FileTransfer):
            return NotImplemented
        return self.transfer_id == other.transfer_id

    def __hash__(self) -> int:
        """Return the hash of the FileTransfer object."""
        return hash(self.transfer_id)

    def __getattr__(self, name: str) -> object:
        """Dynamically retrieve attributes from the underlying SDK payload.

        Args:
            name: The name of the attribute to retrieve.

        Returns:
            The value of the attribute.

        Raises:
            AttributeError: If the attribute does not exist.

        """
        if name in dir(self):
            return self.__dict__[name]
        value = _get_tt_obj_attribute(self.payload, name)
        if isinstance(value, (bytes, sdk.TTCHAR, sdk.TTCHAR_P)):
            return sdk.ttstr(cast("sdk.TTCHAR_P", value))
        return value

    def __setattr__(self, name: str, value: object) -> None:
        """Dynamically set attributes on the underlying SDK payload.

        Args:
            name: The name of the attribute to set.
            value: The value to set.

        Raises:
            AttributeError: If the attribute does not exist.

        """
        if name in dir(self) or name == "payload":
            self.__dict__[name] = value
        else:
            _get_tt_obj_attribute(self.payload, name)  # Check if attribute exists
            _set_tt_obj_attribute(self.payload, name, value)
