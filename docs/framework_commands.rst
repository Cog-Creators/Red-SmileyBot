.. red commands module documentation

================
Commands Package
================

This package acts almost identically to :doc:`discord.ext.commands <dpy:ext/commands/api>`; i.e.
all of the attributes from discord.py's are also in ours. 
Some of these attributes, however, have been slightly modified, while others have been added to
extend functionalities used throughout the bot, as outlined below.

.. autofunction:: redbot.core.commands.command

.. autofunction:: redbot.core.commands.hybrid_command

.. autofunction:: redbot.core.commands.group

.. autofunction:: redbot.core.commands.hybrid_group

.. autoclass:: redbot.core.commands.Cog

    .. automethod:: format_help_for_context
    
    .. automethod:: red_get_data_for_user
    
    .. automethod:: red_delete_data_for_user

.. autoclass:: redbot.core.commands.GroupCog

.. autoclass:: redbot.core.commands.Command
    :members:
    :inherited-members: format_help_for_context

.. autoclass:: redbot.core.commands.HybridCommand
    :members:

.. autoclass:: redbot.core.commands.Group
    :members:

.. autoclass:: redbot.core.commands.HybridGroup
    :members:

.. autoclass:: redbot.core.commands.Context
    :members:

.. autoclass:: redbot.core.commands.GuildContext

.. autoclass:: redbot.core.commands.DMContext

.. autoclass:: redbot.core.commands.UserFeedbackCheckFailure
    :members:

.. automodule:: redbot.core.commands.requires
    :members: PrivilegeLevel, PermState, Requires

.. automodule:: redbot.core.commands.converter
    :members:
    :exclude-members: UserInputOptional, convert
    :no-undoc-members:

    .. autodata:: UserInputOptional
        :annotation:

.. _framework-commands-help:

******************
Help Functionality
******************

.. warning::

    The content in this section is `provisional <developer-guarantees-exclusions>` and may change
    without prior notice or warning. Updates to this will be communicated
    on `this issue <https://github.com/Cog-Creators/Red-DiscordBot/issues/4084>`_


.. automodule:: redbot.core.commands.help
    :members:
