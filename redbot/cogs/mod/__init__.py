from redbot.core.bot import Red
from .mod import Mod


async def setup(bot: Red) -> None:
    await bot.add_cog(Mod(bot))
