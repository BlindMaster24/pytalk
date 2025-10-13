import math
import time
import threading
from .implementation.TeamTalkPy import TeamTalk5 as sdk

def timestamp():
    return int(round(time.time() * 1000))
DEF_WAIT = 1500


def _waitForEvent(ttclient, event, timeout=DEF_WAIT):
    msg = ttclient.getMessage(timeout)
    end = timestamp() + timeout
    while msg.nClientEvent != event:
        if timestamp() >= end:
            return False, sdk.TTMessage()
        msg = ttclient.getMessage(timeout)

    return True, msg


def _waitForCmdSuccess(ttclient, cmdid, timeout):
    result = True
    while result:
        result, msg = _waitForEvent(ttclient, sdk.ClientEvent.CLIENTEVENT_CMD_SUCCESS, timeout)
        if result and msg.nSource == cmdid:
            return result, msg

    return False, sdk.TTMessage()


def _waitForCmd(ttclient, cmdid, timeout):
    end = timestamp() + timeout
    while True:
        msg = ttclient.getMessage()
        if msg.nClientEvent == sdk.ClientEvent.CLIENTEVENT_CMD_ERROR:
            if msg.nSource == cmdid:
                return False, msg.clienterrormsg
        elif msg.nClientEvent == sdk.ClientEvent.CLIENTEVENT_CMD_SUCCESS:
            if msg.nSource == cmdid:
                return True, msg
        if timestamp() >= end:
            return False, sdk.TTMessage()


def _getAbsTimeDiff(t1, t2):
    t1 = int(round(t1 * 1000))
    t2 = int(round(t2 * 1000))
    return abs(t1 - t2)


def _get_tt_obj_attribute(obj, attr):
    name = ""
    for name_part in attr.split("_"):
        # if the name_part is "id" or "ID" then we want to keep it as "ID"
        if name_part.lower() == "id":
            name += "ID"
        else:
            # otherwise we want to capitalize the first letter
            name += name_part.capitalize()
    # first try to prefix with "n" and then get obj.name
    try:
        return getattr(obj, f"n{name}")
    except AttributeError:
        pass
    # if that fails, try to prefix name with "sz" and then get obj.name
    try:
        return getattr(obj, f"sz{name}")
    except AttributeError:
        pass
    # if that fails, try to prefix name with "b" and then get obj.name
    try:
        return getattr(obj, f"b{name}")
    except AttributeError:
        pass
    # if that fails, try to prefix name with "u" and then get obj.name
    try:
        return getattr(obj, f"u{name}")
    except AttributeError:
        pass
    # if that fails, try to lowercase the first letter name and then get obj.name
    try:
        return getattr(obj, f"{name[0].lower()}{name[1:]}")
    except AttributeError:
        pass
    # if we are still here we failed to get the attribute
    raise AttributeError(f"Could not find attribute {name} in {obj}")


def percent_to_ref_volume(percent: float) -> int:
    """Converts a percentage (0-100) to the internal TeamTalk volume value.

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
    return max(sdk.SoundLevel.SOUND_VOLUME_MIN, min(sdk.SoundLevel.SOUND_VOLUME_MAX, internal_volume))


def ref_volume_to_percent(volume: int) -> int:
    """Converts an internal TeamTalk volume value to a percentage (0-100).

    Matches the TeamTalk Qt client's user volume scaling.

    Args:
        volume (int): The internal TeamTalk volume value.

    Returns:
        int: The corresponding volume percentage (0-100).
    """
    if volume <= sdk.SoundLevel.SOUND_VOLUME_MIN:
        return 0

    try:
        internal_volume_float = float(volume)
        safe_volume = max(internal_volume_float, float(sdk.SoundLevel.SOUND_VOLUME_MIN) - 49.9)
        d = (safe_volume + 50.0) / 82.832
        if d <= 0:
            return 0
        percentage = math.log(d) / 0.0508
    except (ValueError, OverflowError):
        return 0

    rounded_percentage = int(round(percentage))
    return max(0, min(100, rounded_percentage))


def _set_tt_obj_attribute(obj, attr, value):
    name = ""
    for name_part in attr.split("_"):
        # if the name_part is "id" or "ID" then we want to keep it as "ID"
        if name_part.lower() == "id":
            name += "ID"
        else:
            # otherwise we want to capitalize the first letter
            name += name_part.capitalize()
    # first try to prefix with "n" and then set obj.name to value
    try:
        setattr(obj, f"n{name}", value)
        return
    except AttributeError:
        pass
    # if that fails, try to prefix name with "sz" and then set obj.name to value
    try:
        setattr(obj, f"sz{name}", value)
        return
    except AttributeError:
        pass
    # if that fails, try to prefix name with "b" and then set obj.name to value
    try:
        setattr(obj, f"b{name}", value)
        return
    except AttributeError:
        pass
    # if that fails, try to prefix name with "u" and then set obj.name to value
    try:
        setattr(obj, f"u{name}", value)
        return
    except AttributeError:
        pass
    # if that fails, try to lowercase the first letter name and then set obj.name to value
    try:
        setattr(obj, f"{name[0].lower()}{name[1:]}", value)
        return
    except AttributeError:
        pass
    # if we are still here we failed to get the attribute
    raise AttributeError(f"Could not set attribute {name} in {obj}")


# now convert the _get_tt_obj_attribute names to python names that can be used in set_tt_obj_attribute
def _tt_attr_to_py_attr(attr):
    name = ""
    # if the attr is id, keep it
    if attr.lower() == "id":
        name = "id"
    else:
        # we want to discard all letters before the first capital letter, keeping the rest
        new_attr = ""
        for x in range(len(attr)):
            if attr[x].isupper():
                new_attr = attr[x:]
                break
        # if everything is ubber, just lowercase everything and return
        if new_attr.isupper():
            return new_attr.lower()
        # now we want to lowercase the first letter
        name = new_attr[0].lower()
        # then replace every other capital letter with an underscore and the lowercase version of that letter
        for x in range(1, len(new_attr)):
            if new_attr[x].isupper():
                # if the next letter is also uppercase, we want to just lowercase this one
                # IF the next letter is lowercase, we want to lowercase this letter and put an underscore after it
                if x + 1 < len(new_attr) and new_attr[x + 1].isupper():
                    name += new_attr[x].lower()
                else:
                    name += f"_{new_attr[x].lower()}"
            else:
                name += new_attr[x]
    return name


def _do_after(delay, func):
    def _do_after_thread(delay, func):
        initial_time = time.time()
        while _getAbsTimeDiff(initial_time, time.time()) < (delay * 1000):
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
