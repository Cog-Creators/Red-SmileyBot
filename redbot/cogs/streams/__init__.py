from redbot.core.bot import Red

from .streams import Streams


async def setup(bot: Red) -> None:
    await bot.add_cog(Streams(bot))
