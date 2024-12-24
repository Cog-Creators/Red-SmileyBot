from redbot.core.bot import Red

from .general import General


async def setup(bot: Red) -> None:
    await bot.add_cog(General(bot))
