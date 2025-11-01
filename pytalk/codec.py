"""Provides codec-related classes for pytalk."""

from typing import cast

from ._utils import _get_tt_obj_attribute, _set_tt_obj_attribute
from .implementation.TeamTalkPy import TeamTalk5 as sdk


class AudioCodecConfig:
    """Represents the audio codec configuration for a channel."""

    def __init__(self, payload: sdk.AudioCodec) -> None:
        """Initialize an AudioCodecConfig object.

        Args:
            payload: The underlying sdk.AudioCodec object.

        """
        self.payload = payload

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


class VideoCodecConfig:
    """Represents the video codec configuration for a channel."""

    def __init__(self, payload: sdk.VideoCodec) -> None:
        """Initialize a VideoCodecConfig object.

        Args:
            payload: The underlying sdk.VideoCodec object.

        """
        self.payload = payload

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


class _CodecTypeMeta(type):
    def __getattr__(cls, name: str) -> int:
        name = f"CODEC_{name}"
        value = getattr(sdk.Codec, name, None)
        if value is None:
            raise AttributeError(f"'{cls.__name__}' object has no attribute '{name}'")
        return cast("int", value)

    def __dir__(cls) -> list[str]:
        return [attr[6:] for attr in dir(sdk.Codec) if attr.startswith("CODEC_")]


class CodecType(metaclass=_CodecTypeMeta):
    """A class representing Codec types in TeamTalk."""
