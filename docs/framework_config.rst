.. config shite

.. role:: python(code)
    :language: python

======
Config
======

Config was introduced in V3 as a way to make data storage easier and safer for all developers regardless of skill level.
It will take some getting used to as the syntax is entirely different from what Red has used before, but we believe
Config will be extremely beneficial to both cog developers and end users in the long run.

.. note:: While config is great for storing data safely, there are some caveats to writing performant code which uses it.
          Make sure to read the section on best practices for more of these details.

***********
Basic Usage
***********

.. code-block:: python

    from redbot.core import Config
    from redbot.core import commands

    class MyCog(commands.Cog):
        def __init__(self):
            self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)

            self.config.register_global(
                foo=True
            )

        @commands.command()
        async def return_some_data(self, ctx):
            await ctx.send(await self.config.foo())

********
Tutorial
********

.. py:currentmodule:: redbot.core.config

This tutorial will walk you through how to use Config.

First, you need to import Config:

.. code-block:: python

    from redbot.core import Config

Then, in the class's :code:`__init__` function, you need to get a config instance:

.. code-block:: python

    class MyCog(commands.Cog):
        def __init__(self):
            self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)

The ``identifier`` in :py:meth:`Config.get_conf` is used to keep your cog's data separate
from that of another cog, and thus should be unique to your cog. For example: if we
have two cogs named :code:`MyCog` and their identifier is different, each will have
its own data without overwriting the other's data.

Note that, as shown by most of the examples in this document, it is also possible to
force registration of a data key before allowing you to get and set data for that key
by adding :code:`force_registration=True` after identifier.
When this is set to :code:`False` (the default), the default value for any key that isn't registered
will be :code:`None`. When this is set to :code:`True` (as shown in this document), attempting
to read from or write to any key that isn't registered will raise an :exc:`AttributeError`.

After we've gotten that, we need to register default values:

.. code-block:: python

    class MyCog(commands.Cog):
        def __init__(self):
            self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
            default_global = {
                "foobar": True,
                "foo": {
                    "bar": True,
                    "baz": False
                }
            }
            default_guild = {
                "blah": [],
                "baz": 1234567890
            }
            self.config.register_global(**default_global)
            self.config.register_guild(**default_guild)

As seen in the example above, we can set up our defaults in dicts and then use those in
the appropriate :code:`register` function. As seen above, there's :py:meth:`Config.register_global`
and :py:meth:`Config.register_guild`, but there's also :py:meth:`Config.register_member`,
:py:meth:`Config.register_role`, :py:meth:`Config.register_user`, and :py:meth:`Config.register_channel`.
Note that :code:`member` stores based on guild id AND the user's id.

Once we have our defaults registered and we have the object, we can now use those values
in various ways:

.. code-block:: python

    @commands.command()
    @commands.admin_or_permissions(manage_guild=True)
    async def setbaz(self, ctx, new_value):
        await self.config.guild(ctx.guild).baz.set(new_value)
        await ctx.send("Value of baz has been changed!")

    @commands.command()
    @commands.is_owner()
    async def setfoobar(self, ctx, new_value):
        await self.config.foobar.set(new_value)

    @commands.command()
    async def checkbaz(self, ctx):
        baz_val = await self.config.guild(ctx.guild).baz()
        await ctx.send("The value of baz is {}".format("True" if baz_val else "False"))

Notice a few things in the above examples:

1. Global doesn't have anything in between :code:`self.config` and the variable.

2. Both the getters and setters need to be awaited because they're coroutines.

3. If you're getting the value, the syntax is::

    self.config.<insert scope here, or nothing if global>.variable_name()

4. If setting, it's::

    self.config.<insert scope here, or nothing if global>.variable_name.set(new_value)

It is also possible to use :code:`async with` syntax to get and set config
values. When entering the statement, the config value is retrieved, and on exit,
it is saved. This puts a safeguard on any code within the :code:`async with`
block such that if it breaks from the block in any way (whether it be from
:code:`return`, :code:`break`, :code:`continue` or an exception), the value will
still be saved.

.. important::

    Only mutable config values can be used in the :code:`async with` statement
    (namely lists or dicts), and they must be modified *in place* for their
    changes to be saved.

Here is an example of the :code:`async with` syntax:

.. code-block:: python

    @commands.command()
    async def addblah(self, ctx, new_blah):
        guild_group = self.config.guild(ctx.guild)
        async with guild_group.blah() as blah:
            blah.append(new_blah)
        await ctx.send("The new blah value has been added!")


.. important::

    Please note that while you have nothing between ``config`` and the variable name for global
    data, you also have the following commands to get data specific to each category.

    * :py:meth:`Config.guild` for guild data which takes an object of type :py:class:`discord.Guild`.
    * :py:meth:`Config.member` which takes :py:class:`discord.Member`.
    * :py:meth:`Config.user` which takes :py:class:`discord.User`.
    * :py:meth:`Config.role` which takes :py:class:`discord.Role`.
    * :py:meth:`Config.channel` which takes :py:class:`discord.abc.GuildChannel` or :py:class:`discord.Thread`.

If you need to wipe data from the config, you want to look at :py:meth:`Group.clear`, or :py:meth:`Config.clear_all`
and similar methods, such as :py:meth:`Config.clear_all_guilds`.

Which one you should use depends on what you want to do.

If you're looking to clear data for a single guild/member/channel/role/user,
you want to use :py:meth:`Group.clear` as that will clear the data only for the
specified thing.

If using :py:meth:`Config.clear_all`, it will reset all data everywhere. 

There are other methods provided to reset data from a particular scope. For
example, :py:meth:`Config.clear_all_guilds` resets all guild data. For member
data, you can clear on both a per-guild and guild-independent basis, see
:py:meth:`Config.clear_all_members` for more info.

**************
Advanced Usage
**************

Config makes it extremely easy to organize data that can easily fit into one of the standard categories (global,
guild, user etc.) but there may come a time when your data does not work with the existing categories. There are now
features within Config to enable developers to work with data how they wish.

This usage guide will cover the following features:

- :py:meth:`Config.init_custom`
- :py:meth:`Config.register_custom`
- :py:meth:`Config.custom`
- :py:meth:`Group.get_raw`
- :py:meth:`Group.set_raw`
- :py:meth:`Group.clear_raw`


Custom Groups
^^^^^^^^^^^^^
While Config has built-in groups for the common discord objects,
sometimes you need a combination of these or your own defined grouping.
Config handles this by allowing you to define custom groups.

Let's start by showing how :py:meth:`Config.custom` can be equivalent to :py:meth:`Config.guild` by modifying the above
Tutorial example.

.. code-block:: python

    from redbot.core import Config, commands


    class MyCog(commands.Cog):
        def __init__(self):
            self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
            default_guild = {
                "blah": [],
                "baz": 1234567890
            }

            # self.config.register_guild(**default_guild)

            self.config.init_custom("CustomGuildGroup", 1)
            self.config.register_custom("CustomGuildGroup", **default_guild)

In the above, we registered the custom group named "CustomGuildGroup" to contain the same defaults
that :code:`self.config.guild` normally would. First, we initialized the group "CustomGuildGroup" to
accept one identifier by calling :py:meth:`Config.init_custom` with the argument :code:`1`. Then we used
:py:meth:`Config.register_custom` to register the default values.

.. important::

    :py:meth:`Config.init_custom` **must** be called prior to using a custom group.


Now let's use this custom group:

.. code-block:: python

    @commands.command()
    async def setbaz(self, ctx, new_value):
        # await self.config.guild(ctx.guild).baz.set(new_value)

        await self.config.custom("CustomGuildGroup", ctx.guild.id).baz.set(new_value)
        await ctx.send("Value of baz has been changed!")

    @commands.command()
    async def checkbaz(self, ctx):
        # baz_val = await self.config.guild(ctx.guild).baz()

        baz_val = await self.config.custom("CustomGuildGroup", ctx.guild.id).baz()
        await ctx.send("The value of baz is {}".format("True" if baz_val else "False"))

Here we used :py:meth:`Config.custom` to access our custom group much like we would have used :py:meth:`Config.guild`.
Since it's a custom group, we need to use :code:`id` attribute of guild to get a unique identifier.

Now let's see an example that uses multiple identifiers:

.. code-block:: python

    from redbot.core import Config, commands


    class ChannelAccess(commands.Cog):
        def __init__(self):
            self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
            default_access = {
                "allowed": False
            }

            self.config.init_custom("ChannelAccess", 2)
            self.config.register_custom("ChannelAccess", **default_access)

        @commands.command()
        @commands.is_owner()
        async def grantaccess(self, ctx, channel: discord.TextChannel, member: discord.Member):
            await self.config.custom("ChannelAccess", channel.id, member.id).allowed.set(True)
            await ctx.send("Member has been granted access to that channel")

        @commands.command()
        async def checkaccess(self, ctx, channel: discord.TextChannel):
            allowed = await self.config.custom("ChannelAccess", channel.id, ctx.author.id).allowed()
            await ctx.send("Your access to this channel is {}".format("Allowed" if allowed else "Denied"))

In the above example, we defined the custom group "ChannelAccess" to accept two identifiers
using :py:meth:`Config.init_custom`. Then, we were able to set the default value for any member's
access to any channel to `False` until the bot owner grants them access.

.. important::

    The ordering of the identifiers matter. :code:`custom("ChannelAccess", channel.id, member.id)` is NOT the same
    as :code:`custom("ChannelAccess", member.id, channel.id)`

Raw Group Access
^^^^^^^^^^^^^^^^

For this example let's suppose that we're creating a cog that allows users to buy and own multiple pets using
the built-in Economy credits::

    from redbot.core import bank
    from redbot.core import Config, commands


    class Pets(commands.Cog):
        def __init__(self):
            self.config = Config.get_conf(self, 1234567890, force_registration=True)

            # Here we'll assign some default costs for the pets
            self.config.register_global(
                dog=100,
                cat=100,
                bird=50
            )
            self.config.register_user(
                pets={}
            )

And now that the cog is set up we'll need to create some commands that allow users to purchase these pets::

    # continued
        @commands.command()
        async def get_pet(self, ctx, pet_type: str, pet_name: str):
            """
            Purchase a pet.

            Pet type must be one of: dog, cat, bird
            """
            # Now we need to determine what the cost of the pet is and
            # if the user has enough credits to purchase it.

            # We will need to use "get_raw"
            try:
                cost = await self.config.get_raw(pet_type)
            except KeyError:
                # KeyError is thrown whenever the data you try to access does not
                # exist in the registered defaults or in the saved data.
                await ctx.send("Bad pet type, try again.")
                return

After we've determined the cost of the pet we need to check if the user has enough credits and then we'll need to
assign a new pet to the user. This is very easily done using the V3 bank API and :py:meth:`Group.set_raw`::

    # continued
            if await bank.can_spend(ctx.author, cost):
                await self.config.user(ctx.author).pets.set_raw(
                    pet_name, value={'cost': cost, 'hunger': 0}
                )

                # this is equivalent to doing the following

                pets = await self.config.user(ctx.author).pets()
                pets[pet_name] = {'cost': cost, 'hunger': 0}
                await self.config.user(ctx.author).pets.set(pets)

Since the pets can get hungry we're gonna need a command that let's pet owners check how hungry their pets are::

    # continued
        @commands.command()
        async def hunger(self, ctx, pet_name: str):
            try:
                hunger = await self.config.user(ctx.author).pets.get_raw(pet_name, 'hunger')
            except KeyError:
                # Remember, this is thrown if something in the provided identifiers
                # is not found in the saved data or the defaults.
                await ctx.send("You don't own that pet!")
                return

            await ctx.send("Your pet has {}/100 hunger".format(hunger))

We're responsible pet owners here, so we've also got to have a way to feed our pets::

    # continued
        @commands.command()
        async def feed(self, ctx, pet_name: str, food: int):
            # This is a bit more complicated because we need to check if the pet is
            # owned first.
            try:
                pet = await self.config.user(ctx.author).pets.get_raw(pet_name)
            except KeyError:
                # If the given pet name doesn't exist in our data
                await ctx.send("You don't own that pet!")
                return

            hunger = pet.get("hunger")

            # Determine the new hunger and make sure it doesn't go negative
            new_hunger = max(hunger - food, 0)

            await self.config.user(ctx.author).pets.set_raw(
                pet_name, 'hunger', value=new_hunger
            )

            # We could accomplish the same thing a slightly different way
            await self.config.user(ctx.author).pets.get_attr(pet_name).hunger.set(new_hunger)

            await ctx.send("Your pet is now at {}/100 hunger!".format(new_hunger)

Of course, if we're less than responsible pet owners, there are consequences::

    #continued
        @commands.command()
        async def adopt(self, ctx, pet_name: str, *, member: discord.Member):
            try:
                pet = await self.config.user(member).pets.get_raw(pet_name)
            except KeyError:
                await ctx.send("That person doesn't own that pet!")
                return

            hunger = pet.get("hunger")
            if hunger < 80:
                await ctx.send("That pet is too well taken care of to be adopted.")
                return

            await self.config.user(member).pets.clear_raw(pet_name)

            # this is equivalent to doing the following

            pets = await self.config.user(member).pets()
            del pets[pet_name]
            await self.config.user(member).pets.set(pets)

            await self.config.user(ctx.author).pets.set_raw(pet_name, value=pet)
            await ctx.send(
                "Your request to adopt this pet has been granted due to "
                "how poorly it was taken care of."
            )


*************
V2 Data Usage
*************
There has been much conversation on how to bring V2 data into V3 and, officially, we recommend that cog developers
make use of the public interface in Config (using the categories as described in these docs) rather than simply
copying and pasting your V2 data into V3. Using Config as recommended will result in a much better experience for
you in the long run and will simplify cog creation and maintenance.

However.

We realize that many of our cog creators have expressed disinterest in writing converters for V2 to V3 style data.
As a result we have opened up config to take standard V2 data and allow cog developers to manipulate it in V3 in
much the same way they would in V2. The following examples will demonstrate how to accomplish this.

.. warning::

    By following this method to use V2 data in V3 you may be at risk of data corruption if your cog is used on a bot
    with multiple shards. USE AT YOUR OWN RISK.

.. code-block:: python

    from redbot.core import Config, commands


    class ExampleCog(commands.Cog):
        def __init__(self):
            self.config = Config.get_conf(self, 1234567890)
            self.config.init_custom("V2", 1)
            self.data = {}

        async def load_data(self):
            self.data = await self.config.custom("V2", "V2").all()

        async def save_data(self):
            await self.config.custom("V2", "V2").set(self.data)


    async def setup(bot):
        cog = ExampleCog()
        await cog.load_data()
        await bot.add_cog(cog)

************************************
Best practices and performance notes
************************************

Config prioritizes being a safe data store without developers needing to
know how end users have configured their bot. 

This does come with some performance costs, so keep the following in mind when choosing to
develop using config

* Config use in events should be kept minimal and should only occur
  after confirming the event needs to interact with config

* Caching frequently used things, especially things used by events, 
  results in faster and less event loop blocking code.

* Only use config's context managers when you intend to modify data.

* While config is a great general use option, it may not always be the right one for you. 
  As a cog developer, even though config doesn't require one,
  you can choose to require a database or store to something such as an sqlite
  database stored within your cog's datapath.


*************
API Reference
*************

.. important::

    Before we begin with the nitty gritty API Reference, you should know that there are tons of working code examples
    inside the bot itself! Simply take a peek inside of the :code:`tests/core/test_config.py` file for examples of using
    Config in all kinds of ways.

.. important::

    When getting, setting or clearing values in Config, all keys are casted to `str` for you. This
    includes keys within a `dict` when one is being set, as well as keys in  nested dictionaries
    within that `dict`. For example::

        >>> config = Config.get_conf(self, identifier=999, force_registration=True)
        >>> config.register_global(foo={})
        >>> await config.foo.set_raw(123, value=True)
        >>> await config.foo()
        {'123': True}
        >>> await config.foo.set({123: True, 456: {789: False}}
        >>> await config.foo()
        {'123': True, '456': {'789': False}}

.. automodule:: redbot.core.config

Config
^^^^^^

.. autoclass:: Config
    :members:

Group
^^^^^

.. autoclass:: Group
    :members:
    :special-members:

Value
^^^^^

.. autoclass:: Value
    :members:
    :special-members: __call__

IdentifierData
^^^^^^^^^^^^^^

.. autoclass:: IdentifierData
    :members:

ConfigCategory
^^^^^^^^^^^^^^

.. autoclass:: ConfigCategory
    :members:
