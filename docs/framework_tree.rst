.. tree module docs

====
Tree
====

Red uses a subclass of discord.py's ``CommandTree`` object in order to allow Cog Creators to add application commands to their cogs without worrying about the command count limit and to support caching ``AppCommand`` objects. When an app command is added to the bot's tree, it will not show up in ``tree.get_commands`` or other similar methods unless the command is "enabled" with ``[p]slash enable`` (similar to "load"ing a cog) and ``tree.red_check_enabled`` has been run since the command was added to the tree.

.. note::

    If you are adding app commands to the tree during load time, the loading process will call ``tree.red_check_enabled`` for your cog and its app commands. If you are adding app commands to the bot **outside of load time**, a call to ``tree.red_check_enabled`` after adding the commands is required to ensure the commands will appear properly.

    If application commands from your cog show up in ``[p]slash list`` as enabled from an ``(unknown)`` cog and disabled from your cog at the same time, you did not follow the instructions above. You must manually call ``tree.red_check_enabled`` **after** adding the commands to the tree.

.. automodule:: redbot.core.tree

RedTree
^^^^^^^

.. autoclass:: RedTree
    :members:
