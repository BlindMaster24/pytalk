"""This module contains the TeamTalkInstance class.

The TeamTalkInstance class contains one instance of a connection to a TeamTalkServer.
It is used to send and receive messages, join and leave channels, and perform other actions.
In addition, it's also here that events are dispatched.
"""

import asyncio
import ctypes
import logging
import os
import threading
import time
from typing import List, Optional, Union

from ._utils import (
    _do_after,
    _waitForCmd,
    _waitForEvent,
    percent_to_ref_volume,
    ref_volume_to_percent,
)
from .audio import (
    AudioBlock,
    MuxedAudioBlock,
    _AcquireUserAudioBlock,
    _ReleaseUserAudioBlock,
)
from .channel import Channel as TeamTalkChannel
from .channel import ChannelType
from .codec import CodecType
from .device import SoundDevice
from .enums import TeamTalkServerInfo, Status, UserType
from .exceptions import PermissionError
from .implementation.TeamTalkPy import TeamTalk5 as sdk
from .message import BroadcastMessage, ChannelMessage, CustomMessage, DirectMessage
from .permission import Permission
from .server import Server as TeamTalkServer
from .statistics import Statistics as TeamTalkServerStatistics
from .subscription import Subscription
from .tt_file import RemoteFile
from .user import User as TeamTalkUser
from .user_account import BannedUserAccount as TeamTalkBannedUserAccount
from .user_account import UserAccount as TeamTalkUserAccount


_log = logging.getLogger(__name__)


class TeamTalkInstance(sdk.TeamTalk):
    """Represents a TeamTalk5 instance."""

    def __init__(self, bot, server_info: TeamTalkServerInfo) -> None:
        """Initializes a pytalk.TeamTalkInstance instance.

        Args:
            bot: The pytalk.Bot instance.
            server_info: The server info for the server we wish to connect to.
        """
        # put the super class in a variable so we can call it later
        self.super = super()
        # call the super class's __init__ method
        self.super.__init__()
        # set the bot
        self.bot = bot
        # set the server info
        self.server_info = server_info
        self.server = TeamTalkServer(self, server_info)
        self.channel = lambda: self.get_channel(self.super.getMyChannelID())
        self.connected = False
        self.logged_in = False
        self.init_time = time.time()
        self.user_accounts = []
        self.banned_users = []
        self._current_input_device_id: Optional[int] = -1
        self._audio_sdk_lock = threading.Lock()

    def connect(self) -> bool:
        """Connects to the server. This doesn't return until the connection is successful or fails.

        Returns:
            bool: True if the connection was successful, False otherwise.
        """
        if not self.super.connect(
            sdk.ttstr(self.server_info.host),
            self.server_info.tcp_port,
            self.server_info.udp_port,
            bEncrypted=self.server_info.encrypted,
        ):
            return False
        result, msg = _waitForEvent(self.super, sdk.ClientEvent.CLIENTEVENT_CON_SUCCESS)
        if not result:
            return False
        self.bot.dispatch("my_connect", self.server)
        self.connected = True
        self.init_time = time.time()
        return True

    def login(self, join_channel_on_login: bool = True) -> bool:
        """Logs in to the server. This doesn't return until the login is successful or fails.

        Args:
            join_channel_on_login: Whether to join the channel on login or not.

        Returns:
            bool: True if the login was successful, False otherwise.
        """
        self.super.doLogin(
            sdk.ttstr(self.server_info.nickname),
            sdk.ttstr(self.server_info.username),
            sdk.ttstr(self.server_info.password),
            sdk.ttstr(self.bot.client_name),
        )
        result, msg = _waitForEvent(self.super, sdk.ClientEvent.CLIENTEVENT_CMD_MYSELF_LOGGEDIN)
        if not result:
            return False
        self.bot.dispatch("my_login", self.server)
        self.logged_in = True
        #        self.super.initSoundInputDevice(1978)
        #        self.super.initSoundOutputDevice(1978)
        if join_channel_on_login:
            channel_id_to_join = self.server_info.join_channel_id
            if channel_id_to_join > 0:  # Only join if channel_id is strictly positive
                self.join_channel_by_id(channel_id_to_join)
            # If channel_id_to_join is 0 or negative, nothing happens.
        self.init_time = time.time()
        return True

    def logout(self):
        """Logs out of the server."""
        self.super.doLogout()
        self.logged_in = False

    def disconnect(self):
        """Disconnects from the server."""
        self.super.disconnect()
        self.connected = False

    def change_nickname(self, nickname: str):
        """Changes the nickname of the bot.

        Args:
            nickname: The new nickname.
        """
        self.super.doChangeNickname(sdk.ttstr(nickname))

    def change_status(self, status_flags: int, status_message: str) -> None:
        """Changes the status of the bot using combined status flags.

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
        current_user_obj = self.get_user(self.super.getMyUserID())
        current_full_status_mode = current_user_obj.status_mode

        new_mode_bits = status_flags & Status._MODE_MASK
        new_gender_bits = status_flags & Status._GENDER_MASK

        other_flags_mask = ~(Status._MODE_MASK | Status._GENDER_MASK)
        preserved_other_flags = current_full_status_mode & other_flags_mask

        final_status = new_mode_bits | new_gender_bits | preserved_other_flags

        self.super.doChangeStatus(final_status, sdk.ttstr(status_message))

    def get_sound_devices(self) -> List[SoundDevice]:
        """Gets the list of available TeamTalk sound devices, marking the default input.

        Returns:
            A list of SoundDevice objects representing the available devices.
            Returns an empty list if the SDK call fails.
        """
        default_in_id = -1
        try:
            defaults = self.super.getDefaultSoundDevices()
            if defaults:
                if isinstance(defaults, (tuple, list)) and len(defaults) == 2:
                    default_in_id, _ = defaults
                else:
                    _log.warning(f"Unexpected return type from getDefaultSoundDevices: {type(defaults)}")
            else:
                _log.warning(f"Call to getDefaultSoundDevices returned None or False for instance {self.server_info.host}")
        except Exception as e:
            _log.exception(f"Error getting default sound devices for instance {self.server_info.host}: {e}")

        sdk_devices = self.super.getSoundDevices()
        if not sdk_devices:
            _log.warning(f"Failed to get sound device list via superclass for instance {self.server_info.host}")
            return []

        devices = [SoundDevice(dev, is_default_input=(dev.nDeviceID == default_in_id)) for dev in sdk_devices]
        return devices

    def get_current_input_device_id(self) -> Optional[int]:
        """Gets the ID of the currently active input device for this instance.

        Note:
            This returns the ID that was stored when the input device was
            last initialized or set for this instance using set_input_device.
            It does not query the SDK directly for the current device.

        Returns:
            The ID of the current input device, or -1 if not set or unknown.
        """
        return self._current_input_device_id

    def set_input_device(self, device_id_or_name: Union[int, str]) -> bool:
        """Sets and initializes the input device for this instance.

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

        if isinstance(device_id_or_name, str) and device_id_or_name.lower() == "default":
            _log.debug(f"Attempting to set default input device for instance {self.server_info.host}")
            try:
                defaults = self.super.getDefaultSoundDevices()
                if defaults and isinstance(defaults, (tuple, list)) and len(defaults) == 2:
                    target_device_id = defaults[0]
                    if target_device_id < 0:
                        _log.error(
                            f"System returned invalid default input device ID ({target_device_id}) "
                            f"for instance {self.server_info.host}"
                        )
                        return False
                    _log.info(f"Resolved 'default' to input device ID: {target_device_id}")
                else:
                    _log.error(f"Could not determine default input device for instance {self.server_info.host}")
                    return False
            except Exception as e:
                _log.exception(f"Error getting default sound devices when setting 'default': {e}")
                return False
        else:
            try:
                target_device_id = int(device_id_or_name)
            except ValueError:
                raise ValueError("Input must be int ID or 'default'")
            except TypeError:
                raise ValueError("Input must be int ID or 'default'")

        _log.debug(f"Setting input device for instance {self.server_info.host} to ID: {target_device_id}")
        sdk._CloseSoundInputDevice(self._tt)
        success = sdk._InitSoundInputDevice(self._tt, target_device_id)

        if success:
            self._current_input_device_id = target_device_id
            _log.info(f"Successfully set input device for instance {self.server_info.host} to ID: {target_device_id}")
        else:
            self._current_input_device_id = -1
            _log.error(f"Failed to set input device for instance {self.server_info.host} to ID: {target_device_id}")
        return success

    def enable_voice_transmission(self, enabled: bool) -> bool:
        """Enables or disables voice transmission state for this instance.

        Args:
            enabled: True to enable voice transmission, False to disable it.

        Returns:
            True if the SDK call was successful, False otherwise.
        """
        action = "Enabling" if enabled else "Disabling"
        _log.debug(f"{action} voice transmission for instance {self.server_info.host}")
        success = self.super.enableVoiceTransmission(enabled)
        if not success:
            _log.error(f"Failed to {action.lower()} voice transmission for instance {self.server_info.host}")
        return success

    def get_input_volume(self) -> int:
        """Gets the current input gain level as percentage (0-100).

        Matches the TeamTalk Qt client's user volume scaling.

        Returns:
            int: The volume percentage (0-100). Returns 0 if the SDK call fails.
        """
        sdk_gain = sdk._GetSoundInputGainLevel(self._tt)
        if sdk_gain < 0:
            _log.warning(f"Could not get input gain for instance {self.server_info.host}, SDK returned {sdk_gain}")
            return 0
        return ref_volume_to_percent(sdk_gain)

    def set_input_volume(self, percentage: int) -> bool:
        """Sets the input gain level from a percentage (0-100).

        Matches the TeamTalk Qt client's user volume scaling.

        Args:
            percentage (int): The desired volume percentage (0-100).

        Returns:
            bool: True on success, False otherwise.

        Raises:
            ValueError: If percentage is out of range (0-100).
        """
        if not 0 <= percentage <= 100:
            raise ValueError("Percentage must be between 0 and 100")

        internal_volume = percent_to_ref_volume(float(percentage))

        _log.debug(
            f"Setting input volume for instance {self.server_info.host} to {percentage}% (internal: {internal_volume})"
        )
        success = sdk._SetSoundInputGainLevel(self._tt, internal_volume)
        if not success:
            _log.error(f"Failed to set input volume for instance {self.server_info.host}")
        return success

    # Media File Streaming Functions
    def start_streaming_media_file_to_channel(self, path: str, video_codec: Optional[sdk.VideoCodec] = None) -> bool:
        """Starts streaming a media file to the channel.

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

        return self.super.startStreamingMediaFileToChannel(sdk.ttstr(path), ctypes.byref(codec_to_use))

    def stop_streaming_media_file_to_channel(self) -> bool:
        """Stops the current media file streaming to the channel.

        Returns:
            bool: True if the streaming stopped successfully, False otherwise.
        """
        return self.super.stopStreamingMediaFileToChannel()

    # permission stuff
    def has_permission(self, permission: Permission) -> bool:
        """Checks if the bot has a permission.

        If the user is an admin, they have all permissions.

        Args:
            permission: The permission to check for.

        Returns:
            bool: True if the bot has the permission, False otherwise.
        """
        user = self.super.getMyUserAccount()
        # first check if they are an admin
        if user.uUserType == sdk.UserType.USERTYPE_ADMIN:
            return True
        user_rights = user.uUserRights
        return (user_rights & permission) == permission

    def is_admin(self) -> bool:
        """Checks if the bot is an admin.

        Returns:
            bool: True if the bot is an admin, False otherwise.
        """
        return self.is_user_admin(self.super.getMyUserID())

    def is_user_admin(self, user: Union[TeamTalkUser, int]) -> bool:
        """Checks if a user is an admin.

        Args:
            user: The user to check.

        Returns:
            bool: True if the user is an admin, False otherwise.

        Raises:
            TypeError: If the user is not of type pytalk.User or int.
        """
        if isinstance(user, int):
            user = self.super.getUser(user)
            return user.uUserType == sdk.UserType.USERTYPE_ADMIN
        if isinstance(user, TeamTalkUser):
            return user.user_type == sdk.UserType.USERTYPE_ADMIN
        raise TypeError("User must be of type pytalk.User or int")

    # Subscription stuff
    def subscribe(self, user: TeamTalkUser, subscription: Subscription):
        """Subscribes to a subscription.

        Args:
            user: The user to subscribe to.
            subscription: The subscription to subscribe to.
        """
        sdk._DoSubscribe(self._tt, user.id, subscription)

    def unsubscribe(self, user: TeamTalkUser, subscription: Subscription):
        """Unsubscribes from a subscription.

        Args:
            user: The user to unsubscribe from.
            subscription: The subscription to unsubscribe from.
        """
        sdk._DoUnsubscribe(self._tt, user.id, subscription)

    def is_subscribed(self, subscription: Subscription) -> bool:
        """Checks if the bot is subscribed to a subscription.

        Args:
            subscription: The subscription to check.

        Returns:
            bool: True if the bot is subscribed to the subscription, False otherwise.
        """
        current_subscriptions = self._get_my_user().local_subscriptions
        # it's a bitfield so we can just check if the subscription is in the bitfield
        return (current_subscriptions & subscription) == subscription

    def join_root_channel(self):
        """Joins the root channel."""
        self.join_channel_by_id(self.super.getRootChannelID())

    def join_channel_by_id(self, id: int, password: str = ""):
        """Joins a channel by its ID.

        Args:
            id: The ID of the channel to join.
            password: The password of the channel to join.
        """
        self.super.doJoinChannelByID(id, sdk.ttstr(password))

    def join_channel(self, channel: TeamTalkChannel):
        """Joins a channel.

        Args:
            channel: The channel to join.
        """
        self.super.doJoinChannelByID(channel.id, channel.password)

    def leave_channel(self):
        """Leaves the current channel."""
        self.super.doLeaveChannel()

    def get_channel(self, channel_id: int) -> TeamTalkChannel:
        """Gets a channel by its ID.

        Args:
            channel_id: The ID of the channel to get.

        Returns:
            TeamTalkChannel: The channel.
        """
        return TeamTalkChannel(self, channel_id)

    def get_path_from_channel(self, channel: Union[TeamTalkChannel, int]) -> str:
        """Gets the path of a channel.

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
        # variable to hold the path
        path = sdk.TTCHAR()
        result = sdk._GetChannelPath(self.super, channel, path)
        if not result:
            raise ValueError("Channel not found")
        return path.value

    def get_channel_from_path(self, path: str) -> TeamTalkChannel:
        """Gets a channel by its path.

        Args:
            path: The path of the channel to get.

        Returns:
            TeamTalkChannel: The channel.

        Raises:
            ValueError: If the channel is not found.
        """
        result = sdk._GetChannelIDFromPath(self._tt, sdk.ttstr(path))
        if result == 0:
            raise ValueError("Channel not found")
        return TeamTalkChannel(self, result)

    # create a channel. Take in a name, parent channel. Optionally take in a topic, password and channel type
    def create_channel(
        self,
        name: str,
        parent_channel: Union[TeamTalkChannel, int],
        topic: str = "",
        password: str = "",
        channel_type: ChannelType = ChannelType.CHANNEL_DEFAULT,
    ) -> bool:
        """Creates a channel.

        Args:
            name: The name of the channel to create.
            parent_channel: The parent channel of the channel.
            topic: The topic of the channel.
            password: The password of the channel. Leave empty for no password.
            channel_type: The type of the channel. Defaults to CHANNEL_DEFAULT.

        Raises:
            PermissionError: If the bot does not have permission to create channels.
            ValueError: If the channel could not be created.

        Returns:
            bool: True if the channel was created, False otherwise.
        """
        if not self.has_permission(Permission.MODIFY_CHANNELS):
            raise PermissionError("The bot does not have permission to create channels")
        if isinstance(parent_channel, TeamTalkChannel):
            parent_channel = parent_channel.id
        new_channel = sdk.Channel()
        new_channel.nParentID = parent_channel
        new_channel.szName = sdk.ttstr(name)
        new_channel.szTopic = sdk.ttstr(topic)
        new_channel.szPassword = sdk.ttstr(password)
        new_channel.bPassword = password != ""
        new_channel.uChannelType = channel_type
        result = sdk._DoMakeChannel(self._tt, new_channel)
        if result == -1:
            raise ValueError("Channel could not be created")
        cmd_result, cmd_err = _waitForCmd(self.super, result, 2000)
        if not cmd_result:
            err_nr = cmd_err.nErrorNo
            if err_nr == sdk.ClientError.CMDERR_NOT_LOGGEDIN:
                raise PermissionError("The bot is not logged in")
            if err_nr == sdk.ClientError.CMDERR_NOT_AUTHORIZED:
                raise PermissionError("The bot does not have permission to create channels")
            if err_nr == sdk.ClientError.CMDERR_CHANNEL_ALREADY_EXISTS:
                raise ValueError("Channel already exists")
            if err_nr == sdk.ClientError.CMDERR_CHANNEL_NOT_FOUND:
                raise ValueError("Combined channel path is too long. Try using a shorter channel name")
            if err_nr == sdk.ClientError.CMDERR_INCORRECT_CHANNEL_PASSWORD:
                raise ValueError("Channel password too long")
        return True

    def delete_channel(self, channel: Union[TeamTalkChannel, int]):
        """Deletes a channel.

        Args:
            channel: The channel to delete.

        Raises:
            TypeError: If the channel is not of type pytalk.Channel or int.
            PermissionError: If the bot doesn't have the permission to delete the channel.
            ValueError: If the channel is not found.

        Returns:
            bool: True if the channel was deleted.
        """
        if not self.has_permission(Permission.MODIFY_CHANNELS):
            raise PermissionError("The bot does not have permission to delete channels")
        if isinstance(channel, TeamTalkChannel):
            channel = channel.id
        result = sdk._DoRemoveChannel(self._tt, channel)
        if result == -1:
            raise ValueError("Channel could not be deleted")
        cmd_result, cmd_err = _waitForCmd(self.super, result, 2000)
        if not cmd_result:
            err_nr = cmd_err.nErrorNo
            if err_nr == sdk.ClientError.CMDERR_NOT_LOGGEDIN:
                raise PermissionError("The bot is not logged in")
            if err_nr == sdk.ClientError.CMDERR_NOT_AUTHORIZED:
                raise PermissionError("The bot does not have permission to delete channels")
            if err_nr == sdk.ClientError.CMDERR_CHANNEL_NOT_FOUND:
                raise ValueError("Channel not found.")
        return True

    def make_channel_operator(
        self, user: Union[TeamTalkUser, int], channel: Union[TeamTalkUser, int], operator_password: str = ""
    ) -> bool:
        """Makes a user the channel operator.

        Args:
            user: The user to make the channel operator.
            channel: The channel to make the user the channel operator in.
            operator_password: The operator password of the channel.

        Raises:
            TypeError: If the user or channel is not of type pytalk.User or int.
            PermissionError: If the bot doesn't have the permission to make a user the channel operator.
            ValueError: If the user or channel is not found.

        Returns:
            bool: True if the user was made the channel operator, False otherwise.
        """
        if isinstance(user, int):
            user = self.get_user(user)
        if isinstance(channel, int):
            channel = self.get_channel(channel)
        result = sdk.DoChannelOpEx(self.super, user.id, channel.id, sdk.ttstr(operator_password), True)
        if result == -1:
            raise PermissionError("The bot does not have the permission to make a user the channel operator")
            return False
        cmd_result, cmd_err = _waitForCmd(self.super, result, 2000)
        if not cmd_result:
            err_nr = cmd_err.nErrorNo
            if err_nr == sdk.ClientError.CMDERR_NOT_LOGGEDIN:
                raise PermissionError("The bot is not logged in")
            if err_nr == sdk.ClientError.CMDERR_NOT_AUTHORIZED:
                raise PermissionError("The bot does not have permission to make a user the channel operator")
            if err_nr == sdk.ClientError.CMDERR_CHANNEL_NOT_FOUND:
                raise ValueError("The channel does not exist")
            if err_nr == sdk.ClientError.CMDERR_USER_NOT_FOUND:
                raise ValueError("The user does not exist")
            if err_nr == sdk.ClientError.CMDERR_INCORRECT_OP_PASSWORD:
                raise ValueError("The operator password is incorrect")
            return False
        return True

    def remove_channel_operator(
        self, user: Union[TeamTalkUser, int], channel: Union[TeamTalkUser, int], operator_password: str = ""
    ) -> bool:
        """Removes a user as the channel operator.

        Args:
            user: The user to make the channel operator.
            channel: The channel to make the user the channel operator in.
            operator_password: The operator password of the channel.

        Raises:
            TypeError: If the user or channel is not of type pytalk.User or int.
            PermissionError: If the bot doesn't have the permission to make a user the channel operator.
            ValueError: If the channel or user does not exist.

        Returns:
            bool: True if the user was removed as the channel operator, False otherwise.
        """
        if isinstance(user, int):
            user = self.get_user(user)
        if isinstance(channel, int):
            channel = self.get_channel(channel)
        result = sdk.DoChannelOpEx(self.super, user.id, channel.id, sdk.ttstr(operator_password), False)
        if result == -1:
            raise PermissionError("The bot does not have the permission to make a user the channel operator")
            return False
        cmd_result, cmd_err = _waitForCmd(self.super, result, 2000)
        if not cmd_result:
            err_nr = cmd_err.nErrorNo
            if err_nr == sdk.ClientError.CMDERR_NOT_LOGGEDIN:
                raise PermissionError("The bot is not logged in")
            if err_nr == sdk.ClientError.CMDERR_NOT_AUTHORIZED:
                raise PermissionError("The bot does not have permission to make a user the channel operator")
            if err_nr == sdk.ClientError.CMDERR_CHANNEL_NOT_FOUND:
                raise ValueError("The channel does not exist")
            if err_nr == sdk.ClientError.CMDERR_USER_NOT_FOUND:
                raise ValueError("The user does not exist")
            if err_nr == sdk.ClientError.CMDERR_INCORRECT_OP_PASSWORD:
                raise ValueError("The operator password is incorrect")
            return False
        return True

    def get_user(self, user_id: int) -> TeamTalkUser:
        """Gets a user by its ID.

        Args:
            user_id: The ID of the user to get.

        Returns:
            TeamTalkUser: The user.
        """
        return TeamTalkUser(self, user_id)

    # user account stuff
    def create_user_account(
        self, username: str, password: str, usertype: UserType, user_rights: Optional[int] = None, note: str = ""
    ) -> bool:
        """Creates a user account on the server.

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
            PermissionError: If the bot lacks permission to create accounts
                or is not logged in.
        """
        account = sdk.UserAccount()
        account.szUsername = sdk.ttstr(username)
        account.szPassword = sdk.ttstr(password)
        account.uUserType = usertype
        account.szNote = sdk.ttstr(note)

        if user_rights is not None:
            account.uUserRights = user_rights

        result = sdk._DoNewUserAccount(self._tt, account)
        if result == -1:
            raise ValueError("Username or password is invalid")
        cmd_result, cmd_err = _waitForCmd(self.super, result, 2000)
        if not cmd_result:
            err_nr = cmd_err.nErrorNo
            if err_nr == sdk.ClientError.CMDERR_INVALID_USERNAME:
                raise ValueError("Username is invalid")
            if err_nr == sdk.ClientError.CMDERR_NOT_AUTHORIZED:
                raise PermissionError("The bot does not have permission to create a user account")
            if err_nr == sdk.ClientError.CMDERR_NOT_LOGGEDIN:
                raise PermissionError("The bot is not logged in")
        return True

    def delete_user_account(self, username: str) -> bool:
        """Deletes a user account.

        Args:
            username: The username of the user account to delete.

        Returns:
            bool: True if the user account was deleted, False otherwise.

        Raises:
            ValueError: If the username is empty or the user account does not exist.
            PermissionError: If the user does not have permission to delete a user account.
        """
        if not username:
            raise ValueError("Username is empty")
        username = sdk.ttstr(username)
        result = sdk._DoDeleteUserAccount(self._tt, username)
        if result == -1:
            raise ValueError("User account does not exist")
        cmd_result, cmd_err = _waitForCmd(self.super, result, 2000)
        if not cmd_result:
            err_nr = cmd_err.nErrorNo
            if err_nr == sdk.ClientError.CMDERR_NOT_AUTHORIZED:
                raise PermissionError("The bot does not have permission to delete a user account")
            if err_nr == sdk.ClientError.CMDERR_NOT_LOGGEDIN:
                raise PermissionError("The bot is not logged in")
            if err_nr == sdk.ClientError.CMDERR_ACCOUNT_NOT_FOUND:
                raise ValueError("User account does not exist")
        return True

    async def list_user_accounts(self) -> List[TeamTalkUserAccount]:
        """Lists all user accounts on the server.

        Returns:
            A list of all user accounts.

        Raises:
            PermissionError: If the bot is not an admin.
            ValueError: If an unknown error occurred.
        """
        if not self.is_admin():
            raise PermissionError("The bot is not an admin")
        self.user_accounts = []
        result = sdk._DoListUserAccounts(self._tt, 0, 1000000)
        if result == -1:
            raise ValueError("Unknown error")
        await asyncio.sleep(1)
        return self.user_accounts

    # file stuff
    def upload_file(self, channel_id: int, filepath: str) -> None:
        """Uploads a local file to a channel.

        Args:
            channel_id: The ID of the channel to upload the file to.
            filepath: The path to the local file to upload.

        Raises:
            PermissionError: If the bot does not have permission to upload files.
            ValueError: If the channel ID is less than 0.
            FileNotFoundError: If the local file does not exist.
        """
        if not self.has_permission(Permission.UPLOAD_FILES):
            raise PermissionError("You do not have permission to upload files")
        if channel_id < 0:
            raise ValueError("Channel ID must be greater than 0")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File {filepath} does not exist")
        self.super.doSendFile(channel_id, sdk.ttstr(filepath))

    def download_file(self, channel_id: int, remote_file_name: str, local_file_path: str) -> None:
        """Downloads a remote file from a channel.

        Args:
            channel_id: The ID of the channel to download the file from.
            remote_file_name: The name of the remote file to download.
            local_file_path: The path to save the file to.

        Raises:
            PermissionError: If the bot does not have permission to download files.
            ValueError: If the channel ID is less than 0.
        """
        if not self.has_permission(Permission.DOWNLOAD_FILES):
            raise PermissionError("You do not have permission to download files")
        if channel_id < 0:
            raise ValueError("Channel ID must be greater than 0")
        remote_files = self.get_channel_files(channel_id)
        # loop through files and print the name
        for file in remote_files:
        if ttstr(file.file_name) == remote_file_name:
                self.download_file_by_id(channel_id, file.file_id, local_file_path)

    def download_file_by_id(self, channel_id: int, file_id: int, filepath: str):
        """Downloads a remote file from a channel by its ID.

        Args:
            channel_id: The ID of the channel to download the file from.
            file_id: The ID of the file to download.
            filepath: The path to save the file to.

        Raises:
            PermissionError: If the bot does not have permission to download files.
        """
        if not self.has_permission(Permission.DOWNLOAD_FILES):
            raise PermissionError("You do not have permission to download files")
        self.super.doRecvFile(channel_id, file_id, sdk.ttstr(filepath))

    def delete_file_by_id(self, channel_id: int, file_id: int):
        """Deletes a remote file from a channel by its ID.

        Args:
            channel_id: The ID of the channel to delete the file from.
            file_id: The ID of the file to delete.

        Raises:
            PermissionError: If the bot does not have permission to delete files.
        """
        if not self.is_admin(self.super.getMyUserID()):
            raise PermissionError("You do not have permission to delete files")
        self.super.doDeleteFile(channel_id, file_id)

    def get_channel_files(self, channel_id: int) -> List[RemoteFile]:
        """Gets a list of remote files in a channel.

        Args:
            channel_id: The ID of the channel to get the files from.

        Returns:
            List[RemoteFile]: A list of remote files in the channel.
        """
        files = self.super.getChannelFiles(channel_id)
        return [RemoteFile(self, file) for file in files]

    def move_user(self, user: Union[TeamTalkUser, int], channel: Union[TeamTalkChannel, int]) -> None:
        """Moves a user to a channel.

        Args:
            user: The user to move.
            channel: The channel to move the user to.

        Raises:
            PermissionError: If the bot does not have permission to move users.
            TypeError: If the user or channel is not a subclass of User or Channel.
        """
        if not self.has_permission(Permission.MOVE_USERS):
            raise PermissionError("You do not have permission to move users")
        _log.debug(f"Moving user {user} to channel {channel}")
        self._do_cmd(user, channel, "_DoMoveUser")

    def kick_user(self, user: Union[TeamTalkUser, int], channel: Union[TeamTalkChannel, int]) -> None:
        """Kicks a user from a channel or the server.

        Args:
            user: The user to kick.
            channel: The channel to kick the user from. If 0, the user will be kicked from the server. # noqa

        Raises:
            PermissionError: If the bot does not have permission to kick users.
            TypeError: If the user or channel is not a subclass of User or Channel.
            ValueError: If the user or channel is not found.
        """
        # first check if we are kicking from channel or server
        if channel == 0:  # server
            if not self.has_permission(Permission.KICK_USERS):
                raise PermissionError("You do not have permission to kick users")
            _log.debug(f"Kicking user {user} from channel {channel}")
            self._do_cmd(user, channel, "_DoKickUser")
        else:  # channel
            if not self.has_permission(Permission.KICK_USERS_FROM_CHANNEL) and not sdk._IsChannelOperator(
                self._tt, self.super.getMyUserID(), channel
            ):
                raise PermissionError("You do not have permission to kick users from channels")
            result = self._do_cmd(user, channel, "_DoKickUser")
        if result == -1:
            raise ValueError("Uknown error")
            cmd_result, cmd_err = _waitForCmd(self.super, result, 2000)
            if not cmd_result:
                err_nr = cmd_err.nErrorNo
                if err_nr == sdk.ClientError.CMDERR_USER_NOT_FOUND:
                    raise ValueError("User not found")
                if err_nr == sdk.ClientError.CMDERR_CHANNEL_NOT_FOUND:
                    raise ValueError("Channel not found")
            return cmd_result

    def ban_user(self, user: Union[TeamTalkUser, int], channel: Union[TeamTalkChannel, int]) -> None:
        """Bans a user from a channel or the server.

        Args:
            user: The user to ban.
            channel: The channel to ban the user from. If 0, the user will be banned from the server. # noqa

        Raises:
            PermissionError: If the bot does not have permission to ban users.
            TypeError: If the user or channel is not a subclass of User or Channel.
            ValueError: If the user is not found.
        """
        if not self.has_permission(Permission.BAN_USERS):
            raise PermissionError("You do not have permission to ban users")
        _log.debug(f"Banning user {user} from channel {channel}")
        result = self._do_cmd(user, channel, "_DoBanUser")
        if result == -1:
            raise ValueError("Uknown error")
            cmd_result, cmd_err = _waitForCmd(self.super, result, 2000)
            if not cmd_result:
                err_nr = cmd_err.nErrorNo
                if err_nr == sdk.ClientError.CMDERR_USER_NOT_FOUND:
                    raise ValueError("User not found")
            return cmd_result

    def unban_user(self, ip: str, channel: Union[TeamTalkChannel, int]) -> None:
        """Unbans a user from the server.

        Args:
            ip: The IP address of the user to unban.
            channel: The channel to unban the user from. If 0, the user will be unbanned from the server. # noqa

        Raises:
            PermissionError: If the bot does not have permission to unban users.
        """
        if not self.has_permission(Permission.UNBAN_USERS):
            raise PermissionError("You do not have permission to unban users")
        if not isinstance(ip, str):
            raise TypeError("IP must be a string")
        if not isinstance(channel, (TeamTalkChannel, int)):
            raise TypeError("Channel must be a subclass of Channel or a channel ID")
        channel_id = channel
        if isinstance(channel, TeamTalkChannel):
            channel_id = channel.id
        _log.debug(f"Unbanning user {ip}")
        sdk._DoUnBanUser(self._tt, sdk.ttstr(ip), channel_id)

    async def list_banned_users(self) -> List[TeamTalkBannedUserAccount]:
        """Lists all banned users.

        Returns:
            List[BannedUserAccount]: A list of banned users.

        Raises:
            PermissionError: If the bot is not an admin.
            ValueError: If an unknown error occurs.
        """
        if not self.is_admin():
            raise PermissionError("The bot is not an admin")
        self.banned_users = []
        result = sdk._DoListBans(self._tt, 0, 0, 1000000)
        if result == -1:
            raise ValueError("Unknown error")
        await asyncio.sleep(1)
        return self.banned_users

    def get_server_statistics(self, timeout: int) -> TeamTalkServerStatistics:
        """
        Gets the statistics from the server.

        Args:
            timeout: The time to wait before assuming that getting the servers statistics failed.

        Raises:
            TimeoutError: If the server statistics are not received with in the given time.

        returns:
            The pytalk.statistics object representing the servers statistics.
        """
        sdk._DoQueryServerStats(self._tt)
        result, msg = _waitForEvent(self.super, sdk.ClientEvent.CLIENTEVENT_CMD_SERVERSTATISTICS, timeout)
        if not result:
            raise TimeoutError("The request for server statistics timed out.")
        return TeamTalkServerStatistics(self, msg.serverstatistics)

    def _send_message(self, message: sdk.TextMessage, **kwargs):
        """Sends a message.

        Args:
            message: The message to send.
            delay: The delay in seconds before sending the message. Defaults to 0 which means no delay. # noqa
            **kwargs: Keyword arguments. Reserved for future use.


        Raises:
            TypeError: If the message is not a subclass of Message.
        """
        if not isinstance(message, sdk.TextMessage):
            raise TypeError("Message must be a subclass of sdk.TextMessage")
        if not issubclass(type(message), sdk.TextMessage):
            raise TypeError("Message must be a subclass of sdk.TextMessage")
        delay = kwargs.get("delay", 0)
        _do_after(delay, lambda: self.super.doTextMessage(ctypes.POINTER(sdk.TextMessage)(message)))

    async def _process_events(self) -> None:  # noqa: C901
        """Processes events from the server. This is automatically called by pytalk.Bot."""
        msg = self.super.getMessage(100)
        event = msg.nClientEvent

        # Ignore Events
        if event == sdk.ClientEvent.CLIENTEVENT_NONE:
            return
        if event == sdk.ClientEvent.CLIENTEVENT_USER_FIRSTVOICESTREAMPACKET:
            return

        # My Events
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_MYSELF_KICKED:
            self.bot.dispatch("my_kicked_from_channel", TeamTalkChannel(self, msg.nSource))
            return
        if event == sdk.ClientEvent.CLIENTEVENT_CON_LOST:
            self.connected = False
            self.logged_in = False
            self.bot.dispatch("my_connection_lost", self.server)
            return

        # User Events
        if event == sdk.ClientEvent.CLIENTEVENT_USER_STATECHANGE:
            user_id = msg.user.nUserID
            current_user_state = msg.user.uUserState
            if current_user_state & sdk.UserState.USERSTATE_VOICE:
                sdk._EnableAudioBlockEventEx(self._tt, user_id, sdk.StreamType.STREAMTYPE_VOICE, None, True)
            else:
                sdk._EnableAudioBlockEventEx(self._tt, user_id, sdk.StreamType.STREAMTYPE_VOICE, None, False)
            return
        if event == sdk.ClientEvent.CLIENTEVENT_USER_AUDIOBLOCK:
            sdk_audio_block_ptr = None
            py_sdk_audio_block_struct_instance = None
            source_id = msg.nSource
            with self._audio_sdk_lock:
                stream_type_enum = sdk.StreamType(msg.nStreamType)
                sdk_audio_block_ptr = _AcquireUserAudioBlock(self._tt, stream_type_enum, source_id)
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
            py_audio_block_wrapper = None
            try:
                if source_id == sdk.TT_MUXED_USERID:
                    py_audio_block_wrapper = MuxedAudioBlock(py_sdk_audio_block_struct_instance)
                    self.bot.dispatch("muxed_audio", py_audio_block_wrapper)
                else:
                    user = TeamTalkUser(self, source_id)
                    py_audio_block_wrapper = AudioBlock(user, py_sdk_audio_block_struct_instance)
                    self.bot.dispatch("user_audio", py_audio_block_wrapper)
            except Exception as e:
                error_message = (
                    f"CLIENTEVENT_USER_AUDIOBLOCK: Error during Python wrapper creation or dispatch"
                    f" for source_id {source_id}. Error: {e}"
                )
                _log.exception(error_message)
            return
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_USER_JOINED:
            user_joined = TeamTalkUser(self, msg.user)
            if user_joined.id == self.super.getMyUserID():
                sdk._EnableAudioBlockEventEx(self._tt, sdk.TT_MUXED_USERID, sdk.StreamType.STREAMTYPE_VOICE, None, True)
            self.bot.dispatch("user_join", user_joined, user_joined.channel)
            return
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_USER_LEFT:
            user_left = TeamTalkUser(self, msg.user)
            channel_left_from = TeamTalkChannel(self, msg.nSource)
            if user_left.id == self.super.getMyUserID():
                sdk._EnableAudioBlockEventEx(self._tt, sdk.TT_MUXED_USERID, sdk.StreamType.STREAMTYPE_VOICE, None, False)
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

        # Message Event
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_USER_TEXTMSG:
            message = None
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

        # Channel Events
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_CHANNEL_NEW:
            self.bot.dispatch("channel_new", TeamTalkChannel(self, msg.channel))
            return
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_CHANNEL_UPDATE:
            self.bot.dispatch("channel_update", TeamTalkChannel(self, msg.channel))
            return
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_CHANNEL_REMOVE:
            self.bot.dispatch("channel_delete", TeamTalkChannel(self, msg.channel))
            return

        # File Events
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_FILE_NEW:
            self.bot.dispatch("file_new", RemoteFile(self, msg.remotefile))
            return
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_FILE_REMOVE:
            self.bot.dispatch("file_delete", RemoteFile(self, msg.remotefile))
            return

        # Server Events
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_SERVER_UPDATE:
            self.bot.dispatch("server_update", self.server)
            return
        if event == sdk.ClientEvent.CLIENTEVENT_CMD_SERVERSTATISTICS:
            self.bot.dispatch("server_statistics", TeamTalkServerStatistics(self, msg.serverstatistics))
            return

        # User Account Management Events
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
            ctypes.memmove(ctypes.byref(banned_user_struct), ctypes.byref(msg.useraccount), ctypes.sizeof(sdk.BannedUser))
            banned_user = TeamTalkBannedUserAccount(self, banned_user_struct)
            self.banned_users.append(banned_user)
            return

        # Other Unhandled Events
        if event not in (
            sdk.ClientEvent.CLIENTEVENT_CMD_PROCESSING,
            sdk.ClientEvent.CLIENTEVENT_CMD_ERROR,
            sdk.ClientEvent.CLIENTEVENT_CMD_SUCCESS,
            sdk.ClientEvent.CLIENTEVENT_AUDIOINPUT,
        ):
            _log.warning(f"Unhandled event: {event}")

    def _get_channel_info(self, channel_id: int):
        _channel = self.getChannel(channel_id)
        _channel_path = sdk.ttstr(self.getChannelPath(channel_id))
        return _channel, _channel_path

    def _get_my_permissions(self):
        return self.super._GetMyUserRights()

    def _get_my_user(self):
        return self.get_user(self.super.getMyUserID())

    def _do_cmd(self, user: Union[TeamTalkUser, int], channel: Union[TeamTalkChannel, int], func) -> None:
        if not self.has_permission(Permission.KICK_USERS):
            raise PermissionError("You do not have permission to kick users")
        if not isinstance(user, (TeamTalkUser, int)):
            raise TypeError("User must be a pytalk.User or a user id")
        if not isinstance(channel, (TeamTalkChannel, int)):
            raise TypeError("Channel must be a pytalk.Channel or a channel id")
        user_id = user
        if isinstance(user, TeamTalkUser):
            user_id = user.user_id
        channel_id = channel
        if isinstance(channel, TeamTalkChannel):
            channel_id = channel.id
        sdk_func = getattr(sdk, func)
        return sdk_func(self._tt, user_id, channel_id)
