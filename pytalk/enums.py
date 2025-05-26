"""TeamTalk enums and constants."""

from typing_extensions import Self


class TeamTalkServerInfo:
    """Holds the required information to connect and login to a TeamTalk server."""

    def __init__(
        self,
        host: str,
        tcp_port: int,
        udp_port: int,
        username: str,
        password: str = "",
        encrypted: bool = False,
        nickname: str = "",
        join_channel_id: int = -1,
        join_channel_password: str = "",
    ) -> None:
        """Initialize a TeamTalkServerInfo object.

        Args:
            host (str): The host of the TeamTalk server.
            tcp_port (int): The TCP port of the TeamTalk server.
            udp_port (int): The UDP port of the TeamTalk server.
            username (str): The username to login with.
            password (str): The password to login with. Defaults to "" (no password).
            encrypted (bool): Whether or not to use encryption. Defaults to False.
            nickname (str): The nickname to use. Defaults to "teamtalk.py Bot".
            join_channel_id (int): The channel ID to join. Defaults to -1 (don't join a channel on login). Set to 0 to join the root channel, or a positive integer to join a specific channel. # noqa: E501
            join_channel_password (str): The password to join the channel with. Defaults to "" (no password).
        """
        self.host = host
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.username = username
        self.password = password
        self.encrypted = encrypted
        self.nickname = nickname if nickname else username
        self.join_channel_id = join_channel_id
        self.join_channel_password = join_channel_password

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Construct a TeamTalkServerInfo object from a dictionary.

        Args:
            data (dict): The dictionary to construct the object from.

        Returns:
            Self: The constructed object.
        """
        return cls(**data)

    # convert this object to a dictionary
    def to_dict(self) -> dict:
        """Convert this object to a dictionary.

        Returns:
            dict: The dictionary representation of this object.
        """
        return {
            "host": self.host,
            "tcp_port": self.tcp_port,
            "udp_port": self.udp_port,
            "username": self.username,
            "password": self.password,
            "encrypted": self.encrypted,
            "nickname": self.nickname if self.nickname else "",
            "join_channel_id": self.join_channel_id,
            "join_channel_password": self.join_channel_password,
        }

    # compare this object to another object
    def __eq__(self, other: object) -> bool:
        """Compare this object to another object.

        Args:
            other: The object to compare to.

        Returns:
            bool: Whether or not the objects are equal.
        """
        if not isinstance(other, TeamTalkServerInfo):
            return False
        return (
            self.host == other.host
            and self.tcp_port == other.tcp_port
            and self.udp_port == other.udp_port
            and self.username == other.username
            and self.password == other.password
            and self.encrypted == other.encrypted
        )

    # compare this object to another object
    def __ne__(self, other: object) -> bool:
        """Compare this object to another object.

        Args:
            other: The object to compare to.

        Returns:
            bool: Whether or not the objects are not equal.
        """
        return not self.__eq__(other)


class _UserStatusMode:
    """Internal representation of status modes (mutually exclusive)."""

    ONLINE = 0
    """The user is online."""

    AWAY = 1
    """The user is away."""

    QUESTION = 2
    """The user has a question."""


class _Gender:
    """Internal representation of gender flags (bitwise combinable)."""

    MALE = 0x00000000
    """Represents a male user status. This corresponds to no specific gender bit being set in the SDK."""

    FEMALE = 0x00000100
    """Represents a female user status. Corresponds to `sdk.StatusMode.STATUSMODE_FEMALE`."""

    NEUTRAL = 0x00001000
    """Represents a neutral gender user status. Corresponds to `sdk.StatusMode.STATUSMODE_NEUTRAL`."""


class Status:
    """A helper class to construct combined status values for a user.

    Use `Status.online`, `Status.away`, or `Status.question` properties,
    then chain them with a gender property (`.male`, `.female`, `.neutral`)
    to get the final status value for `pytalk.TeamTalkInstance.change_status`.

    Examples:
        `Status.online.male`
        `Status.away.female`
        `Status.question.neutral`

    This class should not be instantiated directly.
    """

    class _StatusBuilder:
        """Internal builder for combining status mode and gender."""

        def __init__(self, base_mode_value: int):
            """Initializes the status builder with a base mode value.

            Args:
                base_mode_value (int): The base integer value for the status mode.
            """
            self._value = base_mode_value

        @property
        def male(self) -> int:
            """Represents a male status.

            Returns:
                int: The combined status integer value.
            """
            return self._value | _Gender.MALE

        @property
        def female(self) -> int:
            """Represents a female status.

            Returns:
                int: The combined status integer value.
            """
            return self._value | _Gender.FEMALE

        @property
        def neutral(self) -> int:
            """Represents a neutral gender status.

            Returns:
                int: The combined status integer value.
            """
            return self._value | _Gender.NEUTRAL

    _MODE_MASK = 0xFF
    """A bitmask for extracting the status mode from a combined status integer."""

    _GENDER_MASK = _Gender.FEMALE | _Gender.NEUTRAL
    """A bitmask for extracting the gender bits from a combined status integer."""

    @property
    def online(self) -> _StatusBuilder:
        """Sets the user status to 'online'.

        Returns:
            _StatusBuilder: An internal builder to further specify gender.
        """
        return self._StatusBuilder(_UserStatusMode.ONLINE)

    @property
    def away(self) -> _StatusBuilder:
        """Sets the user status to 'away'.

        Returns:
            _StatusBuilder: An internal builder to further specify gender.
        """
        return self._StatusBuilder(_UserStatusMode.AWAY)

    @property
    def question(self) -> _StatusBuilder:
        """Sets the user status to 'question'.

        Returns:
            _StatusBuilder: An internal builder to further specify gender.
        """
        return self._StatusBuilder(_UserStatusMode.QUESTION)


class UserType:
    """The type of a user account."""

    DEFAULT = 0x1
    """The default user type. This only has the permissions set, and no other permissions."""

    ADMIN = 0x02
    """The admin user type. This has all permissions."""
