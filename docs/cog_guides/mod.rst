.. _mod:

===
Mod
===

This is the cog guide for the mod cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load mod

.. _mod-usage:

-----
Usage
-----

A range of highly customizable moderation tools used to protect your 
guild from users who cannot follow the rules.


.. _mod-commands:

--------
Commands
--------

.. _mod-command-ban:

^^^
ban
^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]ban <user> [days] [reason]

**Description**

Ban a user from this server and optionally delete days of messages.

``days`` is the amount of days of messages to cleanup on ban.

**Arguments**

* ``<user>``: The user to ban. |user-input|
* ``[days]``: The amount of days of messages to cleanup on ban. This parameter defaults to the defaultdays setting, or no days if this has not yet been configured.
* ``[reason]``: The reason why the user was banned (optional).

**Example Usage**

* ``[p]ban 428675506947227648 7 Continued to spam after told to stop.``
    This will ban the user with ID 428675506947227648 and it will delete 7 days worth of messages.
* ``[p]ban @Twentysix 7 Continued to spam after told to stop.``
    This will ban Twentysix and it will delete 7 days worth of messages.

A user ID should be provided if the user is not a member of this server.
If days is not a number, it's treated as the first word of the reason.
Minimum 0 days, maximum 7. If not specified, the defaultdays setting will be used instead.

.. _mod-command-kick:

^^^^
kick
^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]kick <member> [reason]

**Description**

Kick a user.

**Arguments**

* ``<member>``: The member to kick. |member-input|
* ``[reason]``: The reason why the user was kicked (optional).

**Example Usage**

* ``[p]kick 428675506947227648 wanted to be kicked.``
    This will kick the user with ID 428675506947227648 from the server.
* ``[p]kick @Twentysix wanted to be kicked.``
    This will kick Twentysix from the server.

If a reason is specified, it will be the reason that shows up
in the audit log.

.. _mod-command-massban:

^^^^^^^
massban
^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]massban <user_ids...> [days] [reason]

.. tip:: Alias: ``hackban``

**Description**

Mass bans user(s) from the server.

**Arguments**

* ``<user_ids...>``: The users to ban. This must be a list of user IDs separated by spaces.
* ``[days]``: The amount of days of messages to cleanup on massban.
* ``[reason]``: The reason why these users were banned.

**Example Usage**

* ``[p]massban 345628097929936898 57287406247743488 7 they broke all rules.``
    This will ban all the added userids and delete 7 days worth of their messages.

.. _mod-command-modset:

^^^^^^
modset
^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]modset 

**Description**

Manage server administration settings.

.. _mod-command-modset-defaultdays:

""""""""""""""""""
modset defaultdays
""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]modset defaultdays [days=0]

**Description**

Set the default number of days worth of messages to be deleted when a user is banned.

The number of days must be between 0 and 7.

**Arguments**

* ``[days=0]``: The default number of days of messages to be deleted when a user is banned.

.. note:: This value must be between 0 and 7.

.. _mod-command-modset-defaultduration:

""""""""""""""""""""""
modset defaultduration
""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]modset defaultduration <duration>

**Description**

Set the default time to be used when a user is tempbanned.

Accepts: seconds, minutes, hours, days, weeks

**Arguments**

* ``<duration>``: The default duration for when a user is temporarily banned. Accepts seconds, minutes, hours, days or weeks.

**Example Usage**

* ``[p]modset defaultduration 7d12h10m``
* ``[p]modset defaultduration 7 days 12 hours 10 minutes``

.. _mod-command-modset-deletenames:

""""""""""""""""""
modset deletenames
""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]modset deletenames [confirmation=False]

**Description**

Delete all stored usernames, global display names, and server nicknames.

**Arguments**

- ``<confirmation>``: Whether to delete all stored usernames, global display names, and server nicknames. |bool-input|

.. _mod-command-modset-deleterepeats:

""""""""""""""""""""
modset deleterepeats
""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]modset deleterepeats [repeats]

**Description**

Enable auto-deletion of repeated messages.

**Arguments**

* ``[repeats]``: The number of repeated messages needed before further messages are deleted.

.. note:: Must be between 2 and 20. Set to -1 to disable this feature.

.. _mod-command-modset-dm:

"""""""""
modset dm
"""""""""

**Syntax**

.. code-block:: none

    [p]modset dm [enabled]

**Description**

Toggle whether a message should be sent to a user when they are kicked/banned.

If this option is enabled, the bot will attempt to DM the user with the guild name
and reason as to why they were kicked/banned.

**Arguments**

* ``[enabled]``: Whether a message should be sent to a user when they are kicked/banned. |bool-input|

.. _mod-command-modset-requirereason:

""""""""""""""""""""
modset requirereason
""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]modset requirereason [enabled]

**Description**

Toggle whether a reason is required for mod actions.
        
If this is enabled, the bot will require a reason to be provided for all mod actions.

**Arguments**

* ``[enabled]``: Whether a reason should be required when performing mod actions. |bool-input|

.. _mod-command-modset-hierarchy:

""""""""""""""""
modset hierarchy
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]modset hierarchy 

**Description**

Toggle role hierarchy check for mods and admins.

.. warning:: Disabling this setting will allow mods to take actions on users above them in the role hierarchy!

This is enabled by default.

.. _mod-command-modset-mentionspam:

""""""""""""""""""
modset mentionspam
""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]modset mentionspam 

**Description**

Manage the automoderation settings for mentionspam.

.. _mod-command-modset-mentionspam-ban:

""""""""""""""""""""""
modset mentionspam ban
""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]modset mentionspam ban <max_mentions>

**Description**

Set the autoban conditions for mention spam.

Users will be banned if they send any message which contains more than
``<max_mentions>`` mentions.

**Arguments**

* ``<max_mentions>``: Must be 0 or greater. Set to 0 to disable this feature.

.. _mod-command-modset-mentionspam-kick:

"""""""""""""""""""""""
modset mentionspam kick
"""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]modset mentionspam kick <max_mentions>

**Description**

Set the autokick conditions for mention spam.

Users will be kicked if they send any message which contains more than
``<max_mentions>`` mentions.

**Arguments**

* ``<max_mentions>``: Must be 0 or greater. Set to 0 to disable this feature.

.. _mod-command-modset-mentionspam-strict:

"""""""""""""""""""""""""
modset mentionspam strict
"""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]modset mentionspam strict [enabled]

**Description**

Setting to account for duplicate mentions.

If enabled all mentions will count including duplicated mentions.
If disabled only unique mentions will count.

Use this command without any parameter to see the current setting.

**Arguments**

* ``[enabled]``: Whether all mentions will count, including duplicated mentions. |bool-input|

.. _mod-command-modset-mentionspam-warn:

"""""""""""""""""""""""
modset mentionspam warn
"""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]modset mentionspam warn <max_mentions>

**Description**

Sets the autowarn conditions for mention spam.

Users will be warned if they send any messages which contain more than
``<max_mentions>`` mentions.

**Arguments**

* ``<max_mentions>``: Must be 0 or greater. Set to 0 to disable this feature.

.. _mod-command-modset-reinvite:

"""""""""""""""
modset reinvite
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]modset reinvite 

**Description**

Toggle whether an invite will be sent to a user when unbanned.

If this is True, the bot will attempt to create and send a single-use invite
to the newly-unbanned user.

.. _mod-command-modset-showsettings:

"""""""""""""""""""
modset showsettings
"""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]modset showsettings 

**Description**

Show the current server administration settings.

.. _mod-command-modset-trackallnames:

""""""""""""""""""""
modset trackallnames
""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]modset trackallnames [enabled]

**Description**

Toggle whether all name changes should be tracked.

Toggling this off also overrides the tracknicknames setting.

**Arguments**

* ``[enabled]``: Whether all name changes should be tracked. |bool-input|

.. _mod-command-modset-tracknicknames:

"""""""""""""""""""""
modset tracknicknames
"""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]modset tracknicknames [enabled]

**Description**

Toggle whether server nickname changes should be tracked.

This setting will be overridden if trackallnames is disabled.

**Arguments**

* ``[enabled]``: Whether all nickname changes should be tracked. |bool-input|

.. _mod-command-movedeletedelay:

^^^^^^^^^^^^^^^
movedeletedelay
^^^^^^^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]movedeletedelay 

**Description**

Move deletedelay settings to core

.. _mod-command-moveignoredchannels:

^^^^^^^^^^^^^^^^^^^
moveignoredchannels
^^^^^^^^^^^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]moveignoredchannels 

**Description**

Move ignored channels and servers to core

.. _mod-command-names:

^^^^^
names
^^^^^

**Syntax**

.. code-block:: none

    [p]names <member>

**Description**

Show previous usernames, global display names, and server nicknames of a member.

**Arguments**

* ``<member>``: |member-input|

.. _mod-command-rename:

^^^^^^
rename
^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]rename <member> [nickname]

**Description**

Change a member's server nickname.

Leaving the nickname argument empty will remove it.

**Arguments**

* ``<member>``: |member-input|
* ``[nickname]``: The new server nickname for the member.

.. _mod-command-slowmode:

^^^^^^^^
slowmode
^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]slowmode [interval=0:00:00]

**Description**

Changes thread's or channel's slowmode setting.

Interval can be anything from 0 seconds to 6 hours.
Use without parameters to disable.

**Arguments**

* ``[interval=0:00:00]``: The time for the thread's/channel's slowmode settings.

.. note::
    Interval can be anything from 0 seconds to 6 hours.
    Use without parameters to disable.

.. _mod-command-softban:

^^^^^^^
softban
^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]softban <member> [reason]

**Description**

Kick a member and delete 1 day's worth of their messages.

**Arguments**

* ``<member>``: The member to softban. |member-input-quotes|
* ``[reason]``: Reason for the kick (optional).

.. _mod-command-tempban:

^^^^^^^
tempban
^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]tempban <member> [duration] [days] [reason]

**Description**

Temporarily ban a user from this server.

**Arguments**

* ``<member>``: The member to temporarily ban. |member-input-quotes|
* ``[duration]``: The amount of time the user should be banned for.
* ``[days]``: The amount of days of messages to cleanup on tempban.
* ``[reason]``: The reason for the tempban (optional).

**Example Usage**

* ``[p]tempban @Twentysix Because I say so``
    This will ban Twentysix for the default amount of time set by an administrator.
* ``[p]tempban @Twentysix 15m You need a timeout``
    This will ban Twentysix for 15 minutes.
* ``[p]tempban 428675506947227648 1d2h15m 5 Evil person``
    This will ban the user with ID 428675506947227648 for 1 day 2 hours 15 minutes and will delete the last 5 days of their messages.

.. _mod-command-unban:

^^^^^
unban
^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]unban <user_id> [reason]

**Description**

Unban a user from this server.

**Arguments**

* ``<user_id>``: |user-input|
* ``[reason]``: The reason for the unban (optional).

.. _mod-command-userinfo:

^^^^^^^^
userinfo
^^^^^^^^

**Syntax**

.. code-block:: none

    [p]userinfo [member]

**Description**

Show information about a user.

This includes fields for status, discord join date, server
join date, voice state and previous usernames/global display names/nicknames.

If the user has no roles, previous usernames, global display names, or server nicknames,
these fields will be omitted.

**Arguments**

* ``[member]``: |member-input|

.. _mod-command-voiceban:

^^^^^^^^
voiceban
^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]voiceban <member> [reason]

**Description**

Ban a user from speaking and listening in the server's voice channels.

**Arguments**

* ``<member>``: The member to ban from voice. |member-input|
* ``[reason]``: The reason for the voiceban (optional).

.. _mod-command-voicekick:

^^^^^^^^^
voicekick
^^^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]voicekick <member> [reason]

**Description**

Kick a member from a voice channel.

**Arguments**

* ``<member>``: |member-input|
* ``[reason]``: The reason for the voicekick (optional).

.. _mod-command-voiceunban:

^^^^^^^^^^
voiceunban
^^^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]voiceunban <member> [reason]

**Description**

Unban a user from speaking and listening in the server's voice channels.

**Arguments**

* ``<member>``: The member to unban from voice. |member-input-quotes|
* ``[reason]``: The reason for the voiceunban (optional).
