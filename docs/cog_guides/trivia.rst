.. _trivia:

======
Trivia
======

This is the cog guide for the trivia cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load trivia

.. _trivia-usage:

-----
Usage
-----

This cog allows for playing trivia with others. You may 
choose to play just one category at a time or choose 
multiple to add variety to your game. You can even create 
your own lists!

.. _trivia-commands:

--------
Commands
--------

Here is a list of all of the commands for this cog:

.. _trivia-command-triviaset:

^^^^^^^^^
triviaset
^^^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]triviaset

**Description**

Commands for managing trivia settings.

.. _trivia-command-triviaset-botplays:

^^^^^^^^^^^^^^^^^^
triviaset botplays
^^^^^^^^^^^^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]triviaset botplays <true_or_false>

**Description**

Sets whether the bot gains a point if nobody guesses correctly.

**Arguments**

- ``<true_or_false>`` If ``true``, the bot will gain a point if nobody
  guesses correctly, otherwise it will not.

.. _trivia-command-triviaset-maxscore:

^^^^^^^^^^^^^^^^^^
triviaset maxscore
^^^^^^^^^^^^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]triviaset maxscore <score>

**Description**

Sets the total points required to win.

**Arguments**

- ``<score>`` The amount of points required to win.

.. _trivia-command-triviaset-override:

^^^^^^^^^^^^^^^^^^
triviaset override
^^^^^^^^^^^^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]triviaset override <enabled>

**Description**

Allow/disallow trivia lists to override the settings.

**Arguments**

- ``<enabled>`` Whether trivia lists should be able to override settings.

.. _trivia-command-triviaset-payout:

^^^^^^^^^^^^^^^^
triviaset payout
^^^^^^^^^^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]triviaset payout <multiplier>

**Description**

Sets the payout multiplier. 

If a user wins trivia when at least 3 users are playing, they will receive credits; 
the amount received is determined by multiplying their total score by this multiplier.

**Arguments**

- ``<multiplier>`` The amount to multiply the winner's score by to determine payout.
  This can be any positive decimal number. Setting this to 0 will disable.

.. _trivia-command-triviaset-revealanswer:

^^^^^^^^^^^^^^^^^^^^^^
triviaset revealanswer
^^^^^^^^^^^^^^^^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]triviaset revealanswer <true_or_false>

**Description**

Sets whether or not the answer is revealed if the time limit for answering runs out.

**Arguments**

- ``<true_or_false>`` If ``true``, the bot will reveal the answer if there is no
  correct guess within the time limit.

.. _trivia-command-triviaset-showsettings:

^^^^^^^^^^^^^^^^^^^^^^
triviaset showsettings
^^^^^^^^^^^^^^^^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]triviaset showsettings

**Description**

Shows the current trivia settings.

.. _trivia-command-triviaset-stopafter:

^^^^^^^^^^^^^^^^^^^
triviaset stopafter
^^^^^^^^^^^^^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]triviaset stopafter <seconds>

**Description**

Sets how long the bot should wait before stopping the trivia 
session due to lack of response.

**Arguments**

- ``<seconds>`` The number of seconds to wait before stopping the session.

.. _trivia-command-triviaset-timelimit:

^^^^^^^^^^^^^^^^^^^
triviaset timelimit
^^^^^^^^^^^^^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]triviaset timelimit <seconds>

**Description**

Sets the maximum time permitted to answer a question.

**Arguments**

- ``<seconds>`` The number of seconds to wait for an answer.

.. _trivia-command-triviaset-custom:

^^^^^^^^^^^^^^^^
triviaset custom
^^^^^^^^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]triviaset custom

**Description**

Manage custom trivia lists.

.. tip:: 

    Looking to learn how to create your own trivia lists?
    See :ref:`here <guide_trivia_list_creation>` for more information.

.. _trivia-command-triviaset-custom-upload:

^^^^^^^^^^^^^^^^^^^^^^^
triviaset custom upload
^^^^^^^^^^^^^^^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]triviaset custom upload

**Description**

Upload a custom trivia list. The bot will prompt you to upload 
your list as an attachment in Discord.

.. _trivia-command-triviaset-custom-list:

^^^^^^^^^^^^^^^^^^^^^
triviaset custom list
^^^^^^^^^^^^^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]triviaset custom list

**Description**

List all uploaded custom trivia lists.

.. _trivia-command-triviaset-custom-delete:

^^^^^^^^^^^^^^^^^^^^^^^
triviaset custom delete
^^^^^^^^^^^^^^^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]triviaset custom delete <name>

**Description**

Delete a custom trivia list.

**Arguments**

- ``<name>`` The name of the custom list to be deleted.

.. _trivia-command-trivia:

^^^^^^
trivia
^^^^^^

**Syntax**

.. code-block:: none

    [p]trivia <categories...>

**Description**

Start a trivia session on the specified category.

Multiple categories can be listed, in which case the trivia session 
will use all of the specified lists to select questions from.

**Arguments**

- ``<categories...>`` The category to play. Can be multiple.

.. _trivia-command-trivia-info:

^^^^^^^^^^^
trivia info
^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]trivia info <category>

**Description**

Get information about a trivia category.

**Arguments**

* ``<category>``: The category to get the information for.

.. _trivia-command-trivia-leaderboard:

^^^^^^^^^^^^^^^^^^
trivia leaderboard
^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]trivia leaderboard

**Description**

Shows the trivia leaderboard. Defaults to the top ten in the 
current server, sorted by total wins. The subcommands provide 
more customized leaderboards.

.. _trivia-command-trivia-leaderboard-global:

^^^^^^^^^^^^^^^^^^^^^^^^^
trivia leaderboard global
^^^^^^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]trivia leaderboard global [sort_by=wins] [top=10]

**Description**

The global trivia leaderboard.

**Arguments**

- ``[sort_by=wins]`` The method by which to sort the leaderboard (defaults to wins). Can be one of:

    - ``wins`` Total wins
    - ``avg`` Average score
    - ``total`` Total correct answers from all sessions
    - ``games`` Total games played.

- ``[top=10]`` The number of ranks to show on the leaderboard. Defaults to 10

.. _trivia-command-trivia-leaderboard-server:

^^^^^^^^^^^^^^^^^^^^^^^^^
trivia leaderboard server
^^^^^^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]trivia leaderboard server [sort_by=wins] [top=10]

**Description**

The trivia leaderboard for this server.

**Arguments**

- ``[sort_by=wins]`` The method by which to sort the leaderboard (defaults to wins). Can be one of:

    - ``wins`` Total wins
    - ``avg`` Average score
    - ``total`` Total correct answers from all sessions
    - ``games`` Total games played.

- ``[top=10]`` The number of ranks to show on the leaderboard. Defaults to 10

.. _trivia-command-trivia-list:

^^^^^^^^^^^
trivia list
^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]trivia list

**Description**

Lists the available trivia categories

.. _trivia-command-trivia-stop:

^^^^^^^^^^^
trivia stop
^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]trivia stop

**Description**

Stops an ongoing trivia session.
