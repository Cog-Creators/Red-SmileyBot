import asyncio

from redbot.core import commands
from redbot.core.utils.predicates import MessagePredicate

__all__ = ["do_install_agreement"]

REPO_INSTALL_MSG = (
    "You're about to add a 3rd party repository. The creator of Red"
    " and its community have no responsibility for any potential "
    "damage that the content of 3rd party repositories might cause."
    "\n\nBy typing '**I agree**' you declare that you have read and"
    " fully understand the above message. This message won't be "
    "shown again until the next reboot.\n\nYou have **30** seconds"
    " to reply to this message."
)


async def do_install_agreement(ctx: commands.Context):
    downloader = ctx.cog
    if downloader is None or downloader.already_agreed:
        return True

    await ctx.send(REPO_INSTALL_MSG)

    try:
        await ctx.bot.wait_for(
            "message", check=MessagePredicate.equal_to("I agree", ctx), timeout=30
        )
    except asyncio.TimeoutError:
        await ctx.send("Your response has timed out, please try again.")
        return False

    downloader.already_agreed = True
    return True
