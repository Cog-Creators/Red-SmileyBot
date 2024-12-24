from redbot.core.bot import Red
from .reports import Reports


async def setup(bot: Red) -> None:
    await bot.add_cog(Reports(bot))
