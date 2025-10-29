import math
import threading
import time
from collections.abc import Callable
from typing import Any, cast

from .implementation.TeamTalkPy import TeamTalk5 as sdk


def timestamp() -> int:
    return int(round(time.time() * 1000))


DEF_WAIT = 1500


def _wait_for_event(
    ttclient: sdk.TeamTalk,
    event: sdk.ClientEvent | list[sdk.ClientEvent],
    timeout: int = DEF_WAIT,
) -> tuple[bool, sdk.TTMessage]:
    events = event if isinstance(event, list) else [event]
    msg = ttclient.getMessage(timeout)
    end = timestamp() + timeout
    while msg.nClientEvent not in events:
        if timestamp() >= end:
            return False, cast("Any", sdk.TTMessage())
        msg = ttclient.getMessage(timeout)

    return True, msg


def _wait_for_cmd_success(
    ttclient: sdk.TeamTalk, cmdid: int, timeout: int
) -> tuple[bool, sdk.TTMessage]:
    result = True
    while result:
        result, msg = _wait_for_event(
            ttclient,
            cast("sdk.ClientEvent", sdk.ClientEvent.CLIENTEVENT_CMD_SUCCESS),
            timeout,
        )
        if result and msg.nSource == cmdid:
            return result, msg

    return False, cast("Any", sdk.TTMessage())


def _wait_for_cmd(
    ttclient: sdk.TeamTalk, cmdid: int, timeout: int
) -> tuple[bool, sdk.TTMessage | sdk.ClientErrorMsg]:
    end = timestamp() + timeout
    while True:
        msg = ttclient.getMessage()
        if msg.nClientEvent == sdk.ClientEvent.CLIENTEVENT_CMD_ERROR:
            if msg.nSource == cmdid:
                return False, msg.clienterrormsg
        elif (
            msg.nClientEvent == sdk.ClientEvent.CLIENTEVENT_CMD_SUCCESS
            and msg.nSource == cmdid
        ):
            return True, msg
        if timestamp() >= end:
            return False, sdk.TTMessage()


def _get_abs_time_diff(t1: float, t2: float) -> int:
    t1 = int(round(t1 * 1000))
    t2 = int(round(t2 * 1000))
    return abs(t1 - t2)


def _get_tt_obj_attribute(obj: object, attr: str) -> object:  # noqa: C901
    name = ""
    for name_part in attr.split("_"):
        if name_part.lower() == "id":
            name += "ID"
        elif name_part.lower() == "ip":
            name += "IP"
        elif name_part.lower() == "tx":
            name += "TX"
        elif name_part.lower() == "rx":
            name += "RX"
        elif name_part.lower() == "msec":
            name += "MSec"
        elif name_part.isupper():
            name += name_part
        else:
            name += name_part.capitalize()
    prefixes = ["n", "sz", "b", "u"]
    for prefix in prefixes:
        try:
            return getattr(obj, f"{prefix}{name}")
        except AttributeError:
            pass
    try:
        return getattr(obj, f"{name[0].lower()}{name[1:]}")
    except AttributeError:
        pass
    raise AttributeError(f"Could not find attribute {name} in {obj}")


def percent_to_ref_volume(percent: float) -> int:
    """Convert a percentage (0-100) to the internal TeamTalk volume value.

    Matches the TeamTalk Qt client's user volume scaling.

    Args:
        percent (float): The volume percentage (0.0 to 100.0).

    Returns:
        int: The corresponding internal TeamTalk volume value, clamped to SDK limits.

    """
    if percent <= 0:
        return sdk.SoundLevel.SOUND_VOLUME_MIN

    percent = max(0.0, min(100.0, percent))

    try:
        internal_volume_float = 82.832 * math.exp(0.0508 * percent) - 50.0
    except OverflowError:
        return sdk.SoundLevel.SOUND_VOLUME_MAX

    internal_volume = int(round(internal_volume_float))
    return max(
        sdk.SoundLevel.SOUND_VOLUME_MIN,
        min(sdk.SoundLevel.SOUND_VOLUME_MAX, internal_volume),
    )


def ref_volume_to_percent(volume: int) -> int:
    """Convert an internal TeamTalk volume value to a percentage (0-100).

    Matches the TeamTalk Qt client's user volume scaling.

    Args:
        volume (int): The internal TeamTalk volume value.S

    Returns:
        int: The corresponding volume percentage (0-100).

    """
    if volume <= sdk.SoundLevel.SOUND_VOLUME_MIN:
        return 0

    try:
        internal_volume_float = float(volume)
        safe_volume = max(
            internal_volume_float, float(sdk.SoundLevel.SOUND_VOLUME_MIN) - 49.9
        )
        d = (safe_volume + 50.0) / 82.832
        if d <= 0:
            return 0
        percentage = math.log(d) / 0.0508
    except (ValueError, OverflowError):
        return 0

    rounded_percentage = int(round(percentage))
    return max(0, min(100, rounded_percentage))


def _set_tt_obj_attribute(obj: object, attr: str, value: object) -> None:
    name = ""
    for name_part in attr.split("_"):
        if name_part.lower() == "id":
            name += "ID"
        else:
            name += name_part.capitalize()
    try:
        setattr(obj, f"n{name}", value)
        return
    except AttributeError:
        pass
    try:
        setattr(obj, f"sz{name}", value)
        return
    except AttributeError:
        pass
    try:
        setattr(obj, f"b{name}", value)
        return
    except AttributeError:
        pass
    try:
        setattr(obj, f"u{name}", value)
        return
    except AttributeError:
        pass
    try:
        setattr(obj, f"{name[0].lower()}{name[1:]}", value)
        return
    except AttributeError:
        pass
    raise AttributeError(f"Could not set attribute {name} in {obj}")


def _tt_attr_to_py_attr(attr: str) -> str:
    name = ""
    if attr.lower() == "id":
        name = "id"
    else:
        new_attr = ""
        for x in range(len(attr)):
            if attr[x].isupper():
                new_attr = attr[x:]
                break
        if new_attr.isupper():
            return new_attr.lower()
        name = new_attr[0].lower()
        for x in range(1, len(new_attr)):
            if new_attr[x].isupper():
                if x + 1 < len(new_attr) and new_attr[x + 1].isupper():
                    name += new_attr[x].lower()
                else:
                    name += f"_{new_attr[x].lower()}"
            else:
                name += new_attr[x]
    return name


def _do_after(delay: float, func: Callable[..., Any]) -> None:
    def _do_after_thread(delay: float, func: Callable[..., Any]) -> None:
        initial_time = time.time()
        while _get_abs_time_diff(initial_time, time.time()) < (delay * 1000):
            time.sleep(0.001)
        func()

    threading.Thread(
        daemon=True,
        target=_do_after_thread,
        args=(
            delay,
            func,
        ),
    ).start()
