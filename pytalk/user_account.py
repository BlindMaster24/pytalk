"""Module defines a class for a User Account on a TeamTalk server.

The difference between this class and the User class is that this class
represents a user account,
while the User class represents a user that is currently connected to the server.
"""

from typing import TYPE_CHECKING

from ._utils import _get_tt_obj_attribute
from .implementation.TeamTalkPy import TeamTalk5 as sdk

if TYPE_CHECKING:
    from .instance import TeamTalkInstance


class UserAccount:
    """A class for a user account on a TeamTalk server.

    This class is not meant
    to be instantiated directly. Instead, use the
    TeamTalkBot.list_user_accounts() method to get a list of UserAccount objects.
    # noqa
    """

    def __init__(
        self, teamtalk_instance: "TeamTalkInstance", account: sdk.UserAccount
    ) -> None:
        """Initialize a UserAccount object.

        Args:
            teamtalk_instance: The TeamTalk instance.
            account: The user account.

        """
        self.teamtalk_instance = teamtalk_instance
        self._account = account

    def __getattr__(self, name: str) -> object:
        """Try to get the specified attribute from self._user if it is not found in

        self.

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
        return _get_tt_obj_attribute(self._account, name)


# make a subclass of UserAccount for a banned user
class BannedUserAccount(UserAccount):
    """Represents a banned user account on a TeamTalk server.

    This class is not
    meant to be instantiated directly. Instead, use the
    TeamTalkBot.list_banned_users() method to get a list of BannedUserAccount
    objects. # noqa
    """

    # shouldn't do anything extra
