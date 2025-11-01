import pytest
from unittest.mock import MagicMock

from pytalk.codec import AudioCodecConfig, VideoCodecConfig
from pytalk.implementation.TeamTalkPy import TeamTalk5 as sdk


@pytest.fixture
def mock_sdk_audio_codec():
    mock_codec = MagicMock(spec=sdk.AudioCodec)
    mock_codec.nCodec = 1
    mock_codec.nQuality = 2
    mock_codec.nFrameSize = 3
    mock_codec.nSampleRate = 4
    mock_codec.nChannels = 5
    mock_codec.nBitrate = 6
    mock_codec.nFlags = 7
    return mock_codec


@pytest.fixture
def mock_sdk_video_codec():
    mock_codec = MagicMock(spec=sdk.VideoCodec)
    mock_codec.nCodec = 10
    mock_codec.nQuality = 20
    mock_codec.nFrameRate = 30
    mock_codec.nWidth = 40
    mock_codec.nHeight = 50
    mock_codec.nBitrate = 60
    return mock_codec


def test_audio_codec_config_init(mock_sdk_audio_codec):
    config = AudioCodecConfig(mock_sdk_audio_codec)
    assert config.payload == mock_sdk_audio_codec


def test_audio_codec_config_properties(mock_sdk_audio_codec):
    config = AudioCodecConfig(mock_sdk_audio_codec)
    assert config.codec == 1
    assert config.quality == 2
    assert config.frame_size == 3
    assert config.sample_rate == 4
    assert config.channels == 5
    assert config.bitrate == 6
    assert config.flags == 7


def test_audio_codec_config_setters(mock_sdk_audio_codec):
    config = AudioCodecConfig(mock_sdk_audio_codec)
    config.codec = 11
    assert mock_sdk_audio_codec.nCodec == 11
    config.quality = 12
    assert mock_sdk_audio_codec.nQuality == 12
    config.frame_size = 13
    assert mock_sdk_audio_codec.nFrameSize == 13
    config.sample_rate = 14
    assert mock_sdk_audio_codec.nSampleRate == 14
    config.channels = 15
    assert mock_sdk_audio_codec.nChannels == 15
    config.bitrate = 16
    assert mock_sdk_audio_codec.nBitrate == 16
    config.flags = 17
    assert mock_sdk_audio_codec.nFlags == 17


def test_video_codec_config_init(mock_sdk_video_codec):
    config = VideoCodecConfig(mock_sdk_video_codec)
    assert config.payload == mock_sdk_video_codec


def test_video_codec_config_properties(mock_sdk_video_codec):
    config = VideoCodecConfig(mock_sdk_video_codec)
    assert config.codec == 10
    assert config.quality == 20
    assert config.frame_rate == 30
    assert config.width == 40
    assert config.height == 50
    assert config.bitrate == 60


def test_video_codec_config_setters(mock_sdk_video_codec):
    config = VideoCodecConfig(mock_sdk_video_codec)
    config.codec = 110
    assert mock_sdk_video_codec.nCodec == 110
    config.quality = 120
    assert mock_sdk_video_codec.nQuality == 120
    config.frame_rate = 130
    assert mock_sdk_video_codec.nFrameRate == 130
    config.width = 140
    assert mock_sdk_video_codec.nWidth == 140
    config.height = 150
    assert mock_sdk_video_codec.nHeight == 150
    config.bitrate = 160
    assert mock_sdk_video_codec.nBitrate == 160
