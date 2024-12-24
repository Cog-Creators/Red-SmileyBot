.. _filter:

======
Filter
======

This is the cog guide for the filter cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load filter

.. _filter-usage:

-----
Usage
-----

This cog is designed for "filtering" unwanted words and phrases from a server.

It provides tools to manage a list of words or sentences, and to customize automatic actions to be taken against users who use those words in channels or in their name/nickname.

This can be used to prevent inappropriate language, off-topic discussions, invite links, and more.


.. _filter-commands:

--------
Commands
--------

.. _filter-command-filter:

^^^^^^
filter
^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]filter 

**Description**

Base command to add or remove words from the server filter.

Use double quotes to add or remove sentences.

.. _filter-command-filter-add:

""""""""""
filter add
""""""""""

**Syntax**

.. code-block:: none

    [p]filter add [words...]

**Description**

Add words to the filter.

Use double quotes to add sentences.

Examples:
    - ``[p]filter add word1 word2 word3``
    - ``[p]filter add "This is a sentence"``

**Arguments:**

- ``[words...]`` The words or sentences to filter.

.. _filter-command-filter-channel:

""""""""""""""
filter channel
""""""""""""""

**Syntax**

.. code-block:: none

    [p]filter channel 

**Description**

Base command to add or remove words from the channel filter.

Use double quotes to add or remove sentences.

.. _filter-command-filter-channel-add:

""""""""""""""""""
filter channel add
""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]filter channel add [words...]

**Description**

Add words to the filter.

Use double quotes to add sentences.

Examples:
    - ``[p]filter channel add #channel word1 word2 word3``
    - ``[p]filter channel add #channel "This is a sentence"``

**Arguments:**

- ``<channel>`` The text, voice, stage, or forum channel to add filtered words to.
- ``[words...]`` The words or sentences to filter.

.. _filter-command-filter-channel-clear:

""""""""""""""""""""
filter channel clear
""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]filter channel clear

**Description**

Clears this channel's filter list.

.. _filter-command-filter-channel-list:

"""""""""""""""""""
filter channel list
"""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]filter channel list 

**Description**

Send a list of the channel's filtered words.

.. _filter-command-filter-channel-remove:

"""""""""""""""""""""
filter channel remove
"""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]filter channel remove <channel> [words...]

**Description**

Remove words from the filter.

Use double quotes to remove sentences.

Examples:
    - ``[p]filter channel remove #channel word1 word2 word3``
    - ``[p]filter channel remove #channel "This is a sentence"``

**Arguments:**

- ``<channel>`` The text, voice, stage, or forum channel to add filtered words to.
- ``[words...]`` The words or sentences to no longer filter.

.. _filter-command-filter-clear:

""""""""""""
filter clear
""""""""""""

**Syntax**

.. code-block:: none

    [p]filter clear

**Description**

Clears this server's filter list.

.. _filter-command-filter-delete:

"""""""""""""
filter delete
"""""""""""""

**Syntax**

.. code-block:: none

    [p]filter delete [words...]

.. tip:: Aliases: ``filter remove``, ``filter del``

**Description**

Remove words from the filter.

Use double quotes to remove sentences.

Examples:
    - ``[p]filter remove word1 word2 word3``
    - ``[p]filter remove "This is a sentence"``

**Arguments:**

- ``[words...]`` The words or sentences to no longer filter.

.. _filter-command-filter-list:

"""""""""""
filter list
"""""""""""

**Syntax**

.. code-block:: none

    [p]filter list 

**Description**

Send a list of this server's filtered words.

.. _filter-command-filter-names:

""""""""""""
filter names
""""""""""""

**Syntax**

.. code-block:: none

    [p]filter names 

**Description**

Toggle name and nickname filtering.

This is disabled by default.

.. _filter-command-filterset:

^^^^^^^^^
filterset
^^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]filterset 

**Description**

Base command to manage filter settings.

.. _filter-command-filterset-ban:

"""""""""""""
filterset ban
"""""""""""""

**Syntax**

.. code-block:: none

    [p]filterset ban <count> <timeframe>

**Description**

Set the filter's autoban conditions.

Users will be banned if they send ``<count>`` filtered words in
``<timeframe>`` seconds.

Set both to zero to disable autoban.

Examples:
    - ``[p]filterset ban 5 5`` - Ban users who say 5 filtered words in 5 seconds.
    - ``[p]filterset ban 2 20`` - Ban users who say 2 filtered words in 20 seconds.

**Arguments:**

- ``<count>`` The amount of filtered words required to trigger a ban.
- ``<timeframe>`` The period of time in which too many filtered words will trigger a ban.

.. _filter-command-filterset-defaultname:

"""""""""""""""""""""
filterset defaultname
"""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]filterset defaultname <name>

**Description**

Set the nickname for users with a filtered name.

Note that this has no effect if filtering names is disabled
(to toggle, run ``[p]filter names``).

The default name used is *John Doe*.

Example:
    - ``[p]filterset defaultname Missingno``

**Arguments:**

- ``<name>`` The new nickname to assign.
