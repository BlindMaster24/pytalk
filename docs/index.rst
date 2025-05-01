Welcome to the Pytalk Documentation
========================================

Pytalk is a Python library that provides a simple interface to connect to, and interact with, TeamTalk servers.


Installation
------------

To install Pytalk, simply run the following command:

.. code-block::

    pip install pytalk

Alternatively, you can download the source code from the GitHub repository and run the following command:

.. code-block::

    git clone https://github.com/BlindMaster24/pytalk.git
    cd pytalk
    uv build
    pip install dist/py_talk-*.tar.gz


Quick Start
-----------

To quickly get started with Pytalk, you can use the following code snippet:

.. code-block::

    import pytalk

    # Create a new TeamTalk bot
    bot = teamtalk.Bot()

    # listen to some events
    @bot.event
    def on_ready():
        print("Bot is ready!")

    @bot.event
    def on_message(message):
        print(f"Received message: {message}")

    # then add our servers
    bot.add_server("localhost", 10333, 10333, "serveradmin", "password")

    # and finally, connect to the servers and start listening for events
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
