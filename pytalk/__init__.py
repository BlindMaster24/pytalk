__version__ = "0.0.0"


import os
import sys
from pathlib import Path
from typing import Optional, Tuple
import tomllib

from ctypes import *


def _load_config() -> Tuple[Optional[str], str]:
    """Resolve desired SDK version/edition with precedence: env > pyproject > defaults."""
    env_version = os.getenv("PYTALK_TTSDK_VERSION")
    env_edition = os.getenv("PYTALK_TTSDK_EDITION")

    cfg_version = None
    cfg_edition = None
    try:
        root = Path(__file__).resolve().parent.parent
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            data = tomllib.loads(pyproject.read_text())
            tool = data.get("tool", {})
            pytalk_cfg = tool.get("pytalk", {})
            cfg_version = pytalk_cfg.get("sdk_version")
            cfg_edition = pytalk_cfg.get("sdk_edition")
    except Exception:
        # pyproject is optional at runtime; ignore parse errors gracefully.
        pass

    edition = (env_edition or cfg_edition or "standard").lower()
    version = env_version or cfg_version
    return version, edition


_requested_version, _requested_edition = _load_config()


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

    download_sdk(version=_requested_version, edition=_requested_edition)
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
