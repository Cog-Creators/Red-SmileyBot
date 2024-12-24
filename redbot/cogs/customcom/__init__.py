from redbot.core.bot import Red

from .customcom import CustomCommands


async def setup(bot: Red) -> None:
    await bot.add_cog(CustomCommands(bot))
