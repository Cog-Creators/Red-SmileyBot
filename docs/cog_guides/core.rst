.. _core:

====
Core
====

This is the cog guide for the core cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. _core-usage:

-----
Usage
-----

The Core cog has many commands related to core functions.

These commands come loaded with every Red bot, and cover some of the most basic usage of the bot.


.. _core-commands:

--------
Commands
--------

.. _core-command-allowlist:

^^^^^^^^^
allowlist
^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]allowlist 

.. tip:: Alias: ``whitelist``

**Description**

Commands to manage the allowlist.

.. Warning:: When the allowlist is in use, the bot will ignore commands from everyone not on the list.


Use ``[p]allowlist clear`` to disable the allowlist

.. _core-command-allowlist-add:

"""""""""""""
allowlist add
"""""""""""""

**Syntax**

.. code-block:: none

    [p]allowlist add <users...>

**Description**

Adds users to the allowlist.

**Examples:**
    - ``[p]allowlist add @26 @Will`` - Adds two users to the allowlist.
    - ``[p]allowlist add 262626262626262626`` - Adds a user by ID.

**Arguments:**
    - ``<users...>`` - The user or users to add to the allowlist.

.. _core-command-allowlist-clear:

"""""""""""""""
allowlist clear
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]allowlist clear 

**Description**

Clears the allowlist.

This disables the allowlist.

**Example:**
    - ``[p]allowlist clear``

.. _core-command-allowlist-list:

""""""""""""""
allowlist list
""""""""""""""

**Syntax**

.. code-block:: none

    [p]allowlist list 

**Description**

Lists users on the allowlist.

**Example:**
    - ``[p]allowlist list``

.. _core-command-allowlist-remove:

""""""""""""""""
allowlist remove
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]allowlist remove <users...>

**Description**

Removes users from the allowlist.

The allowlist will be disabled if all users are removed.

**Examples:**
    - ``[p]allowlist remove @26 @Will`` - Removes two users from the allowlist.
    - ``[p]allowlist remove 262626262626262626`` - Removes a user by ID.

**Arguments:**
    - ``<users...>`` - The user or users to remove from the allowlist.

.. _core-command-autoimmune:

^^^^^^^^^^
autoimmune
^^^^^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]autoimmune 

**Description**

Commands to manage server settings for immunity from automated actions.

This includes duplicate message deletion and mention spam from the Mod cog, and filters from the Filter cog.

.. _core-command-autoimmune-add:

""""""""""""""
autoimmune add
""""""""""""""

**Syntax**

.. code-block:: none

    [p]autoimmune add <user_or_role>

**Description**

Makes a user or role immune from automated moderation actions.

**Examples:**
    - ``[p]autoimmune add @Twentysix`` - Adds a user.
    - ``[p]autoimmune add @Mods`` - Adds a role.

**Arguments:**
    - ``<user_or_role>`` - The user or role to add immunity to.

.. _core-command-autoimmune-isimmune:

"""""""""""""""""""
autoimmune isimmune
"""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]autoimmune isimmune <user_or_role>

**Description**

Checks if a user or role would be considered immune from automated actions.

**Examples:**
    - ``[p]autoimmune isimmune @Twentysix``
    - ``[p]autoimmune isimmune @Mods``

**Arguments:**
    - ``<user_or_role>`` - The user or role to check the immunity of.

.. _core-command-autoimmune-list:

"""""""""""""""
autoimmune list
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]autoimmune list 

**Description**

Gets the current members and roles configured for automatic moderation action immunity.

**Example:**
    - ``[p]autoimmune list``

.. _core-command-autoimmune-remove:

"""""""""""""""""
autoimmune remove
"""""""""""""""""

**Syntax**

.. code-block:: none

    [p]autoimmune remove <user_or_role>

**Description**

Remove a user or role from being immune to automated moderation actions.

**Examples:**
    - ``[p]autoimmune remove @Twentysix`` - Removes a user.
    - ``[p]autoimmune remove @Mods`` - Removes a role.

**Arguments:**
    - ``<user_or_role>`` - The user or role to remove immunity from.

.. _core-command-bankset:

^^^^^^^
bankset
^^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]bankset

**Description**

Base command for configuring bank settings.

.. _core-command-bankset-bankname:

""""""""""""""""
bankset bankname
""""""""""""""""

.. note:: |owner-lock| However, if the bank is server-wide, the
    server owner or an administrator can use this command.

**Syntax**

.. code-block:: none

    [p]bankset bankname <name>

**Description**

Set bank's name.

**Arguments**

* ``<name>``: The new bank's name.

.. _core-command-bankset-creditsname:

"""""""""""""""""""
bankset creditsname
"""""""""""""""""""

.. note:: |owner-lock| However, if the bank is server-wide, the
    server owner or an administrator can use this command.

**Syntax**

.. code-block:: none

    [p]bankset creditsname <name>

**Description**

Change the credits name of the bank. It is ``credits`` by default.

For example, if you switch it to ``dollars``, the payday
command will show this:

.. TODO reference the payday command

.. code-block:: none

    Here, take some dollars. Enjoy! (+120 dollars!)

    You currently have 220 dollars.

**Arguments**

* ``<name>``: The new credits name.

.. _core-command-bankset-maxbal:

""""""""""""""
bankset maxbal
""""""""""""""

.. note:: |owner-lock| However, if the bank is server-wide, the
    server owner or an administrator can use this command.

**Syntax**

.. code-block:: none

    [p]bankset maxbal <amount>

**Description**

Defines the maximum amount of money a user can have with the bot.

If a user reaches this limit, they will be unable to gain more money.

**Arguments**

*   ``<amount>``: The maximum amount of money for users.

.. _core-command-bankset-prune:

"""""""""""""
bankset prune
"""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]bankset prune 

**Description**

Base command for pruning bank accounts.

.. _core-command-bankset-prune-global:

""""""""""""""""""""
bankset prune global
""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]bankset prune global [confirmation=False]

**Description**

Prune bank accounts for users who no longer share a server with the bot.

Cannot be used without a global bank. See ``[p]bankset prune server``.

Examples:
    - ``[p]bankset prune global`` - Did not confirm. Shows the help message.
    - ``[p]bankset prune global yes``

**Arguments**

- ``<confirmation>`` This will default to false unless specified.

.. _core-command-bankset-prune-server:

""""""""""""""""""""
bankset prune server
""""""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]bankset prune server [confirmation=False]

.. tip:: Aliases: ``bankset prune guild``, ``bankset prune local``

**Description**

Prune bank accounts for users no longer in the server.

Cannot be used with a global bank. See ``[p]bankset prune global``.

Examples:
    - ``[p]bankset prune server`` - Did not confirm. Shows the help message.
    - ``[p]bankset prune server yes``

**Arguments**

- ``<confirmation>`` This will default to false unless specified.

.. _core-command-bankset-prune-user:

""""""""""""""""""
bankset prune user
""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]bankset prune user <user> [confirmation=False]

**Description**

Delete the bank account of a specified user.

Examples:
    - ``[p]bankset prune user @Twentysix`` - Did not confirm. Shows the help message.
    - ``[p]bankset prune user @Twentysix yes``

**Arguments**

- ``<user>`` The user to delete the bank of. Takes mentions, names, and user ids.
- ``<confirmation>`` This will default to false unless specified.

.. _core-command-bankset-registeramount:

""""""""""""""""""""""
bankset registeramount
""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]bankset registeramount <creds>

**Description**

Set the initial balance for new bank accounts.

Example:
    - ``[p]bankset registeramount 5000``

**Arguments**

- ``<creds>`` The new initial balance amount. Default is 0.

.. _core-command-bankset-reset:

"""""""""""""
bankset reset
"""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]bankset reset [confirmation=False]

**Description**

Delete all bank accounts.

Examples:
    - ``[p]bankset reset`` - Did not confirm. Shows the help message.
    - ``[p]bankset reset yes``

**Arguments**

- ``<confirmation>`` This will default to false unless specified.

.. _core-command-bankset-showsettings:

""""""""""""""""""""
bankset showsettings
""""""""""""""""""""

.. note:: |owner-lock| However, if the bank is server-wide, the
    server owner or an administrator can use this command.

**Syntax**

.. code-block:: none

    [p]bankset showsettings

**Description**

Shows the current settings of your bank.

This will display the following information:

*   Name of the bank
*   Scope of the bank (global or per server)
*   Currency name
*   Default balance
*   Maximum allowed balance

.. _core-command-bankset-toggleglobal:

""""""""""""""""""""
bankset toggleglobal
""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]bankset toggleglobal [confirm=False]

**Description**

Makes the bank global instead of server-wide. If it
is already global, the command will switch it back
to the server-wide bank.

.. warning:: Using this command will reset **all** accounts.

**Arguments**

* ``[confirm=False]``: Put ``yes`` to confirm.

.. _core-command-blocklist:

^^^^^^^^^
blocklist
^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]blocklist 

.. tip:: Aliases: ``blacklist``, ``denylist``

**Description**

Commands to manage the blocklist.

Use ``[p]blocklist clear`` to disable the blocklist

.. _core-command-blocklist-add:

"""""""""""""
blocklist add
"""""""""""""

**Syntax**

.. code-block:: none

    [p]blocklist add <users...>

**Description**

Adds users to the blocklist.

**Examples:**
    - ``[p]blocklist add @26 @Will`` - Adds two users to the blocklist.
    - ``[p]blocklist add 262626262626262626`` - Blocks a user by ID.

**Arguments:**
    - ``<users...>`` - The user or users to add to the blocklist.

.. _core-command-blocklist-clear:

"""""""""""""""
blocklist clear
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]blocklist clear 

**Description**

Clears the blocklist.

**Example:**
    - ``[p]blocklist clear``

.. _core-command-blocklist-list:

""""""""""""""
blocklist list
""""""""""""""

**Syntax**

.. code-block:: none

    [p]blocklist list 

**Description**

Lists users on the blocklist.

**Example:**
    - ``[p]blocklist list``

.. _core-command-blocklist-remove:

""""""""""""""""
blocklist remove
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]blocklist remove <users...>

**Description**

Removes users from the blocklist.

**Examples:**
    - ``[p]blocklist remove @26 @Will`` - Removes two users from the blocklist.
    - ``[p]blocklist remove 262626262626262626`` - Removes a user by ID.

**Arguments:**
    - ``<users...>`` - The user or users to remove from the blocklist.

.. _core-command-command:

^^^^^^^
command
^^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]command 

**Description**

Commands to enable and disable commands and cogs.

.. _core-command-command-defaultdisablecog:

"""""""""""""""""""""""""
command defaultdisablecog
"""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]command defaultdisablecog <cog>

**Description**

Set the default state for a cog as disabled.

This will disable the cog for all servers by default.
To override it, use ``[p]command enablecog`` on the servers you want to allow usage.

.. Note:: This will only work on loaded cogs, and must reference the title-case cog name.


**Examples:**
    - ``[p]command defaultdisablecog Economy``
    - ``[p]command defaultdisablecog ModLog``

**Arguments:**
    - ``<cog>`` - The name of the cog to make disabled by default. Must be title-case.

.. _core-command-command-defaultenablecog:

""""""""""""""""""""""""
command defaultenablecog
""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]command defaultenablecog <cog>

**Description**

Set the default state for a cog as enabled.

This will re-enable the cog for all servers by default.
To override it, use ``[p]command disablecog`` on the servers you want to disallow usage.

.. Note:: This will only work on loaded cogs, and must reference the title-case cog name.


**Examples:**
    - ``[p]command defaultenablecog Economy``
    - ``[p]command defaultenablecog ModLog``

**Arguments:**
    - ``<cog>`` - The name of the cog to make enabled by default. Must be title-case.

.. _core-command-command-disable:

"""""""""""""""
command disable
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]command disable <command>

**Description**

Disable a command.

If you're the bot owner, this will disable commands globally by default.
Otherwise, this will disable commands on the current server.

**Examples:**
    - ``[p]command disable userinfo`` - Disables the ``userinfo`` command in the Mod cog.
    - ``[p]command disable urban`` - Disables the ``urban`` command in the General cog.

**Arguments:**
    - ``<command>`` - The command to disable.

.. _core-command-command-disable-global:

""""""""""""""""""""""
command disable global
""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]command disable global <command>

**Description**

Disable a command globally.

**Examples:**
    - ``[p]command disable global userinfo`` - Disables the ``userinfo`` command in the Mod cog.
    - ``[p]command disable global urban`` - Disables the ``urban`` command in the General cog.

**Arguments:**
    - ``<command>`` - The command to disable globally.

.. _core-command-command-disable-server:

""""""""""""""""""""""
command disable server
""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]command disable server <command>

.. tip:: Alias: ``command disable guild``

**Description**

Disable a command in this server only.

        **Examples:**
            - ``[p]command disable server userinfo`` - Disables the ``userinfo`` command in the Mod cog.
            - ``[p]command disable server urban`` - Disables the ``urban`` command in the General cog.

        **Arguments:**
            - ``<command>`` - The command to disable for the current server.

.. _core-command-command-disablecog:

""""""""""""""""""
command disablecog
""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]command disablecog <cog>

**Description**

Disable a cog in this server.

.. Note:: This will only work on loaded cogs, and must reference the title-case cog name.


**Examples:**
    - ``[p]command disablecog Economy``
    - ``[p]command disablecog ModLog``

**Arguments:**
    - ``<cog>`` - The name of the cog to disable on this server. Must be title-case.

.. _core-command-command-disabledmsg:

"""""""""""""""""""
command disabledmsg
"""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]command disabledmsg [message]

**Description**

Set the bot's response to disabled commands.

Leave blank to send nothing.

To include the command name in the message, include the ``{command}`` placeholder.

**Examples:**
    - ``[p]command disabledmsg This command is disabled``
    - ``[p]command disabledmsg {command} is disabled``
    - ``[p]command disabledmsg`` - Sends nothing when a disabled command is attempted.

**Arguments:**
    - ``[message]`` - The message to send when a disabled command is attempted.

.. _core-command-command-enable:

""""""""""""""
command enable
""""""""""""""

**Syntax**

.. code-block:: none

    [p]command enable <command>

**Description**

Enable a command.

If you're the bot owner, this will try to enable a globally disabled command by default.
Otherwise, this will try to enable a command disabled on the current server.

**Examples:**
    - ``[p]command enable userinfo`` - Enables the ``userinfo`` command in the Mod cog.
    - ``[p]command enable urban`` - Enables the ``urban`` command in the General cog.

**Arguments:**
    - ``<command>`` - The command to enable.

.. _core-command-command-enable-global:

"""""""""""""""""""""
command enable global
"""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]command enable global <command>

**Description**

        Enable a command globally.

**Examples:**
    - ``[p]command enable global userinfo`` - Enables the ``userinfo`` command in the Mod cog.
    - ``[p]command enable global urban`` - Enables the ``urban`` command in the General cog.

**Arguments:**
    - ``<command>`` - The command to enable globally.

.. _core-command-command-enable-server:

"""""""""""""""""""""
command enable server
"""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]command enable server <command>

.. tip:: Alias: ``command enable guild``

**Description**

    Enable a command in this server.

**Examples:**
    - ``[p]command enable server userinfo`` - Enables the ``userinfo`` command in the Mod cog.
    - ``[p]command enable server urban`` - Enables the ``urban`` command in the General cog.

**Arguments:**
    - ``<command>`` - The command to enable for the current server.

.. _core-command-command-enablecog:

"""""""""""""""""
command enablecog
"""""""""""""""""

**Syntax**

.. code-block:: none

    [p]command enablecog <cog>

**Description**

Enable a cog in this server.

.. Note:: This will only work on loaded cogs, and must reference the title-case cog name.


**Examples:**
    - ``[p]command enablecog Economy``
    - ``[p]command enablecog ModLog``

**Arguments:**
    - ``<cog>`` - The name of the cog to enable on this server. Must be title-case.

.. _core-command-command-listdisabled:

""""""""""""""""""""
command listdisabled
""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]command listdisabled 

**Description**

List disabled commands.

If you're the bot owner, this will show global disabled commands by default.
Otherwise, this will show disabled commands on the current server.

**Example:**
    - ``[p]command listdisabled``

.. _core-command-command-listdisabled-global:

"""""""""""""""""""""""""""
command listdisabled global
"""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]command listdisabled global 

**Description**

List disabled commands globally.

**Example:**
    - ``[p]command listdisabled global``

.. _core-command-command-listdisabled-guild:

""""""""""""""""""""""""""
command listdisabled guild
""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]command listdisabled guild 

**Description**

List disabled commands in this server.

**Example:**
    - ``[p]command listdisabled guild``

.. _core-command-command-listdisabledcogs:

""""""""""""""""""""""""
command listdisabledcogs
""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]command listdisabledcogs 

**Description**

List the cogs which are disabled in this server.

**Example:**
    - ``[p]command listdisabledcogs``

.. _core-command-contact:

^^^^^^^
contact
^^^^^^^

**Syntax**

.. code-block:: none

    [p]contact <message>

**Description**

Sends a message to the owner.

This is limited to one message every 60 seconds per person.

**Example:**
    - ``[p]contact Help! The bot has become sentient!``

**Arguments:**
    - ``[message]`` - The message to send to the owner.

.. _core-command-diagnoseissues:

^^^^^^^^^^^^^^
diagnoseissues
^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]diagnoseissues [channel] <member> <command_name>

**Description**

Diagnose issues with the command checks with ease!

If you want to diagnose the command from a text channel in a different server,
you can do so by using the command in DMs.

**Example:**
    - ``[p]diagnoseissues #general @Slime ban`` - Diagnose why @Slime can't use ``[p]ban`` in #general channel.

**Arguments:**
    - ``[channel]`` - The text channel that the command should be tested for. Defaults to the current channel.
    - ``<member>`` - The member that should be considered as the command caller.
    - ``<command_name>`` - The name of the command to test.

.. _core-command-dm:

^^
dm
^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]dm <user_id> <message>

**Description**

Sends a DM to a user.

This command needs a user ID to work.

To get a user ID, go to Discord's settings and open the 'Appearance' tab.
Enable 'Developer Mode', then right click a user and click on 'Copy ID'.

**Example:**
    - ``[p]dm 262626262626262626 Do you like me? Yes / No``

**Arguments:**
    - ``[message]`` - The message to dm to the user.

.. _core-command-embedset:

^^^^^^^^
embedset
^^^^^^^^

**Syntax**

.. code-block:: none

    [p]embedset 

**Description**

Commands for toggling embeds on or off.

This setting determines whether or not to use embeds as a response to a command (for commands that support it).
The default is to use embeds.

The embed settings are checked until the first True/False in this order:
    - In guild context:
        1. Channel override - ``[p]embedset channel``
        2. Server command override - ``[p]embedset command server``
        3. Server override - ``[p]embedset server``
        4. Global command override - ``[p]embedset command global``
        5. Global setting  -``[p]embedset global``

    - In DM context:
        1. User override - ``[p]embedset user``
        2. Global command override - ``[p]embedset command global``
        3. Global setting - ``[p]embedset global``

.. _core-command-embedset-channel:

""""""""""""""""
embedset channel
""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]embedset channel <channel> [enabled]

**Description**

Set's a channel's embed setting.

If set, this is used instead of the guild and command defaults to determine whether or not to use embeds.
This is used for all commands done in a channel.

If enabled is left blank, the setting will be unset and the guild default will be used instead.

To see full evaluation order of embed settings, run ``[p]help embedset``.

**Examples:**
    - ``[p]embedset channel #text-channel False`` - Disables embeds in the #text-channel.
    - ``[p]embedset channel #forum-channel disable`` - Disables embeds in the #forum-channel.
    - ``[p]embedset channel #text-channel`` - Resets value to use guild default in the #text-channel.

**Arguments:**
    - ``<channel>`` - The text, voice, stage, or forum channel to set embed setting for.
    - ``[enabled]`` - Whether to use embeds in this channel. Leave blank to reset to default.

.. _core-command-embedset-command:

""""""""""""""""
embedset command
""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]embedset command <command> [enabled]

**Description**

Sets a command's embed setting.

If you're the bot owner, this will try to change the command's embed setting globally by default.
Otherwise, this will try to change embed settings on the current server.

If enabled is left blank, the setting will be unset.

To see full evaluation order of embed settings, run ``[p]help embedset``.

**Examples:**
    - ``[p]embedset command info`` - Clears command specific embed settings for 'info'.
    - ``[p]embedset command info False`` - Disables embeds for 'info'.
    - ``[p]embedset command "ignore list" True`` - Quotes are needed for subcommands.

**Arguments:**
    - ``[enabled]`` - Whether to use embeds for this command. Leave blank to reset to default.

.. _core-command-embedset-command-global:

"""""""""""""""""""""""
embedset command global
"""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]embedset command global <command> [enabled]

**Description**

Sets a command's embed setting globally.

If set, this is used instead of the global default to determine whether or not to use embeds.

If enabled is left blank, the setting will be unset.

To see full evaluation order of embed settings, run ``[p]help embedset``.

**Examples:**
    - ``[p]embedset command global info`` - Clears command specific embed settings for 'info'.
    - ``[p]embedset command global info False`` - Disables embeds for 'info'.
    - ``[p]embedset command global "ignore list" True`` - Quotes are needed for subcommands.

**Arguments:**
    - ``[enabled]`` - Whether to use embeds for this command. Leave blank to reset to default.

.. _core-command-embedset-command-server:

"""""""""""""""""""""""
embedset command server
"""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]embedset command server <command> [enabled]

.. tip:: Alias: ``embedset command guild``

**Description**

Sets a command's embed setting for the current server.

If set, this is used instead of the server default to determine whether or not to use embeds.

If enabled is left blank, the setting will be unset and the server default will be used instead.

To see full evaluation order of embed settings, run ``[p]help embedset``.

**Examples:**
    - ``[p]embedset command server info`` - Clears command specific embed settings for 'info'.
    - ``[p]embedset command server info False`` - Disables embeds for 'info'.
    - ``[p]embedset command server "ignore list" True`` - Quotes are needed for subcommands.

**Arguments:**
    - ``[enabled]`` - Whether to use embeds for this command. Leave blank to reset to default.

.. _core-command-embedset-global:

"""""""""""""""
embedset global
"""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]embedset global 

**Description**

Toggle the global embed setting.

This is used as a fallback if the user or guild hasn't set a preference.
The default is to use embeds.

To see full evaluation order of embed settings, run ``[p]help embedset``.

**Example:**
    - ``[p]embedset global``

.. _core-command-embedset-server:

"""""""""""""""
embedset server
"""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]embedset server [enabled]

.. tip:: Alias: ``embedset guild``

**Description**

Set the server's embed setting.

If set, this is used instead of the global default to determine whether or not to use embeds.
This is used for all commands done in a server.

If enabled is left blank, the setting will be unset and the global default will be used instead.

To see full evaluation order of embed settings, run ``[p]help embedset``.

**Examples:**
    - ``[p]embedset server False`` - Disables embeds on this server.
    - ``[p]embedset server`` - Resets value to use global default.

**Arguments:**
    - ``[enabled]`` - Whether to use embeds on this server. Leave blank to reset to default.

.. _core-command-embedset-showsettings:

"""""""""""""""""""""
embedset showsettings
"""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]embedset showsettings [command]

**Description**

Show the current embed settings.

Provide a command name to check for command specific embed settings.

**Examples:**
    - ``[p]embedset showsettings`` - Shows embed settings.
    - ``[p]embedset showsettings info`` - Also shows embed settings for the 'info' command.
    - ``[p]embedset showsettings "ignore list"`` - Checking subcommands requires quotes.

**Arguments:**
    - ``[command]`` - Checks this command for command specific embed settings.

.. _core-command-embedset-user:

"""""""""""""
embedset user
"""""""""""""

**Syntax**

.. code-block:: none

    [p]embedset user [enabled]

**Description**

Sets personal embed setting for DMs.

If set, this is used instead of the global default to determine whether or not to use embeds.
This is used for all commands executed in a DM with the bot.

If enabled is left blank, the setting will be unset and the global default will be used instead.

To see full evaluation order of embed settings, run ``[p]help embedset``.

**Examples:**
    - ``[p]embedset user False`` - Disables embeds in your DMs.
    - ``[p]embedset user`` - Resets value to use global default.

**Arguments:**
    - ``[enabled]`` - Whether to use embeds in your DMs. Leave blank to reset to default.

.. _core-command-helpset:

^^^^^^^
helpset
^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]helpset 

**Description**

Commands to manage settings for the help command.

All help settings are applied globally.

.. _core-command-helpset-deletedelay:

"""""""""""""""""""
helpset deletedelay
"""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset deletedelay <seconds>

**Description**

Set the delay after which help pages will be deleted.

The setting is disabled by default, and only applies to non-menu help,
sent in server text channels.
Setting the delay to 0 disables this feature.

The bot has to have MANAGE_MESSAGES permission for this to work.

**Examples:**
    - ``[p]helpset deletedelay 60`` - Delete the help pages after a minute.
    - ``[p]helpset deletedelay 1`` - Delete the help pages as quickly as possible.
    - ``[p]helpset deletedelay 1209600`` - Max time to wait before deleting (14 days).
    - ``[p]helpset deletedelay 0`` - Disable deleting help pages.

**Arguments:**
    - ``<seconds>`` - The seconds to wait before deleting help pages.

.. _core-command-helpset-maxpages:

""""""""""""""""
helpset maxpages
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset maxpages <pages>

**Description**

Set the maximum number of help pages sent in a server channel.

If a help message contains more pages than this value, the help message will
be sent to the command author via DM. This is to help reduce spam in server
text channels.

The default value is 2 pages.

**Examples:**
    - ``[p]helpset maxpages 50`` - Basically never send help to DMs.
    - ``[p]helpset maxpages 0`` - Always send help to DMs.

**Arguments:**
    - ``<limit>`` - The max pages allowed to send per help in a server.

.. _core-command-helpset-pagecharlimit:

"""""""""""""""""""""
helpset pagecharlimit
"""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset pagecharlimit <limit>

**Description**

Set the character limit for each page in the help message.

.. Note:: This setting only applies to embedded help.


The default value is 1000 characters. The minimum value is 500.
The maximum is based on the lower of what you provide and what discord allows.

Please note that setting a relatively small character limit may
mean some pages will exceed this limit.

**Example:**
    - ``[p]helpset pagecharlimit 1500``

**Arguments:**
    - ``<limit>`` - The max amount of characters to show per page in the help message.

.. _core-command-helpset-reacttimeout:

""""""""""""""""""""
helpset reacttimeout
""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset reacttimeout <seconds>

**Description**

Set the timeout for reactions, if menus are enabled.

The default is 30 seconds.
The timeout has to be between 15 and 300 seconds.

**Examples:**
    - ``[p]helpset reacttimeout 30`` - The default timeout.
    - ``[p]helpset reacttimeout 60`` - Timeout of 1 minute.
    - ``[p]helpset reacttimeout 15`` - Minimum allowed timeout.
    - ``[p]helpset reacttimeout 300`` - Max allowed timeout (5 mins).

**Arguments:**
    - ``<seconds>`` - The timeout, in seconds, of the reactions.

.. _core-command-helpset-resetformatter:

""""""""""""""""""""""
helpset resetformatter
""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset resetformatter 

**Description**

This resets Red's help formatter to the default formatter.

**Example:**
    - ``[p]helpset resetformatter``

.. _core-command-helpset-resetsettings:

"""""""""""""""""""""
helpset resetsettings
"""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset resetsettings 

**Description**

This resets Red's help settings to their defaults.

This may not have an impact when using custom formatters from 3rd party cogs

**Example:**
    - ``[p]helpset resetsettings``

.. _core-command-helpset-showaliases:

"""""""""""""""""""
helpset showaliases
"""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset showaliases [show_aliases]

**Description**

This allows the help command to show existing commands aliases if there is any.

This defaults to True.
Using this without a setting will toggle.

**Examples:**
    - ``[p]helpset showaliases False`` - Disables showing aliases on this server.
    - ``[p]helpset showaliases`` - Toggles the value.

**Arguments:**
    - ``[show_aliases]`` - Whether to include aliases in help. Leave blank to toggle.

.. _core-command-helpset-showhidden:

""""""""""""""""""
helpset showhidden
""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset showhidden [show_hidden]

**Description**

This allows the help command to show hidden commands.

This defaults to False.
Using this without a setting will toggle.

**Examples:**
    - ``[p]helpset showhidden True`` - Enables showing hidden commands.
    - ``[p]helpset showhidden`` - Toggles the value.

**Arguments:**
    - ``[show_hidden]`` - Whether to use show hidden commands in help. Leave blank to toggle.

.. _core-command-helpset-showsettings:

""""""""""""""""""""
helpset showsettings
""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset showsettings 

**Description**

Show the current help settings.

.. Warning:: These settings may not be accurate if the default formatter is not in use.


**Example:**
    - ``[p]helpset showsettings``

.. _core-command-helpset-tagline:

"""""""""""""""
helpset tagline
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset tagline [tagline]

**Description**

Set the tagline to be used.

The maximum tagline length is 2048 characters.
This setting only applies to embedded help. If no tagline is specified, the default will be used instead.

You can use ``[p]`` in your tagline, which will be replaced by the bot's prefix.

**Examples:**
    - ``[p]helpset tagline Thanks for using the bot!``
    - ``[p]helpset tagline Use [p]invite to add me to your server.``
    - ``[p]helpset tagline`` - Resets the tagline to the default.

**Arguments:**
    - ``[tagline]`` - The tagline to appear at the bottom of help embeds. Leave blank to reset.

.. _core-command-helpset-usemenus:

""""""""""""""""
helpset usemenus
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset usemenus <"buttons"|"reactions"|"select"|"selectonly"|"disable">

**Description**

Allows the help command to be sent as a paginated menu instead of separate
messages.

When "reactions", "buttons", "select", or "selectonly" is passed, ``[p]help`` will
only show one page at a time and will use the associated control scheme to navigate between pages.

**Examples:**
    - ``[p]helpset usemenus reactions`` - Enables using reaction menus.
    - ``[p]helpset usemenus buttons`` - Enables using button menus.
    - ``[p]helpset usemenus select`` - Enables buttons with a select menu.
    - ``[p]helpset usemenus selectonly`` - Enables a select menu only on help.
    - ``[p]helpset usemenus disable`` - Disables help menus.

**Arguments:**
    - ``<"buttons"|"reactions"|"select"|"selectonly"|"disable">`` - Whether to use ``buttons``,
      ``reactions``, ``select``, ``selectonly``, or no menus.

.. _core-command-helpset-usetick:

"""""""""""""""
helpset usetick
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset usetick [use_tick]

**Description**

This allows the help command message to be ticked if help is sent to a DM.

Ticking is reacting to the help message with a ✅.

Defaults to False.
Using this without a setting will toggle.

.. Note:: This is only used when the bot is not using menus.


**Examples:**
    - ``[p]helpset usetick False`` - Disables ticking when help is sent to DMs.
    - ``[p]helpset usetick`` - Toggles the value.

**Arguments:**
    - ``[use_tick]`` - Whether to tick the help command when help is sent to DMs. Leave blank to toggle.

.. _core-command-helpset-verifychecks:

""""""""""""""""""""
helpset verifychecks
""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset verifychecks [verify]

**Description**

Sets if commands which can't be run in the current context should be filtered from help.

Defaults to True.
Using this without a setting will toggle.

**Examples:**
    - ``[p]helpset verifychecks False`` - Enables showing unusable commands in help.
    - ``[p]helpset verifychecks`` - Toggles the value.

**Arguments:**
    - ``[verify]`` - Whether to hide unusable commands in help. Leave blank to toggle.

.. _core-command-helpset-verifyexists:

""""""""""""""""""""
helpset verifyexists
""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]helpset verifyexists [verify]

**Description**

Sets whether the bot should respond to help commands for nonexistent topics.

When enabled, this will indicate the existence of help topics, even if the user can't use it.

.. Note:: This setting on its own does not fully prevent command enumeration.


Defaults to False.
Using this without a setting will toggle.

**Examples:**
    - ``[p]helpset verifyexists True`` - Enables sending help for nonexistent topics.
    - ``[p]helpset verifyexists`` - Toggles the value.

**Arguments:**
    - ``[verify]`` - Whether to respond to help for nonexistent topics. Leave blank to toggle.

.. _core-command-ignore:

^^^^^^
ignore
^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]ignore 

**Description**

Commands to add servers or channels to the ignore list.

The ignore list will prevent the bot from responding to commands in the configured locations.

.. Note:: Owners and Admins override the ignore list.


.. _core-command-ignore-channel:

""""""""""""""
ignore channel
""""""""""""""

**Syntax**

.. code-block:: none

    [p]ignore channel [channel]

**Description**

Ignore commands in the channel, thread, or category.

Defaults to the current thread or channel.

.. Note:: Owners, Admins, and those with Manage Channel permissions override ignored channels.


**Examples:**
    - ``[p]ignore channel #general`` - Ignores commands in the #general channel.
    - ``[p]ignore channel`` - Ignores commands in the current channel.
    - ``[p]ignore channel "General Channels"`` - Use quotes for categories with spaces.
    - ``[p]ignore channel 356236713347252226`` - Also accepts IDs.

**Arguments:**
    - ``<channel>`` - The channel to ignore. This can also be a thread or category channel.

.. _core-command-ignore-list:

"""""""""""
ignore list
"""""""""""

**Syntax**

.. code-block:: none

    [p]ignore list 

**Description**

List the currently ignored servers and channels.

**Example:**
    - ``[p]ignore list``

.. _core-command-ignore-server:

"""""""""""""
ignore server
"""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]ignore server 

.. tip:: Alias: ``ignore guild``

**Description**

Ignore commands in this server.

.. Note:: Owners, Admins, and those with Manage Server permissions override ignored servers.


**Example:**
    - ``[p]ignore server`` - Ignores the current server

.. _core-command-info:

^^^^
info
^^^^

**Syntax**

.. code-block:: none

    [p]info 

**Description**

Shows info about Red.

.. _core-command-invite:

^^^^^^
invite
^^^^^^

**Syntax**

.. code-block:: none

    [p]invite 

**Description**

Shows Red's invite url.

This will always send the invite to DMs to keep it private.

This command is locked to the owner unless ``[p]inviteset public`` is set to True.

**Example:**
    - ``[p]invite``

.. _core-command-inviteset:

^^^^^^^^^
inviteset
^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]inviteset 

**Description**

Commands to setup Red's invite settings.

.. _core-command-inviteset-perms:

"""""""""""""""
inviteset perms
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]inviteset perms <level>

**Description**

Make the bot create its own role with permissions on join.

The bot will create its own role with the desired permissions when it joins a new server. This is a special role that can't be deleted or removed from the bot.

For that, you need to provide a valid permissions level.
You can generate one here: https://discordapi.com/permissions.html

Please note that you might need two factor authentication for some permissions.

**Example:**
    - ``[p]inviteset perms 134217728`` - Adds a "Manage Nicknames" permission requirement to the invite.

**Arguments:**
    - ``<level>`` - The permission level to require for the bot in the generated invite.

.. _core-command-inviteset-public:

""""""""""""""""
inviteset public
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]inviteset public [confirm=False]

**Description**

Toggles if ``[p]invite`` should be accessible for the average user.

The bot must be made into a ``Public bot`` in the developer dashboard for public invites to work.

**Example:**
    - ``[p]inviteset public yes`` - Toggles the public invite setting.

**Arguments:**
    - ``[confirm]`` - Required to set to public. Not required to toggle back to private.

.. _core-command-leave:

^^^^^
leave
^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]leave [servers...]

**Description**

Leaves servers.

If no server IDs are passed the local server will be left instead.

.. Note:: This command is interactive.


**Examples:**
    - ``[p]leave`` - Leave the current server.
    - ``[p]leave "Red - Discord Bot"`` - Quotes are necessary when there are spaces in the name.
    - ``[p]leave 133049272517001216 240154543684321280`` - Leaves multiple servers, using IDs.

**Arguments:**
    - ``[servers...]`` - The servers to leave. When blank, attempts to leave the current server.

.. _core-command-licenseinfo:

^^^^^^^^^^^
licenseinfo
^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]licenseinfo 

.. tip:: Alias: ``licenceinfo``

**Description**

Get info about Red's licenses.

.. _core-command-load:

^^^^
load
^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]load <cogs...>

**Description**

Loads cog packages from the local paths and installed cogs.

See packages available to load with ``[p]cogs``.

Additional cogs can be added using Downloader, or from local paths using ``[p]addpath``.

**Examples:**
    - ``[p]load general`` - Loads the ``general`` cog.
    - ``[p]load admin mod mutes`` - Loads multiple cogs.

**Arguments:**
    - ``<cogs...>`` - The cog packages to load.

.. _core-command-localallowlist:

^^^^^^^^^^^^^^
localallowlist
^^^^^^^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]localallowlist 

.. tip:: Alias: ``localwhitelist``

**Description**

Commands to manage the server specific allowlist.

.. Warning:: When the allowlist is in use, the bot will ignore commands from everyone not on the list in the server.


Use ``[p]localallowlist clear`` to disable the allowlist

.. _core-command-localallowlist-add:

""""""""""""""""""
localallowlist add
""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]localallowlist add <users_or_roles...>

**Description**

Adds a user or role to the server allowlist.

**Examples:**
    - ``[p]localallowlist add @26 @Will`` - Adds two users to the local allowlist.
    - ``[p]localallowlist add 262626262626262626`` - Allows a user by ID.
    - ``[p]localallowlist add "Super Admins"`` - Allows a role with a space in the name without mentioning.

**Arguments:**
    - ``<users_or_roles...>`` - The users or roles to remove from the local allowlist.

.. _core-command-localallowlist-clear:

""""""""""""""""""""
localallowlist clear
""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]localallowlist clear 

**Description**

Clears the allowlist.

This disables the local allowlist and clears all entires.

**Example:**
    - ``[p]localallowlist clear``

.. _core-command-localallowlist-list:

"""""""""""""""""""
localallowlist list
"""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]localallowlist list 

**Description**

Lists users and roles on the server allowlist.

**Example:**
    - ``[p]localallowlist list``

.. _core-command-localallowlist-remove:

"""""""""""""""""""""
localallowlist remove
"""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]localallowlist remove <users_or_roles...>

**Description**

Removes user or role from the allowlist.

The local allowlist will be disabled if all users are removed.

**Examples:**
    - ``[p]localallowlist remove @26 @Will`` - Removes two users from the local allowlist.
    - ``[p]localallowlist remove 262626262626262626`` - Removes a user by ID.
    - ``[p]localallowlist remove "Super Admins"`` - Removes a role with a space in the name without mentioning.

**Arguments:**
    - ``<users_or_roles...>`` - The users or roles to remove from the local allowlist.

.. _core-command-localblocklist:

^^^^^^^^^^^^^^
localblocklist
^^^^^^^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]localblocklist 

.. tip:: Alias: ``localblacklist``

**Description**

Commands to manage the server specific blocklist.

Use ``[p]localblocklist clear`` to disable the blocklist

.. _core-command-localblocklist-add:

""""""""""""""""""
localblocklist add
""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]localblocklist add <users_or_roles...>

**Description**

Adds a user or role to the local blocklist.

**Examples:**
    - ``[p]localblocklist add @26 @Will`` - Adds two users to the local blocklist.
    - ``[p]localblocklist add 262626262626262626`` - Blocks a user by ID.
    - ``[p]localblocklist add "Bad Apples"`` - Blocks a role with a space in the name without mentioning.

**Arguments:**
    - ``<users_or_roles...>`` - The users or roles to add to the local blocklist.

.. _core-command-localblocklist-clear:

""""""""""""""""""""
localblocklist clear
""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]localblocklist clear 

**Description**

Clears the server blocklist.

This disabled the server blocklist and clears all entries.

**Example:**
    - ``[p]blocklist clear``

.. _core-command-localblocklist-list:

"""""""""""""""""""
localblocklist list
"""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]localblocklist list 

**Description**

Lists users and roles on the server blocklist.

**Example:**
    - ``[p]localblocklist list``

.. _core-command-localblocklist-remove:

"""""""""""""""""""""
localblocklist remove
"""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]localblocklist remove <users_or_roles...>

**Description**

Removes user or role from blocklist.

**Examples:**
    - ``[p]localblocklist remove @26 @Will`` - Removes two users from the local blocklist.
    - ``[p]localblocklist remove 262626262626262626`` - Unblocks a user by ID.
    - ``[p]localblocklist remove "Bad Apples"`` - Unblocks a role with a space in the name without mentioning.

**Arguments:**
    - ``<users_or_roles...>`` - The users or roles to remove from the local blocklist.

.. _core-command-modlogset:

^^^^^^^^^
modlogset
^^^^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]modlogset 

**Description**

Manage modlog settings.

.. _core-command-modlogset-cases:

"""""""""""""""
modlogset cases
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]modlogset cases [action]

**Description**

Enable or disable case creation for a mod action, like disabling warnings, enabling bans, etc.

**Examples:**
    - ``[p]modlogset cases kick`` - Enables/disables modlog messages for kicks.
    - ``[p]modlogset cases ban`` - Enables/disables modlog messages for bans.

**Arguments:**
    - ``[action]`` - The type of mod action to be enabled/disabled for case creation.


.. _core-command-modlogset-modlog:

""""""""""""""""
modlogset modlog
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]modlogset modlog [channel]

.. tip:: Alias: ``modlogset channel``

**Description**

Set a channel as the modlog.

**Arguments**

* ``[channel]``: The channel to set as the modlog. If omitted, the modlog will be disabled.

.. _core-command-modlogset-resetcases:

""""""""""""""""""""
modlogset resetcases
""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]modlogset resetcases 

**Description**

Reset all modlog cases in this server.

.. _core-command-mydata:

^^^^^^
mydata
^^^^^^

**Syntax**

.. code-block:: none

    [p]mydata 

**Description**

Commands which interact with the data Red has about you.

More information can be found in the :doc:`End User Data Documentation.<../red_core_data_statement>`

.. _core-command-mydata-3rdparty:

"""""""""""""""
mydata 3rdparty
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]mydata 3rdparty 

**Description**

View the End User Data statements of each 3rd-party module.

This will send an attachment with the End User Data statements of all loaded 3rd party cogs.

**Example:**
    - ``[p]mydata 3rdparty``

.. _core-command-mydata-forgetme:

"""""""""""""""
mydata forgetme
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]mydata forgetme 

**Description**

Have Red forget what it knows about you.

This may not remove all data about you, data needed for operation,
such as command cooldowns will be kept until no longer necessary.

Further interactions with Red may cause it to learn about you again.

**Example:**
    - ``[p]mydata forgetme``

.. _core-command-mydata-getmydata:

""""""""""""""""
mydata getmydata
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]mydata getmydata 

**Description**

[Coming Soon] Get what data Red has about you.

.. _core-command-mydata-ownermanagement:

""""""""""""""""""""""
mydata ownermanagement
""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]mydata ownermanagement 

**Description**

Commands for more complete data handling.

.. _core-command-mydata-ownermanagement-allowuserdeletions:

"""""""""""""""""""""""""""""""""""""""""
mydata ownermanagement allowuserdeletions
"""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]mydata ownermanagement allowuserdeletions 

**Description**

Set the bot to allow users to request a data deletion.

This is on by default.
Opposite of ``[p]mydata ownermanagement disallowuserdeletions``

**Example:**
    - ``[p]mydata ownermanagement allowuserdeletions``

.. _core-command-mydata-ownermanagement-deleteforuser:

""""""""""""""""""""""""""""""""""""
mydata ownermanagement deleteforuser
""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]mydata ownermanagement deleteforuser <user_id>

**Description**

Delete data Red has about a user for a user.

This will cause the bot to get rid of or disassociate a lot of non-operational data from the specified user.
Users have access to a different command for this unless they can't interact with the bot at all.
This is a mostly safe operation, but you should not use it unless processing a request from this user as it may impact their usage of the bot.

**Arguments:**
    - ``<user_id>`` - The id of the user whose data would be deleted.

.. _core-command-mydata-ownermanagement-deleteuserasowner:

""""""""""""""""""""""""""""""""""""""""
mydata ownermanagement deleteuserasowner
""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]mydata ownermanagement deleteuserasowner <user_id>

**Description**

Delete data Red has about a user.

This will cause the bot to get rid of or disassociate a lot of data about the specified user.
This may include more than just end user data, including anti abuse records.

**Arguments:**
    - ``<user_id>`` - The id of the user whose data would be deleted.

.. _core-command-mydata-ownermanagement-disallowuserdeletions:

""""""""""""""""""""""""""""""""""""""""""""
mydata ownermanagement disallowuserdeletions
""""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]mydata ownermanagement disallowuserdeletions 

**Description**

Set the bot to not allow users to request a data deletion.

Opposite of ``[p]mydata ownermanagement allowuserdeletions``

**Example:**
    - ``[p]mydata ownermanagement disallowuserdeletions``

.. _core-command-mydata-ownermanagement-processdiscordrequest:

""""""""""""""""""""""""""""""""""""""""""""
mydata ownermanagement processdiscordrequest
""""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]mydata ownermanagement processdiscordrequest <user_id>

**Description**

Handle a deletion request from Discord.

This will cause the bot to get rid of or disassociate all data from the specified user ID.
You should not use this unless Discord has specifically requested this with regard to a deleted user.
This will remove the user from various anti-abuse measures.
If you are processing a manual request from a user, you may want ``[p]mydata ownermanagement deleteforuser`` instead.

**Arguments:**
    - ``<user_id>`` - The id of the user whose data would be deleted.

.. _core-command-mydata-ownermanagement-setuserdeletionlevel:

"""""""""""""""""""""""""""""""""""""""""""
mydata ownermanagement setuserdeletionlevel
"""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]mydata ownermanagement setuserdeletionlevel <level>

**Description**

Sets how user deletions are treated.

**Example:**
    - ``[p]mydata ownermanagement setuserdeletionlevel 1``

**Arguments:**
    - ``<level>`` - The strictness level for user deletion. See Level guide below.

Level:
    - ``0``: What users can delete is left entirely up to each cog.
    - ``1``: Cogs should delete anything the cog doesn't need about the user.

.. _core-command-mydata-whatdata:

"""""""""""""""
mydata whatdata
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]mydata whatdata 

**Description**

Find out what type of data Red stores and why.

**Example:**
    - ``[p]mydata whatdata``

.. _core-command-reload:

^^^^^^
reload
^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]reload <cogs...>

**Description**

Reloads cog packages.

This will unload and then load the specified cogs.

Cogs that were not loaded will only be loaded.

**Examples:**
    - ``[p]reload general`` - Unloads then loads the ``general`` cog.
    - ``[p]reload admin mod mutes`` - Unloads then loads multiple cogs.

**Arguments:**
    - ``<cogs...>`` - The cog packages to reload.

.. _core-command-restart:

^^^^^^^
restart
^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]restart [silently=False]

**Description**

Attempts to restart Red.

Makes Red quit with exit code 26.
The restart is not guaranteed: it must be dealt with by the process manager in use.

**Examples:**
    - ``[p]restart``
    - ``[p]restart True`` - Restarts silently.

**Arguments:**
    - ``[silently]`` - Whether to skip sending the restart message. Defaults to False.

.. _core-command-servers:

^^^^^^^
servers
^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]servers 

**Description**

Lists the servers Red is currently in.

.. Note:: This command is interactive.


.. _core-command-set:

^^^
set
^^^

**Syntax**

.. code-block:: none

    [p]set 

**Description**

Commands for changing Red's settings.

.. _core-command-set-api:

"""""""
set api
"""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set api <service> <tokens>

**Description**

Commands to set, list or remove various external API tokens.

This setting will be asked for by some 3rd party cogs and some core cogs.

To add the keys provide the service name and the tokens as a comma separated
list of key,values as described by the cog requesting this command.

.. Note:: API tokens are sensitive, so this command should only be used in a private channel or in DM with the bot.


**Examples:**
    - ``[p]set api spotify redirect_uri localhost``
    - ``[p]set api github client_id,whoops client_secret,whoops``

**Arguments:**
    - ``<service>`` - The service you're adding tokens to.
    - ``<tokens>`` - Pairs of token keys and values. The key and value should be separated by one of `` ``, ``,``, or ``;``.

.. _core-command-set-api-list:

""""""""""""
set api list
""""""""""""

**Syntax**

.. code-block:: none

    [p]set api list 

**Description**

Show all external API services along with their keys that have been set.

Secrets are not shown.

**Example:**
    - ``[p]set api list``

.. _core-command-set-api-remove:

""""""""""""""
set api remove
""""""""""""""

**Syntax**

.. code-block:: none

    [p]set api remove <services...>

**Description**

Remove the given services with all their keys and tokens.

**Examples:**
    - ``[p]set api remove spotify``
    - ``[p]set api remove github youtube``

**Arguments:**
    - ``<services...>`` - The services to remove.

.. _core-command-set-bot:

"""""""
set bot
"""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]set bot

**Description**

Commands for changing Red's metadata.

.. _core-command-set-bot-avatar:

""""""""""""""
set bot avatar
""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set bot avatar [url]

**Description**

Sets Red's avatar

Supports either an attachment or an image URL.

**Examples:**
    - ``[p]set bot avatar`` - With an image attachment, this will set the avatar.
    - ``[p]set bot avatar`` - Without an attachment, this will show the command help.
    - ``[p]set bot avatar https://avatars.githubusercontent.com/u/23690422`` - Sets the avatar to the provided url.

**Arguments:**
    - ``[url]`` - An image url to be used as an avatar. Leave blank when uploading an attachment.

.. _core-command-set-bot-avatar-remove:

"""""""""""""""""""""
set bot avatar remove
"""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set bot avatar remove 

.. tip:: Alias: ``set bot avatar clear``

**Description**

Removes Red's avatar.

**Example:**
    - ``[p]set bot avatar remove``

.. _core-command-set-bot-banner:

""""""""""""""
set bot banner
""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set bot banner [url]

**Description**

Sets Red's banner

Supports either an attachment or an image URL.

**Examples:**
    - ``[p]set bot banner`` - With an image attachment, this will set the banner.
    - ``[p]set bot banner`` - Without an attachment, this will show the command help.
    - ``[p]set bot banner https://opengraph.githubassets.com`` - Sets the banner to the provided url.

**Arguments:**
    - ``[url]`` - An image url to be used as an banner. Leave blank when uploading an attachment.

.. _core-command-set-bot-banner-remove:

"""""""""""""""""""""
set bot banner remove
"""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set bot banner remove

.. tip:: Alias: ``set bot banner clear``

**Description**

Removes Red's banner.

**Example:**
    - ``[p]set bot banner remove``

.. _core-command-set-bot-custominfo:

""""""""""""""""""
set bot custominfo
""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set bot custominfo [text]

**Description**

Customizes a section of ``[p]info``.

The maximum amount of allowed characters is 1024.
Supports markdown, links and "mentions".

Link example: ``[My link](https://example.com)``

**Examples:**
    - ``[p]set bot custominfo >>> I can use **markdown** such as quotes, ||spoilers|| and multiple lines.``
    - ``[p]set bot custominfo Join my [support server](discord.gg/discord)!``
    - ``[p]set bot custominfo`` - Removes custom info text.

**Arguments:**
    - ``[text]`` - The custom info text.

.. _core-command-set-bot-description:

"""""""""""""""""""
set bot description
"""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set bot description [description]

**Description**

Sets the bot's description.

Use without a description to reset.
This is shown in a few locations, including the help menu.

The maximum description length is 250 characters to ensure it displays properly.

The default is "Red V3".

**Examples:**
    - ``[p]set bot description`` - Resets the description to the default setting.
    - ``[p]set bot description MyBot: A Red V3 Bot``

**Arguments:**
    - ``[description]`` - The description to use for this bot. Leave blank to reset to the default.

.. _core-command-set-bot-nickname:

""""""""""""""""
set bot nickname
""""""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]set bot nickname [nickname]

**Description**

Sets Red's nickname for the current server.

Maximum length for a nickname is 32 characters.

**Example:**
    - ``[p]set bot nickname 🎃 SpookyBot 🎃``

**Arguments:**
    - ``[nickname]`` - The nickname to give the bot. Leave blank to clear the current nickname.

.. _core-command-set-bot-username:

""""""""""""""""
set bot username
""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set bot username <username>

.. tip:: Alias: ``set bot name``

**Description**

Sets Red's username.

Maximum length for a username is 32 characters.

.. Note:: The username of a verified bot cannot be manually changed.

    Please contact Discord support to change it.

**Example:**
    - ``[p]set bot username BaguetteBot``

**Arguments:**
    - ``<username>`` - The username to give the bot.

.. _core-command-set-colour:

""""""""""
set colour
""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set colour [colour]

.. tip:: Alias: ``set color``

**Description**

Sets a default colour to be used for the bot's embeds.

Acceptable values for the colour parameter can be found at:

https://discordpy.readthedocs.io/en/stable/ext/commands/api.html#discord.ext.commands.ColourConverter

**Examples:**
    - ``[p]set colour dark red``
    - ``[p]set colour blurple``
    - ``[p]set colour 0x5DADE2``
    - ``[p]set color 0x#FDFEFE``
    - ``[p]set color #7F8C8D``

**Arguments:**
    - ``[colour]`` - The colour to use for embeds. Leave blank to set to the default value (red).

.. _core-command-set-deletedelay:

"""""""""""""""
set deletedelay
"""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]set deletedelay [time]

**Description**

Set the delay until the bot removes the command message.

Must be between -1 and 60.

Set to -1 to disable this feature.

This is only applied to the current server and not globally.

**Examples:**
    - ``[p]set deletedelay`` - Shows the current delete delay setting.
    - ``[p]set deletedelay 60`` - Sets the delete delay to the max of 60 seconds.
    - ``[p]set deletedelay -1`` - Disables deleting command messages.

**Arguments:**
    - ``[time]`` - The seconds to wait before deleting the command message. Use -1 to disable.

.. _core-command-set-errormsg:

""""""""""""
set errormsg
""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set errormsg [msg]

**Description**

Set the message that will be sent on uncaught bot errors.

To include the command name in the message, use the ``{command}`` placeholder.

If you omit the ``msg`` argument, the message will be reset to the default one.

**Examples:**
    - ``[p]set errormsg`` - Resets the error message back to the default: "Error in command '{command}'.". If the command invoker is one of the bot owners, the message will also include "Check your console or logs for details.".
    - ``[p]set errormsg Oops, the command {command} has failed! Please try again later.`` - Sets the error message to a custom one.

**Arguments:**
    - ``[msg]`` - The custom error message. Must be less than 1000 characters. Omit to reset to the default one.

.. _core-command-set-fuzzy:

"""""""""
set fuzzy
"""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set fuzzy 

**Description**

Toggle whether to enable fuzzy command search in DMs.

This allows the bot to identify potential misspelled commands and offer corrections.

Default is for fuzzy command search to be disabled.

**Example:**
    - ``[p]set fuzzy``

.. _core-command-set-locale:

""""""""""
set locale
""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]set locale <language_code>

**Description**

Changes the bot's locale in this server.

Go to `Red's Crowdin page <https://translate.discord.red>`_ to see locales that are available with translations.

Use "default" to return to the bot's default set language.

If you want to change bot's global locale, see ``[p]set locale global`` command.

**Examples:**
    - ``[p]set locale en-US``
    - ``[p]set locale de-DE``
    - ``[p]set locale fr-FR``
    - ``[p]set locale pl-PL``
    - ``[p]set locale default`` - Resets to the global default locale.

**Arguments:**
    - ``<language_code>`` - The default locale to use for the bot. This can be any language code with country code included.

.. _core-command-set-locale-global:

"""""""""""""""""
set locale global
"""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set locale global <language_code>

**Description**

Changes the bot's default locale.

This will be used when a server has not set a locale, or in DMs.

Go to `Red's Crowdin page <https://translate.discord.red>`_ to see locales that are available with translations.

To reset to English, use "en-US".

**Examples:**
    - ``[p]set locale global en-US``
    - ``[p]set locale global de-DE``
    - ``[p]set locale global fr-FR``
    - ``[p]set locale global pl-PL``

**Arguments:**
    - ``<language_code>`` - The default locale to use for the bot. This can be any language code with country code included.

.. _core-command-set-locale-server:

"""""""""""""""""
set locale server
"""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]set locale server <language_code>

.. tip:: Aliases: ``set locale local``, ``set locale guild``

**Description**

Changes the bot's locale in this server.

Go to `Red's Crowdin page <https://translate.discord.red>`_ to see locales that are available with translations.

Use "default" to return to the bot's default set language.

**Examples:**
    - ``[p]set locale server en-US``
    - ``[p]set locale server de-DE``
    - ``[p]set locale server fr-FR``
    - ``[p]set locale server pl-PL``
    - ``[p]set locale server default`` - Resets to the global default locale.

**Arguments:**
    - ``<language_code>`` - The default locale to use for the bot. This can be any language code with country code included.

.. _core-command-set-ownernotifications:

""""""""""""""""""""""
set ownernotifications
""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set ownernotifications 

**Description**

Commands for configuring owner notifications.

Owner notifications include usage of ``[p]contact`` and available Red updates.

.. _core-command-set-ownernotifications-adddestination:

"""""""""""""""""""""""""""""""""""""
set ownernotifications adddestination
"""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]set ownernotifications adddestination <channel>

**Description**

Adds a destination text channel to receive owner notifications.

**Examples:**
    - ``[p]set ownernotifications adddestination #owner-notifications``
    - ``[p]set ownernotifications adddestination 168091848718417920`` - Accepts channel IDs.

**Arguments:**
    - ``<channel>`` - The channel to send owner notifications to.

.. _core-command-set-ownernotifications-listdestinations:

"""""""""""""""""""""""""""""""""""""""
set ownernotifications listdestinations
"""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]set ownernotifications listdestinations 

**Description**

Lists the configured extra destinations for owner notifications.

**Example:**
    - ``[p]set ownernotifications listdestinations``

.. _core-command-set-ownernotifications-optin:

""""""""""""""""""""""""""""
set ownernotifications optin
""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]set ownernotifications optin 

**Description**

Opt-in on receiving owner notifications.

This is the default state.

.. Note:: This will only resume sending owner notifications to your DMs.

    Additional owners and destinations will not be affected.

**Example:**
    - ``[p]set ownernotifications optin``

.. _core-command-set-ownernotifications-optout:

"""""""""""""""""""""""""""""
set ownernotifications optout
"""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]set ownernotifications optout 

**Description**

Opt-out of receiving owner notifications.

.. Note:: This will only stop sending owner notifications to your DMs.

    Additional owners and destinations will still receive notifications.

**Example:**
    - ``[p]set ownernotifications optout``

.. _core-command-set-ownernotifications-removedestination:

""""""""""""""""""""""""""""""""""""""""
set ownernotifications removedestination
""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]set ownernotifications removedestination <channel>

.. tip:: Aliases: ``set ownernotifications remdestination``, ``set ownernotifications deletedestination``, ``set ownernotifications deldestination``

**Description**

Removes a destination text channel from receiving owner notifications.

**Examples:**
    - ``[p]set ownernotifications removedestination #owner-notifications``
    - ``[p]set ownernotifications deletedestination 168091848718417920`` - Accepts channel IDs.

**Arguments:**
    - ``<channel>`` - The channel to stop sending owner notifications to.

.. _core-command-set-prefix:

""""""""""
set prefix
""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set prefix <prefixes...>

.. tip:: Alias: ``set prefixes``

**Description**

Sets Red's global prefix(es).

.. Warning:: This is not additive. It will replace all current prefixes.


See also the ``--mentionable`` flag to enable mentioning the bot as the prefix.

**Examples:**
    - ``[p]set prefix !``
    - ``[p]set prefix "! "`` - Quotes are needed to use spaces in prefixes.
    - ``[p]set prefix "@Red "`` - This uses a mention as the prefix. See also the ``--mentionable`` flag.
    - ``[p]set prefix ! ? .`` - Sets multiple prefixes.

**Arguments:**
    - ``<prefixes...>`` - The prefixes the bot will respond to globally.

.. _core-command-set-regionalformat:

""""""""""""""""""
set regionalformat
""""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]set regionalformat <language_code>

.. tip:: Alias: ``set region``

**Description**

Changes the bot's regional format in this server. This is used for formatting date, time and numbers.

``language_code`` can be any language code with country code included, e.g. ``en-US``, ``de-DE``, ``fr-FR``, ``pl-PL``, etc.
Pass "reset" to ``language_code`` to base regional formatting on bot's locale in this server.

If you want to change bot's global regional format, see ``[p]set regionalformat global`` command.

**Examples:**
    - ``[p]set regionalformat en-US``
    - ``[p]set region de-DE``
    - ``[p]set regionalformat reset`` - Resets to the locale.

**Arguments:**
    - ``[language_code]`` - The region format to use for the bot in this server.

.. _core-command-set-regionalformat-global:

"""""""""""""""""""""""""
set regionalformat global
"""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set regionalformat global <language_code>

**Description**

Changes the bot's regional format. This is used for formatting date, time and numbers.

``language_code`` can be any language code with country code included, e.g. ``en-US``, ``de-DE``, ``fr-FR``, ``pl-PL``, etc.
Pass "reset" to ``language_code`` to base regional formatting on bot's locale.

**Examples:**
    - ``[p]set regionalformat global en-US``
    - ``[p]set region global de-DE``
    - ``[p]set regionalformat global reset`` - Resets to the locale.

**Arguments:**
    - ``[language_code]`` - The default region format to use for the bot.

.. _core-command-set-regionalformat-server:

"""""""""""""""""""""""""
set regionalformat server
"""""""""""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]set regionalformat server <language_code>

.. tip:: Aliases: ``set regionalformat local``, ``set regionalformat guild``

**Description**

Changes the bot's regional format in this server. This is used for formatting date, time and numbers.

``language_code`` can be any language code with country code included, e.g. ``en-US``, ``de-DE``, ``fr-FR``, ``pl-PL``, etc.
Pass "reset" to ``language_code`` to base regional formatting on bot's locale in this server.

**Examples:**
    - ``[p]set regionalformat server en-US``
    - ``[p]set region local de-DE``
    - ``[p]set regionalformat server reset`` - Resets to the locale.

**Arguments:**
    - ``[language_code]`` - The region format to use for the bot in this server.

.. _core-command-set-roles:

"""""""""
set roles
"""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]set roles

**Description**

Set server's admin and mod roles for Red.

.. _core-command-set-roles-addadminrole:

""""""""""""""""""""""
set roles addadminrole
""""""""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]set roles addadminrole <role>

**Description**

Adds an admin role for this guild.

Admins have the same access as Mods, plus additional admin level commands like:
 - ``[p]set serverprefix``
 - ``[p]addrole``
 - ``[p]ban``
 - ``[p]ignore guild``

 And more.

 **Examples:**
    - ``[p]set roles addadminrole @Admins``
    - ``[p]set roles addadminrole Super Admins``

**Arguments:**
    - ``<role>`` - The role to add as an admin.

.. _core-command-set-roles-addmodrole:

""""""""""""""""""""
set roles addmodrole
""""""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]set roles addmodrole <role>

**Description**

Adds a moderator role for this guild.

This grants access to moderator level commands like:
 - ``[p]mute``
 - ``[p]cleanup``
 - ``[p]customcommand create``

 And more.

 **Examples:**
    - ``[p]set roles addmodrole @Mods``
    - ``[p]set roles addmodrole Loyal Helpers``

**Arguments:**
    - ``<role>`` - The role to add as a moderator.

.. _core-command-set-roles-removeadminrole:

"""""""""""""""""""""""""
set roles removeadminrole
"""""""""""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]set roles removeadminrole <role>

.. tip:: Aliases: ``set roles remadmindrole``, ``set roles deladminrole``, ``set roles deleteadminrole``

**Description**

Removes an admin role for this guild.

**Examples:**
    - ``[p]set roles removeadminrole @Admins``
    - ``[p]set roles removeadminrole Super Admins``

**Arguments:**
    - ``<role>`` - The role to remove from being an admin.

.. _core-command-set-roles-removemodrole:

"""""""""""""""""""""""
set roles removemodrole
"""""""""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]set roles removemodrole <role>

.. tip:: Aliases: ``set roles remmodrole``, ``set roles delmodrole``, ``set roles deletemodrole``

**Description**

Removes a mod role for this guild.

**Examples:**
    - ``[p]set roles removemodrole @Mods``
    - ``[p]set roles removemodrole Loyal Helpers``

**Arguments:**
    - ``<role>`` - The role to remove from being a moderator.

.. _core-command-set-serverfuzzy:

"""""""""""""""
set serverfuzzy
"""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]set serverfuzzy 

**Description**

Toggle whether to enable fuzzy command search for the server.

This allows the bot to identify potential misspelled commands and offer corrections.

.. Note:: This can be processor intensive and may be unsuitable for larger servers.


Default is for fuzzy command search to be disabled.

**Example:**
    - ``[p]set serverfuzzy``

.. _core-command-set-serverprefix:

""""""""""""""""
set serverprefix
""""""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]set serverprefix [server] [prefixes...]

.. tip:: Alias: ``set serverprefixes``

**Description**

Sets Red's server prefix(es).

.. Warning:: This will override global prefixes, the bot will not respond to any global prefixes in this server.

    This is not additive. It will replace all current server prefixes.

    You cannot have a prefix with more than 25 characters.

**Examples:**
    - ``[p]set serverprefix !``
    - ``[p]set serverprefix "! "`` - Quotes are needed to use spaces in prefixes.
    - ``[p]set serverprefix "@Red "`` - This uses a mention as the prefix.
    - ``[p]set serverprefix ! ? .`` - Sets multiple prefixes.
    - ``[p]set serverprefix "Red - Discord Bot" ?`` - Sets the prefix for a specific server. Quotes are needed to use spaces in the server name.

**Arguments:**
    - ``[server]`` - The server to set the prefix for. Defaults to current server.
    - ``[prefixes...]`` - The prefixes the bot will respond to on this server. Leave blank to clear server prefixes.

.. _core-command-set-showsettings:

""""""""""""""""
set showsettings
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]set showsettings [server]

**Description**

Show the current settings for Red.

Accepts optional server parameter to allow prefix recovery.

**Arguments:**
    - ``[server]`` - The server to show the settings for. Defaults to current server, or no server in a DM context.

.. _core-command-set-status:

""""""""""
set status
""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set status

**Description**

Commands for setting Red's status.

.. _core-command-set-status-competing:

""""""""""""""""""""
set status competing
""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set status competing [competing]

**Description**

Sets Red's competing status.

This will appear as ``Competing in <competing>``.

Maximum length for a competing status is 128 characters.

**Examples:**
    - ``[p]set status competing`` - Clears the activity status.
    - ``[p]set status competing London 2012 Olympic Games``

**Arguments:**
    - ``[competing]`` - The text to follow ``Competing in``. Leave blank to clear the current activity status.

.. _core-command-set-status-custom:

"""""""""""""""""
set status custom
"""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set status custom [text]

**Description**

Sets Red's custom status.

This will appear as ``<text>``.

Maximum length for a custom status is 128 characters.

**Examples:**
    - ``[p]set status custom`` - Clears the activity status.
    - ``[p]set status custom Running cogs...``

**Arguments:**
    - ``[text]`` - The custom status text. Leave blank to clear the current activity status.

.. _core-command-set-status-dnd:

""""""""""""""
set status dnd
""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set status dnd

.. tip:: Aliases: ``set status donotdisturb``, ``set status busy``

**Description**

Sets Red's status to do not disturb.

.. _core-command-set-status-idle:

"""""""""""""""
set status idle
"""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set status idle

.. tip:: Aliases: ``set status away``, ``set status afk``

**Description**

Sets Red's status to idle.

.. _core-command-set-status-invisible:

""""""""""""""""""""
set status invisible
""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set status invisible

.. tip:: Alias: ``set status offline``

**Description**

Sets Red's status to invisible.

.. _core-command-set-status-listening:

""""""""""""""""""""
set status listening
""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set status listening [listening]

**Description**

Sets Red's listening status.

This will appear as ``Listening to <listening>``.

Maximum length for a listening status is 128 characters.

**Examples:**
    - ``[p]set status listening`` - Clears the activity status.
    - ``[p]set status listening jams``

**Arguments:**
    - ``[listening]`` - The text to follow ``Listening to``. Leave blank to clear the current activity status.

.. _core-command-set-status-online:

"""""""""""""""""
set status online
"""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set status online

**Description**

Sets Red's status to online.

.. _core-command-set-status-playing:

""""""""""""""""""
set status playing
""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set status playing [game]

.. tip:: Alias: ``set status game``

**Description**

Sets Red's playing status.

This will appear as ``Playing <game>`` or ``PLAYING A GAME: <game>`` depending on the context.

Maximum length for a playing status is 128 characters.

**Examples:**
    - ``[p]set status playing`` - Clears the activity status.
    - ``[p]set status playing the keyboard``

**Arguments:**
    - ``[game]`` - The text to follow ``Playing``. Leave blank to clear the current activity status.

.. _core-command-set-status-streaming:

""""""""""""""""""""
set status streaming
""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set status streaming [(<streamer> <stream_title>)]

.. tip:: Aliases: ``set status stream``, ``set status twitch``

**Description**

Sets Red's streaming status to a twitch stream.

This will appear as ``Streaming <stream_title>`` or ``LIVE ON TWITCH`` depending on the context.
It will also include a ``Watch`` button with a twitch.tv url for the provided streamer.

Maximum length for a stream title is 128 characters.

Leaving both streamer and stream_title empty will clear it.

**Examples:**
    - ``[p]set status stream`` - Clears the activity status.
    - ``[p]set status stream 26 Twentysix is streaming`` - Sets the stream to ``https://www.twitch.tv/26``.
    - ``[p]set status stream https://twitch.tv/26 Twentysix is streaming`` - Sets the URL manually.

**Arguments:**
    - ``<streamer>`` - The twitch streamer to provide a link to. This can be their twitch name or the entire URL.
    - ``<stream_title>`` - The text to follow ``Streaming`` in the status.

.. _core-command-set-status-watching:

"""""""""""""""""""
set status watching
"""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set status watching [watching]

**Description**

Sets Red's watching status.

This will appear as ``Watching <watching>``.

Maximum length for a watching status is 128 characters.

**Examples:**
    - ``[p]set status watching`` - Clears the activity status.
    - ``[p]set status watching [p]help``

**Arguments:**
    - ``[watching]`` - The text to follow ``Watching``. Leave blank to clear the current activity status.

.. _core-command-set-usebotcolour:

""""""""""""""""
set usebotcolour
""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]set usebotcolour 

.. tip:: Alias: ``set usebotcolor``

**Description**

Toggle whether to use the bot owner-configured colour for embeds.

Default is to use the bot's configured colour.
Otherwise, the colour used will be the colour of the bot's top role.

**Example:**
    - ``[p]set usebotcolour``
    
.. _core-command-set-usebuttons:

""""""""""""""
set usebuttons
""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]set usebuttons [use_buttons]
    
**Description**

Set a global bot variable for using buttons in menus. When enabled, all usage of
cores menus API will use buttons instead of reactions. This defaults to False.
Using this without a setting will toggle.

**Examples:**
- ``[p]set usebuttons True`` - Enables using buttons.
- ``[p]helpset usebuttons`` - Toggles the value.

**Arguments:**
    - ``[use_buttons]`` - Whether to use buttons. Leave blank to toggle.

.. _core-command-shutdown:

^^^^^^^^
shutdown
^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]shutdown [silently=False]

**Description**

Shuts down the bot.

Allows Red to shut down gracefully.

This is the recommended method for shutting down the bot.

**Examples:**
    - ``[p]shutdown``
    - ``[p]shutdown True`` - Shutdowns silently.

**Arguments:**
    - ``[silently]`` - Whether to skip sending the shutdown message. Defaults to False.

.. _core-command-slash:

^^^^^
slash
^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]slash 

**Description**

Base command for managing what application commands are able to be used on Red.

.. _core-command-slash-disable:

"""""""""""""
slash disable
"""""""""""""

**Syntax**

.. code-block:: none

    [p]slash disable <command_name> [command_type]
    
**Description**

Marks an application command as being disabled, preventing it from being added to the bot.
See commands available to disable with ``[p]slash list``. This command does NOT sync the
enabled commands with Discord, that must be done manually with ``[p]slash sync`` for
commands to appear in users' clients.

**Arguments:**
    - ``<command_name>`` - The command name to disable. Only the top level name of a group command should be used.
    - ``[command_type]`` - What type of application command to disable. Must be one of ``slash``, ``message``, or ``user``. Defaults to ``slash``.

.. _core-command-slash-disablecog:

""""""""""""""""
slash disablecog
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]slash disablecog <cog_names...>
    
**Description**

Marks all application commands in a cog as being disabled, preventing them from being
added to the bot. See a list of cogs with application commands with ``[p]slash list``.
This command does NOT sync the enabled commands with Discord, that must be done manually
with ``[p]slash sync`` for commands to appear in users' clients.

**Arguments:**
    - ``<cog_names>`` - The cogs to disable commands from. This argument is case sensitive.

.. _core-command-slash-enable:

""""""""""""
slash enable
""""""""""""

**Syntax**

.. code-block:: none

    [p]slash enable <command_name> [command_type]
    
**Description**

Marks an application command as being enabled, allowing it to be added to the bot.
See commands available to enable with ``[p]slash list``. This command does NOT sync the
enabled commands with Discord, that must be done manually with ``[p]slash sync`` for
commands to appear in users' clients.

**Arguments:**
    - ``<command_name>`` - The command name to enable. Only the top level name of a group command should be used.
    - ``[command_type]`` - What type of application command to enable. Must be one of ``slash``, ``message``, or ``user``. Defaults to ``slash``.

.. _core-command-slash-enablecog:

"""""""""""""""
slash enablecog
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]slash enablecog <cog_names...>
    
**Description**

Marks all application commands in a cog as being enabled, allowing them to be
added to the bot. See a list of cogs with application commands with ``[p]slash list``.
This command does NOT sync the enabled commands with Discord, that must be done manually
with ``[p]slash sync`` for commands to appear in users' clients.

**Arguments:**
    - ``<cog_names>`` - The cogs to enable commands from. This argument is case sensitive.

.. _core-command-slash-list:

""""""""""
slash list
""""""""""

**Syntax**

.. code-block:: none

    [p]slash list
    
**Description**

List the slash commands the bot can see, and whether or not they are enabled.

This command shows the state that will be changed to when ``[p]slash sync`` is run.
Commands from the same cog are grouped, with the cog name as the header.

The prefix denotes the state of the command:
- Commands starting with ``- `` have not yet been enabled.
- Commands starting with ``+ `` have been manually enabled.
- Commands starting with ``++`` have been enabled by the cog author, and cannot be disabled.

.. _core-command-slash-sync:

""""""""""
slash sync
""""""""""

**Syntax**

.. code-block:: none

    [p]slash sync [guild]
    
**Description**

Syncs the slash settings to discord.
Settings from ``[p]slash list`` will be synced with discord, changing what commands appear for users.
This should be run sparingly, make all necessary changes before running this command.
        
**Arguments:**
    - ``[guild]`` - If provided, syncs commands for that guild. Otherwise, syncs global commands.

.. _core-command-traceback:

^^^^^^^^^
traceback
^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]traceback [public=False]

**Description**

Sends to the owner the last command exception that has occurred.

If public (yes is specified), it will be sent to the chat instead.

.. Warning:: Sending the traceback publicly can accidentally reveal sensitive information about your computer or configuration.


**Examples:**
    - ``[p]traceback`` - Sends the traceback to your DMs.
    - ``[p]traceback True`` - Sends the last traceback in the current context.

**Arguments:**
    - ``[public]`` - Whether to send the traceback to the current context. Leave blank to send to your DMs.

.. _core-command-unignore:

^^^^^^^^
unignore
^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]unignore 

**Description**

Commands to remove servers or channels from the ignore list.

.. _core-command-unignore-channel:

""""""""""""""""
unignore channel
""""""""""""""""

**Syntax**

.. code-block:: none

    [p]unignore channel [channel]

**Description**

Remove a channel, thread, or category from the ignore list.

Defaults to the current thread or channel.

**Examples:**
    - ``[p]unignore channel #general`` - Unignores commands in the #general channel.
    - ``[p]unignore channel`` - Unignores commands in the current channel.
    - ``[p]unignore channel "General Channels"`` - Use quotes for categories with spaces.
    - ``[p]unignore channel 356236713347252226`` - Also accepts IDs. Use this method to unignore categories.

**Arguments:**
    - ``<channel>`` - The channel to unignore. This can also be a thread or category channel.

.. _core-command-unignore-server:

"""""""""""""""
unignore server
"""""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]unignore server 

.. tip:: Alias: ``unignore guild``

**Description**

Remove this server from the ignore list.

**Example:**
    - ``[p]unignore server`` - Stops ignoring the current server

.. _core-command-unload:

^^^^^^
unload
^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]unload <cogs...>

**Description**

Unloads previously loaded cog packages.

See packages available to unload with ``[p]cogs``.

**Examples:**
    - ``[p]unload general`` - Unloads the ``general`` cog.
    - ``[p]unload admin mod mutes`` - Unloads multiple cogs.

**Arguments:**
    - ``<cogs...>`` - The cog packages to unload.

.. _core-command-uptime:

^^^^^^
uptime
^^^^^^

**Syntax**

.. code-block:: none

    [p]uptime 

**Description**

Shows Red's uptime.
