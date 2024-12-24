.. V3 Mod log

.. role:: python(code)
    :language: python


=======
Mod log
=======

Mod log has now been separated from Mod for V3.

***********
Basic Usage
***********

.. code-block:: python

    from redbot.core import commands, modlog
    import discord

    class MyCog(commands.Cog):
        @commands.command()
        @commands.admin_or_permissions(ban_members=True)
        async def ban(self, ctx, user: discord.Member, reason: str = None):
            await ctx.guild.ban(user)
            case = await modlog.create_case(
                ctx.bot, ctx.guild, ctx.message.created_at, action_type="ban",
                user=user, moderator=ctx.author, reason=reason
            )
            await ctx.send("Done. It was about time.")


**********************
Registering Case types
**********************

To register case types, use a special ``cog_load()`` method which is called when you add a cog:

.. code-block:: python

    # mycog/mycog.py
    from redbot.core import modlog, commands
    import discord

    class MyCog(commands.Cog):

        async def cog_load(self):
            await self.register_casetypes()

        @staticmethod
        async def register_casetypes():
            # Registering a single casetype
            ban_case = {
                "name": "ban",
                "default_setting": True,
                "image": "\N{HAMMER}",
                "case_str": "Ban",
            }
            try:
                await modlog.register_casetype(**ban_case)
            except RuntimeError:
                pass

            # Registering multiple casetypes
            new_types = [
                {
                    "name": "hackban",
                    "default_setting": True,
                    "image": "\N{BUST IN SILHOUETTE}\N{HAMMER}",
                    "case_str": "Hackban",
                },
                {
                    "name": "kick",
                    "default_setting": True,
                    "image": "\N{WOMANS BOOTS}",
                    "case_str": "Kick",
                }
            ]
            await modlog.register_casetypes(new_types)

.. code-block:: python

    # mycog/__init__.py
    from .mycog import MyCog

    async def setup(bot):
        cog = MyCog()
        await bot.add_cog(cog)

.. important::
    Image should be the emoji you want to represent your case type with.


*************
API Reference
*************

Mod log
=======

.. automodule:: redbot.core.modlog
    :members:
