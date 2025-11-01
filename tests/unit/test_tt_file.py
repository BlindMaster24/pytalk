import unittest
from unittest.mock import MagicMock

from pytalk.implementation.TeamTalkPy import TeamTalk5 as sdk
from pytalk.tt_file import FileTransfer


class TestFileTransfer(unittest.TestCase):
    def setUp(self):
        self.sdk_file_transfer = sdk.FileTransfer()
        self.sdk_file_transfer.nTransferID = 1
        self.sdk_file_transfer.nFileSize = 1024
        self.sdk_file_transfer.nTransferred = 512
        self.sdk_file_transfer.nStatus = 2

        self.file_transfer = FileTransfer(self.sdk_file_transfer)

    def test_file_transfer_properties(self):
        self.assertEqual(self.file_transfer.transfer_id, 1)
        self.assertEqual(self.file_transfer.file_size, 1024)
        self.assertEqual(self.file_transfer.transferred, 512)
        self.assertEqual(self.file_transfer.status, 2)

    def test_file_transfer_repr(self):
        expected_repr = "<FileTransfer id=1 status=2 transferred=512/1024>"
        self.assertEqual(repr(self.file_transfer), expected_repr)

    def test_file_transfer_eq(self):
        other_file_transfer = FileTransfer(self.sdk_file_transfer)
        self.assertEqual(self.file_transfer, other_file_transfer)

        another_sdk_file_transfer = sdk.FileTransfer()
        another_sdk_file_transfer.nTransferID = 2
        another_file_transfer = FileTransfer(another_sdk_file_transfer)
        self.assertNotEqual(self.file_transfer, another_file_transfer)

    def test_file_transfer_hash(self):
        self.assertEqual(hash(self.file_transfer), hash(1))


if __name__ == "__main__":
    unittest.main()
