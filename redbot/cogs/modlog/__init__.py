from redbot.core.bot import Red
from .modlog import ModLog


async def setup(bot: Red) -> None:
    await bot.add_cog(ModLog(bot))
