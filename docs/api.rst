API Reference
===============

The following section outlines the API of pytalk.

.. note::

    This module uses the Python logging module to log diagnostic and errors
    in an output independent way.  If the logging module is not configured,


Bot
--------

.. automodule:: pytalk.bot

.. autoclass:: pytalk.bot.TeamTalkBot
    :members:
    :exclude-members: event,dispatch

    .. automethod:: pytalk.bot.TeamTalkBot.event()
        :decorator:


Enums
--------

.. automodule:: pytalk.enums
    :members:


Server
--------

.. automodule:: pytalk.server
    :members:


Channel
--------

.. automodule:: pytalk.channel
    :members:


UserAccount
--------

.. automodule:: pytalk.user_account
    :members:


User
--------

.. automodule:: pytalk.user
    :members:


Message
-----------

.. automodule:: pytalk.message
    :members:


Audio Streaming
--------------------

.. automodule:: pytalk.streamer
    :members:


Files
--------

.. automodule:: pytalk.tt_file
    :members:


Permission
-------------

.. automodule:: pytalk.permission
    :members:


Subscriptions
-------------

.. automodule:: pytalk.subscription
    :members:


Exceptions
------------

.. automodule:: pytalk.exceptions
    :members:


TeamTalkInstance (low level)
--------------------------------

.. automodule:: pytalk.instance
    :members:
