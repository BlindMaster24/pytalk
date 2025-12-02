"""Module contains the AudioBlock class.

Not to be confused with the underlying AudioBlock class, this is used in the
"on_user_audio" event. # noqa

Example:
-------

        .. code-block:: python3

            import pyaudio
            streams: dict = {}
            p = pyaudio.PyAudio()
            @client.event
            async def on_user_audio(block):
                print(block.user.username) # Print the username that the audio is from.
                                if block.user.id not in streams.keys():
                    streams [block.user.id] = p.open(format=pyaudio.paInt16,
                        channels = block.channels,
                        rate = block.sample_rate,
                        output = True)
                stream = streams[block.user.id]
                stream.write(block.data) # Play the audio data.


                See the :doc:`event Reference </events>` for more information and a
                list of all events.


"""

import ctypes
from typing import TYPE_CHECKING, Any

from ._utils import _get_tt_obj_attribute
from .implementation.TeamTalkPy import TeamTalk5 as sdk

if TYPE_CHECKING:
    from .instance import TeamTalkInstance
    from .user import User as TeamTalkUser

_AcquireUserAudioBlock = sdk.function_factory(
    sdk.dll.TT_AcquireUserAudioBlock,
    [sdk.POINTER(sdk.AudioBlock), [sdk._TTInstance, sdk.StreamType, sdk.INT32]],  # type: ignore [attr-defined]
)
_ReleaseUserAudioBlock = sdk.function_factory(
    sdk.dll.TT_ReleaseUserAudioBlock,
    [sdk.BOOL, [sdk._TTInstance, sdk.POINTER(sdk.AudioBlock)]],  # type: ignore [attr-defined]
)


class AudioBlock:
    """Represents an audio block for the on_user_audio event.

    Attributes:
        user: The user that the audio is from.
        id: The stream ID of the audio block.
        data: The audio data.
        sample_rate: The sample rate of the audio data.
        channels: The number of channels in the audio data.
        samples: The number of samples in the audio data.

    """

    def __init__(self, user: "TeamTalkUser | None", block: sdk.AudioBlock) -> None:
        """Represent an audio block for the on_user_audio event.

        Args:
            user: The user that the audio is from.
            block: The underlying AudioBlock object.

        """
        self._user = user
        self._block = block
        self.id = block.nStreamID
        self.data_pointer = block.lpRawAudio
        self._data = b""

    @property
    def data(self) -> bytes:
        """The audio data.

        Returns:
            The audio data.

        """
        if self._data is None:
            total_samples = self._block.nSamples * self._block.nChannels
            buffer_type = ctypes.c_short * total_samples
            buffer_ptr = ctypes.cast(self.data_pointer, ctypes.POINTER(buffer_type))
            self._data = bytes(buffer_ptr.contents)
        return self._data

    @property
    def user(self) -> "TeamTalkUser | None":
        """The user that the audio is from."""
        return self._user

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401
        """Try to get the attribute from the AUdioBlock object.

        Args:
            name: The name of the attribute.

        Returns:
            The value of the specified attribute.

        Raises:
            AttributeError: If the specified attribute is not found.
                This is the default behavior. # noqa

        """
        if name in dir(self):
            return self.__dict__[name]
        return _get_tt_obj_attribute(self._block, name)


class MuxedAudioBlock(AudioBlock):
    """Represents an audio block for the on_muxed_audio event.

    .. note:
        This class inherits from :class:`AudioBlock`.

    Attributes:
        id: The stream ID of the audio block.
        data: The audio data.
        sample_rate: The sample rate of the audio data.
        channels: The number of channels in the audio data.
        samples: The number of samples in the audio data.

    """

    def __init__(self, teamtalk: "TeamTalkInstance", block: sdk.AudioBlock) -> None:
        """Represent an audio block for the on_muxed_audio event.

        Args:
            teamtalk: The TeamTalkInstance this block belongs to.
            block: The underlying AudioBlock object.

        """
        super().__init__(None, block)
        self.teamtalk = teamtalk

    @property
    def user(self) -> None:
        """The user that the audio is from.

        Raises:
            AttributeError: MuxedAudioBlock has no attribute 'user'

        """
        raise AttributeError("MuxedAudioBlock has no attribute 'user'")
