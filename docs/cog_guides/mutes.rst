.. _mutes:

=====
Mutes
=====

This is the cog guide for the mutes cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load mutes

.. _mutes-usage:

-----
Usage
-----

Mute users temporarily or indefinitely.

.. _mutes-commands:

--------
Commands
--------

.. _mutes-command-activemutes:

^^^^^^^^^^^
activemutes
^^^^^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]activemutes 

**Description**

Displays active mutes on this server.

.. _mutes-command-mute:

^^^^
mute
^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]mute <users...> [time_and_reason]

**Description**

Mute users.

Examples:

* ``[p]mute @member1 @member2 spam 5 hours``
* ``[p]mute @member1 3 days``

**Arguments**

* ``<users...>``: A space separated list of usernames, ID's, or mentions.
* ``[time_and_reason]``: The time and reason. If no time is provided, the mute will use the default set time or indefinite if this hasn't been configured.

.. _mutes-command-mutechannel:

^^^^^^^^^^^
mutechannel
^^^^^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]mutechannel <users...> [time_and_reason]

.. tip:: Alias: ``channelmute``

**Description**

Mute a user in the current text channel (or in the parent of the current thread).

Examples:

* ``[p]mutechannel @member1 @member2 spam 5 hours``
* ``[p]mutechannel @member1 3 days``

**Arguments**

* ``<users...>``: A space separated list of usernames, ID's, or mentions.
* ``[time_and_reason]``: The time and reason. If no time is provided, the mute will use the default set time or indefinite if this hasn't been configured.

.. _mutes-command-muteset:

^^^^^^^
muteset
^^^^^^^

**Syntax**

.. code-block:: none

    [p]muteset 

**Description**

Mute settings.

.. _mutes-command-muteset-defaulttime:

"""""""""""""""""""
muteset defaulttime
"""""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]muteset defaulttime [time]

.. tip:: Alias: ``muteset time``

**Description**

Set the default mute time for the mute command.

If no time interval is provided this will be cleared.

**Arguments**

* ``[time]``: The length of time for a default mute.

.. _mutes-command-muteset-makerole:

""""""""""""""""
muteset makerole
""""""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]muteset makerole <name>

**Description**

Create a Muted role.

This will create a role and apply overwrites to all available channels
to more easily setup muting a user.

If you already have a muted role created on the server use
``[p]muteset role ROLE_NAME_HERE``

**Arguments**

* ``<name>``: The name of the muted role to create.

.. _mutes-command-muteset-notification:

""""""""""""""""""""
muteset notification
""""""""""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]muteset notification [channel]

**Description**

Set the notification channel for automatic unmute issues.

If no channel is provided this will be cleared and notifications
about issues when unmuting users will not be sent anywhere.

**Arguments**

* ``[channel]``: The channel to receive unmute issue updates. |channel-input|

.. _mutes-command-muteset-role:

""""""""""""
muteset role
""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]muteset role [role]

**Description**

Sets the role to be applied when muting a user.

If no role is setup the bot will attempt to mute a user
by utilizing server timeouts.

.. Note:: 
    
    If no role is setup a user may be able to leave the server
    and rejoin no longer being muted.

**Arguments**

* ``[role]``: The role for muted users to receive. |role-input|

.. _mutes-command-muteset-senddm:

""""""""""""""
muteset senddm
""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]muteset senddm <true_or_false>

**Description**

Set whether mute notifications should be sent to users in DMs.

**Arguments**

* ``<true_or_false>``: Whether to enable or disable this setting, must provide ``true`` or ``false``.

.. _mutes-command-muteset-settings:

""""""""""""""""
muteset settings
""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]muteset settings 

.. tip:: Alias: ``muteset showsettings``

**Description**

Shows the current mute settings for this guild.

.. _mutes-command-muteset-showmoderator:

"""""""""""""""""""""
muteset showmoderator
"""""""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]muteset showmoderator <true_or_false>

**Description**

Decide whether the name of the moderator muting a user should be included in the DM to that user.

**Arguments**

* ``<true_or_false>``: Whether to enable or disable this setting, must provide ``true`` or ``false``.

.. _mutes-command-unmute:

^^^^^^
unmute
^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]unmute <users...> [reason]

**Description**

Unmute users.

**Arguments**

* ``<users...>``: A space separated list of usernames, ID's, or mentions.
* ``[reason]``: The reason for the unmute.

.. _mutes-command-unmutechannel:

^^^^^^^^^^^^^
unmutechannel
^^^^^^^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]unmutechannel <users...> [reason]

.. tip:: Alias: ``channelunmute``

**Description**

Unmute a user in this channel (or in the parent of this thread).

**Arguments**

* ``<users...>``: A space separated list of usernames, ID's, or mentions.
* ``[reason]``: The reason for the unmute.

.. _mutes-command-timeout:

^^^^^^^
timeout
^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]timeout <users...> [time_and_reason]

**Description**

Timeout users.

Examples:

* ``[p]timeout @member1 @member2 spam 5 hours``
* ``[p]timeout @member1 3 days``

**Arguments**

* ``<users...>``: A space separated list of usernames, ID's, or mentions.
* ``[time_and_reason]``: The time and reason. If no time is provided, the mute will use the default set time or give an error if this hasn't been configured.

.. _mutes-command-voicemute:

^^^^^^^^^
voicemute
^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]voicemute <users...> [time_and_reason]

**Description**

Mute a user in their current voice channel.

Examples:

* ``[p]voicemute @member1 @member2 spam 5 hours``
* ``[p]voicemute @member1 3 days``

**Arguments**

* ``<users...>``: A space separated list of usernames, ID's, or mentions.
* ``[time_and_reason]``: The time and reason. If no time is provided, the mute will use the default set time or indefinite if this hasn't been configured.

.. _mutes-command-voiceunmute:

^^^^^^^^^^^
voiceunmute
^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]voiceunmute <users...> [reason]

**Description**

Unmute a user in their current voice channel.

**Arguments**

* ``<users...>``: A space separated list of usernames, ID's, or mentions.
* ``[reason]``: The reason for the unmute.