from redbot.core.bot import Red

from .warnings import Warnings


async def setup(bot: Red) -> None:
    await bot.add_cog(Warnings(bot))
