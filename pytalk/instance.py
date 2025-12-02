"""Module contains the TeamTalkInstance class.

The TeamTalkInstance class contains one instance of a connection to a TeamTalkServer.
It is used to send and receive messages, join and leave channels,
and perform other actions.
In addition, it's also here that events are dispatched.
"""

from __future__ import annotations

import asyncio
import ctypes
import logging
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Callable

from ._utils import (
    _do_after,
    _wait_for_cmd,
    _wait_for_event,
    percent_to_ref_volume,
    ref_volume_to_percent,
)
from .audio import (
    AudioBlock,
    MuxedAudioBlock,
    _AcquireUserAudioBlock,
    _ReleaseUserAudioBlock,
)
from .backoff import Backoff, BackoffConfig

if TYPE_CHECKING:
    from .bot import TeamTalkBot
from .channel import Channel as TeamTalkChannel
from .channel import ChannelType
from .codec import AudioCodecConfig, CodecType
from .device import SoundDevice
from .enums import Status, TeamTalkServerInfo, UserType
from .exceptions import PytalkPermissionError, TeamTalkError
from .implementation.TeamTalkPy import TeamTalk5 as sdk
from .message import (
    BroadcastMessage,
    ChannelMessage,
    CustomMessage,
    DirectMessage,
    Message,
)
from .permission import Permission
from .server import Server as TeamTalkServer
from .statistics import Statistics as TeamTalkServerStatistics
from .tt_file import FileTransfer, RemoteFile

if TYPE_CHECKING:
    from .subscription import Subscription
from .user import User as TeamTalkUser
from .user_account import BannedUserAccount as TeamTalkBannedUserAccount
from .user_account import UserAccount as TeamTalkUserAccount

DEFAULT_SOUND_DEVICE_COUNT = 2
PERCENTAGE_MIN = 0
PERCENTAGE_MAX = 100

_log = logging.getLogger(__name__)


class TeamTalkInstance(sdk.TeamTalk):
    """Represents a TeamTalk5 instance."""

    def __init__(
        self,
        bot: TeamTalkBot,
        server_info: TeamTalkServerInfo,
        reconnect: bool = True,
        backoff_config: BackoffConfig | dict[str, Any] | None = None,
    ) -> None:
        """Initialize a pytalk.TeamTalkInstance instance.

        Args:
            bot: The pytalk.Bot instance.
            server_info: The server info for the server we wish to connect to.
            reconnect (bool): Whether to automatically reconnect to the server if the
                connection is lost. Defaults to True.
            backoff_config (Optional[Union[BackoffConfig, dict]]): Configuration for the
                exponential backoff. Can be a BackoffConfig object or a dictionary
                with keys like `base`, `exponent`, `max_value`, `max_tries`,
                `jitter_type`.
                Defaults to `None` (using default BackoffConfig settings).

        """
        super().__init__()
        self.bot = bot
        self.server_info = server_info
        self.server = TeamTalkServer(self, server_info)
        self.channel = lambda: self.get_channel(self.getMyChannelID())
        self.connected = False
        self.logged_in = False
        self.init_time = time.time()
        self.user_accounts: list[TeamTalkUserAccount] = []
        self.banned_users: list[TeamTalkBannedUserAccount] = []
        self._current_input_device_id: int | None = -1
        self._audio_sdk_lock = threading.Lock()
        self.reconnect_enabled = reconnect
        self._file_transfer_callbacks: dict[int, Callable[[FileTransfer], None]] = {}

        if isinstance(backoff_config, dict):
            self._backoff = Backoff(config=BackoffConfig(**backoff_config))
        elif isinstance(backoff_config, BackoffConfig):
            self._backoff = Backoff(config=backoff_config)
        else:
            self._backoff = Backoff()

    def connect(self, *_args: Any, **_kwargs: Any) -> bool:  # noqa: ANN401
        """Make a single synchronous attempt to connect to the server.

        Waits for a success or failure event from the SDK for this attempt.

        Returns:
            bool: True if the connection was successful, False otherwise.

        """
        if not super().connect(
            sdk.ttstr(self.server_info.host),  # type: ignore [arg-type]
            self.server_info.tcp_port,
            self.server_info.udp_port,
            bEncrypted=self.server_info.encrypted,
        ):
            return False
        result, msg = _wait_for_event(
            self, cast("sdk.ClientEvent", sdk.ClientEvent.CLIENTEVENT_CON_SUCCESS)
        )
        if not result:
            return False

        if msg.nClientEvent == sdk.ClientEvent.CLIENTEVENT_CON_SUCCESS:
            self.bot.dispatch("my_connect", self)
            self.connected = True
            self.init_time = time.time()
            return True
        if msg.nClientEvent == sdk.ClientEvent.CLIENTEVENT_CON_FAILED:
            self.bot.dispatch("my_connect_failed", self)
            return False
        if msg.nClientEvent == sdk.ClientEvent.CLIENTEVENT_CON_CRYPT_ERROR:
            self.bot.dispatch("my_connect_crypt_error", self)
            return False
        return False

    def login(self, join_channel_on_login: bool = True) -> bool:
        """Make a single synchronous attempt to log in to the server.

        Waits for a success or failure event from the SDK for this attempt.

        Args:
            join_channel_on_login: Whether to join the channel on login or not.

        Returns:
            bool: True if the login was successful, False otherwise.

        """
        super().doLogin(
            sdk.ttstr(self.server_info.nickname),  # type: ignore [arg-type]
            sdk.ttstr(self.server_info.username),  # type: ignore [arg-type]
            sdk.ttstr(self.server_info.password),
            sdk.ttstr(self.bot.client_name),  # type: ignore [arg-type]
        )
        result, msg = _wait_for_event(
            self,
            cast("sdk.ClientEvent", sdk.ClientEvent.CLIENTEVENT_CMD_MYSELF_LOGGEDIN),
        )
        if not result:
            return False
        self.bot.dispatch("my_login", self)
        self.logged_in = True

        if join_channel_on_login:
            channel_id_to_join = self.server_info.join_channel_id
            if channel_id_to_join > 0:  # Only join if channel_id is strictly positive
                self.join_channel_by_id(channel_id_to_join)
        self.init_time = time.time()
        return True

    def logout(self) -> None:
        """Log out of the server."""
        super().doLogout()
        self.logged_in = False

    def disconnect(self) -> None:
        """Disconnects from the server."""
        super().disconnect()
        self.connected = False

    async def force_reconnect(self) -> bool:
        """Manually forces a new attempt to connect and log in to the server.

        This method resets the backoff counter and then initiates the
        standard initial connection and login loop (`initial_connect_loop`).
        Useful if the instance has previously stopped trying to reconnect
        due to exhausting `max_tries` in its backoff configuration, or if
        a manual reconnection attempt is desired for other reasons.

        Note: If the instance is already connected and logged in, this
        will likely cause a disconnection before attempting to reconnect.
        Consider checking `self.connected` and `self.logged_in` before calling
        if a disconnect is not desired.

        Returns:
            bool: True if the reconnection and login were successful, False otherwise.

        """
        _log.info("Forcing reconnect attempt to %s...", self.server_info.host)
        if self.connected:
            _log.debug(
                "Force_reconnect: Instance to %s is currently "
                "connected. Disconnecting first.",
                self.server_info.host,
            )
            await self.bot.loop.run_in_executor(None, self.disconnect)
            self.connected = False
            self.logged_in = False

        return await self.initial_connect_loop()

    def change_nickname(self, nickname: str) -> None:
        """Change the nickname of the bot.

        Args:
            nickname: The new nickname.

        """
        super().doChangeNickname(sdk.ttstr(nickname))  # type: ignore [arg-type]

    def change_status(self, status_flags: int, status_message: str) -> None:
        """Change the status of the bot using combined status flags.

        This method allows setting the user's online mode (online, away, question)
        and gender simultaneously, while preserving other active status flags
        (like video/desktop transmission).

        Args:
            status_flags (int): A combined integer value representing the desired
                                  status mode and gender. This can be constructed
                                  using the `pytalk.enums.Status` helper class
                                  (e.g., `Status.online.female`).
            status_message (str): The status message to display.

        """
        current_user_obj = self.get_user(super().getMyUserID())
        current_full_status_mode = cast("int", current_user_obj.status_mode)

        new_mode_bits = status_flags & Status._MODE_MASK
        new_gender_bits = status_flags & Status._GENDER_MASK

        other_flags_mask = ~(Status._MODE_MASK | Status._GENDER_MASK)
        preserved_other_flags = current_full_status_mode & other_flags_mask

        final_status = new_mode_bits | new_gender_bits | preserved_other_flags

        super().doChangeStatus(final_status, sdk.ttstr(status_message))  # type: ignore [arg-type]

    def get_sound_devices(self) -> list[SoundDevice]:
        """Get the list of available TeamTalk sound devices, marking the default input.

        Returns:
            A list of SoundDevice objects representing the available devices.
            Returns an empty list if the SDK call fails.

        """
        default_in_id = -1
        try:
            defaults = super().getDefaultSoundDevices()
            if defaults:
                if (
                    isinstance(defaults, (tuple, list))
                    and len(defaults) == DEFAULT_SOUND_DEVICE_COUNT
                ):
                    default_in_id, _ = defaults
                else:
                    _log.warning(
                        "Unexpected return type from getDefaultSoundDevices: %s",
                        type(defaults),
                    )
            else:
                _log.warning(
                    "Call to getDefaultSoundDevices returned None or False for "
                    "instance %s",
                    self.server_info.host,
                )
        except Exception as e:  # noqa: BLE001
            _log.exception(
                "Error getting default sound devices for instance %s: %s",
                self.server_info.host,
                e,
            )

        sdk_devices = super().getSoundDevices()
        if not sdk_devices:
            _log.warning(
                "Failed to get sound device list via superclass for instance %s",
                self.server_info.host,
            )
            return []

        return [
            SoundDevice(dev, is_default_input=(dev.nDeviceID == default_in_id))
            for dev in sdk_devices
        ]

    def get_current_input_device_id(self) -> int | None:
        """Get the ID of the currently active input device for this instance.

        Note:
            This returns the ID that was stored when the input device was
            last initialized or set for this instance using set_input_device.
            It does not query the SDK directly for the current device.

        Returns:
            The ID of the current input device, or -1 if not set or unknown.

        """
        return self._current_input_device_id

    def set_input_device(self, device_id_or_name: int | str) -> bool:
        """Set and initialize the input device for this instance.

        Accepts a specific device ID (int) or the string "default" to use the
        system default input device.
        Updates the stored current input device ID on success.

        Args:
            device_id_or_name: The ID (int) of the device or the string "default".

        Returns:
            True on success, False on initialization failure or if default not found.

        Raises:
            ValueError: If the input is not a valid integer or "default".

        """
        target_device_id = -1

        if (
            isinstance(device_id_or_name, str)
            and device_id_or_name.lower() == "default"
        ):
            _log.debug(
                "Attempting to set default input device for instance %s",
                self.server_info.host,
            )
            try:
                defaults = super().getDefaultSoundDevices()
                if (
                    defaults
                    and isinstance(defaults, (tuple, list))
                    and len(defaults) == DEFAULT_SOUND_DEVICE_COUNT
                ):
                    target_device_id = defaults[0]
                    if target_device_id < 0:
                        _log.error(
                            "System returned invalid default input device ID (%s) for "
                            "instance %s",
                            target_device_id,
                            self.server_info.host,
                        )
                        return False
                    _log.info(
                        "Resolved 'default' to input device ID: %s",
                        target_device_id,
                    )
                else:
                    _log.error(
                        "Could not determine default input device for instance %s",
                        self.server_info.host,
                    )
                    return False
            except Exception as e:  # noqa: BLE001
                _log.exception(
                    "Error getting default sound devices when setting 'default': %s",
                    e,
                )
                return False
        else:
            try:
                target_device_id = int(device_id_or_name)
            except (ValueError, TypeError):
                raise ValueError(
                    "device_id_or_name must be an int or 'default', "
                    f"not {device_id_or_name}"
                ) from None

        _log.debug(
            "Setting input device for instance %s to ID: %s",
            self.server_info.host,
            target_device_id,
        )
        sdk._CloseSoundInputDevice(self._tt)
        success = sdk._InitSoundInputDevice(self._tt, target_device_id)

        if success:
            self._current_input_device_id = target_device_id
            _log.info(
                "Successfully set input device for instance %s to ID: %s",
                self.server_info.host,
                target_device_id,
            )
        else:
            self._current_input_device_id = -1
            _log.error(
                "Failed to set input device for instance %s to ID: %s",
                self.server_info.host,
                target_device_id,
            )
        return bool(success)

    def enable_voice_transmission(self, enabled: bool) -> bool:
        """Enable or disable voice transmission state for this instance.

        Args:
            enabled: True to enable voice transmission, False to disable it.

        Returns:
            True if the SDK call was successful, False otherwise.

        """
        action = "Enabling" if enabled else "Disabling"
        _log.debug(
            "%s voice transmission for instance %s", action, self.server_info.host
        )
        success = super().enableVoiceTransmission(enabled)
        if not success:
            _log.error(
                "Failed to %s voice transmission for instance %s",
                action.lower(),
                self.server_info.host,
            )
        return bool(success)

    def get_input_volume(self) -> int:
        """Get the current input gain level as percentage (0-100).

        Matches the TeamTalk Qt client's user volume scaling.

        Returns:
            int: The volume percentage (0-100). Returns 0 if the SDK call fails.

        """
        sdk_gain = sdk._GetSoundInputGainLevel(self._tt)
        if sdk_gain < 0:
            _log.warning(
                "Could not get input gain for instance %s, SDK returned %s",
                self.server_info.host,
                sdk_gain,
            )
            return 0
        return ref_volume_to_percent(sdk_gain)

    def set_input_volume(self, percentage: int) -> bool:
        """Set the input gain level from a percentage (0-100).

        Matches the TeamTalk Qt client's user volume scaling.

        Args:
            percentage (int): The desired volume percentage (0-100).

        Returns:
            bool: True on success, False otherwise.

        Raises:
            ValueError: If percentage is out of range (0-100).

        """
        if not PERCENTAGE_MIN <= percentage <= PERCENTAGE_MAX:
            raise ValueError("Percentage must be between 0 and 100")

        internal_volume = percent_to_ref_volume(float(percentage))

        _log.debug(
            "Setting input volume for instance %s to %s%% (internal: %s)",
            self.server_info.host,
            percentage,
            internal_volume,
        )
        success = sdk._SetSoundInputGainLevel(self._tt, internal_volume)
        if not success:
            _log.error(
                "Failed to set input volume for instance %s",
                self.server_info.host,
            )
        return bool(success)

    def start_streaming_media_file_to_channel(
        self, path: str, video_codec: sdk.VideoCodec | None = None
    ) -> bool:
        """Start streaming a media file to the channel.

        If no video codec is specified, it defaults to WebM VP8.

        Args:
            path (str): The path to the media file.
            video_codec (Optional[sdk.VideoCodec]): An optional video codec object.

        Returns:
            bool: True if the streaming started successfully, False otherwise.

        """
        if video_codec is None:
            codec_to_use = sdk.VideoCodec()
            codec_to_use.nCodec = CodecType.WEBM_VP8
        else:
            codec_to_use = video_codec

        return bool(
            super().startStreamingMediaFileToChannel(
                sdk.ttstr(path),  # type: ignore [arg-type]
                ctypes.byref(codec_to_use),  # type: ignore [arg-type]
            )
        )

    def stop_streaming_media_file_to_channel(self) -> bool:
        """Stop the current media file streaming to the channel.

        Returns:
            bool: True if the streaming stopped successfully, False otherwise.

        """
        return bool(super().stopStreamingMediaFileToChannel())

    def has_permission(self, permission: int) -> bool:
        """Check if the bot has a permission.

        If the user is an admin, they have all permissions.

        Args:
            permission: The permission to check for.

        Returns:
            bool: True if the bot has the permission, False otherwise.

        """
        user = super().getMyUserAccount()
        if user.uUserType == sdk.UserType.USERTYPE_ADMIN:
            return True
        user_rights = user.uUserRights
        return bool((user_rights & permission) == permission)

    def is_admin(self) -> bool:
        """Check if the bot is an admin.

        Returns:
            bool: True if the bot is an admin, False otherwise.

        """
        return self.is_user_admin(super().getMyUserID())

    def is_user_admin(self, user: TeamTalkUser | int) -> bool:
        """Check if a user is an admin.

        Args:
            user: The user to check.

        Returns:
            bool: True if the user is an admin, False otherwise.

        Raises:
            TypeError: If the user is not of type pytalk.User or int.

        """
        if isinstance(user, int):
            sdk_user = super().getUser(user)
            return bool(sdk_user.uUserType == sdk.UserType.USERTYPE_ADMIN)
        if isinstance(user, TeamTalkUser):
            return user.user_type == sdk.UserType.USERTYPE_ADMIN
        raise TypeError("User must be of type pytalk.User or int")

    def subscribe(self, user: TeamTalkUser, subscription: Subscription) -> None:
        """Subscribe to a subscription.

        Args:
            user: The user to subscribe to.
            subscription: The subscription to subscribe to.

        """
        sdk._DoSubscribe(self._tt, user.id, subscription)

    def unsubscribe(self, user: TeamTalkUser, subscription: Subscription) -> None:
        """Unsubscribes from a subscription.

        Args:
            user: The user to unsubscribe from.
            subscription: The subscription to unsubscribe from.

        """
        sdk._DoUnsubscribe(self._tt, user.id, subscription)

    def is_subscribed(self, subscription: Subscription) -> bool:
        """Check if the bot is subscribed to a subscription.

        Args:
            subscription: The subscription to check.

        Returns:
            bool: True if the bot is subscribed to the subscription, False otherwise.

        """
        current_subscriptions = cast("int", self._get_my_user().local_subscriptions)
        return (current_subscriptions & cast("int", subscription)) == cast(
            "int", subscription
        )

    def join_root_channel(self) -> None:
        """Join the root channel."""
        self.join_channel_by_id(super().getRootChannelID())

    def join_channel_by_id(self, channel_id: int, password: str = "") -> None:
        """Join a channel by its ID.

        Args:
            channel_id: The ID of the channel to join.
            password: The password of the channel to join.

        """
        super().doJoinChannelByID(channel_id, sdk.ttstr(password))  # type: ignore [arg-type]

    def join_channel(self, channel: TeamTalkChannel) -> None:
        """Join a channel.

        Args:
            channel: The channel to join.

        """
        super().doJoinChannelByID(channel.id, sdk.ttstr(channel.password))  # type: ignore [arg-type]

    def leave_channel(self) -> None:
        """Leaves the current channel."""
        super().doLeaveChannel()

    def get_channel(self, channel_id: int) -> TeamTalkChannel:
        """Get a channel by its ID.

        Args:
            channel_id: The ID of the channel to get.

        Returns:
            TeamTalkChannel: The channel.

        """
        return TeamTalkChannel(self, channel_id)

    def get_path_from_channel(self, channel: TeamTalkChannel | int) -> str:
        """Get the path of a channel.

        Args:
            channel: The channel to get the path of.

        Returns:
            str: The path of the channel.

        Raises:
            TypeError: If the channel is not of type pytalk.Channel or int.
            ValueError: If the channel is not found.

        """
        if isinstance(channel, TeamTalkChannel):
            channel = channel.id
        path = (sdk.TTCHAR * sdk.TT_STRLEN)()
        result = sdk._GetChannelPath(self._tt, channel, path)
        if not result:
            raise ValueError("Channel not found")
        if sys.platform == "win32":
            return path.value
        return sdk.ttstr(cast("sdk.TTCHAR_P", path.value))

    def get_channel_from_path(self, path: str) -> TeamTalkChannel:
        """Get a channel by its path.

        Args:
            path: The path of the channel to get.

        Returns:
            TeamTalkChannel: The channel.

        Raises:
            ValueError: If the channel is not found.

        """
        result = sdk._GetChannelIDFromPath(self._tt, sdk.ttstr(path))  # type: ignore [arg-type]
        if result == 0:
            raise ValueError("Channel not found")
        return TeamTalkChannel(self, result)

    def create_channel(  # noqa: C901, PLR0913
        self,
        name: str,
        parent_channel: TeamTalkChannel | int,
        topic: str = "",
        password: str = "",
        channel_type: int = ChannelType.DEFAULT,
        disk_quota: int = 0,
        max_users: int = 0,
        timeout_media_file_msec: int = 0,
        timeout_voice_msec: int = 0,
        op_password: str = "",
        user_data: int = 0,
        audiocfg: AudioCodecConfig | None = None,
    ) -> bool:
        """Create a channel.

        Args:
            name: The name of the channel to create.
            parent_channel: The parent channel of the channel.
            topic: The topic of the channel.
            password: The password of the channel. Leave empty for no password.
            channel_type: The type of the channel. Defaults to CHANNEL_DEFAULT.
            disk_quota: The disk quota for files in the channel.
                Defaults to 0 (unlimited).
            max_users: The maximum number of users allowed in the channel.
                Defaults to 0 (unlimited).
            timeout_media_file_msec: Timeout for media file transmission in
                milliseconds. Defaults to 0.
            timeout_voice_msec: Timeout for voice transmission in milliseconds.
                Defaults to 0.
            op_password: The operator password for the channel. Defaults to "".
            user_data: User-defined data associated with the channel. Defaults to 0.
            audiocfg: Audio codec configuration. Defaults to None.
            videocodec: Video codec configuration. Defaults to None.

        Raises:
            PytalkPermissionError: If the bot does not have permission
                to create channels.
            ValueError: If the channel could not be created.

        Returns:
            bool: True if the channel was created, False otherwise.

        """
        if not self.has_permission(cast("int", Permission.MODIFY_CHANNELS)):
            raise PytalkPermissionError(
                "The bot does not have permission to create channels"
            )
        if isinstance(parent_channel, TeamTalkChannel):
            parent_channel = parent_channel.id
        new_channel = sdk.Channel()
        new_channel.nParentID = parent_channel
        new_channel.szName = sdk.ttstr(name)  # type: ignore [arg-type]
        new_channel.szTopic = sdk.ttstr(topic)  # type: ignore [arg-type]
        new_channel.szPassword = sdk.ttstr(password)  # type: ignore [arg-type]
        new_channel.bPassword = password != ""
        new_channel.uChannelType = channel_type
        new_channel.nDiskQuota = disk_quota
        new_channel.nMaxUsers = max_users
        new_channel.nTimeOutTimerMediaFileMSec = timeout_media_file_msec
        new_channel.nTimeOutTimerVoiceMSec = timeout_voice_msec
        new_channel.szOpPassword = sdk.ttstr(op_password)  # type: ignore [arg-type]
        new_channel.nUserData = user_data

        if audiocfg:
            new_channel.audiocfg = audiocfg.payload

        result = sdk._DoMakeChannel(self._tt, new_channel)
        if result == -1:
            raise ValueError("Channel could not be created")
        cmd_result, cmd_err = _wait_for_cmd(self, result, 2000)
        if not cmd_result:
            err_nr = cmd_err.nErrorNo
            if err_nr == sdk.ClientError.CMDERR_NOT_LOGGEDIN:
                raise PytalkPermissionError("The bot is not logged in")
            if err_nr == sdk.ClientError.CMDERR_NOT_AUTHORIZED:
                raise PytalkPermissionError(
                    "The bot does not have permission to create channels"
                )
            if err_nr == sdk.ClientError.CMDERR_CHANNEL_ALREADY_EXISTS:
                raise ValueError("Channel already exists")
            if err_nr == sdk.ClientError.CMDERR_CHANNEL_NOT_FOUND:
                raise ValueError(
                    "Combined channel path is too long. "
                    "Try using a shorter channel name"
                )
            if err_nr == sdk.ClientError.CMDERR_INCORRECT_CHANNEL_PASSWORD:
                raise ValueError("Channel password too long")
        return True

    def delete_channel(self, channel: TeamTalkChannel | int) -> bool:
        """Delete a channel.

        Args:
            channel: The channel to delete.

        Raises:
            TypeError: If the channel is not of type pytalk.Channel or int.
            PytalkPermissionError: If the bot doesn't have the permission to delete the
            channel.
            ValueError: If the channel is not found.

        Returns:
            bool: True if the channel was deleted.

        """
        if not self.has_permission(cast("int", Permission.MODIFY_CHANNELS)):
            raise PytalkPermissionError(
                "The bot does not have permission to delete channels"
            )
        if isinstance(channel, TeamTalkChannel):
            channel = channel.id
        result = sdk._DoRemoveChannel(self._tt, channel)
        if result == -1:
            raise ValueError("Channel could not be deleted")
        cmd_result, cmd_err = _wait_for_cmd(self, result, 2000)
        if not cmd_result:
            err_nr = cmd_err.nErrorNo
            if err_nr == sdk.ClientError.CMDERR_NOT_LOGGEDIN:
                raise PytalkPermissionError("The bot is not logged in")
            if err_nr == sdk.ClientError.CMDERR_NOT_AUTHORIZED:
                raise PytalkPermissionError(
                    "The bot does not have permission to delete channels"
                )
            if err_nr == sdk.ClientError.CMDERR_CHANNEL_NOT_FOUND:
                raise ValueError("Channel not found.")
        return True

    def make_channel_operator(
        self,
        user: TeamTalkUser | int,
        channel: TeamTalkChannel | int,
        operator_password: str = "",
    ) -> bool:
        """Make a user the channel operator.

        Args:
            user: The user to make the channel operator.
            channel: The channel to make the user the channel operator in.
            operator_password: The operator password of the channel.

        Raises:
            TypeError: If the user or channel is not of type pytalk.User or int.
            PytalkPermissionError: If the bot doesn't have the permission to make a user
            the channel operator.
            ValueError: If the user or channel is not found.

        Returns:
            bool: True if the user was made the channel operator, False otherwise.

        """
        if isinstance(user, int):
            user_obj: TeamTalkUser = self.get_user(user)
        else:
            user_obj = user
        if isinstance(channel, int):
            channel_obj: TeamTalkChannel = self.get_channel(channel)
        else:
            channel_obj = channel
        result = sdk._DoChannelOpEx(
            self._tt,
            user_obj.id,
            channel_obj.id,
            sdk.ttstr(operator_password),  # type: ignore [arg-type]
            True,
        )
        if result == -1:
            raise PytalkPermissionError(
                "The bot does not have the permission to make a user the channel "
                "operator"
            )
            return False
        cmd_result, cmd_err = _wait_for_cmd(self, result, 2000)
        if not cmd_result:
            err_nr = cmd_err.nErrorNo
            if err_nr == sdk.ClientError.CMDERR_NOT_LOGGEDIN:
                raise PytalkPermissionError("The bot is not logged in")
            if err_nr == sdk.ClientError.CMDERR_NOT_AUTHORIZED:
                raise PytalkPermissionError(
                    "The bot does not have permission to make a user the channel "
                    "operator"
                )
            if err_nr == sdk.ClientError.CMDERR_CHANNEL_NOT_FOUND:
                raise ValueError("The channel does not exist")
            if err_nr == sdk.ClientError.CMDERR_USER_NOT_FOUND:
                raise ValueError("The user does not exist")
            if err_nr == sdk.ClientError.CMDERR_INCORRECT_OP_PASSWORD:
                raise ValueError("The operator password is incorrect")
            return False
        return True

    def remove_channel_operator(
        self,
        user: TeamTalkUser | int,
        channel: TeamTalkChannel | int,
        operator_password: str = "",
    ) -> bool:
        """Remove a user as the channel operator.

        Args:
            user: The user to make the channel operator.
            channel: The channel to make the user the channel operator in.
            operator_password: The operator password of the channel.

        Raises:
            TypeError: If the user or channel is not of type pytalk.User or int.
            PytalkPermissionError: If the bot doesn't have the permission to make a user
                the channel operator.
            ValueError: If the channel or user does not exist.

        Returns:
            bool: True if the user was removed as the channel operator, False otherwise.

        """
        if isinstance(user, int):
            user_obj: TeamTalkUser = self.get_user(user)
        else:
            user_obj = user
        if isinstance(channel, int):
            channel_obj: TeamTalkChannel = self.get_channel(channel)
        else:
            channel_obj = channel
        result = sdk._DoChannelOpEx(
            self._tt,
            user_obj.id,
            channel_obj.id,
            sdk.ttstr(operator_password),  # type: ignore [arg-type]
            False,
        )
        if result == -1:
            raise PytalkPermissionError(
                "The bot does not have the permission to make a user the channel "
                "operator"
            )
            return False
        cmd_result, cmd_err = _wait_for_cmd(self, result, 2000)
        if not cmd_result:
            err_nr = cmd_err.nErrorNo
            if err_nr == sdk.ClientError.CMDERR_NOT_LOGGEDIN:
                raise PytalkPermissionError("The bot is not logged in")
            if err_nr == sdk.ClientError.CMDERR_NOT_AUTHORIZED:
                raise PytalkPermissionError(
                    "The bot does not have permission to make a user the channel "
                    "operator"
                )
            if err_nr == sdk.ClientError.CMDERR_CHANNEL_NOT_FOUND:
                raise ValueError("The channel does not exist")
            if err_nr == sdk.ClientError.CMDERR_USER_NOT_FOUND:
                raise ValueError("The user does not exist")
            if err_nr == sdk.ClientError.CMDERR_INCORRECT_OP_PASSWORD:
                raise ValueError("The operator password is incorrect")
            return False
        return True

    def get_user(self, user_id: int) -> TeamTalkUser:
        """Get a user by its ID.

        Args:
            user_id: The ID of the user to get.

        Returns:
            TeamTalkUser: The user.

        """
        return TeamTalkUser(self, user_id)

    def create_user_account(
        self,
        username: str,
        password: str,
        usertype: UserType,
        user_rights: int | None = None,
        note: str = "",
    ) -> bool:
        """Create a user account on the server.

        Args:
            username (str): The username for the new account.
            password (str): The password for the new account.
            usertype (UserType): The type of user account (e.g.,
                `pytalk.UserType.DEFAULT` or `pytalk.UserType.ADMIN`).
            user_rights (Optional[int], optional): Specific rights to assign,
                as a bitmask of `pytalk.Permission` values. If `None`
                (default), `uUserRights` is sent as `0`, and server
                defaults based on `usertype` will apply.
            note (str, optional): An optional note for the user account.
                If this argument is not provided when calling the
                function, it defaults to an empty string, which means
                no note will be set.

        Returns:
            bool: True if the command to create the account was
                successfully dispatched.

        Raises:
            ValueError: If username or password is invalid.
            PytalkPermissionError: If the bot lacks permission to create accounts
                or is not logged in.

        """
        account = sdk.UserAccount()
        account.szUsername = sdk.ttstr(username)  # type: ignore [arg-type]
        account.szPassword = sdk.ttstr(password)  # type: ignore [arg-type]
        account.uUserType = usertype
        account.szNote = sdk.ttstr(note)  # type: ignore [arg-type]

        if user_rights is not None:
            account.uUserRights = user_rights

        result = sdk._DoNewUserAccount(self._tt, account)
        if result == -1:
            raise ValueError("Username or password is invalid")
        cmd_result, cmd_err = _wait_for_cmd(self, result, 2000)
        if not cmd_result:
            err_nr = cmd_err.nErrorNo
            if err_nr == sdk.ClientError.CMDERR_INVALID_USERNAME:
                raise ValueError("Username is invalid")
            if err_nr == sdk.ClientError.CMDERR_NOT_AUTHORIZED:
                raise PytalkPermissionError(
                    "The bot does not have permission to create a user account"
                )
            if err_nr == sdk.ClientError.CMDERR_NOT_LOGGEDIN:
                raise PytalkPermissionError("The bot is not logged in")
        return True

    def delete_user_account(self, username: str) -> bool:
        """Delete a user account.

        Args:
            username: The username of the user account to delete.

        Returns:
            bool: True if the user account was deleted, False otherwise.

        Raises:
            ValueError: If the username is empty or the user account does not exist.
            PytalkPermissionError: If the user does not have permission to delete a user
                account.

        """
        if not username:
            raise ValueError("Username is empty")
        username = sdk.ttstr(username)  # type: ignore [arg-type]
        result = sdk._DoDeleteUserAccount(self._tt, username)
        if result == -1:
            raise ValueError("User account does not exist")
        cmd_result, cmd_err = _wait_for_cmd(self, result, 2000)
        if not cmd_result:
            err_nr = cmd_err.nErrorNo
            if err_nr == sdk.ClientError.CMDERR_NOT_AUTHORIZED:
                raise PytalkPermissionError(
                    "The bot does not have permission to delete a user account"
                )
            if err_nr == sdk.ClientError.CMDERR_NOT_LOGGEDIN:
                raise PytalkPermissionError("The bot is not logged in")
            if err_nr == sdk.ClientError.CMDERR_ACCOUNT_NOT_FOUND:
                raise ValueError("User account does not exist")
        return True

    async def list_user_accounts(self) -> list[TeamTalkUserAccount]:
        """List all user accounts on the server.

        Returns:
            A list of all user accounts.

        Raises:
            PytalkPermissionError: If the bot is not an admin.
            ValueError: If an unknown error occurred.

        """
        if not self.is_admin():
            raise PytalkPermissionError("The bot is not an admin")
        self.user_accounts = []
        result = sdk._DoListUserAccounts(self._tt, 0, 1000000)
        if result == -1:
            raise ValueError("Unknown error")
        await asyncio.sleep(1)
        return self.user_accounts

    def upload_file(
        self,
        channel_id: int,
        filepath: str,
        progress_callback: Callable[[FileTransfer], None] | None = None,
    ) -> int:
        """Upload a local file to a channel.

        Args:
            channel_id: The ID of the channel to upload the file to.
            filepath: The path to the local file to upload.
            progress_callback: A callback function that will be called with a
                pytalk.tt_file.FileTransfer object on file transfer progress.

        Raises:
            PytalkPermissionError: If the bot does not have permission to upload files.
            ValueError: If the channel ID is less than 0.
            FileNotFoundError: If the local file does not exist.

        Returns:
            int: The transfer ID for the initiated file transfer.

        """
        if not self.has_permission(cast("int", Permission.UPLOAD_FILES)):
            raise PytalkPermissionError("You do not have permission to upload files")
        if channel_id < 0:
            raise ValueError("Channel ID must be greater than 0")
        if not Path(filepath).exists():
            raise FileNotFoundError(f"File {filepath} does not exist")
        transfer_id = super().doSendFile(channel_id, sdk.ttstr(filepath))  # type: ignore [arg-type]
        if progress_callback:
            self._file_transfer_callbacks[transfer_id] = progress_callback
        return transfer_id

    def download_file(
        self,
        channel_id: int,
        remote_file_name: str,
        local_file_path: str,
        progress_callback: Callable[[FileTransfer], None] | None = None,
    ) -> int:
        """Download a remote file from a channel.

        Args:
            channel_id: The ID of the channel to download the file from.
            remote_file_name: The name of the remote file to download.
            local_file_path: The path to save the file to.
            progress_callback: A callback function that will be called with a
                pytalk.tt_file.FileTransfer object on file transfer progress.

        Raises:
                        PytalkPermissionError: If the bot does not have permission
                        to download files.
            ValueError: If the channel ID is less than 0.

        Returns:
            int: The transfer ID for the initiated file transfer.

        """
        if not self.has_permission(cast("int", Permission.DOWNLOAD_FILES)):
            raise PytalkPermissionError("You do not have permission to download files")
        if channel_id < 0:
            raise ValueError("Channel ID must be greater than 0")
        remote_files = self.get_channel_files(channel_id)
        for file in remote_files:
            if sdk.ttstr(file.file_name) == remote_file_name:  # type: ignore [arg-type]
                return self.download_file_by_id(
                    channel_id,
                    file.file_id,
                    local_file_path,
                    progress_callback,
                )
        return -1  # Indicate failure to find file

    def download_file_by_id(
        self,
        channel_id: int,
        file_id: int,
        filepath: str,
        progress_callback: Callable[[FileTransfer], None] | None = None,
    ) -> int:
        """Download a remote file from a channel by its ID.

        Args:
            channel_id: The ID of the channel to download the file from.
            file_id: The ID of the file to download.
            filepath: The path to save the file to.
            progress_callback: A callback function that will be called with a
                pytalk.tt_file.FileTransfer object on file transfer progress.

        Raises:
            PytalkPermissionError: If the bot does not have permission
            to download files.

        Returns:
            int: The transfer ID for the initiated file transfer.

        """
        if not self.has_permission(cast("int", Permission.DOWNLOAD_FILES)):
            raise PytalkPermissionError("You do not have permission to download files")
        transfer_id = super().doRecvFile(channel_id, file_id, sdk.ttstr(filepath))  # type: ignore [arg-type]
        if progress_callback:
            self._file_transfer_callbacks[transfer_id] = progress_callback
        return transfer_id

    def cancel_file_transfer(self, transfer_id: int) -> bool:
        """Cancel a file transfer.

        Args:
            transfer_id: The ID of the file transfer to cancel.

        Returns:
            bool: True if the file transfer was cancelled, False otherwise.

        """
        if transfer_id in self._file_transfer_callbacks:
            del self._file_transfer_callbacks[transfer_id]
        return bool(sdk._CancelFileTransfer(self._tt, transfer_id))

    def delete_file_by_id(self, channel_id: int, file_id: int) -> None:
        """Delete a remote file from a channel by its ID.

        Args:
            channel_id: The ID of the channel to delete the file from.
            file_id: The ID of the file to delete.

        Raises:
            PytalkPermissionError: If the bot does not have permission to delete files.

        """
        if not self.is_admin():
            raise PytalkPermissionError("You do not have permission to delete files")
        super().doDeleteFile(channel_id, file_id)

    def get_channel_files(self, channel_id: int) -> list[RemoteFile]:
        """Get a list of remote files in a channel.

        Args:
            channel_id: The ID of the channel to get the files from.

        Returns:
            List[RemoteFile]: A list of remote files in the channel.

        """
        files = super().getChannelFiles(channel_id)
        return [RemoteFile(self, file) for file in files]

    def move_user(
        self, user: TeamTalkUser | int, channel: TeamTalkChannel | int
    ) -> None:
        """Move a user to a channel.

        Args:
            user: The user to move.
            channel: The channel to move the user to.

        Raises:
            PytalkPermissionError: If the bot does not have permission to move users.
            TypeError: If the user or channel is not a subclass of User or Channel.

        """
        if not self.has_permission(cast("int", Permission.MOVE_USERS)):
            raise PytalkPermissionError("You do not have permission to move users")
        _log.debug("Moving user %s to channel %s", user, channel)
        self._do_cmd(user, channel, sdk._DoMoveUser)

    def kick_user(
        self, user: TeamTalkUser | int, channel: TeamTalkChannel | int
    ) -> bool:
        """Kicks a user from a channel or the server.

        Args:
            user: The user to kick.
            channel: The channel to kick the user from. If 0, the user will be kicked
                from the server. # noqa

        Raises:
            PytalkPermissionError: If the bot does not have permission to kick users.
            TypeError: If the user or channel is not a subclass of User or Channel.
            ValueError: If the user or channel is not found.

        """
        if channel == 0:  # server
            if not self.has_permission(cast("int", Permission.KICK_USERS)):
                raise PytalkPermissionError("You do not have permission to kick users")
            _log.debug("Kicking user %s from channel %s", user, channel)
            result = self._do_cmd(user, channel, sdk._DoKickUser)
        else:  # channel
            channel_id = (
                channel.id if isinstance(channel, TeamTalkChannel) else int(channel)
            )
            can_kick = self.has_permission(
                cast("int", Permission.KICK_USERS_FROM_CHANNEL)
            ) or sdk._IsChannelOperator(self._tt, super().getMyUserID(), channel_id)
            if not can_kick:
                raise PytalkPermissionError(
                    "You do not have permission to kick users from channels"
                )
            result = self._do_cmd(user, channel_id, sdk._DoKickUser)

        if result == -1:
            raise ValueError("SDK failed to dispatch the kick command.")

        cmd_result, cmd_err = _wait_for_cmd(self, result, 2000)
        if not cmd_result:
            err_nr = cmd_err.nErrorNo
            if err_nr == sdk.ClientError.CMDERR_USER_NOT_FOUND:
                raise ValueError("User not found")
            if err_nr == sdk.ClientError.CMDERR_CHANNEL_NOT_FOUND:
                raise ValueError("Channel not found")
            raise TeamTalkError(f"Kick command failed with server error: {err_nr}")
        return cmd_result

    def ban_user(
        self, user: TeamTalkUser | int, channel: TeamTalkChannel | int
    ) -> bool:
        """Bans a user from a channel or the server.

        Args:
            user: The user to ban.
            channel: The channel to ban the user from. If 0, the user will be banned
                from the server. # noqa

        Raises:
            PytalkPermissionError: If the bot does not have permission to ban users.
            TypeError: If the user or channel is not a subclass of User or Channel.
            ValueError: If the user is not found.

        """
        if not self.has_permission(cast("int", Permission.BAN_USERS)):
            raise PytalkPermissionError("You do not have permission to ban users")
        _log.debug("Banning user %s from channel %s", user, channel)
        result = self._do_cmd(user, channel, sdk._DoBanUser)
        if result == -1:
            raise ValueError("SDK failed to dispatch the ban command.")

        cmd_result, cmd_err = _wait_for_cmd(self, result, 2000)
        if not cmd_result:
            err_nr = cmd_err.nErrorNo
            if err_nr == sdk.ClientError.CMDERR_USER_NOT_FOUND:
                raise ValueError("User not found")
            raise TeamTalkError(f"Ban command failed with server error: {err_nr}")
        return cmd_result

    def unban_user(self, ip: str, channel: TeamTalkChannel | int) -> None:
        """Unbans a user from the server.

        Args:
            ip: The IP address of the user to unban.
            channel: The channel to unban the user from. If 0, the user will be
                unbanned from the server. # noqa

        Raises:
            PytalkPermissionError: If the bot does not have permission to unban users.

        """
        if not self.has_permission(cast("int", Permission.UNBAN_USERS)):
            raise PytalkPermissionError("You do not have permission to unban users")
        if not isinstance(ip, str):
            raise TypeError("IP must be a string")
        if not isinstance(channel, (TeamTalkChannel, int)):
            raise TypeError("Channel must be a subclass of Channel or a channel ID")
        channel_id = channel
        if isinstance(channel, TeamTalkChannel):
            channel_id = channel.id
        _log.debug("Unbanning user %s", ip)
        sdk._DoUnBanUser(self._tt, sdk.ttstr(ip), channel_id)  # type: ignore [arg-type]

    async def list_banned_users(self) -> list[TeamTalkBannedUserAccount]:
        """List all banned users.

        Returns:
            List[BannedUserAccount]: A list of banned users.

        Raises:
            PytalkPermissionError: If the bot is not an admin.
            ValueError: If an unknown error occurs.

        """
        if not self.is_admin():
            raise PytalkPermissionError("The bot is not an admin")
        self.banned_users = []
        result = sdk._DoListBans(self._tt, 0, 0, 1000000)
        if result == -1:
            raise ValueError("Unknown error")
        await asyncio.sleep(1)
        return self.banned_users

    def get_server_statistics(self, timeout: int) -> TeamTalkServerStatistics:
        """Get the statistics from the server.

        Args:
            timeout: The time to wait before assuming that getting the servers
                statistics failed.

        Raises:
            TimeoutError: If the server statistics are not received with in the given
                time.

        Returns:
            The pytalk.statistics object representing the servers statistics.

        """
        sdk._DoQueryServerStats(self._tt)
        result, msg = _wait_for_event(
            self,
            cast("sdk.ClientEvent", sdk.ClientEvent.CLIENTEVENT_CMD_SERVERSTATISTICS),
            timeout * 1000,
        )
        if not result:
            raise TimeoutError("The request for server statistics timed out.")
        return TeamTalkServerStatistics(self, msg.serverstatistics)

    async def _send_message(self, message: sdk.TextMessage, **kwargs: object) -> None:
        """Send a message.

        Args:
            message: The message to send.
            delay: The delay in seconds before sending the message. Defaults to 0 which
                means no delay. # noqa
            **kwargs: Keyword arguments. Reserved for future use.


        Raises:
            TypeError: If the message is not a subclass of Message.

        """
        if not isinstance(message, sdk.TextMessage):
            raise TypeError("Message must be a subclass of sdk.TextMessage")
        if not issubclass(type(message), sdk.TextMessage):
            raise TypeError("Message must be a subclass of sdk.TextMessage")
        delay = cast("float", kwargs.get("delay", 0))
        await _do_after(
            delay,
            lambda: self.doTextMessage(message),
        )

    async def _process_events(self) -> None:  # noqa: C901, PLR0911, PLR0912, PLR0915
        """Process events from the server.

        This is automatically called by pytalk.Bot.
        """
        msg = super().getMessage(100)
        event = msg.nClientEvent

        if event == sdk.ClientEvent.CLIENTEVENT_NONE:
            return
        if event == sdk.ClientEvent.CLIENTEVENT_USER_FIRSTVOICESTREAMPACKET:
            return

        if event == sdk.ClientEvent.CLIENTEVENT_CMD_MYSELF_KICKED:
            self.connected = False
            self.logged_in = False

            self.bot.dispatch(
                "my_kicked_from_channel", TeamTalkChannel(self, msg.nSource)
            )

            if self.reconnect_enabled:
                _log.info(
                    "Kicked from %s. Attempting to reconnect...",
                    self.server_info.host,
                )
                asyncio.create_task(self._reconnect())
            return
        if event == sdk.ClientEvent.CLIENTEVENT_CON_LOST:
            self.connected = False
            self.logged_in = False
            self.bot.dispatch("my_connection_lost", self)
            if self.reconnect_enabled:
                _log.info(
                    "Connection lost to %s. Attempting to reconnect...",
                    self.server_info.host,
                )
                asyncio.create_task(self._reconnect())
            return

        if event == sdk.ClientEvent.CLIENTEVENT_USER_STATECHANGE:
            user_id = msg.user.nUserID
            current_user_state = msg.user.uUserState
            if current_user_state & sdk.UserState.USERSTATE_VOICE:
                if self.bot._listeners.get("user_audio") or self.bot._listeners.get(
                    "muxed_audio"
                ):
                    sdk._EnableAudioBlockEventEx(
                        self._tt,
                        user_id,
                        sdk.StreamType.STREAMTYPE_VOICE,
                        None,
                        True,
                    )
            else:
                sdk._EnableAudioBlockEventEx(
                    self._tt, user_id, sdk.StreamType.STREAMTYPE_VOICE, None, False
                )
            return
        if event == sdk.ClientEvent.CLIENTEVENT_USER_AUDIOBLOCK:
            sdk_audio_block_ptr = None
            py_sdk_audio_block_struct_instance = None
            source_id = msg.nSource
            with self._audio_sdk_lock:
                stream_type_enum = sdk.StreamType(msg.nStreamType)
                sdk_audio_block_ptr = _AcquireUserAudioBlock(
                    self._tt, stream_type_enum, source_id
                )
                if not sdk_audio_block_ptr:
                    return
                py_sdk_audio_block_struct_instance = sdk.AudioBlock()
                try:
                    ctypes.memmove(
                        ctypes.addressof(py_sdk_audio_block_struct_instance),
                        sdk_audio_block_ptr,
                        ctypes.sizeof(py_sdk_audio_block_struct_instance),
                    )
                except OSError:
                    _ReleaseUserAudioBlock(self._tt, sdk_audio_block_ptr)
                    return
                _ReleaseUserAudioBlock(self._tt, sdk_audio_block_ptr)
            py_audio_block_wrapper: AudioBlock | MuxedAudioBlock | None = None
            try:
                if source_id == sdk.TT_MUXED_USERID:
                    py_audio_block_wrapper = MuxedAudioBlock(
                        self, py_sdk_audio_block_struct_instance
                    )
                    self.bot.dispatch("muxed_audio", py_audio_block_wrapper)
                else:
                    user = TeamTalkUser(self, source_id)
                    py_audio_block_wrapper = AudioBlock(
                        user, py_sdk_audio_block_struct_instance
                    )
                    self.bot.dispatch("user_audio", py_audio_block_wrapper)
            except Exception as e:  # noqa: BLE001
                _log.exception(
                    "CLIENTEVENT_USER_AUDIOBLOCK: Error during Python wrapper "
                    "creation or dispatch for source_id %s. Error: %s",
                    source_id,
                    e,
                )
            return
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_USER_JOINED:
            user_joined = TeamTalkUser(self, msg.user)
            if user_joined.id == super().getMyUserID() and self.bot._listeners.get(
                "muxed_audio"
            ):
                sdk._EnableAudioBlockEventEx(
                    self._tt,
                    sdk.TT_MUXED_USERID,
                    sdk.StreamType.STREAMTYPE_VOICE,
                    None,
                    True,
                )
            self.bot.dispatch("user_join", user_joined, user_joined.channel)
            return
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_USER_LEFT:
            user_left = TeamTalkUser(self, msg.user)
            channel_left_from = TeamTalkChannel(self, msg.nSource)
            if user_left.id == super().getMyUserID():
                sdk._EnableAudioBlockEventEx(
                    self._tt,
                    sdk.TT_MUXED_USERID,
                    sdk.StreamType.STREAMTYPE_VOICE,
                    None,
                    False,
                )
            self.bot.dispatch("user_left", user_left, channel_left_from)
            return
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_USER_LOGGEDIN:
            self.bot.dispatch("user_login", TeamTalkUser(self, msg.user))
            return
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_USER_LOGGEDOUT:
            self.bot.dispatch("user_logout", TeamTalkUser(self, msg.user))
            return
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_USER_UPDATE:
            self.bot.dispatch("user_update", TeamTalkUser(self, msg.user))
            return

        if event == sdk.ClientEvent.CLIENTEVENT_CMD_USER_TEXTMSG:
            message: Message | None = None
            if msg.textmessage.nMsgType == sdk.TextMsgType.MSGTYPE_USER:
                message = DirectMessage(self, msg.textmessage)
            elif msg.textmessage.nMsgType == sdk.TextMsgType.MSGTYPE_CHANNEL:
                message = ChannelMessage(self, msg.textmessage)
            elif msg.textmessage.nMsgType == sdk.TextMsgType.MSGTYPE_BROADCAST:
                message = BroadcastMessage(self, msg.textmessage)
            elif msg.textmessage.nMsgType == sdk.TextMsgType.MSGTYPE_CUSTOM:
                message = CustomMessage(self, msg.textmessage)
            if message:
                self.bot.dispatch("message", message)
            return

        if event == sdk.ClientEvent.CLIENTEVENT_CMD_CHANNEL_NEW:
            self.bot.dispatch("channel_new", TeamTalkChannel(self, msg.channel))
            return
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_CHANNEL_UPDATE:
            self.bot.dispatch("channel_update", TeamTalkChannel(self, msg.channel))
            return
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_CHANNEL_REMOVE:
            self.bot.dispatch("channel_delete", TeamTalkChannel(self, msg.channel))
            return

        if event == sdk.ClientEvent.CLIENTEVENT_CMD_FILE_NEW:
            self.bot.dispatch("file_new", RemoteFile(self, msg.remotefile))
            return
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_FILE_REMOVE:
            self.bot.dispatch("file_delete", RemoteFile(self, msg.remotefile))
            return

        if event == sdk.ClientEvent.CLIENTEVENT_FILETRANSFER:
            transfer_id = msg.filetransfer.nTransferID
            sdk_file_transfer = sdk.FileTransfer()
            sdk._GetFileTransferInfo(self._tt, transfer_id, sdk_file_transfer)
            file_transfer = FileTransfer(self, sdk_file_transfer)
            if transfer_id in self._file_transfer_callbacks:
                self._file_transfer_callbacks[transfer_id](file_transfer)
            self.bot.dispatch("file_transfer_progress", file_transfer)
            return

        if event == sdk.ClientEvent.CLIENTEVENT_CMD_SERVER_UPDATE:
            self.bot.dispatch("server_update", self)
            return
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_SERVERSTATISTICS:
            self.bot.dispatch(
                "server_statistics",
                TeamTalkServerStatistics(self, msg.serverstatistics),
            )
            return

        if event == sdk.ClientEvent.CLIENTEVENT_CMD_USERACCOUNT_NEW:
            account = TeamTalkUserAccount(self, msg.useraccount)
            self.bot.dispatch("user_account_new", account)
            return
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_USERACCOUNT_REMOVE:
            account = TeamTalkUserAccount(self, msg.useraccount)
            self.bot.dispatch("user_account_remove", account)
            return
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_USERACCOUNT:  # Internal
            account = TeamTalkUserAccount(self, msg.useraccount)
            self.user_accounts.append(account)
            return
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_BANNEDUSER:  # Internal
            banned_user_struct = sdk.BannedUser()
            ctypes.memmove(
                ctypes.byref(banned_user_struct),
                ctypes.byref(msg.useraccount),
                ctypes.sizeof(sdk.BannedUser),
            )
            banned_user = TeamTalkBannedUserAccount(
                self, cast("Any", banned_user_struct)
            )
            self.banned_users.append(banned_user)
            return

        if event not in (
            sdk.ClientEvent.CLIENTEVENT_CMD_PROCESSING,
            sdk.ClientEvent.CLIENTEVENT_CMD_ERROR,
            sdk.ClientEvent.CLIENTEVENT_CMD_SUCCESS,
            sdk.ClientEvent.CLIENTEVENT_AUDIOINPUT,
        ):
            _log.warning("Unhandled event: %s", event)

    async def initial_connect_loop(self) -> bool:
        """Attempt to establish an initial connection and login to the server.

        This method will loop, attempting to connect and then log in,
        using the configured backoff strategy if attempts fail.
        The backoff mechanism is reset before the first attempt and
        upon successful connection and login.

        Returns:
            bool: True if connection and login were successful within retry limits,
                  False otherwise.

        """
        _log.info("Attempting initial connection to %s...", self.server_info.host)
        self._backoff.reset()

        while True:
            connected_ok = await self.bot.loop.run_in_executor(None, self.connect)

            if connected_ok:
                _log.info(
                    "Successfully connected to %s. Attempting login...",
                    self.server_info.host,
                )
                logged_in_ok = await self.bot.loop.run_in_executor(None, self.login)
                if logged_in_ok:
                    _log.info("Successfully logged in to %s.", self.server_info.host)
                    self._backoff.reset()
                    return True
                _log.warning(
                    "Login failed for %s after successful connection.",
                    self.server_info.host,
                )
            else:
                _log.warning(
                    "Initial connection attempt failed for %s.",
                    self.server_info.host,
                )

            delay = self._backoff.delay()
            if delay is None:
                _log.error(
                    "Max retries exceeded for initial connection to %s. "
                    "Stopping attempts.",
                    self.server_info.host,
                )
                return False

            _log.info(
                "Will retry initial connection to %s in %.2f seconds...",
                self.server_info.host,
                delay,
            )
            await asyncio.sleep(delay)

    async def _reconnect(self) -> None:
        while True:
            delay = self._backoff.delay()
            if delay is None:
                _log.error(
                    "Max retries exceeded for reconnecting to %s. Stopping attempts.",
                    self.server_info.host,
                )
                return

            _log.info(
                "Will retry reconnect to %s in %.2f seconds...",
                self.server_info.host,
                delay,
            )
            await asyncio.sleep(delay)

            _log.info(
                "Attempting reconnect to %s (attempt %s)...",
                self.server_info.host,
                self._backoff.attempts,
            )

            await self.bot.loop.run_in_executor(None, self.disconnect)

            connected_ok = await self.bot.loop.run_in_executor(None, self.connect)

            if connected_ok:
                _log.info(
                    "Re-established connection to %s. Attempting login...",
                    self.server_info.host,
                )
                logged_in_ok = await self.bot.loop.run_in_executor(
                    None, self.login, True
                )
                if logged_in_ok:
                    _log.info(
                        "Successfully reconnected and logged in to %s.",
                        self.server_info.host,
                    )
                    self._backoff.reset()
                    return
                _log.warning(
                    "Login failed for %s after successful reconnect.",
                    self.server_info.host,
                )
            else:
                _log.warning(
                    "Reconnect attempt %s failed for %s.",
                    self._backoff.attempts,
                    self.server_info.host,
                )

    def _get_channel_info(self, channel_id: int) -> tuple[sdk.Channel, str]:
        _channel = super().getChannel(channel_id)
        _channel_path = sdk.ttstr(super().getChannelPath(channel_id))
        return _channel, _channel_path

    def _get_my_permissions(self) -> int:
        return cast("int", sdk._GetMyUserRights(self._tt))

    def _get_my_user(self) -> TeamTalkUser:
        return self.get_user(super().getMyUserID())

    def _do_cmd(
        self,
        user: TeamTalkUser | int,
        channel: TeamTalkChannel | int,
        func: Callable[..., Any] | str,
    ) -> int:
        if not isinstance(user, (TeamTalkUser, int)):
            raise TypeError("User must be a pytalk.User or a user id")
        if not isinstance(channel, (TeamTalkChannel, int)):
            raise TypeError("Channel must be a pytalk.Channel or a channel id")
        user_id: int = user.id if isinstance(user, TeamTalkUser) else user
        channel_id = channel.id if isinstance(channel, TeamTalkChannel) else channel

        sdk_func = getattr(sdk, func) if isinstance(func, str) else func

        return cast("int", sdk_func(self._tt, user_id, channel_id))
