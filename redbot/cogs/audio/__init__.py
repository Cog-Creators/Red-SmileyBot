from redbot.core.bot import Red

from .cog import Audio


def setup(bot: Red):
    bot.add_cog(Audio(bot))
