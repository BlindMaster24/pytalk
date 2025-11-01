"""A module containing the Streamer class.

This module contains the Streamer class, which is used to stream audio data to a
TeamTalk channel.

.. warning::
   To use other files than .wav files, you need to have ffmpeg installed on your system.

.. warning::
   To stream urls, you need to have yt-dlp installed on your system.

Example:
    >>> import teamtalk
    >>> # asuming we have a bot in the variable bot
    >>> @bot.event
    >>> async def on_message(message):
    >>>     if message.content.lower() == "play":
    >>>         streamer = teamtalk.Streamer.get_streamer_for_channel(message.channel)
    >>>         streamer.stream("path/to/file.wav")
    >>> # or for an url
    >>> streamer.stream("https://www.example.com/youtube/or/other/stream")


It's also possible to stream audio from an arbitrary data stream, such as a microphone.
To do this, you need to set the correct sample rate and number of channels on
initialization,
and then feed the data to the streamer as it becomes available.
The data needs to be in 16 bit PCM format (pcm_s16le).

Example:
    >>> import teamtalk
    >>> # asuming we have a bot in the variable bot
    >>> @bot.event
    >>> async def on_message(message):
    >>>     if message.content.lower() == "play":
    >>>         streamer = teamtalk.Streamer.get_streamer_for_channel(
    ...             message.channel, sample_rate=48000, channels=2
    ...         )
    >>>         # we could get the data from any source, so let's assume it's
    ...         # coming from a live microphone.
    >>>         data_stream = # connect to microphone
    >>>         while True:
    >>>             # get the data from the stream
    >>>             data = data_stream.read(
    ...                 streamer.block_size * 16
    ...             )  # we are reading 16 chunks at a time to combat buffering
    >>>             if data == 0:
    >>>                 break
    >>>             # add the data to the streamer
    >>>             streamer.feed(data)
    >>>         # close the connection to our microphone

"""

import ctypes
import multiprocessing
import random
import subprocess
import threading

from .channel import Channel as TeamTalkChannel
from .implementation.TeamTalkPy import TeamTalk5 as sdk

_audio_streamers = {}


class Streamer:
    """A class representing a streamer for audio data to a TeamTalk channel."""

    @staticmethod
    def get_streamer_for_channel(
        channel: TeamTalkChannel,
        sample_rate: int = 48000,
        channels: int = 2,
        block_size: int = 4 * 1024,
    ) -> "Streamer":
        """Get a streamer for a channel.

        Args:
            channel (TeamTalkChannel): The channel to get the streamer for.

        Args:
            sample_rate (int, optional): The sample rate of the audio data.
                Defaults to 48000.
            channels (int, optional): The number of channels in the audio data.
                Defaults to 2.
            block_size (int, optional): The block size of the audio data.
                Defaults to 4 * 1024 (4kb)

        Returns:
            Streamer: The streamer for the channel.

        """
        if channel not in _audio_streamers:
            _audio_streamers[channel] = Streamer(
                channel, sample_rate, channels, block_size
            )
        return _audio_streamers[channel]

    def __init__(
        self,
        channel: TeamTalkChannel,
        sample_rate: int = 48000,
        channels: int = 2,
        block_size: int = 4 * 1024,
    ) -> None:
        """Initialize a new instance of the TeamTalkStreamer class.

        Args:
            channel (TeamTalkChannel): The TeamTalk channel to which the streamer
                streams the audio data.
            sample_rate (int, optional): The sample rate of the audio data.
                Defaults to 48000.
            channels (int, optional): The number of channels in the audio data.
                Defaults to 2.
            block_size (int, optional): The block size of the audio data. Defaults
                to 4 * 1024 (4kb)

        """
        self.channel = channel
        self.sample_rate = sample_rate
        self.channels = channels
        self.block_size = block_size
        self.blocks: list[bytes] = []
        self.current_data = b""
        self.stream_id = random.randint(6000, 6999)  # noqa: S311
        self.ffmpeg_available = self._has_ffmpeg()
        self.yt_dlp_available = self._has_yt_dlp()
        self.running = True
        self._streamer_thread = threading.Thread(target=self._do_stream, daemon=True)
        self._streamer_thread.start()
        self._current_streamer_thread: threading.Thread | None = None
        self._current_streamer_running = False
        self._stream_lock = threading.Lock()

        def __del__(self: "Streamer") -> None:  # noqa: N807
            """Shuts down the streamer by adding a null-block to the blocks list and.

            waiting for the blocks list to be empty.

            """
            self.blocks.append(b"")

        while len(self.blocks) > 0:
            pass
        self.running = False

    def search_and_stream(self, query: str) -> None:
        """Search for a song and stream it to the channel.

        Args:
            query (str): The query to search for.

        Returns:
            None

        """
        self.stop()
        self.channel.teamtalk.bot.loop.create_task(
            self.channel.send_message(f"Searching for {query}...")
        )
        yt_dlp_command = f'yt-dlp -f bestaudio --extract-audio --audio-format best --audio-quality 0 --quiet --get-url "ytsearch:{query}"'  # noqa
        result = subprocess.run(  # noqa: S602
            yt_dlp_command,
            check=False,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        song = result.stdout.decode("utf-8").strip()
        if not song:
            self.channel.teamtalk.bot.loop.create_task(
                self.channel.send_message("No results found.")
            )
            return
        self.stream(song)

    def stop(self) -> None:
        """Stop the current stream."""
        self.blocks.clear()
        self._request_stop_stream()
        self._wait_for_cleanup()

    def stream(self, path: str) -> None:
        """Streams a file or an url to the channel.

        Args:
            path(str): The file or url to stream.

        Raises:
            RuntimeError: If the url could not be opened as a wav file or if the
                file could not be converted to a wav file.

        """
        with self._stream_lock:
            self._request_stop_stream()
            self._wait_for_cleanup()
            self._start_new_stream(path)

    def _request_stop_stream(self) -> None:
        if self._current_streamer_thread is not None:
            self._current_streamer_running = False

    def _wait_for_cleanup(self) -> None:
        if self._current_streamer_thread:
            self._current_streamer_running = False
            self.blocks.clear()
            self.blocks.append(b"")

    def _start_new_stream(self, path: str) -> None:
        self._current_streamer_running = True
        self._current_streamer_thread = threading.Thread(
            target=self._stream, args=(path,), daemon=True
        )
        if self._current_streamer_thread:
            self._current_streamer_thread.start()

    def _stream(self, path: str) -> None:
        if not self.ffmpeg_available:
            raise RuntimeError(
                "Could not convert file to wav. ffmpeg is not installed."
            )
        if path.startswith("http"):
            if not self.yt_dlp_available:
                raise RuntimeError("Could not download file. yt-dlp is not installed.")
            ffmpeg_process, yt_dlp_process = self._get_url_data(path)
        else:
            ffmpeg_command = [
                "ffmpeg",
                "-i",
                path,
                "-f",
                "wav",
                "-acodec",
                "pcm_s16le",
                "-ar",
                f"{str(self.sample_rate)}",
                "-ac",
                str(self.channels),
                "-threads",
                str(multiprocessing.cpu_count()),
                "-hide_banner",
                "-loglevel",
                "error",
                "-",
            ]
            ffmpeg_process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE)
        try:
            if ffmpeg_process.stdout:
                while self._current_streamer_running:
                    block = ffmpeg_process.stdout.read(self.block_size)
                    if len(block) == 0:
                        break
                    self.feed(block)
        except KeyboardInterrupt:
            raise
        finally:
            self._graceful_shutdown(ffmpeg_process)
            if path.startswith("http"):
                self._graceful_shutdown(yt_dlp_process)

    @property
    def volume(self) -> int:
        """The volume of the streamer.

        Returns:
            int: The volume of the streamer.

        """
        pre_processor = sdk.AudioPreprocessor()
        sdk._GetSoundInputPreprocessEx(
            self.channel.server.teamtalk_instance._tt, pre_processor
        )
        result = pre_processor.u.ttpreprocessor.nGainLevel
        return int(round(result.value // 10))

    @volume.setter
    def volume(self, value: int) -> None:
        """Set the volume of the streamer.

        Args:
            value (int): The volume to set, between 0 and 100.

        """
        tt_volume = ctypes.c_int(value * 10)
        pre_processor = sdk.AudioPreprocessor()
        sdk._GetSoundInputPreprocessEx(
            self.channel.server.teamtalk_instance._tt, pre_processor
        )
        pre_processor.u.ttpreprocessor.nGainLevel = tt_volume
        sdk._SetSoundInputPreprocessEx(
            self.channel.server.teamtalk_instance._tt, pre_processor
        )

    @property
    def mute_left(self) -> bool:
        """If the left channel of the speaker is muted.

        Returns:
            bool: True if the left channel is muted, False otherwise.

        """
        pre_processor = sdk.AudioPreprocessor()
        sdk._GetSoundInputPreprocessEx(
            self.channel.server.teamtalk_instance._tt, pre_processor
        )
        return bool(pre_processor.u.ttpreprocessor.bMuteLeft.value)

    @mute_left.setter
    def mute_left(self, mute: bool) -> None:
        """Set the mute state of the left channel of the speaker.

        Args:
            mute (bool): True to mute the left channel, False to unmute it.

        """
        pre_processor = sdk.AudioPreprocessor()
        sdk._GetSoundInputPreprocessEx(
            self.channel.server.teamtalk_instance._tt, pre_processor
        )
        pre_processor.u.ttpreprocessor.bMuteLeft = ctypes.c_bool(mute)
        sdk._SetSoundInputPreprocessEx(
            self.channel.server.teamtalk_instance._tt, pre_processor
        )

    @property
    def mute_right(self) -> bool:
        """If the right channel of the speaker is muted.

        Returns:
            bool: True if the right channel is muted, False otherwise.

        """
        pre_processor = sdk.AudioPreprocessor()
        sdk._GetSoundInputPreprocessEx(
            self.channel.server.teamtalk_instance._tt, pre_processor
        )
        return bool(pre_processor.u.ttpreprocessor.bMuteRight.value)

    @mute_right.setter
    def mute_right(self, mute: bool) -> None:
        """Set the mute state of the right channel of the speaker.

        Args:
            mute (bool): True to mute the right channel, False to unmute it.

        """
        pre_processor = sdk.AudioPreprocessor()
        sdk._GetSoundInputPreprocessEx(
            self.channel.server.teamtalk_instance._tt, pre_processor
        )
        pre_processor.u.ttpreprocessor.bMuteRight = ctypes.c_bool(mute)
        sdk._SetSoundInputPreprocessEx(
            self.channel.server.teamtalk_instance._tt, pre_processor
        )

    def _get_url_data(
        self, url: str
    ) -> tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]]:
        yt_dlp_command = [
            "yt-dlp",
            "-f",
            "bestaudio",
            "--extract-audio",
            "--audio-format",
            "best",
            "--audio-quality",
            "0",
            "--quiet",
            "-o",
            "-",
            url,
        ]
        ffmpeg_command = [
            "ffmpeg",
            "-i",
            "pipe:0",
            "-f",
            "wav",
            "-acodec",
            "pcm_s16le",
            "-ar",
            str(self.sample_rate),
            "-ac",
            str(self.channels),
            "-threads",
            str(multiprocessing.cpu_count()),
            "-hide_banner",
            "-loglevel",
            "error",
            "-",
        ]

        yt_dlp_process = subprocess.Popen(yt_dlp_command, stdout=subprocess.PIPE)
        return (
            subprocess.Popen(
                ffmpeg_command, stdin=yt_dlp_process.stdout, stdout=subprocess.PIPE
            ),
            yt_dlp_process,
        )

    def _graceful_shutdown(self, process: subprocess.Popen[bytes]) -> None:
        if process:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
            finally:
                if process.stdout:
                    process.stdout.close()
                if process.stderr:
                    process.stderr.close()

    def feed(self, data: bytes) -> int:
        """Feed data to the streamer.

        Args:
            data (bytes): The data to feed to the streamer.

        Returns:
            int: The stream id of the stream.

        """
        self.current_data += data
        if len(self.current_data) >= self.block_size:
            chunks = [
                self.current_data[i : i + self.block_size]
                for i in range(0, len(self.current_data), self.block_size)
            ]
            self.blocks.extend(chunks[:-1])
            self.current_data = chunks[-1]
        else:
            self.blocks.append(data)
        return self.stream_id

    def _do_stream(self) -> None:
        while self.running:
            if len(self.blocks) > 0:
                block = self.blocks[0]
                audio_block = sdk.AudioBlock()
                audio_block.nStreamID = self.stream_id
                audio_block.nSampleRate = self.sample_rate
                audio_block.nChannels = self.channels
                audio_block.nSamples = len(block) // 4
                audio_block.lpRawAudio = ctypes.cast(
                    (ctypes.c_char * len(block)).from_buffer_copy(block),
                    ctypes.c_void_p,
                )
                audio_block.uStreamTypes = sdk.StreamType.STREAMTYPE_VOICE
                result = 0
                while result == 0:
                    result = sdk._InsertAudioBlock(
                        self.channel.teamtalk._tt, audio_block
                    )
                self.blocks = self.blocks[1:]

    def _has_ffmpeg(self) -> bool:
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],  # noqa: S607
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode != 0:
                return False
        except FileNotFoundError:
            return False
        return True

    def _has_yt_dlp(self) -> bool:
        try:
            result = subprocess.run(
                ["yt-dlp", "--version"],  # noqa: S607
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode != 0:
                return False
        except FileNotFoundError:
            return False
        return True
