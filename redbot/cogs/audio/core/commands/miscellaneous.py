import datetime
import heapq
import math
import random
from pathlib import Path

import discord
import lavalink
from red_commons.logging import getLogger

from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import humanize_number, pagify
from redbot.core.utils.menus import menu

from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = getLogger("red.cogs.Audio.cog.Commands.miscellaneous")
_ = Translator("Audio", Path(__file__))


class MiscellaneousCommands(MixinMeta, metaclass=CompositeMetaClass):
    @commands.command(name="sing")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_sing(self, ctx: commands.Context):
        """Make Red sing one of her songs."""
        ids = (
            "zGTkAVsrfg8",
            "cGMWL8cOeAU",
            "vFrjMq4aL-g",
            "WROI5WYBU_A",
            "41tIUr_ex3g",
            "f9O2Rjn1azc",
        )
        url = f"https://www.youtube.com/watch?v={random.choice(ids)}"
        await ctx.invoke(self.command_play, query=url)

    @commands.command(name="audiostats")
    @commands.guild_only()
    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True)
    @commands.bot_can_react()
    async def command_audiostats(self, ctx: commands.Context):
        """Audio stats."""
        server_num = len(lavalink.active_players())
        total_num = len(lavalink.all_connected_players())

        msg = ""
        async for p in AsyncIter(lavalink.all_connected_players()):
            connect_dur = (
                self.get_time_string(
                    int(
                        (
                            datetime.datetime.now(datetime.timezone.utc) - p.connected_at
                        ).total_seconds()
                    )
                )
                or "0s"
            )
            try:
                if not p.current:
                    raise AttributeError
                current_title = await self.get_track_description(
                    p.current, self.local_folder_current_path
                )
                msg += f"{p.guild.name} [`{connect_dur}`]: {current_title}\n"
            except AttributeError:
                msg += "{} [`{}`]: **{}**\n".format(
                    p.guild.name, connect_dur, _("Nothing playing.")
                )

        if total_num == 0:
            return await self.send_embed_msg(ctx, title=_("Not connected anywhere."))
        servers_embed = []
        pages = 1
        for page in pagify(msg, delims=["\n"], page_length=1500):
            em = discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("Playing in {num}/{total} servers:").format(
                    num=humanize_number(server_num), total=humanize_number(total_num)
                ),
                description=page,
            )
            em.set_footer(
                text=_("Page {}/{}").format(
                    humanize_number(pages), humanize_number((math.ceil(len(msg) / 1500)))
                )
            )
            pages += 1
            servers_embed.append(em)

        await menu(ctx, servers_embed)

    @commands.command(name="percent")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_percent(self, ctx: commands.Context):
        """Queue percentage."""
        if not self._player_check(ctx):
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))
        player = lavalink.get_player(ctx.guild.id)
        queue_tracks = player.queue
        requesters = {"total": 0, "users": {}}

        async def _usercount(req_user_handle):
            if req_user_handle in requesters["users"]:
                requesters["users"][req_user_handle]["songcount"] += 1
                requesters["total"] += 1
            else:
                requesters["users"][req_user_handle] = {}
                requesters["users"][req_user_handle]["songcount"] = 1
                requesters["total"] += 1

        async for track in AsyncIter(queue_tracks):
            req_user_handle = str(track.requester)
            await _usercount(req_user_handle)

        try:
            req_user_handle = str(player.current.requester)
            await _usercount(req_user_handle)
        except AttributeError:
            return await self.send_embed_msg(ctx, title=_("There's nothing in the queue."))

        async for req_user_handle in AsyncIter(requesters["users"]):
            percentage = float(requesters["users"][req_user_handle]["songcount"]) / float(
                requesters["total"]
            )
            requesters["users"][req_user_handle]["percent"] = round(percentage * 100, 1)

        top_queue_users = heapq.nlargest(
            20,
            [
                (x, requesters["users"][x][y])
                for x in requesters["users"]
                for y in requesters["users"][x]
                if y == "percent"
            ],
            key=lambda x: x[1],
        )
        queue_user = ["{}: {:g}%".format(x[0], x[1]) for x in top_queue_users]
        queue_user_list = "\n".join(queue_user)
        await self.send_embed_msg(
            ctx, title=_("Queued and playing tracks:"), description=queue_user_list
        )
