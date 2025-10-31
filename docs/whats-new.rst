What's new
===============

This document holds a human-readable list of changes between releases.

.. note::
   pytalk follows the Semantic Versioning guidelines. Releases are numbered with the following format:

    <major>.<minor>.<patch>

   And constructed with the following guidelines:

    Breaking backward compatibility bumps the major (and resets the minor and patch)
    New additions without breaking backward compatibility bumps the minor (and resets the patch)
    Bug fixes and misc changes bump the patch

    For more information on SemVer, please visit http://semver.org/.

:version:`2.0.0` - unreleased
---------------------------------

Breaking Changes & Important Notices
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- **`TeamTalkServerInfo`**: The constructor now accepts only a single dictionary argument.
- **Exceptions**: `TeamTalkException` has been renamed to `TeamTalkError`, and `PermissionError` has been renamed to `PytalkPermissionError`.

Added
~~~~~
- **`TeamTalkServerInfo`**: Added hashability to `TeamTalkServerInfo` objects.

Changed
~~~~~~~
- **`pytalk.enums.Status`**: The `online`, `away`, etc., attributes are now class methods (e.g., `Status.online()`).

Improved
~~~~~~~~
- **Static Typing**: The entire codebase is now fully type-hinted and validated with `mypy` in strict mode.
- **Code Quality**: Replaced all `self.super` calls with standard `super()`.
- **Modernization**: Replaced `os.path` with `pathlib` for path manipulations.
- **Type Safety**: Replaced `typing.Any` with more specific types where possible.
- **Project Management**: Switched to `hatch` for project management, utilizing `uv` for dependency installation.

Fixed
~~~~~
- **Documentation**: Added `on_my_connect_failed` and `on_my_connect_crypt_error` events. Fixed typo in `on_my_disconnect` event and reordered events.
- **Platform Compatibility**: Fixed channel path decoding in `pytalk.TeamTalkInstance.get_path_from_channel` for non-Windows platforms.
- **API Correctness**:
    - Ensured multiple methods consistently return strict `bool` values.
    - Changed the return type of `kick_user` and `ban_user` methods to `bool`.
    - Fixed the `unban_user` method signature to correctly accept an `ip` string.
    - Corrected the `USER_TEXTMESSAGE` subscription mapping.
    - Implemented consistent string decoding in wrapper classes to resolve `b''` prefixes.
- **Bug Fixes**:
    - Fixed the `doPing` method in `pytalk.Server`.
    - Corrected a logic error in `pytalk.TeamTalkInstance.set_input_device`.
    - Fixed the default value for `channel_type` in `pytalk.TeamTalkInstance.create_channel`.
    - Corrected the implementation of `move_user` in `pytalk.TeamTalkInstance`.
    - Fixed `update_properties` in `pytalk.Server` to correctly await SDK confirmation.
    - Fixed a timeout conversion bug in `pytalk.TeamTalkInstance.get_server_statistics`.
    - Fixed an `AttributeError` in statistics by improving `_get_tt_obj_attribute`.
    - Fixed a logical error in the `Statistics.refresh()` method.
- **Internal**:
    - Resolved various `mypy` and `Ruff` linting errors.
    - Ensured `uvloop` is only imported and used on Linux to prevent errors on other platforms.

:version:`1.6.2` - 2025-10-12
---------------------------------

Added
~~~~~
- Added and enabled `uvloop` on Linux to improve asyncio performance.

Fixed
~~~~~
- Fixed a critical `UnboundLocalError` in `pytalk.instance.TeamTalkInstance.kick_user` that occurred when kicking a user from the server.
- Fixed the SDK downloader (`ttsdk_downloader.py`) exiting prematurely, which prevented the library from importing the SDK on the first run after download.

:version:`1.6.1` - 2025-10-12
---------------------------------

Added
~~~~~
- Automatic reconnection with exponential backoff for initial connection failures (`CLIENTEVENT_CON_FAILED`) in `TeamTalkBot.add_server()`.
- Automatic reconnection with exponential backoff on kick (`CLIENTEVENT_CMD_MYSELF_KICKED`), controlled by `reconnect` flag in `TeamTalkBot.add_server()`.
- `backoff_config` parameter (dict) in `TeamTalkBot.add_server()` for per-server customization of backoff behavior (`base`, `exponent`, `max_value`, `max_tries`).
- `pytalk.backoff.Backoff` class for managing exponential backoff logic with jitter.
- `TeamTalkInstance.initial_connect_loop()` method for initial connect & login sequence with retries.
- `TeamTalkInstance.force_reconnect()` method for manual triggering of a full reconnection sequence.

Improved
~~~~~~~~
- Reconnection and retry logic now uses exponential backoff with jitter by default to enhance server stability by desynchronizing mass client reconnections.
- Synchronous SDK calls (`TeamTalkInstance.connect()`, `TeamTalkInstance.login()`) now run in a thread pool executor during connection loops to prevent blocking asyncio event loop.

Fixed
~~~~~
- Corrected permission logic in `kick_user` to allow action if user has global kick rights OR is a channel operator.
- Fixed unreachable code and improved error handling in `kick_user` and `ban_user` methods to provide more specific exceptions.
- Removed incorrect permission check from the internal `_do_cmd` method, ensuring checks are handled by the specific calling methods.
- Added missing `TeamTalkException` import in `pytalk/instance.py`.
- `TeamTalkInstance.connected` and `TeamTalkInstance.logged_in` flags are correctly updated to `False` on `CLIENTEVENT_CMD_MYSELF_KICKED` before reconnection attempts.
- `Backoff` state is reset only after a complete and successful connection and login sequence in `TeamTalkInstance`.

:version:`1.6.0` - 2025-06-05
---------------------------------

Added
~~~~~
- Added media file streaming capabilities:
    - Introduced `pytalk.TeamTalkInstance.start_streaming_media_file_to_channel` for streaming local media files to a channel.
    - Introduced `pytalk.TeamTalkInstance.stop_streaming_media_file_to_channel` to stop active media file streaming.
- Introduced a new `pytalk.enums.Status` helper class for `pytalk.TeamTalkInstance.change_status`:
    - Allows combining user status modes (e.g., `online`, `away`) with gender properties (`.male`, `.female`, `.neutral`) in a more Pythonic and intuitive manner (e.g., `Status.online.female`).

Improved
~~~~~~~~
- The `pytalk.TeamTalkInstance.change_status` method now accepts a combined status integer, intelligently preserving other non-mode/gender related status flags (like video or desktop sharing) when updating.

Changed
~~~~~~~
- In `TeamTalkInstance.login()`, the automatic channel join based on `server_info.join_channel_id`
  will now only attempt to join a channel if `join_channel_id` is strictly positive (>0).
  Previously, a value of 0 or negative would result in joining the root channel. Now, such
  values will result in no channel being joined automatically.

Fixed
~~~~~
- In `Server.join_channel()`, attempting to join a channel by path with an empty or
  whitespace-only string now correctly results in no action (and returns `False`).
  Previously, this would lead to an attempt to join the root channel.
- Fixed several linter issues.

:version:`1.5.1` - 2025-05-16
---------------------------------

Fixed
~~~~~
- Improved stability of audio event processing in ``pytalk.TeamTalkInstance`` by implementing an SDK lock (`_audio_sdk_lock`) to serialize access to critical TeamTalk SDK audio functions. This addresses potential segmentation faults and race conditions during high-frequency audio events.
- Enhanced resource management for audio blocks by ensuring SDK pointers are correctly acquired, data is copied, and pointers are released reliably, even in error scenarios within the event processing loop.
- Refined the internal logic for handling ``CLIENTEVENT_USER_STATECHANGE`` to correctly enable/disable audio block events based on user voice transmission status.

Improved
~~~~~~~~
- Restructured parts of the internal ``_process_events`` method in ``pytalk.TeamTalkInstance`` for better clarity and logical flow of event handling.

:version:`1.5.0` - 2025-05-15
---------------------------------

Added
~~~~~
- Reinstated audio receiving events: `on_user_audio` and `on_muxed_audio` are now available again. (Originally planned for 1.4.5)
- Added new events: `on_user_account_new` (called when a new user account is created on the server) and `on_user_account_remove` (called when a user account is deleted from the server).
- Enhanced `pytalk.TeamTalkInstance.create_user_account` method:
    - Added `user_rights` parameter to allow specifying user permissions (using `pytalk.Permission` values) upon user account creation.
    - Added `note` parameter to allow setting a note upon user account creation.

Changed
~~~~~~~
- Corrected the return type annotation for `pytalk.TeamTalkInstance.create_user_account` from `TeamTalkUserAccount` to `bool` to accurately reflect its actual return value.

Fixed
~~~~~
- Resolved an issue where documentation was not being generated correctly for some elements.
- Fixed Flake8 `DAR203` error related to return type mismatch in `pytalk.TeamTalkInstance.create_user_account` docstring.

Improved
~~~~~~~~
- Updated and significantly clarified docstrings for `pytalk.TeamTalkInstance.create_user_account`, including detailed explanations of new parameters and default behaviors.

Notes
~~~~~
- The core logic for `on_user_audio` and `on_muxed_audio` has not been altered in this version. If your bot encounters issues or crashes when using these re-enabled audio events, please report them via a GitHub issue. While they may function correctly, thorough testing in your environment is recommended. (Note originally from 1.4.5)

:version:`1.4.1` - 2025-05-01
---------------------------------

This release marks a significant transition! The library is now **Pytalk**, residing in its own dedicated repository. This separation stems from the current maintainer's decision to pursue a distinct development path, introducing changes that may differ from the original vision for teamtalk.py held by its previous owner. Driven by differing opinions on future development, a desire for more rapid updates, and the goal of making specific improvements, Pytalk now operates independently as a separate library. As part of this new direction, the restructuring also aims to align Pytalk more closely with the user-friendly patterns found in libraries like discord.py/py-cord, enhancing the developer experience.

Breaking Changes & Important Notices
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- **Project Renamed:** The library is now officially ``pytalk``. This project is independent and not related to ``teamtalk.py``.
  **Action Required:** You **must** update your import statements (e.g., change ``import teamtalk`` to ``import pytalk``) and any other code references. Please review the updated documentation for new conventions.
- **Separate Repository:** Pytalk has been moved to its own repository.
- **PyPI Availability:** Versions prior to 1.4.4 under the old name will **no longer be available** for installation from PyPI. You must use version 1.4.4 or newer of ``pytalk``.
- **Changelog History:** While older versions are unavailable on PyPI, previous changelog entries will be maintained within the new repository for historical reference.

Fixes / Improvements
~~~~~~~~~~~~~~~~~~~~
- **Complete Audio Function Overhaul:** All audio-related functions have been thoroughly reviewed, fixed, and rewritten for improved stability and correctness.
- **Accurate Audio Calculations:** Audio calculation formulas were taken directly from the official TeamTalk Qt client and now work perfectly.

Notes
~~~~~
- Please update your dependencies to use the new ``pytalk`` package name and version 1.4.1 or later.
- Review your existing code for any instances of the old library name and update them to ``pytalk``.

:version:`1.4.0` - 2025-04-28
---------------------------------

Added new capabilities for managing audio input devices and settings.

Added
~~~~~

- Added the ability to list available sound devices and select the desired input device.
- Added functions to get and set the microphone input gain level.
- Added control to enable or disable voice transmission.

:version:`1.3.1` - 2025-04-12
---------------------------------

Removed
~~~~~~~
- Temporarily removed audio receiving event.

:version:`1.3.0` - 2024-11-23
---------------------------------

This release adds audio receiving support through the on_user_audio and on_muxed_audio event. It also adds server statistics support through the teamtalk.Statistics class. In addition, we now do not ignore the first 1 second of events, and we have fixed various recursion errors when trying to get underlying SDK properties from a teamtalk.Channel. We have also fixed a PermissionError when trying to kick a user from a channel, and errors on linux with certain functions due to improper use of sdk.ttstr.

Added
~~~~~

- Added server statistics support. See the new teamtalk.Statistics class for more information.
- Added audio receiving support, see the teamtalk.AudioBlock and teamtalk.MuxedAudioBlock classes for more information.
- Added so we now do not ignore the first 1 second of events.

Fixed
~~~~~

- Fixed various recursion errors when trying to get underlying SDK properties from a teamtalk.Channel.
- Fixed PermissionError when trying to kick a user from a channel.
- Fixed errors on linux with certain functions do to improper use of sdk.ttstr.

:version:`1.2.1` - 2024-07-12
---------------------------------

This release adds the handling of the bot lost connection to the server event, a join_channel method to the teamtalk.Server class, an is_me function to the teamtalk.User class, and more descriptive error messages for the TT SDK Downloader, when failing to extract the sdk due to missing 7zip or equivalent.

Added
~~~~~

- Added the handling of the bot lost connection to the server event.
- Added a join_channel method to the teamtalk.Server class.
- Added an is_me function to the teamtalk.User class.
- Added more descriptive error messages for the TT SDK Downloader, when failing to extract the sdk due to missing 7zip or equivalent.

Fixed
~~~~~

- Fixed a bug that would force debug logging to be enabled globally.



:version:`1.2.0` - 2024-01-31
---------------------------------

This release adds subscriptions, and more expressive dir methods for Permissions, Channel Types and Server Properties, as well as fixing some long standing asyncio bugs. In addition, we also drop test compatibility for python 3.8, and we have updated to TeamTalk SDK 5.15

Added
~~~~~

- Added support for subscriptions. You can now subscribe to events per user and get notified when they happen. You can also unsubscribe from events.
- Added more expressive dir methods for Permissions, Channel Types and Server Properties. Now you can call dir(teamtalk.Permissions) and get a list of all permissions. Same for Channel Types and Server Properties.

Changed / Fixed
~~~~~~~~~~~~~~~

- Updated to TeamTalk SDK 5.15
- Fixed a bug where if a registered coroutine called asyncio.sleep, the entire event loop would freeze until a new event was received.

:version:`1.1.0` - 2023-03-24
---------------------------------

Added
~~~~~

- Added the possibility to get and update TeamTalk Server properties.
- Added the possibility to create, delete, get and list user accounts.
- Added the possibility to create, update and delete channels.
- Added a teamtalk.UserAccount and teamtalk.BannedUserAccount type.
- Added a method that can list banned users.
- Added methods to get a channel from a path and a path from a channel.
- Added methods to make or remove a user as a channel operator.

Changed / Fixed
~~~~~~~~~~~~~~~

- Changed the way we check for permissions. If the bot is admin, it will have all
    permissions. If it is not, it will only have the permissions that are set
    for the bot's user account.
- Fixed the teamtalk.Instance.get_channel function so it now returns correctly.
- Fixed kicking and banning users. We now handle the case where the bot is not
    admin.
- Fixed kicking and banning users. We now handle more errors and raise when appropriate.
- Fixed a bug where it was impossible to get the server from the channel class
    when using it as part of a chain.
- Fixed a bug where it was impossible to get the server from the user class
    when using it as part of a chain.
- Fixed a bug where the sdk downloader would not work on linux, due to missing a user agent.



:version:`1.0.0` - 2023-03-01
----------------------------------

Initial release.
