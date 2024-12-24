from redbot.core.bot import Red
from .economy import Economy


async def setup(bot: Red) -> None:
    await bot.add_cog(Economy(bot))
