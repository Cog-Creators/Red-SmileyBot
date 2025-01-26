import math
from pathlib import Path

from typing import List, Tuple

import discord
import lavalink
from red_commons.logging import getLogger

import rapidfuzz
from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import humanize_number

from ...audio_dataclasses import LocalPath, Query
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = getLogger("red.cogs.Audio.cog.Utilities.queue")
_ = Translator("Audio", Path(__file__))


class QueueUtilities(MixinMeta, metaclass=CompositeMetaClass):
    async def _build_queue_page(
        self,
        ctx: commands.Context,
        queue: list,
        player: lavalink.player.Player,
        page_num: int,
    ) -> discord.Embed:
        shuffle = await self.config.guild(ctx.guild).shuffle()
        repeat = await self.config.guild(ctx.guild).repeat()
        autoplay = await self.config.guild(ctx.guild).auto_play()

        queue_num_pages = math.ceil(len(queue) / 10)
        queue_idx_start = (page_num - 1) * 10
        queue_idx_end = queue_idx_start + 10
        if len(player.queue) > 500:
            queue_list = _("__Too many songs in the queue, only showing the first 500__.\n\n")
        else:
            queue_list = ""

        arrow = await self.draw_time(ctx)
        pos = self.format_time(player.position)

        if player.current.is_stream:
            dur = "LIVE"
        else:
            dur = self.format_time(player.current.length)

        query = Query.process_input(player.current, self.local_folder_current_path)
        current_track_description = await self.get_track_description(
            player.current, self.local_folder_current_path
        )
        if query.is_stream:
            queue_list += _("**Currently livestreaming:**\n")
            queue_list += f"{current_track_description}\n"
            queue_list += _("Requested by: **{user}**").format(user=player.current.requester)
            queue_list += f"\n\n{arrow}`{pos}`/`{dur}`\n\n"
        else:
            queue_list += _("Playing: ")
            queue_list += f"{current_track_description}\n"
            queue_list += _("Requested by: **{user}**").format(user=player.current.requester)
            queue_list += f"\n\n{arrow}`{pos}`/`{dur}`\n\n"

        async for i, track in AsyncIter(queue[queue_idx_start:queue_idx_end]).enumerate(
            start=queue_idx_start
        ):
            req_user = track.requester
            track_idx = i + 1
            track_description = await self.get_track_description(
                track, self.local_folder_current_path, shorten=True
            )
            queue_list += f"`{track_idx}.` {track_description}, "
            queue_list += _("requested by **{user}**\n").format(user=req_user)

        embed = discord.Embed(
            colour=await ctx.embed_colour(),
            title=_("Queue for __{guild_name}__").format(guild_name=ctx.guild.name),
            description=queue_list,
        )

        if await self.config.guild(ctx.guild).thumbnail() and player.current.thumbnail:
            embed.set_thumbnail(url=player.current.thumbnail)
        queue_dur = await self.queue_duration(ctx)
        queue_total_duration = self.format_time(queue_dur)
        text = _(
            "Page {page_num}/{total_pages} | {num_tracks} tracks, {num_remaining} remaining\n"
        ).format(
            page_num=humanize_number(page_num),
            total_pages=humanize_number(queue_num_pages),
            num_tracks=len(player.queue),
            num_remaining=queue_total_duration,
        )
        text += (
            _("Auto-Play")
            + ": "
            + ("\N{WHITE HEAVY CHECK MARK}" if autoplay else "\N{CROSS MARK}")
        )
        text += (
            (" | " if text else "")
            + _("Shuffle")
            + ": "
            + ("\N{WHITE HEAVY CHECK MARK}" if shuffle else "\N{CROSS MARK}")
        )
        text += (
            (" | " if text else "")
            + _("Repeat")
            + ": "
            + ("\N{WHITE HEAVY CHECK MARK}" if repeat else "\N{CROSS MARK}")
        )
        embed.set_footer(text=text)
        return embed

    async def _build_queue_search_list(
        self, queue_list: List[lavalink.Track], search_words: str
    ) -> List[Tuple[int, str]]:
        tracks = {}
        async for queue_idx, track in AsyncIter(queue_list).enumerate(start=1):
            if not self.match_url(track.uri):
                query = Query.process_input(track, self.local_folder_current_path)
                if (
                    query.is_local
                    and query.local_track_path is not None
                    and track.title == "Unknown title"
                ):
                    track_title = query.local_track_path.to_string_user()
                else:
                    track_title = "{} - {}".format(track.author, track.title)
            else:
                track_title = track.title

            tracks[queue_idx] = track_title
        search_results = rapidfuzz.process.extract(
            search_words, tracks, limit=50, processor=rapidfuzz.utils.default_process
        )
        search_list = []
        async for title, percent_match, queue_position in AsyncIter(search_results):
            if percent_match > 89:
                search_list.append((queue_position, title))
        return search_list

    async def _build_queue_search_page(
        self, ctx: commands.Context, page_num: int, search_list: List[Tuple[int, str]]
    ) -> discord.Embed:
        search_num_pages = math.ceil(len(search_list) / 10)
        search_idx_start = (page_num - 1) * 10
        search_idx_end = search_idx_start + 10
        track_match = ""
        async for i, track in AsyncIter(search_list[search_idx_start:search_idx_end]).enumerate(
            start=search_idx_start
        ):
            track_idx = i + 1
            if type(track) is str:
                track_location = LocalPath(track, self.local_folder_current_path).to_string_user()
                track_match += "`{}.` **{}**\n".format(track_idx, track_location)
            else:
                track_match += "`{}.` **{}**\n".format(track[0], track[1])
        embed = discord.Embed(
            colour=await ctx.embed_colour(), title=_("Matching Tracks:"), description=track_match
        )
        embed.set_footer(
            text=_("Page {page_num}/{total_pages} | {num_tracks} tracks").format(
                page_num=humanize_number(page_num),
                total_pages=humanize_number(search_num_pages),
                num_tracks=len(search_list),
            )
        )
        return embed
