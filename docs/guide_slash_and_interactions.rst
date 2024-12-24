.. Slash Commands and Interactions

.. role:: python(code)
    :language: python

===============================
Slash Commands and Interactions
===============================

This guide is going to cover on how to write a simple slash command into a Red cog.
This guide will assume that you have a working basic cog.
If you do not have a basic cog, please refer to the :ref:`getting started <getting-started>` guide.
It is also adviced to make yourself familiar with `Application Commands <https://discord.com/developers/docs/interactions/application-commands>`__ from Discord's documentation. 

---------------
Getting Started
---------------

To start off, we will have to import some additional modules to our cog file.
We will be using the ``redbot.core.app_commands`` module to create our slash commands.
Once we have imported the module, we can start creating our slash commands in our cog class.
For this example we will use a basic hello world command.

.. code-block:: python

    import discord

    from redbot.core import commands, app_commands

    class MyCog(commands.Cog):
        def __init__(self, bot):
            self.bot = bot

        @app_commands.command()
        async def hello(self, interaction: discord.Interaction):
            await interaction.response.send_message("Hello World!", ephemeral=True)

Go ahead and load your cog. Once it is loaded, we will have to enable and sync our slash commands.
We can do this by using the :ref:`[p]slash<core-command-slash>` command to manage our slash commands.
Once you have registered your slash commands, you can test them out by typing ``/hello`` in your server.

.. tip::

    You may need to restart your Discord client with ``Ctrl + R`` (or your device's equivalent) to force
    your client to see the new command after syncing.

----------------------------
Slash Commands and Arguments
----------------------------

There is a lot of flexibility when it comes to slash commands.
Below we will go over some of the different stuff you can do with slash commands.

Decorators
----------
Just like with text commands, we can use decorators to modify the behaviour of our slash commands.
For example, we can use the `app_commands.guild_only() <discord.app_commands.guild_only>` decorator to make our slash command only work in guilds.

.. code-block:: python

    import discord

    from redbot.core import commands, app_commands

    class MyCog(commands.Cog):
        def __init__(self, bot):
            self.bot = bot

        @app_commands.command()
        @app_commands.guild_only()
        async def hello(self, interaction: discord.Interaction):
            await interaction.response.send_message("Hello World!", ephemeral=True)

One of the more useful decorators is the `app_commands.choices() <discord.app_commands.choices>` decorator.
This decorator allows us to specify a list of choices for a specific argument.
This is useful for arguments that have a limited number of options.
For example, we can use this to create a command that allows us to choose between two different colors.

.. code-block:: python

    from redbot.core import commands, app_commands

    class MyCog(commands.Cog):
        def __init__(self, bot):
            self.bot = bot

        @app_commands.command()
        @app_commands.describe(color="The color you want to choose")
        @app_commands.choices(color=[
             app_commands.Choice(name="Red", value="red"),
             app_commands.Choice(name="Blue", value="blue"),
        ])
        async def color(self, interaction: discord.Interaction, color: app_commands.Choice[str]):
            await interaction.response.send_message(f"Your color is {color.value}", ephemeral=True)

The user will be shown the ``name`` of the choice, and the argument will be passed a
`app_commands.Choice <discord.app_commands.Choice>` object with the ``name`` and ``value`` associated with that choice.
This allows user-facing names to be prettier than what is actually processed by the command.

Alternatively, ``Literal`` can be used if the argument does not need a different
user-facing label. When done this way, the resulting parameter will be one of
the literal values listed.

.. code-block:: python

    from redbot.core import commands, app_commands
    from typing import Literal

    class MyCog(commands.Cog):
        def __init__(self, bot):
            self.bot = bot

        @app_commands.command()
        @app_commands.describe(color="The color you want to choose")
        async def color(self, interaction: discord.Interaction, color: Literal["Red", "Blue"]):
            await interaction.response.send_message(f"Your color is {color}", ephemeral=True)

Finally, an `enum.Enum` subclass can be used to specify choices. When done this way, the
resulting parameter will be an instance of that enum, rather than `app_commands.Choice <discord.app_commands.Choice>`.

.. code-block:: python

    from enum import Enum
    from redbot.core import commands, app_commands

    class Color(Enum):
        Red = "red"
        Blue = "blue"

    class MyCog(commands.Cog):
        def __init__(self, bot):
            self.bot = bot

        @app_commands.command()
        @app_commands.describe(color="The color you want to choose")
        async def color(self, interaction: discord.Interaction, color: Color):
            await interaction.response.send_message(f"Your color is {color.value}", ephemeral=True)

Check out :dpy_docs:`the full reference of decorators at Discord.py's documentation <interactions/api.html#decorators>`.


Groups & Subcommands
--------------------
Slash commands can also be grouped together into groups and subcommands.
These can be used to create a more complex command structure.

.. note::
    Unlike text command groups, top level slash command groups **cannot** be invoked.

.. code-block:: python

    import discord
    
    from redbot.core import commands, app_commands

    class MyCog(commands.Cog):
        def __init__(self, bot):
            self.bot = bot

        zoo = app_commands.Group(name="zoo", description="Zoo related commands")

        @zoo.command(name="add", description="Add an animal to the zoo")
        @app_commands.describe(animal="The animal you want to add")
        async def zoo_add(self, interaction: discord.Interaction, animal: str):
            await interaction.response.send_message(f"Added {animal} to the zoo", ephemeral=True)

        @zoo.command(name="remove", description="Remove an animal from the zoo")
        @app_commands.describe(animal="The animal you want to remove")
        async def zoo_remove(self, interaction: discord.Interaction, animal: str):
            await interaction.response.send_message(f"Removed {animal} from the zoo", ephemeral=True)

Arguments
---------
As shown in some of the above examples, we can amplify our slash commands with arguments.
However with slash commands Discord allows us to do a few more things.
Such as specifically select a channel that we'd like to use in our commands,
we can do the same with roles and members.
Let's take a look at how we can do that.

.. code-block:: python

    import discord

    from redbot.core import commands, app_commands

    class MyCog(commands.Cog):
        def __init__(self, bot):
            self.bot = bot

        @app_commands.command()
        @app_commands.describe(channel="The channel you want to mention")
        async def mentionchannel(self, interaction: discord.Interaction, channel: discord.abc.GuildChannel):
            await interaction.response.send_message(f"That channel is {channel.mention}", ephemeral=True)

        @app_commands.command()
        @app_commands.describe(role="The role you want to mention")
        async def mentionrole(self, interaction: discord.Interaction, role: discord.Role):
            await interaction.response.send_message(f"That role is {role.mention}", ephemeral=True)

        @app_commands.command()
        @app_commands.describe(member="The member you want to mention")
        async def mentionmember(self, interaction: discord.Interaction, member: discord.Member):
            await interaction.response.send_message(f"That member is {member.mention}", ephemeral=True)

If you try out the mentionchannel command, you will see that it currently accepts any type of channel,
however let's say we want to limit this to voice channels only.
We can do so by adjusting our type hint to :class:`discord.VoiceChannel` instead of :class:`discord.abc.GuildChannel`.

.. code-block:: python

    import discord

    from redbot.core import commands, app_commands

    class MyCog(commands.Cog):
        def __init__(self, bot):
            self.bot = bot

        @app_commands.command()
        @app_commands.describe(channel="The channel you want to mention")
        async def mentionchannel(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
            await interaction.response.send_message(f"That channel is {channel.mention}", ephemeral=True)

With integer and float arguments, we can also specify a minimum and maximum value.
This can also be done to strings to set a minimum and maximum length.
These limits will be reflected within Discord when the user is filling out the command.

.. code-block:: python

    import discord

    from redbot.core import commands, app_commands

    class MyCog(commands.Cog):
        def __init__(self, bot):
            self.bot = bot

        @app_commands.command()
        @app_commands.describe(number="The number you want to say, max 10")
        async def saynumber(self, interaction: discord.Interaction, number: app_commands.Range[int, None, 10]):
            await interaction.response.send_message(f"Your number is {number}", ephemeral=True)

See the `Discord.py documentation <https://discordpy.readthedocs.io/en/stable/interactions/api.html#range>`__ for more information on this.


---------------
Hybrid Commands
---------------
Hybrid commands are a way to bridge the gap between text commands and slash commands.
These types of commands allow you to write a text and slash command simultaneously using the same function.
This is useful for commands that you want to be able to use in both text and slash commands.

.. note::
    As with slash command groups, top level hybrid command groups **cannot** be invoked as a slash command. They can however be invoked as a text command.

.. code-block:: python

    from redbot.core import commands

    class MyCog(commands.Cog):
        def __init__(self, bot):
            self.bot = bot

        @commands.hybrid_command(name="cat")
        async def cat(self, ctx: commands.Context):
            await ctx.send("Meow")

        @commands.hybrid_group(name="dog")
        async def dog(self, ctx: commands.Context):
            await ctx.send("Woof")
            # As discussed above, top level hybrid command groups cannot be invoked as a slash command.
            # Thus, this will not work as a slash command.

        @dog.command(name="bark")
        async def bark(self, ctx: commands.Context):
            await ctx.send("Bark", ephemeral=True)

After syncing your cog via the :ref:`[p]slash<core-command-slash>` command, you'll be able to use the commands as both a slash and text command.

---------------------
Context Menu Commands
---------------------
Context menu commands are a way to provide a interaction via the context menu.
These are seen under ``Apps`` in the Discord client when you right click on a message or user.
Context menu commands are a great way to provide a quick way to interact with your bot.
These commands accept one arguement, the contextual ``user`` or ``message`` that was right clicked.

Setting up context commands is a bit more involved then setting up slash commands.
First lets setup our context commands in our cog.

.. code-block:: python
    
    import discord

    from redbot.core import commands, app_commands


    # Important: we're building the commands outside of our cog class.
    @app_commands.context_menu(name="Get message ID")
    async def get_message_id(interaction: discord.Interaction, message: discord.Message):
        await interaction.response.send_message(f"Message ID: {message.id}", ephemeral=True)

    @app_commands.context_menu(name="Get user ID")
    async def get_user_id(interaction: discord.Interaction, user: discord.User):
        await interaction.response.send_message(f"User ID: {user.id}", ephemeral=True)

Once we've prepared our main cog file, we have to add a small bit of code to our ``__init__.py`` file.

.. code-block:: python

    from .my_cog import get_message_id, get_user_id

    async def setup(bot):
        bot.tree.add_command(get_message_id)
        bot.tree.add_command(get_user_id)

    async def teardown(bot):
        # We're removing the commands here to ensure they get unloaded properly when the cog is unloaded.
        bot.tree.remove_command("Get message ID", type=discord.AppCommandType.message)
        bot.tree.remove_command("Get user ID", type=discord.AppCommandType.user)

Now we're ready to sync our commands to Discord.
We can do this by using the :ref:`[p]slash<core-command-slash>` command.
Take note of the specific arguments you have to use to sync a context command.

---------------------------------
Closing Words and Further Reading
---------------------------------
If you're reading this, it means that you've made it to the end of this guide.
Congratulations! You are now prepared with the basics of slash commands for Red.
However there is a lot we didn't touch on in this guide.
Below this paragraph you'll find a list of resources that you can use to learn more about slash commands.
As always, if you have any questions, feel free to ask in the `Red support server <https://discord.gg/red>`__.

For more information on `Application Commands <https://discord.com/developers/docs/interactions/application-commands>`__ as a whole, please refer to the official Discord documentation.
Discord.py also offers documentation regarding everything discussed on this page.
You can find the documentation `here <https://discordpy.readthedocs.io/en/stable/interactions/api.html>`__.
And lastly, AbstractUmbra has a great write up of `examples <https://gist.github.com/AbstractUmbra/a9c188797ae194e592efe05fa129c57f>`__.

