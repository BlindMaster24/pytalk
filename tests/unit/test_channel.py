import unittest
from unittest.mock import MagicMock, patch

from pytalk.channel import Channel
from pytalk.implementation.TeamTalkPy import TeamTalk5 as sdk


class TestChannel(unittest.TestCase):
    def setUp(self):
        self.teamtalk_mock = MagicMock()
        self.channel_id = 1

        # Mock the _get_channel_info method to return a mock channel and path
        self.sdk_channel = sdk.Channel()
        self.sdk_channel.nChannelID = self.channel_id
        self.sdk_channel.szName = sdk.ttstr("Test Channel")
        self.sdk_channel.szTopic = sdk.ttstr("Test Topic")
        self.sdk_channel.nMaxUsers = 10
        self.sdk_channel.nDiskQuota = 1024
        self.sdk_channel.uChannelType = 0

        self.teamtalk_mock._get_channel_info.return_value = (self.sdk_channel, "/Test Channel")

        self.channel = Channel(self.teamtalk_mock, self.channel_id)

    def test_channel_properties(self):
        # Mock the underlying SDK channel object
        sdk_channel = sdk.Channel()
        sdk_channel.nChannelID = self.channel_id
        sdk_channel.szName = sdk.ttstr("Test Channel")
        sdk_channel.szTopic = sdk.ttstr("Test Topic")
        sdk_channel.nMaxUsers = 10
        sdk_channel.nDiskQuota = 1024
        sdk_channel.uChannelType = 0

        # Patch the _get_channel_info method to return our mock channel
        with patch.object(
            self.teamtalk_mock, "_get_channel_info", return_value=(sdk_channel, "/Test Channel")
        ) as mock_get_channel_info:
            self.channel = Channel(self.teamtalk_mock, self.channel_id)
            # Test properties
            self.assertEqual(self.channel.id, self.channel_id)
            self.assertEqual(self.channel.name, "Test Channel")
            self.assertEqual(self.channel.topic, "Test Topic")
            self.assertEqual(self.channel.max_users, 10)
            self.assertEqual(self.channel.disk_quota, 1024)
            self.assertEqual(self.channel.channel_type, 0)

            # Verify that the getChannel method was called
            mock_get_channel_info.assert_called_with(self.channel_id)


if __name__ == "__main__":
    unittest.main()
