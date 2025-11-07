"""TeamTalk enums and constants."""

from typing import Any, Self


class TeamTalkServerInfo:
    """Holds the required information to connect and login to a TeamTalk server."""

    def __init__(self, data: dict[str, Any]) -> None:
        """Initialize a TeamTalkServerInfo object.

        Args:
            data (dict): A dictionary containing the server information.

        """
        self.host = data.get("host")
        self.tcp_port = data.get("tcp_port", 0)
        self.udp_port = data.get("udp_port", 0)
        self.username = data.get("username")
        self.password = data.get("password", "")
        self.encrypted = data.get("encrypted", False)
        self.nickname = data.get("nickname", data.get("username"))
        self.join_channel_id = data.get("join_channel_id", -1)
        self.join_channel_password = data.get("join_channel_password", "")
        self.auto_login = data.get("auto_login", True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Construct a TeamTalkServerInfo object from a dictionary.

        Args:
            data (dict): The dictionary to construct the object from.

        Returns:
            Self: The constructed object.

        """
        return cls(data)

    def to_dict(self) -> dict[str, Any]:
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
            "auto_login": self.auto_login,
        }

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
            and self.auto_login == other.auto_login
        )

    def __ne__(self, other: object) -> bool:
        """Compare this object to another object.

        Args:
            other: The object to compare to.

        Returns:
            bool: Whether or not the objects are not equal.

        """
        return not self.__eq__(other)

    def __hash__(self) -> int:
        """Return the hash value of the object."""
        return hash(
            (
                self.host,
                self.tcp_port,
                self.udp_port,
                self.username,
                self.encrypted,
                self.auto_login,
            )
        )


class UserStatusMode:
    """Represents user status modes (mutually exclusive)."""

    ONLINE = 0
    """The user is online."""

    AWAY = 1
    """The user is away."""

    QUESTION = 2
    """The user has a question."""


class _Gender:
    """Internal representation of gender flags (bitwise combinable)."""

    MALE = 0x00000000
    """Represents a male user status.
    This corresponds to no specific gender bit being set in the SDK."""

    FEMALE = 0x00000100
    """Represents a female user status.
    Corresponds to `sdk.StatusMode.STATUSMODE_FEMALE`."""

    NEUTRAL = 0x00001000
    """Represents a neutral gender user status.
    Corresponds to `sdk.StatusMode.STATUSMODE_NEUTRAL`."""


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

    def __init__(self) -> None:
        """Prevent direct instantiation of the Status class.

        Raises:
            TypeError: If an attempt is made to instantiate this class.

        """
        raise TypeError(
            "Status class is not meant to be instantiated directly. "
            "Use class properties like Status.online, Status.away, or "
            "Status.question instead."
        )

    class _StatusBuilder:
        """Internal builder for combining status mode and gender."""

        def __init__(self, base_mode_value: int) -> None:
            """Initialize the status builder with a base mode value.

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

    @classmethod
    def online(cls) -> _StatusBuilder:
        """Set the user status to 'online'."""
        return cls._StatusBuilder(UserStatusMode.ONLINE)

    @classmethod
    def away(cls) -> _StatusBuilder:
        """Set the user status to 'away'."""
        return cls._StatusBuilder(UserStatusMode.AWAY)

    @classmethod
    def question(cls) -> _StatusBuilder:
        """Set the user status to 'question'."""
        return cls._StatusBuilder(UserStatusMode.QUESTION)


class UserType:
    """The type of a user account."""

    DEFAULT = 0x1
    """The default user type.
    This only has the permissions set, and no other permissions."""

    ADMIN = 0x02
    """The admin user type. This has all permissions."""
