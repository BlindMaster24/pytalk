"""Channel module for pytalk."""

from typing import TYPE_CHECKING, Any, cast

from ._utils import _get_tt_obj_attribute, _set_tt_obj_attribute, _wait_for_cmd
from .codec import AudioCodecConfig
from .exceptions import PytalkPermissionError
from .implementation.TeamTalkPy import TeamTalk5 as sdk

if TYPE_CHECKING:
    from .instance import TeamTalkInstance
from .permission import Permission
from .subscription import Subscription
from .tt_file import RemoteFile
from .user import User as TeamTalkUser


class Channel:
    """Represents a channel on a TeamTalk server."""

    def __init__(
        self, teamtalk: "TeamTalkInstance", channel: int | sdk.Channel
    ) -> None:
        """Initialize a Channel object.

        Args:
            teamtalk: The pytalk.TeamTalkInstance instance.
            channel (Union[int, sdk.Channel]): The channel ID or a sdk.Channel object.

        """
        self.teamtalk = teamtalk
        if isinstance(channel, int):
            self.id = channel
            self._channel, self.path = self.teamtalk._get_channel_info(self.id)

        elif isinstance(channel, sdk.Channel):
            self._channel = channel
            self.id = channel.nChannelID
            self._channel, self.path = self.teamtalk._get_channel_info(self.id)
        self.server = self.teamtalk.server
        self._audiocfg = AudioCodecConfig(self._channel.audiocfg)

    @property
    def audiocfg(self) -> AudioCodecConfig:
        """The audio codec configuration for the channel."""
        return self._audiocfg

    @property
    def disk_quota(self) -> int:
        """The disk quota for files in the channel."""
        return cast("int", self._channel.nDiskQuota)

    @disk_quota.setter
    def disk_quota(self, value: int) -> None:
        self._channel.nDiskQuota = value

    @property
    def max_users(self) -> int:
        """The maximum number of users allowed in the channel."""
        return cast("int", self._channel.nMaxUsers)

    @max_users.setter
    def max_users(self, value: int) -> None:
        self._channel.nMaxUsers = value

    @property
    def timeout_media_file_msec(self) -> int:
        """Timeout for media file transmission in milliseconds."""
        return cast("int", self._channel.nTimeOutTimerMediaFileMSec)

    @timeout_media_file_msec.setter
    def timeout_media_file_msec(self, value: int) -> None:
        self._channel.nTimeOutTimerMediaFileMSec = value

    @property
    def timeout_voice_msec(self) -> int:
        """Timeout for voice transmission in milliseconds."""
        return cast("int", self._channel.nTimeOutTimerVoiceMSec)

    @timeout_voice_msec.setter
    def timeout_voice_msec(self, value: int) -> None:
        self._channel.nTimeOutTimerVoiceMSec = value

    @property
    def op_password(self) -> str:
        """The operator password for the channel."""
        return sdk.ttstr(cast("sdk.TTCHAR_P", self._channel.szOpPassword))

    @op_password.setter
    def op_password(self, value: str) -> None:
        self._channel.szOpPassword = sdk.ttstr(cast("sdk.TTCHAR_P", value))

    @property
    def user_data(self) -> int:
        """User-defined data associated with the channel."""
        return cast("int", self._channel.nUserData)

    @user_data.setter
    def user_data(self, value: int) -> None:
        self._channel.nUserData = value

    def update(self) -> bool:
        """Update the channel information.

        Example:
            >>> channel = teamtalk.get_channel(1)
            >>> channel.name = "New Channel Name"
            >>> channel.update()

        Raises:
            PytalkPermissionError: If the bot does not have permission
                to update the channel.
            ValueError: If the channel could not be updated.

        Returns:
            bool: True if the channel was updated successfully.

        """
        if not self.teamtalk.has_permission(
            cast("int", Permission.MODIFY_CHANNELS)
        ) or not sdk._IsChannelOperator(
            self.teamtalk._tt, self.teamtalk.getMyUserID(), self.id
        ):
            raise PytalkPermissionError(
                "the bot does not have permission to update the channel."
            )
        # Ensure changes to audiocfg and videocodec objects are reflected in _channel
        self._channel.audiocfg = self._audiocfg.payload

        result = sdk._DoUpdateChannel(self.teamtalk._tt, self._channel)
        if result == -1:
            raise ValueError("Channel could not be updated")
        cmd_result, cmd_err = _wait_for_cmd(self.teamtalk, result, 2000)
        if not cmd_result:
            err_nr = cmd_err.nErrorNo
            if err_nr == sdk.ClientError.CMDERR_NOT_LOGGEDIN:
                raise PytalkPermissionError("The bot is not logged in")
            if err_nr == sdk.ClientError.CMDERR_NOT_AUTHORIZED:
                raise PytalkPermissionError(
                    "The bot does not have permission to update channels"
                )
            if err_nr == sdk.ClientError.CMDERR_CHANNEL_NOT_FOUND:
                raise ValueError("Channel could not be found")
            if err_nr == sdk.ClientError.CMDERR_CHANNEL_ALREADY_EXISTS:
                raise ValueError("Channel already exists")
            if err_nr == sdk.ClientError.CMDERR_CHANNEL_HAS_USERS:
                raise ValueError("Channel has users and can therefore not be updated")
        return True

    def _refresh(self) -> None:
        self._channel, self.path = self.teamtalk._get_channel_info(self.id)

    async def send_message(self, content: str, **kwargs: Any) -> None:  # noqa: ANN401
        """Send a message to the channel.

        Args:
            content: The message to send.
            **kwargs: Keyword arguments. See pytalk.TeamTalkInstance.send_message for
                more information.

        Raises:
            PytalkPermissionError: If the bot is not in the channel and is not an admin.

        """
        if self.teamtalk.getMyChannelID() != self.id and not self.teamtalk.is_admin():
            raise PytalkPermissionError(
                "Missing permission to send message to a channel the bot is not in"
            )
        msg = sdk.TextMessage()
        msg.nMsgType = sdk.TextMsgType.MSGTYPE_CHANNEL
        msg.nFromUserID = self.teamtalk.getMyUserID()
        msg.szFromUsername = self.teamtalk.getMyUserAccount().szUsername
        msg.nChannelID = self.id
        msg.szMessage = sdk.ttstr(content)  # type: ignore [arg-type]
        msg.bMore = False
        await self.teamtalk._send_message(msg, **kwargs)

    def upload_file(self, filepath: str) -> None:
        """Upload a file to the channel.

        Args:
            filepath (str): The local path to the file to upload.

        """
        self.teamtalk.upload_file(self.id, filepath)

    def get_users(self) -> list[TeamTalkUser]:
        """Get a list of users in the channel.

        Returns:
            List[TeamTalkUser]: A list of pytalk.User instances in the channel.

        """
        users = self.teamtalk.getChannelUsers(self.id)
        return [TeamTalkUser(self.teamtalk, user) for user in users]

    def get_files(self) -> list[RemoteFile]:
        """Get a list of files in the channel.

        Returns:
            List[RemoteFile]: A list of pytalk.RemoteFile instances in the channel.

        """
        files = self.teamtalk.getChannelFiles(self.id)
        return [RemoteFile(self.teamtalk, f) for f in files]

    def move(self, user: TeamTalkUser | int) -> None:
        """Move a user to this channel.

        Args:
            user: The user to move.

        """
        self.teamtalk.move_user(user, self)

    def kick(self, user: TeamTalkUser | int) -> None:
        """Kick a user from this channel.

        Args:
            user: The user to kick.

        """
        self.teamtalk.kick_user(user, self)

    def ban(self, user: TeamTalkUser | int) -> None:
        """Ban a user from this channel.

        Args:
            user: The user to ban.

        """
        self.teamtalk.ban_user(user, self)

    def subscribe(self, subscription: Subscription) -> None:
        """Subscribe to a subscription for all users in this channel.

        Args:
            subscription: The subscription to subscribe to.

        """
        users = self.get_users()
        for user in users:
            user.subscribe(subscription)

    def unsubscribe(self, subscription: Subscription) -> None:
        """Unsubscribe from a subscription for all users in this channel.

        Args:
            subscription: The subscription to unsubscribe from.

        """
        users = self.get_users()
        for user in users:
            user.unsubscribe(subscription)

    def __getattr__(self, name: str) -> object:
        """Try to get the attribute from the channel object.

        Args:
            name: The name of the attribute.

        Raises:
            AttributeError: If the specified attribute is not found.
                This is the default behavior. # noqa

        """
        if name in dir(self):
            return self.__dict__[name]
        value = _get_tt_obj_attribute(self._channel, name)
        if isinstance(value, (bytes, sdk.TTCHAR, sdk.TTCHAR_P)):
            return sdk.ttstr(cast("sdk.TTCHAR_P", value))
        return value

    def __setattr__(self, name: str, value: object) -> None:
        """Try to set the specified attribute.

        Args:
            name: The name of the attribute.
            value: The value to set the attribute to.

        Raises:
            AttributeError: If the specified attribute is not found.
                This is the default behavior. # noqa

        """
        if name in dir(self) or name in [
            "teamtalk",
            "id",
            "server",
            "path",
            "_channel",
            "_audiocfg",
        ]:
            self.__dict__[name] = value
        else:
            _get_tt_obj_attribute(self._channel, name)
            _set_tt_obj_attribute(self._channel, name, value)


class _ChannelTypeMeta(type):
    def __getattr__(cls, name: str) -> int:
        name = f"CHANNEL_{name}"
        value = getattr(sdk.ChannelType, name, None)
        if value is None:
            raise AttributeError(f"'{cls.__name__}' object has no attribute '{name}'")
        return cast("int", value)

    def __dir__(cls) -> list[str]:
        return [
            attr[8:] for attr in dir(sdk.ChannelType) if attr.startswith("CHANNEL_")
        ]


class ChannelType(metaclass=_ChannelTypeMeta):
    """A class representing Channel types in TeamTalk."""
