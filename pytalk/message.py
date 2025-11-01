"""Module contains the Message class and its subclasses."""

from typing import TYPE_CHECKING, cast

from .exceptions import PytalkPermissionError
from .implementation.TeamTalkPy import TeamTalk5 as sdk

if TYPE_CHECKING:
    from .instance import TeamTalkInstance


class Message:
    """Represents a TeamTalk5 message.

    This class should not be instantiated directly.
    """

    def __init__(
        self, teamtalk_instance: "TeamTalkInstance", msg: sdk.TextMessage
    ) -> None:
        """Initialize a Message instance.

        Args:
            teamtalk_instance: An instance of pytalk.TeamTalkInstance.
            msg: The message.

        """
        self.teamtalk_instance = teamtalk_instance
        self.type = msg.nMsgType
        self.from_id = msg.nFromUserID
        self.to_id = msg.nToUserID
        self.content = sdk.ttstr(msg.szMessage)
        self.user = self.teamtalk_instance.get_user(self.from_id)

    def reply(self, content: str, **kwargs: object) -> None:
        """Reply to the message.

        The reply will be sent to the place where the message was sent from.
        Meaning that if the message was sent to a channel, the reply will be sent to
        the channel.
        If the message was sent to a user, the reply will be sent to the user.
        And if the message was a broadcast message, the reply will be sent to the
        server as a broadcast.

        Args:
            content: The content of the message.
            **kwargs: Keyword arguments. See pytalk.TeamTalkInstance.send_message for
                more information.

        Returns:
            The ID of the message if successful, or a negative value if unsuccessful.

        Raises:
            PytalkPermissionError: If the sender doesn't have permission
                to send the message.

        """
        msg = sdk.TextMessage()
        msg.nMsgType = self.type
        msg.nFromUserID = self.teamtalk_instance.getMyUserID()
        msg.szFromUsername = self.teamtalk_instance.getMyUserAccount().szUsername
        if isinstance(self, ChannelMessage):
            if (
                self.teamtalk_instance.getMyChannelID() != self.to_id
                and not self.teamtalk_instance.is_admin()
            ):
                raise PytalkPermissionError(
                    "You don't have permission to send messages across channels."
                )
            msg.nChannelID = self.to_id
        if isinstance(self, BroadcastMessage):
            if not self.teamtalk_instance.is_admin():
                raise PytalkPermissionError(
                    "You don't have permission to send broadcast messages."
                )
            msg.nToUserID = 0
            msg.nChannelID = 0
        else:
            msg.nToUserID = self.from_id
        msg.szMessage = sdk.ttstr(content)  # type: ignore [arg-type]
        msg.bMore = False
        self.teamtalk_instance.bot.loop.create_task(
            self.teamtalk_instance._send_message(msg, **kwargs)
        )

    def is_me(self) -> bool:
        """Check if the message was sent by the bot.

        Returns:
            True if the message was sent by the bot, False otherwise.

        """
        return cast("bool", self.from_id == self.teamtalk_instance.getMyUserID())

    def __str__(self) -> str:
        """Return a string representation of the message.

        Returns:
            A string representation of the message.

        """
        return (
            f"pytalk.{type(self).__name__}(from_id={self.from_id}, "
            f"to_id={self.to_id}, content={self.content})"
        )


class ChannelMessage(Message):
    """Represents a message sent to a channel.

    This class should not be instantiated directly.
    """

    def __init__(
        self, teamtalk_instance: "TeamTalkInstance", msg: sdk.TextMessage
    ) -> None:
        """Initialize a ChannelMessage instance.

        Args:
            teamtalk_instance: An instance of pytalk.TeamTalkInstance.
            msg: The message payload.

        """
        super().__init__(teamtalk_instance, msg)
        self.to_id = msg.nChannelID
        self.channel_id = msg.nChannelID
        self.channel = self.teamtalk_instance.get_channel(self.channel_id)


class DirectMessage(Message):
    """Represents a message sent to a user.

    This class should not be instantiated directly.
    """

    def __init__(
        self, teamtalk_instance: "TeamTalkInstance", msg: sdk.TextMessage
    ) -> None:
        """Initialize a DirectMessage instance.

        Args:
            teamtalk_instance: An instance of pytalk.TeamTalkInstance.
            msg: The message payload.

        """
        super().__init__(teamtalk_instance, msg)
        self.to_id = msg.nToUserID
        if self.to_id == 0:
            self.to_id = teamtalk_instance.getMyUserID()


class BroadcastMessage(Message):
    """Represents a message sent to a server.

    This class should not be instantiated directly.
    """

    def __init__(
        self, teamtalk_instance: "TeamTalkInstance", msg: sdk.TextMessage
    ) -> None:
        """Initialize a BroadcastMessage instance.

        Args:
            teamtalk_instance: An instance of pytalk.TeamTalkInstance.
            msg: The message payload.

        """
        super().__init__(teamtalk_instance, msg)


class CustomMessage(Message):
    """Represents a custom message. This class should not be instantiated directly."""

    def __init__(
        self, teamtalk_instance: "TeamTalkInstance", msg: sdk.TextMessage
    ) -> None:
        """Initialize a CustomMessage instance.

        Args:
            teamtalk_instance: An instance of pytalk.TeamTalkInstance.
            msg: The message payload.

        """
        super().__init__(teamtalk_instance, msg)
