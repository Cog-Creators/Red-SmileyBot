.. _customcommands:

==============
CustomCommands
==============

This is the cog guide for the customcommands cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load customcom

.. _customcommands-usage:

-----
Usage
-----

This cog contains commands for creating and managing custom commands that display text.

These are useful for storing information members might need, like FAQ answers or invite links.
Custom commands can be used by anyone by default, so be careful with pings.
Commands can only be lowercase, and will not respond to any uppercase letters.


.. _customcommands-commands:

--------
Commands
--------

.. _customcommands-command-customcom:

^^^^^^^^^
customcom
^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]customcom 

.. tip:: Alias: ``cc``

**Description**

Base command for Custom Commands management.

.. _customcommands-command-customcom-cooldown:

""""""""""""""""""
customcom cooldown
""""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]customcom cooldown <command> [cooldown] [per=member]

**Description**

Set, edit, or view the cooldown for a custom command.

You may set cooldowns per member, thread/channel, or guild. Multiple
cooldowns may be set. All cooldowns must be cooled to call the
custom command.

Examples:
    - ``[p]customcom cooldown pingrole``
    - ``[p]customcom cooldown yourcommand 30``
    - ``[p]cc cooldown mycommand 30 guild``

**Arguments:**

- ``<command>`` The custom command to check or set the cooldown.
- ``[cooldown]`` The number of seconds to wait before allowing the command to be invoked again. If omitted, will instead return the current cooldown settings.
- ``[per]`` The group to apply the cooldown on. Defaults to per member. Valid choices are server / guild, user / member, and channel.

.. _customcommands-command-customcom-create:

""""""""""""""""
customcom create
""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]customcom create <command> <text>

.. tip:: Alias: ``customcom add``

**Description**

Create custom commands.

If a type is not specified, a simple CC will be created.
CCs can be enhanced with arguments, see the guide
:ref:`here <cog_customcom>`.

.. _customcommands-command-customcom-create-random:

"""""""""""""""""""""""
customcom create random
"""""""""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]customcom create random <command>

**Description**

Create a CC where it will randomly choose a response!

Note: This command is interactive.

**Arguments:**

- ``<command>`` The command executed to return the text. Cast to lowercase.

.. _customcommands-command-customcom-create-simple:

"""""""""""""""""""""""
customcom create simple
"""""""""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]customcom create simple <command> <text>

**Description**

Add a simple custom command.

Example:
    - ``[p]customcom create simple yourcommand Text you want``

**Arguments:**

- ``<command>`` The command executed to return the text. Cast to lowercase.
- ``<text>`` The text to return when executing the command. See guide for enhanced usage.

.. _customcommands-command-customcom-delete:

""""""""""""""""
customcom delete
""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]customcom delete <command>

.. tip:: Aliases: ``customcom del``, ``customcom remove``

**Description**

Delete a custom command.

Example:
    - ``[p]customcom delete yourcommand``

**Arguments:**

- ``<command>`` The custom command to delete.

.. _customcommands-command-customcom-edit:

""""""""""""""
customcom edit
""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]customcom edit <command> [text]

**Description**

Edit a custom command.

Example:
    - ``[p]customcom edit yourcommand Text you want``

**Arguments:**

- ``<command>`` The custom command to edit.
- ``<text>`` The new text to return when executing the command.

.. _customcommands-command-customcom-list:

""""""""""""""
customcom list
""""""""""""""

**Syntax**

.. code-block:: none

    [p]customcom list 

**Description**

List all available custom commands.

The list displays a preview of each command's response, with
markdown escaped and newlines replaced with spaces.

.. _customcommands-command-customcom-raw:

"""""""""""""
customcom raw
"""""""""""""

**Syntax**

.. code-block:: none

    [p]customcom raw <command>

**Description**

Get the raw response of a custom command, to get the proper markdown.

This is helpful for copy and pasting.

**Arguments:**

- ``<command>`` The custom command to get the raw response of.

.. _customcommands-command-customcom-search:

""""""""""""""""
customcom search
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]customcom search <query>

**Description**

Searches through custom commands, according to the query.

Uses fuzzy searching to find close matches.

**Arguments:**

- ``<query>`` The query to search for. Can be multiple words.

.. _customcommands-command-customcom-show:

""""""""""""""
customcom show
""""""""""""""

**Syntax**

.. code-block:: none

    [p]customcom show <command_name>

**Description**

Shows a custom command's responses and its settings.

**Arguments:**

- ``<command_name>`` The custom command to show.
