import unittest
from unittest.mock import MagicMock, patch

from pytalk.implementation.TeamTalkPy import TeamTalk5 as sdk
from pytalk.user import User


class TestUser(unittest.TestCase):
    def setUp(self):
        self.teamtalk_mock = MagicMock()
        self.user_id = 1
        self.user = User(self.teamtalk_mock, self.user_id)

    async def test_send_message(self):
        self.teamtalk_mock._send_message = MagicMock()

        await self.user.send_message("test message")

        self.teamtalk_mock._send_message.assert_called_once()
        sent_message = self.teamtalk_mock._send_message.call_args[0][0]
        self.assertEqual(sent_message.nMsgType, sdk.TextMsgType.MSGTYPE_USER)
        self.assertEqual(sdk.ttstr(sent_message.szMessage), "test message")


if __name__ == "__main__":
    unittest.main()
