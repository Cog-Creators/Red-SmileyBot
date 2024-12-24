import discord
import re
from .abc import MixinMeta
from datetime import timedelta
from redbot.core import commands, i18n
from redbot.core.utils.chat_formatting import humanize_timedelta

_ = i18n.Translator("Mod", __file__)


class Slowmode(MixinMeta):
    """
    Commands regarding channel slowmode management.
    """

    @commands.command()
    @commands.guild_only()
    @commands.bot_can_manage_channel()
    @commands.admin_or_can_manage_channel()
    async def slowmode(
        self,
        ctx,
        *,
        interval: commands.TimedeltaConverter(
            minimum=timedelta(seconds=0), maximum=timedelta(hours=6), default_unit="seconds"
        ) = timedelta(seconds=0),
    ):
        """Changes thread's or text channel's slowmode setting.

        Interval can be anything from 0 seconds to 6 hours.
        Use without parameters to disable.
        """
        seconds = interval.total_seconds()
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds > 0:
            await ctx.send(
                _("Slowmode interval is now {interval}.").format(
                    interval=humanize_timedelta(timedelta=interval)
                )
            )
        else:
            await ctx.send(_("Slowmode has been disabled."))
