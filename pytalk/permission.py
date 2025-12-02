"""Module containing the Permission class for TeamTalk."""

from typing import cast

from .implementation.TeamTalkPy import TeamTalk5 as sdk


class _PermissionMeta(type):
    def __getattr__(cls, name: str) -> sdk.UserRight:
        name = f"USERRIGHT_{name}"
        return cast("sdk.UserRight", getattr(sdk.UserRight, name, None))

    def __dir__(cls) -> list[str]:
        return [
            name[10:] for name in dir(sdk.UserRight) if name.startswith("USERRIGHT_")
        ]


class Permission(metaclass=_PermissionMeta):
    """A class representing user permissions in TeamTalk."""
