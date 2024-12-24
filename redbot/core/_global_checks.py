"""The checks in this module run on every command."""
from . import commands


def init_global_checks(bot):
    @bot.check_once
    async def check_message_is_eligible_as_command(ctx: commands.Context) -> bool:
        return await ctx.bot.message_eligible_as_command(ctx.message)
