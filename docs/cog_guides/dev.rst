.. _dev:

===
Dev
===

This is the cog guide for the dev cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load dev

.. _dev-usage:

-----
Usage
-----

Various development focused utilities. All commands in this cog are
restricted to the bot owners.

.. note::

    Unlike other cogs, the Dev cog is only loaded if the bot is
    started with the ``--dev`` flag.

    .. warning::

        It is not suggested that you run Dev in production. Many
        of these cog's commands may cause down-the-line complications if
        not used appropriately.

.. _dev-commands:

--------
Commands
--------

.. _dev-command-bypasscooldowns:

^^^^^^^^^^^^^^^
bypasscooldowns
^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]bypasscooldowns [toggle]

**Description**

Give bot owners the ability to bypass cooldowns. Note that this bypass
does not persist through restarts/shutdowns.

**Arguments**

* ``[toggle]``: |bool-input| Otherwise, defaults to the inverse of the current setting.

.. _dev-command-debug:

^^^^^
debug
^^^^^

**Syntax**

.. code-block:: none

    [p]debug <code>

**Description**

Evaluate a statement of python code.

The bot will always respond with the return value of the code.
If the return value of the code is a coroutine, it will be awaited,
and the result of that will be the bot's response.

Note: Only one statement may be evaluated. Using certain restricted
keywords, e.g. yield, will result in a syntax error. For multiple
lines or asynchronous code, see [p]repl or [p]eval.

**Environment Variables**

* ``ctx``: Command invocation context
* ``bot``: The bot object
* ``channel``: The current channel object
* ``author``: The current author's member object
* ``guild``: The current guild object
* ``message``: The command's message object
* ``aiohttp``: The aiohttp library
* ``asyncio``: The asyncio library
* ``discord``: The discord.py library
* ``commands``: The redbot.core.commands module
* ``cf``: The redbot.core.utils.chat_formatting module
* ``_``: The result from the last dev command

**Arguments**

* ``<code>``: The statement to run.

.. _dev-command-eval:

^^^^
eval
^^^^

**Syntax**

.. code-block:: none

    [p]eval <body>

**Description**

Execute asynchronous code.

This command wraps code into the body of an async function and then
calls and awaits it. The bot will respond with anything printed to
stdout, as well as the return value of the function.

The code can be within a codeblock, inline code or neither, as long
as they are not mixed and they are formatted correctly.

**Environment Variables**

* ``ctx``: Command invocation context
* ``bot``: The bot object
* ``channel``: The current channel object
* ``author``: The current author's member object
* ``guild``: The current guild object
* ``message``: The command's message object
* ``aiohttp``: The aiohttp library
* ``asyncio``: The asyncio library
* ``discord``: The discord.py library
* ``commands``: The redbot.core.commands module
* ``cf``: The redbot.core.utils.chat_formatting module
* ``_``: The result from the last dev command

**Arguments**

* ``<body>``: The code to evaluate.

.. _dev-command-mock:

^^^^
mock
^^^^

**Syntax**

.. code-block:: none

    [p]mock <user> <command>

**Description**

Mock another user invoking a command. The prefix must not be entered.

**Arguments**

* ``<user>``: The user to mock. |user-input-quotes|
* ``<command>``: The command to invoke.

.. _dev-command-mockmsg:

^^^^^^^
mockmsg
^^^^^^^

**Syntax**

.. code-block:: none

    [p]mockmsg <user> <content>

**Description**

Dispatch a message event as if it were sent by a different user.

Current message is used as a base (including attachments, embeds, etc.),
the content and author of the message are replaced with the given arguments.

**Arguments**

* ``<user>``: The member to mock. |user-input-quotes|
* ``<content>``: The content used for the message.

.. note:: 

        If ``content`` isn't passed, the message needs to contain embeds, attachments,
        or anything else that makes the message non-empty.

.. _dev-command-repl:

^^^^
repl
^^^^

**Syntax**

.. code-block:: none

    [p]repl 

**Description**

Open an interactive REPL.

The REPL will only recognise code as messages which start with a
backtick. This includes codeblocks, and as such multiple lines can be
evaluated.

Use ``exit()`` or ``quit`` to exit the REPL session, prefixed with
a backtick so they may be interpreted.

**Environment Variables**

* ``ctx``: Command invocation context
* ``bot``: The bot object
* ``channel``: The current channel object
* ``author``: The current author's member object
* ``guild``: The current guild object
* ``message``: The command's message object
* ``aiohttp``: The aiohttp library
* ``asyncio``: The asyncio library
* ``discord``: The discord.py library
* ``commands``: The redbot.core.commands module
* ``cf``: The redbot.core.utils.chat_formatting module
* ``_``: The result from the last dev command

.. _dev-command-repl-pause:

""""""""""
repl pause
""""""""""

**Syntax**

.. code-block:: none

    [p]repl pause [toggle]

**Description**

Pauses/resumes the REPL running in the current channel.

**Arguments**

* ``[toggle]``: |bool-input| Otherwise, defaults to the inverse of the current setting.
