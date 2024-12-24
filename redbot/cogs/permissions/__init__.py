from redbot.core.bot import Red

from .permissions import Permissions


async def setup(bot: Red) -> None:
    cog = Permissions(bot)
    await cog.initialize()
    # We should add the rules for the Permissions cog and its own commands *before* adding the cog.
    # The actual listeners ought to skip the ones we're passing here.
    await cog._on_cog_add(cog)
    for command in cog.__cog_commands__:
        await cog._on_command_add(command)
    await bot.add_cog(cog)
