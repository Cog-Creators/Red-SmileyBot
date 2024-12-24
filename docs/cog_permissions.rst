.. Permissions Cog Reference
.. _cog_permissions:

=========================
Permissions Cog Reference
=========================

------------
How it works
------------

When loaded, the permissions cog will allow you to define extra custom rules for who can use a
command.

If no applicable rules are found, the command will behave normally.

Rules can also be added to cogs, which will affect all commands from that cog. The cog name can be
found from the help menu.

-------------
Rule priority
-------------

Rules set for subcommands will take precedence over rules set for the parent commands, which
lastly take precedence over rules set for the cog. So for example, if a user is denied the Core
cog, but allowed the ``[p]set token`` command, the user will not be able to use any command in the
Core cog except for ``[p]set token``.

In terms of scope, global rules will be checked first, then server rules.

For each of those, the first rule pertaining to one of the following models will be used:

1. User
2. Voice/stage channel a user is connected to
3. The channel command was issued in (parent channel in case of invocations in threads)
4. Channel category
5. Roles, highest to lowest
6. Server (can only be in global rules)
7. Default rules

In private messages, only global rules about a user will be checked.

-------------------------
Setting Rules From a File
-------------------------

The permissions cog can also set, display or update rules with a YAML file with the
``[p]permissions yaml`` command. Models must be represented by ID. Rules must be ``true`` for
allow, or ``false`` for deny. Here is an example:

.. code-block:: yaml

    COG:
      Admin:
        78631113035100160: true
        96733288462286848: false
      Audio:
        133049272517001216: true
        default: false
    COMMAND:
      cleanup bot:
        78631113035100160: true
        default: false
      ping:
        96733288462286848: false
        default: true

----------------------
Example configurations
----------------------

Locking the ``[p]play`` command to approved server(s) as a bot owner:

.. code-block:: none

    [p]permissions setdefaultglobalrule deny play
    [p]permissions addglobalrule allow play [server ID or name]

Locking the ``[p]play`` command to specific voice channel(s) as a serverowner or admin:

.. code-block:: none

    [p]permissions setdefaultserverrule deny play
    [p]permissions setdefaultserverrule deny "playlist start"
    [p]permissions addserverrule allow play [voice channel ID or name]
    [p]permissions addserverrule allow "playlist start" [voice channel ID or name]

Allowing extra roles to use ``[p]cleanup``:

.. code-block:: none

    [p]permissions addserverrule allow cleanup [role ID]

Preventing ``[p]cleanup`` from being used in channels where message history is important:

.. code-block:: none

    [p]permissions addserverrule deny cleanup [channel ID or mention]
