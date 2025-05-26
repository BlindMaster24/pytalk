"""Provides a dynamic way to access SDK codec identifiers by user-friendly names."""

from typing import Any
from .implementation.TeamTalkPy import TeamTalk5 as sdk

class _CodecTypeMeta(type):
    def __getattr__(cls, name: str) -> Any:
        name_upper = name.upper()
        
        potential_names_in_sdk = [
            name_upper,
            name_upper + "_CODEC",
        ]
        if name_upper.endswith("_CODEC"):
            potential_names_in_sdk.append(name_upper[:-6])

        for sdk_name_candidate in potential_names_in_sdk:
            if hasattr(sdk.Codec, sdk_name_candidate):
                return getattr(sdk.Codec, sdk_name_candidate)
            
        raise AttributeError(
            f"'{cls.__name__}' has no attribute '{name}' corresponding to a "
            f"known SDK Codec. Tried resolving from: "
            f"{potential_names_in_sdk} in sdk.Codec."
        )

    def __dir__(cls) -> list[str]:
        members = set()
        excluded_attributes = [
            'name', 'value', 'values', 
            'name_mapping', 'value_mapping', 'mro',
        ]
        
        for attr_name_sdk in dir(sdk.Codec):
            if (not attr_name_sdk.startswith('_') and
                    attr_name_sdk not in excluded_attributes):
                
                user_friendly_name = attr_name_sdk
                if user_friendly_name.endswith("_CODEC"):
                    user_friendly_name = user_friendly_name[:-6]
                
                try:
                    resolved_attr = getattr(cls, user_friendly_name)
                    if isinstance(resolved_attr, int):
                        members.add(user_friendly_name)
                except AttributeError:
                    pass
                    
        return sorted(list(members))


class CodecType(metaclass=_CodecTypeMeta):
    """Represents media codec types available in the SDK (both audio and video).

    Allows dynamic access to SDK codec integer values by their common names,
    similar to how `pytalk.Permission` works. The lookup is case-insensitive
    and attempts to match common naming patterns in `sdk.Codec`.

    Example:
        `CodecType.WEBM_VP8` (resolves to `sdk.Codec.WEBM_VP8_CODEC`)
        `CodecType.OPUS` (resolves to `sdk.Codec.OPUS_CODEC`)

    Warning: 
        When using these values with specific SDK functions (like setting
        a video codec for media file streaming), ensure you are passing a codec type
        appropriate for that function's parameter.
    """
    pass