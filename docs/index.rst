Welcome to the Pytalk Documentation
========================================

Pytalk is a Python library that provides a simple interface to connect to, and interact with, TeamTalk servers.


Installation
------------

To install Pytalk, simply run the following command:

.. code-block::

    pip install py-talk-ex

Alternatively, you can download the source code from the GitHub repository and run the following command:

.. code-block::

    git clone https://github.com/BlindMaster24/pytalk.git
    cd pytalk
    uv build
    pip install dist/py_talk_ex-*.tar.gz


Quick Start
-----------

If you own a TeamTalk SDK license, you can supply it at initialization so the
SDK is unlocked with your credentials. Both ``license_name`` and
``license_key`` must be provided together, and the license is process-wide, so
all bot instances must share the same credentials. Otherwise, you can omit
them.

To quickly get started with Pytalk, you can use the following code snippet:

.. code-block::

    import pytalk

bot = pytalk.TeamTalkBot(
    # Optional: apply your TeamTalk SDK license details if you have them
    license_name="Your Company",
    license_key="XXXXX-XXXXX-XXXXX-XXXXX",
)

@bot.event
async def on_ready():
    test_server = pytalk.TeamTalkServerInfo("localhost", 10335, 10335, "user", "pass")
    await bot.add_server(test_server)

@bot.event
async def on_message(message):
    if message.content.lower() == "ping":
        message.reply("pong")

bot.run()


Useful Links
------------

Below are some useful links to help you get started with teamtalk.py:

* :doc:`event reference </events>`
* :doc:`API Documentation </api>`
* :doc:`whats-new </whats-new>`
* `GitHub Repository <https://github.com/BlindMaster24/pytalk>`_
* `PyPI <https://pypi.org/project/py-talk-ex/>`_


Contributing
------------

So you want to contribute to teamtalk.py? Great! There are many ways to contribute to this project, and all contributions are welcome.

If you have found a bug, have a feature request or want to help improve documentation please `open an issue <https://github.com/BlindMaster24/pytalk/issues/new>`_


License
-------

Pytalk is licensed under the MIT License. See the `LICENSE <https://github.com/BlindMaster24/pytalk/blob/master/LICENSE>`_ file for more information.
