.. _admin:

=====
Admin
=====

This is the cog guide for the admin cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load admin

.. _admin-usage:

-----
Usage
-----

This cog will provide tools for server admins and bot owners.

It can add or remove a role to a member, edit one or make some available
for members so they can self-assign them as they wish.

It also provides tools for the bot owner such as server locking (once enabled,
the bot will instantly leave new servers it joins) and announcements, which
can send something in all the servers of the bot.

.. _admin-commands:

--------
Commands
--------

Here's a list of all commands available for this cog.

.. _admin-command-selfrole:

^^^^^^^^
selfrole
^^^^^^^^

**Syntax**

.. code-block:: none

    [p]selfrole <selfrole>

**Description**

Add or remove a role from yourself. It must have been configured as user settable
by admins using the :ref:`selfroleset command <admin-command-selfroleset>`.

**Arguments**

* ``<selfrole>``: The role you want to attribute or remove from yourself. |role-input|

.. _admin-command-selfrole-add:

""""""""""""
selfrole add
""""""""""""

**Syntax**

.. code-block:: none

    [p]selfrole add <selfrole>

**Description**

Add a role to yourself. It must have been configured as user settable
by admins using the :ref:`selfroleset command <admin-command-selfroleset>`.

**Arguments**

* ``<selfrole>``: The role you want to attribute to yourself. |role-input|

.. _admin-command-selfrole-remove:

"""""""""""""""
selfrole remove
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]selfrole remove <selfrole>

**Description**

Remove a role from yourself. It must have been configured as user settable
by admins using the :ref:`selfroleset command <admin-command-selfroleset>`.

**Arguments**

* ``<selfrole>``: The role you want to remove from yourself. |role-input|


.. _admin-command-selfrole-list:

"""""""""""""
selfrole list
"""""""""""""

**Syntax**

.. code-block:: none

    [p]selfrole list

**Description**

List all of the available roles you can assign to yourself.

.. _admin-command-selfroleset:

^^^^^^^^^^^
selfroleset
^^^^^^^^^^^

.. note:: |admin-lock| This is also usable by the members with the
    ``Manage roles`` permission.

**Syntax**

.. code-block:: none

    [p]selfroleset

**Description**

Define the list of user settable roles. Those roles will be available to any
member using the :ref:`selfrole command <admin-command-selfrole>`.

.. _admin-command-selfroleset-add:

"""""""""""""""
selfroleset add
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]selfroleset add <role>

**Description**

Add a role, or a selection of roles, to the list of available selfroles.

.. warning:: Members will be able to assign themselves the role.
    Make sure it doesn't give extra perms or anything that can break
    your server's security.

**Arguments**

* ``<role>``: The role to add to the list. |role-input|

.. _admin-command-selfroleset-clear:

"""""""""""""""""
selfroleset clear
"""""""""""""""""

**Syntax**

.. code-block:: none

    [p]selfroleset clear

**Description**

Clear the list of available selfroles for this server.

.. _admin-command-selfroleset-remove:

""""""""""""""""""
selfroleset remove
""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]selfroleset remove <role>

**Description**

Remove a role, or a selection of roles, from the list of available selfroles.

**Arguments**

* ``<role>``: The role to remove from the list. |role-input|

.. _admin-command-addrole:

^^^^^^^
addrole
^^^^^^^

.. note:: |admin-lock| This is also usable by the members with the ``Manage
    roles`` permission.

**Syntax**

.. code-block:: none

    [p]addrole <rolename> [user]

**Description**

Adds a role to a member. If ``user`` is not given, it will be considered
as yourself, the command author.

**Arguments**

* ``<role>``: The role to add to the member. |role-input-quotes|

* ``[user]``: The member you want to add the role to. Defaults to the
  command author. |member-input|

.. _admin-command-removerole:

^^^^^^^^^^
removerole
^^^^^^^^^^

.. note:: |admin-lock| This is also usable by the members with the
    ``Manage roles`` permission.

**Syntax**

.. code-block:: none

    [p]removerole <rolename> [user]

**Description**

Removes a role from a member. If ``user`` is not given, it will be considered
as yourself, the command author.

**Arguments**

* ``<role>``: The role to remove. |role-input-quotes|

* ``[user]``: The member to remove the role from. |member-input| Defaults
  to the command author.

.. _admin-command-editrole:

^^^^^^^^
editrole
^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]editrole

**Description**

Edits the settings of a role.

.. _admin-command-editrole-name:

"""""""""""""
editrole name
"""""""""""""

**Syntax**

.. code-block:: none

    [p]editrole name <role> <name>

**Description**

Edits the name of a role.

**Arguments**

* ``<role>``: The role name to edit. |role-input-quotes|

* ``<name>``: The new role name. If it has spaces, you must use quotes.

.. _admin-command-editrole-color:

""""""""""""""
editrole color
""""""""""""""

**Syntax**

.. code-block:: none

    [p]editrole color <role> <color>

**Description**

Edits the color of a role.

**Arguments**

* ``<role>``: The role name to edit. |role-input-quotes|

* ``<color>``: The new color to assign. |color-input|

**Examples**

* ``[p]editrole color "My role" #ff0000``

* ``[p]editrole color "My role" dark_blue``

.. _admin-command-announce:

^^^^^^^^
announce
^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]announce <message>

**Description**

Announce your message to all of the servers the bot is in.

The bot will announce the message in the guild's announcements channel.
If this channel is not set, the message won't be announced.

**Arguments**

* ``<message>``: The message to send.

.. _admin-command-announce-cancel:

"""""""""""""""
announce cancel
"""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]announce cancel

**Description**

Cancels an active announcement.

.. _admin-command-announceset:

^^^^^^^^^^^
announceset
^^^^^^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]announceset

**Description**

Change how announcements are received in this guild.

.. _admin-command-announceset-channel:

"""""""""""""""""""
announceset channel
"""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]announceset channel <channel>

**Description**

Sets the channel where the bot owner announcements will be sent.

**Arguments**

* ``<channel>``: The channel that will be used for bot announcements.
  |channel-input|

.. _admin-command-announceset-clearchannel:

""""""""""""""""""""""""
announceset clearchannel
""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]announceset clearchannel

**Description**

Disables announcements on your server. To enable them again, you will have to
re-enter your announcements channel with the :ref:`announceset channel
<admin-command-announceset-channel>` command.

.. _admin-command-serverlock:

^^^^^^^^^^
serverlock
^^^^^^^^^^

.. note:: |owner-lock| This is also usable by the members with the
    ``Administrator`` permission.

**Syntax**

.. code-block:: none

    [p]serverlock

**Description**

Lock a bot to its current servers only.

This means that, once you enable this, if someone invites the bot to a new
server, the bot will automatically leave the server.

.. tip:: Another way to prevent your bot from being invited on more servers is
    making it private directly from the developer portal.

    Once a bot is private, it can only be invited by its owner (or team
    owners). Other users will get an error on Discord's webpage explaining that
    the bot is private.

    To do this, go to the `Discord developer portal
    <https://discord.com/developers>`_, select your application, click "Bot" in
    the sidebar, then untick "Public bot".

    .. image:: ../.resources/admin/public_bot.png
