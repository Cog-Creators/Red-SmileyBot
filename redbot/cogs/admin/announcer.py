import asyncio
from typing import Optional

import discord
from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import humanize_list, inline

_ = Translator("Announcer", __file__)


class Announcer:
    def __init__(self, ctx: commands.Context, message: str, config=None):
        """
        :param ctx:
        :param message:
        :param config: Used to determine channel overrides
        """
        self.ctx = ctx
        self.message = message
        self.config = config

        self.active = None

    def start(self):
        """
        Starts an announcement.
        :return:
        """
        if self.active is None:
            self.active = True
            asyncio.create_task(self.announcer())

    def cancel(self):
        """
        Cancels a running announcement.
        :return:
        """
        self.active = False

    async def _get_announce_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        if await self.ctx.bot.cog_disabled_in_guild_raw("Admin", guild.id):
            return
        channel_id = await self.config.guild(guild).announce_channel()
        return guild.get_channel(channel_id)

    async def announcer(self):
        guild_list = self.ctx.bot.guilds
        failed = []
        async for g in AsyncIter(guild_list, delay=0.5):
            if not self.active:
                return

            channel = await self._get_announce_channel(g)

            if channel:
                if channel.permissions_for(g.me).send_messages:
                    try:
                        await channel.send(self.message)
                    except discord.Forbidden:
                        failed.append(str(g.id))
                else:
                    failed.append(str(g.id))

        if failed:
            msg = (
                _("I could not announce to the following server: ")
                if len(failed) == 1
                else _("I could not announce to the following servers: ")
            )
            msg += humanize_list(tuple(map(inline, failed)))
            await self.ctx.bot.send_to_owners(msg)
        self.active = False
