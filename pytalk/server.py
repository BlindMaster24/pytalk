"""Provides the Server class for interacting with a TeamTalk5 server."""

import ctypes
from typing import TYPE_CHECKING

from ._utils import _get_tt_obj_attribute, _set_tt_obj_attribute, _tt_attr_to_py_attr
from .channel import Channel as TeamTalkChannel
from .enums import TeamTalkServerInfo
from .exceptions import PytalkPermissionError
from .implementation.TeamTalkPy import TeamTalk5 as sdk

if TYPE_CHECKING:
    from .instance import TeamTalkInstance
from .permission import Permission
from .user import User as TeamTalkUser

if TYPE_CHECKING:
    from .statistics import Statistics as TeamTalkServerStatistics


class Server:
    """Represents a TeamTalk5 server.

    Attributes:
        teamtalk_instance: An instance of pytalk.TeamTalkInstance.
        info: The server information.

    """

    def __init__(
        self, teamtalk_instance: "TeamTalkInstance", server_info: TeamTalkServerInfo
    ) -> None:
        """Initialize a Server instance.

        Args:
            teamtalk_instance: An instance of pytalk.TeamTalkInstance.
            server_info: The server information.

        """
        self.teamtalk_instance = teamtalk_instance
        self.info = server_info

    def send_message(self, content: str, **kwargs: object) -> int:
        """Send a message to all users on the server, using a broadcast message.

        Args:
            content: The content of the message.
            **kwargs: Keyword arguments. See pytalk.TeamTalkInstance.send_message for
                more information.

        Returns:
            The result of the doTextMessage call.

        Raises:
            PytalkPermissionError: If the user is not an admin.

        """
        if not self.teamtalk_instance.is_admin():
            raise PytalkPermissionError(
                "You must be an admin to send messages to the server"
            )
        msg = sdk.TextMessage()
        msg.nMsgType = sdk.TextMsgType.MSGTYPE_BROADCAST
        msg.nFromUserID = self.teamtalk_instance.getMyUserID()
        msg.szFromUsername = self.teamtalk_instance.getMyUserAccount().szUsername
        msg.nToUserID = 0
        msg.szMessage = sdk.ttstr(content)
        msg.bMore = False
        # get a pointer to our message
        return self.teamtalk_instance._send_message(msg, **kwargs)

    def ping(self) -> bool:
        """Pings the server.

        Returns:
            True if the ping is successful, False otherwise.

        """
        return self.teamtalk_instance.super._DoPing(self.info.nServerPort)

    def get_users(self) -> list:
        """Get a list of users on the server.

        Returns:
            A list of pytalk.User instances representing the users on the server.

        """
        users = self.teamtalk_instance.super.getServerUsers()
        return [TeamTalkUser(self.teamtalk_instance, user) for user in users]

    def get_channels(self) -> list:
        """Get a list of channels on the server.

        Returns:
            A list of pytalk.Channel instances representing the channels on the server.

        """
        channels = self.teamtalk_instance.super.getServerChannels()
        return [
            TeamTalkChannel(self.teamtalk_instance, channel) for channel in channels
        ]

    def get_channel(self, channel_id: int) -> TeamTalkChannel:
        """Get the channel with the specified ID.

        Args:
            channel_id: The ID of the channel.

        Returns:
            The pytalk.Channel instance representing the channel with the specified ID.

        """
        channel = self.teamtalk_instance.super.getChannel(channel_id)
        return TeamTalkChannel(self.teamtalk_instance, channel)

    def get_user(self, user_id: int) -> TeamTalkUser:
        """Get the user with the specified ID.

        Args:
            user_id: The ID of the user.

        Returns:
            The pytalk.User instance representing the user with the specified ID.

        """
        user = self.teamtalk_instance.super.getUser(user_id)
        return TeamTalkUser(self.teamtalk_instance, user)

    def join_channel(
        self, channel: TeamTalkChannel | str | int, password: str = ""
    ) -> bool:
        """Join the specified channel.

        Args:
            channel: The channel to join.
            password: The password for the channel, if required.

        Returns:
            True if the channel was joined successfully, False otherwise.

        """
        _channel = None
        if isinstance(channel, str):
            if not channel.strip():
                return False
            if not channel.endswith("/"):
                channel += "/"
            _channel = self.teamtalk_instance.get_channel_from_path(channel)
        elif isinstance(channel, int):
            _channel = self.get_channel(channel)
        elif isinstance(channel, TeamTalkChannel):
            _channel = channel
        if _channel is None:
            return False
        return self.teamtalk_instance.join_channel(_channel, password)

    def get_statistics(self, timeout: int = 2) -> "TeamTalkServerStatistics":
        """Get the server statistics.

        Args:
            timeout: The time to wait before assuming that getting the servers
                statistics failed.

        Returns:
            The pytalk.Statistics instance representing the servers statistics.

        """
        return self.teamtalk_instance.get_server_statistics(timeout)

    def move_user(
        self, user: TeamTalkUser | int, channel: TeamTalkChannel | int
    ) -> None:
        """Move the specified user to the specified channel.

        Args:
            user: The user to move.
            channel: The channel to move the user to.

        Raises:
            PytalkPermissionError: If the user is not an admin.

        """
        if not self.teamtalk_instance.is_admin():
            raise PytalkPermissionError("You must be an admin to move users")
        if isinstance(user, TeamTalkUser):
            user = user.id
        if isinstance(channel, TeamTalkChannel):
            channel = channel.id
        self.teamtalk_instance.move_user(user, channel)

    def kick(self, user: TeamTalkUser | int) -> None:
        """Kicks the specified user from the specified channel.

        Args:
            user: The user to kick.

        Raises:
            PytalkPermissionError: If the user is not an admin.

        """
        self.teamtalk_instance.kick_user(user, 0)

    def ban(self, user: TeamTalkUser | int) -> None:
        """Bans the specified user from the specified channel.

        Args:
            user: The user to ban.

        Raises:
            PytalkPermissionError: If the user is not an admin.

        """
        self.teamtalk_instance.ban_user(user, 0)

    def unban(self, user: TeamTalkUser | int) -> None:
        """Unbans the specified user from the specified channel.

        Args:
            user: The user to unban.

        Raises:
            PytalkPermissionError: If the user is not an admin.

        """
        self.teamtalk_instance.unban_user(user, 0)

    def subscribe(self, subscription: object) -> None:
        """Subscribe to the specified subscription for all users on the server.

        Args:
            subscription: The subscription to subscribe to.

        """
        users = self.get_users()
        for user in users:
            user.subscribe(subscription)

    def unsubscribe(self, subscription: object) -> None:
        """Unsubscribes to the specified subscription for all users on the server.

        Args:
            subscription: The subscription to unsubscribe to.

        """
        users = self.get_users()
        for user in users:
            user.unsubscribe(subscription)

    def get_properties(self) -> "ServerProperties":
        """Get the properties of the server.

        Returns:
            A pytalk.ServerProperties instance representing the properties of the
            server.

        """
        props = self.teamtalk_instance.super.getServerProperties()
        return ServerProperties(self.teamtalk_instance, props)

    def update_properties(self, properties: "ServerProperties") -> None:
        """Update the properties of the server.

        Args:
            properties: The updated properties. See pytalk.ServerProperties for more
                information.

        Raises:
            PytalkPermissionError: If the bot does not have the permission to update the
                properties.

        """
        if not self.teamtalk_instance.has_permission(
            Permission.UPDATE_SERVERPROPERTIES
        ):
            raise PytalkPermissionError(
                "The bot does not have permission to update the server properties"
            )
        # get the underlying properties object
        properties = properties.properties
        sdk._DoUpdateServer(self.teamtalk_instance._tt, ctypes.byref(properties))

    def __getattr__(self, name: str) -> object:
        """Try to get the specified attribute on server.

        Args:
            name: The name of the attribute.

        Returns:
            The value of the specified attribute.

        Raises:
            AttributeError: If the specified attribute is not found. This is the
                default behavior.

        """
        if name in dir(self):
            return self.__dict__[name]
        return getattr(self.info, name)


class _ServerPropertiesMeta(type):
    def __dir__(cls) -> list[str]:
        """Get the list of attributes on properties.

        Returns:
            A list of attributes on properties.

        """
        return [
            _tt_attr_to_py_attr(attr)
            for attr in dir(sdk.ServerProperties)
            if not attr.startswith("_")
        ]


class ServerProperties(metaclass=_ServerPropertiesMeta):
    """Represents the properties of a server.

    This class should not be instantiated directly. Instead, use the
    pytalk.Server.get_properties() method.

    Example:
        >>> server = teamtalk server
        >>> properties = server.get_properties()
        >>> properties.max_users
        1000
        >>> properties.max_users = 500
        >>> server.update_properties(properties)
        >>> properties = server.get_properties()
        >>> properties.max_users
        500

    """

    def __init__(
        self, teamtalk_instance: "TeamTalkInstance", properties: object
    ) -> None:
        """Initialize a new instance of the ServerProperties class.

        Args:
            teamtalk_instance: The pytalk.TeamTalk instance.
            properties: The underlying properties object.

        """
        self.teamtalk_instance = teamtalk_instance
        self.properties = properties

    def __getattr__(self, name: str) -> object:
        """Try to get the specified attribute on server.

        Args:
            name: The name of the attribute.

        Returns:
            The value of the specified attribute.

        Raises:
            AttributeError: If the specified attribute is not found. This is the
                default behavior.

        """
        if name in dir(self):
            return self.__dict__[name]
        return _get_tt_obj_attribute(self.properties, name)

    def __setattr__(self, name: str, value: object) -> None:
        """Try to set the specified attribute on properties.

        Args:
            name: The name of the attribute.
            value: The value to set the attribute to.

        Raises:
                AttributeError: If the specified attribute is not found.

        """
        if name in dir(self) or name in ["teamtalk_instance", "properties"]:
            self.__dict__[name] = value
        else:
            _get_tt_obj_attribute(self.properties, name)
            # if we have gotten here, we can set the attribute
            _set_tt_obj_attribute(self.properties, name, value)
