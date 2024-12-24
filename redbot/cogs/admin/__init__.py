from redbot.core.bot import Red

from .admin import Admin


async def setup(bot: Red) -> None:
    await bot.add_cog(Admin(bot))
