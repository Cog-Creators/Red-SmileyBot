from redbot.core.bot import Red

from .core import Audio


async def setup(bot: Red) -> None:
    cog = Audio(bot)
    await bot.add_cog(cog)
    cog.start_up_task()
