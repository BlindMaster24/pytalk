# if the implementation can't be found. Try to download it
# from the internet and install it.

# first add our to be implementation/TeamTalk_DLL to the path
import os
import sys
import ctypes

# if we are on linux we do a little hack for the LD_LIBRARY_PATH
try:
    if sys.platform.startswith("linux"):
        # get the full path to the implementation/TeamTalk_DLL folder
        libpath = os.path.join(os.path.dirname(__file__), "implementation", "TeamTalk_DLL", "libTeamTalk5.so")
        dll = ctypes.cdll.LoadLibrary(libpath)
    from .implementation.TeamTalkPy import TeamTalk5 as sdk
except (ImportError, OSError):
    from .download_sdk import download_sdk

    download_sdk()
    if sys.platform.startswith("linux"):
        # get the full path to the implementation/TeamTalk_DLL folder
        libpath = os.path.join(os.path.dirname(__file__), "implementation", "TeamTalk_DLL", "libTeamTalk5.so")
        dll = ctypes.cdll.LoadLibrary(libpath)
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

__all__ = [
    "TeamTalkBot",
    "Channel",
    "UserAccount",
    "BannedUserAccount",
    "Status",
    "TeamTalkServerInfo",
    "UserStatusMode",
    "UserType",
    "TeamTalkInstance",
    "BroadcastMessage",
    "ChannelMessage",
    "CustomMessage",
    "DirectMessage",
    "Permission",
    "Streamer",
    "Subscription",
    "sdk",
]
