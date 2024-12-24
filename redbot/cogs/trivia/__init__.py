"""Package for Trivia cog."""
from redbot.core.bot import Red

from .trivia import *
from .session import *
from .log import *


async def setup(bot: Red) -> None:
    """Load Trivia."""
    await bot.add_cog(Trivia(bot))
