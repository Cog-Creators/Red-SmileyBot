from redbot.core.bot import Red

from .downloader import Downloader


async def setup(bot: Red) -> None:
    cog = Downloader(bot)
    await bot.add_cog(cog)
    cog.create_init_task()
