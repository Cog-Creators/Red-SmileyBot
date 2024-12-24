.. CustomCommands Cog Reference
.. _cog_customcom:

============================
CustomCommands Cog Reference
============================

------------
How it works
------------

CustomCommands allows you to create simple commands for your bot without requiring you to code your own cog for Red.

If the command you attempt to create shares a name with an already loaded command, you cannot overwrite it with this cog.

---------
Cooldowns
---------

You can set cooldowns for your custom commands. If a command is on cooldown, it will not be triggered.

You can set cooldowns per member or per thread/channel, or set a cooldown guild-wide. You can also set multiple types of cooldown on a single custom command. All cooldowns must pass before the command will trigger.

------------------
Context Parameters
------------------

You can enhance your custom command's response by leaving spaces for the bot to substitute.

+-----------+--------------------------------------------------+
| Argument  | Substitute                                       |
+===========+==================================================+
| {message} | The message the bot is responding to.            |
+-----------+--------------------------------------------------+
| {author}  | The user who called the command.                 |
+-----------+--------------------------------------------------+
| {channel} | The channel or thread the command was called in. |
+-----------+--------------------------------------------------+
| {server}  | The server the command was called in.            |
+-----------+--------------------------------------------------+
| {guild}   | Same as with {server}.                           |
+-----------+--------------------------------------------------+

You can further refine the response with dot notation. For example, {author.mention} will mention the user who called the command.

------------------
Command Parameters
------------------

You can further enhance your custom command's response by leaving spaces for the user to substitute.

To do this, simply put {#} in the response, replacing # with any number starting with 0. Each number will be replaced with what the user gave the command, in order.

You can refine the response with colon notation. For example, {0:Member} will accept members of the server, and {0:int} will accept a number. If no colon notation is provided, the argument will be returned unchanged.

+-----------------+--------------------------------+
| Argument        | Substitute                     |
+=================+================================+
| {#:Member}      | A member of your server.       |
+-----------------+--------------------------------+
| {#:TextChannel} | A text channel in your server. |
+-----------------+--------------------------------+
| {#:Role}        | A role in your server.         |
+-----------------+--------------------------------+
| {#:int}         | A whole number.                |
+-----------------+--------------------------------+
| {#:float}       | A decimal number.              |
+-----------------+--------------------------------+
| {#:bool}        | True or False.                 |
+-----------------+--------------------------------+

You can specify more than the above with colon notation, but those are the most common.

As with context parameters, you can use dot notation to further refine the response. For example, {0.mention:Member} will mention the Member specified.

----------------
Example commands
----------------

Showing your own avatar

.. code-block:: none

    [p]customcom add simple avatar {author.display_avatar}
    [p]avatar
        https://cdn.discordapp.com/avatars/133801473317404673/be4c4a4fe47cb3e74c31a0504e7a295e.webp?size=1024

Repeating the user

.. code-block:: none

    [p]customcom add simple say {0}
    [p]say Pete and Repeat
        Pete and Repeat

Greeting the specified member

.. code-block:: none

    [p]customcom add simple greet Hello, {0.mention:Member}!
    [p]greet Twentysix
        Hello, @Twentysix!

Comparing two text channel's categories

.. code-block:: none

    [p]customcom add simple comparecategory {0.category:TextChannel}  |  {1.category:TextChannel}
    [p]comparecategory #support #general
        Red  |  Community
