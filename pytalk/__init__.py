__version__ = "0.0.0"


import os
import sys

from ctypes import *

try:
    if sys.platform.startswith("linux"):
        libpath = os.path.join(
            os.path.dirname(__file__),
            "implementation",
            "TeamTalk_DLL",
            "libTeamTalk5.so",
        )
        dll = cdll.LoadLibrary(libpath)
    from .implementation.TeamTalkPy import TeamTalk5 as sdk
except:
    from .download_sdk import download_sdk

    download_sdk()
    if sys.platform.startswith("linux"):
        libpath = os.path.join(
            os.path.dirname(__file__),
            "implementation",
            "TeamTalk_DLL",
            "libTeamTalk5.so",
        )
        dll = cdll.LoadLibrary(libpath)
    from .implementation.TeamTalkPy import TeamTalk5 as sdk

from .bot import TeamTalkBot
from .channel import Channel
from .user_account import UserAccount, BannedUserAccount
from .enums import Status, TeamTalkServerInfo, UserStatusMode, UserType
from .instance import TeamTalkInstance
from .message import BroadcastMessage, ChannelMessage, CustomMessage, DirectMessage
from .permission import Permission
from .streamer import Streamer
from .subscription import Subscription
