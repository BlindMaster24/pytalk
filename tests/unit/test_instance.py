import unittest
from unittest.mock import MagicMock, patch

from pytalk.instance import TeamTalkInstance
from pytalk.implementation.TeamTalkPy import TeamTalk5 as sdk


class TestInstance(unittest.TestCase):
    def setUp(self):
        self.bot_mock = MagicMock()
        self.server_info_mock = MagicMock()
        self.instance = TeamTalkInstance(self.bot_mock, self.server_info_mock)

    @patch("pytalk.instance.sdk.TeamTalk.doSendFile")
    @patch("pytalk.instance.Path")
    def test_upload_file(self, mock_path, mock_do_send_file):
        mock_path.return_value.exists.return_value = True
        mock_do_send_file.return_value = 1
        self.instance.has_permission = MagicMock(return_value=True)

        transfer_id = self.instance.upload_file(1, "test.txt")

        self.assertEqual(transfer_id, 1)
        mock_do_send_file.assert_called_with(1, sdk.ttstr("test.txt"))

    def test_download_file(self):
        self.instance.has_permission = MagicMock(return_value=True)
        self.instance.get_channel_files = MagicMock(
            return_value=[
                MagicMock(file_name=sdk.ttstr("test.txt"), file_id=1)
            ]
        )
        self.instance.download_file_by_id = MagicMock(return_value=1)

        transfer_id = self.instance.download_file(1, "test.txt", "test.txt")

        self.assertEqual(transfer_id, 1)
        self.instance.download_file_by_id.assert_called_with(1, 1, "test.txt", None)

    def test_cancel_file_transfer(self):
        sdk._CancelFileTransfer = MagicMock(return_value=True)

        result = self.instance.cancel_file_transfer(1)

        self.assertTrue(result)
        sdk._CancelFileTransfer.assert_called_with(self.instance._tt, 1)


if __name__ == "__main__":
    unittest.main()
