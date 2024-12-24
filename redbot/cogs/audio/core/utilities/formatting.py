import math
import re
import time
from pathlib import Path

from typing import List, Optional

import discord
import lavalink
from red_commons.logging import getLogger

from lavalink import NodeNotFound

from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import box, escape

from ...audio_dataclasses import LocalPath, Query
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = getLogger("red.cogs.Audio.cog.Utilities.formatting")
_ = Translator("Audio", Path(__file__))
RE_SQUARE = re.compile(r"[\[\]]")


class FormattingUtilities(MixinMeta, metaclass=CompositeMetaClass):
    async def _genre_search_button_action(
        self, ctx: commands.Context, options: List, emoji: str, page: int, playlist: bool = False
    ) -> str:
        try:
            if emoji == "\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = options[0 + (page * 5)]
            elif emoji == "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = options[1 + (page * 5)]
            elif emoji == "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = options[2 + (page * 5)]
            elif emoji == "\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = options[3 + (page * 5)]
            elif emoji == "\N{DIGIT FIVE}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = options[4 + (page * 5)]
            else:
                search_choice = options[0 + (page * 5)]
        except IndexError:
            search_choice = options[-1]
        if not playlist:
            return list(search_choice.items())[0]
        else:
            return search_choice.get("uri")

    async def _build_genre_search_page(
        self,
        ctx: commands.Context,
        tracks: List,
        page_num: int,
        title: str,
        playlist: bool = False,
    ) -> discord.Embed:
        search_num_pages = math.ceil(len(tracks) / 5)
        search_idx_start = (page_num - 1) * 5
        search_idx_end = search_idx_start + 5
        search_list = ""
        async for i, entry in AsyncIter(tracks[search_idx_start:search_idx_end]).enumerate(
            start=search_idx_start
        ):
            search_track_num = i + 1
            if search_track_num > 5:
                search_track_num = search_track_num % 5
            if search_track_num == 0:
                search_track_num = 5
            if playlist:
                name = "**[{}]({})** - {} {}".format(
                    entry.get("name"), entry.get("url"), str(entry.get("tracks")), _("tracks")
                )
            else:
                name = f"{list(entry.keys())[0]}"
            search_list += f"`{search_track_num}.` {name}\n"

        embed = discord.Embed(
            colour=await ctx.embed_colour(), title=title, description=search_list
        )
        embed.set_footer(
            text=_("Page {page_num}/{total_pages}").format(
                page_num=page_num, total_pages=search_num_pages
            )
        )
        return embed

    async def _search_button_action(
        self, ctx: commands.Context, tracks: List, emoji: str, page: int
    ):
        if not self._player_check(ctx):
            if self.lavalink_connection_aborted:
                msg = _("Connection to Lavalink node has failed")
                description = None
                if await self.bot.is_owner(ctx.author):
                    description = _("Please check your console or logs for details.")
                return await self.send_embed_msg(ctx, title=msg, description=description)
            try:
                await lavalink.connect(
                    ctx.author.voice.channel,
                    self_deaf=await self.config.guild_from_id(ctx.guild.id).auto_deafen(),
                )
            except AttributeError:
                return await self.send_embed_msg(ctx, title=_("Connect to a voice channel first."))
            except NodeNotFound:
                return await self.send_embed_msg(
                    ctx, title=_("Connection to Lavalink node has not yet been established.")
                )
        player = lavalink.get_player(ctx.guild.id)
        player.store("notify_channel", ctx.channel.id)
        guild_data = await self.config.guild(ctx.guild).all()
        if len(player.queue) >= 10000:
            return await self.send_embed_msg(
                ctx, title=_("Unable To Play Tracks"), description=_("Queue size limit reached.")
            )
        if not await self.maybe_charge_requester(ctx, guild_data["jukebox_price"]):
            return
        try:
            if emoji == "\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = tracks[0 + (page * 5)]
            elif emoji == "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = tracks[1 + (page * 5)]
            elif emoji == "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = tracks[2 + (page * 5)]
            elif emoji == "\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = tracks[3 + (page * 5)]
            elif emoji == "\N{DIGIT FIVE}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = tracks[4 + (page * 5)]
            else:
                search_choice = tracks[0 + (page * 5)]
        except IndexError:
            search_choice = tracks[-1]
        if not hasattr(search_choice, "is_local") and getattr(search_choice, "uri", None):
            description = await self.get_track_description(
                search_choice, self.local_folder_current_path
            )
        else:
            search_choice = Query.process_input(search_choice, self.local_folder_current_path)
            if search_choice.is_local:
                if (
                    search_choice.local_track_path.exists()
                    and search_choice.local_track_path.is_dir()
                ):
                    return await ctx.invoke(self.command_search, query=search_choice)
                elif (
                    search_choice.local_track_path.exists()
                    and search_choice.local_track_path.is_file()
                ):
                    search_choice.invoked_from = "localtrack"
            return await ctx.invoke(self.command_play, query=search_choice)

        songembed = discord.Embed(title=_("Track Enqueued"), description=description)
        queue_dur = await self.queue_duration(ctx)
        queue_total_duration = self.format_time(queue_dur)
        before_queue_length = len(player.queue)
        query = Query.process_input(search_choice, self.local_folder_current_path)
        if not await self.is_query_allowed(
            self.config,
            ctx,
            f"{search_choice.title} {search_choice.author} {search_choice.uri} {str(query)}",
            query_obj=query,
        ):
            log.debug("Query is not allowed in %r (%s)", ctx.guild.name, ctx.guild.id)
            self.update_player_lock(ctx, False)
            return await self.send_embed_msg(
                ctx, title=_("This track is not allowed in this server.")
            )
        elif guild_data["maxlength"] > 0:
            if self.is_track_length_allowed(search_choice, guild_data["maxlength"]):
                search_choice.extras.update(
                    {
                        "enqueue_time": int(time.time()),
                        "vc": player.channel.id,
                        "requester": ctx.author.id,
                    }
                )
                player.add(ctx.author, search_choice)
                player.maybe_shuffle()
                self.bot.dispatch(
                    "red_audio_track_enqueue", player.guild, search_choice, ctx.author
                )
            else:
                return await self.send_embed_msg(ctx, title=_("Track exceeds maximum length."))
        else:
            search_choice.extras.update(
                {
                    "enqueue_time": int(time.time()),
                    "vc": player.channel.id,
                    "requester": ctx.author.id,
                }
            )
            player.add(ctx.author, search_choice)
            player.maybe_shuffle()
            self.bot.dispatch("red_audio_track_enqueue", player.guild, search_choice, ctx.author)

        if not guild_data["shuffle"] and queue_dur > 0:
            songembed.set_footer(
                text=_("{time} until track playback: #{position} in queue").format(
                    time=queue_total_duration, position=before_queue_length + 1
                )
            )

        if not player.current:
            await player.play()
        return await self.send_embed_msg(ctx, embed=songembed)

    async def _format_search_options(self, search_choice):
        query = Query.process_input(search_choice, self.local_folder_current_path)
        description = await self.get_track_description(
            search_choice, self.local_folder_current_path
        )
        return description, query

    async def _build_search_page(
        self, ctx: commands.Context, tracks: List, page_num: int
    ) -> discord.Embed:
        search_num_pages = math.ceil(len(tracks) / 5)
        search_idx_start = (page_num - 1) * 5
        search_idx_end = search_idx_start + 5
        search_list = ""
        command = ctx.invoked_with
        folder = False
        async for i, track in AsyncIter(tracks[search_idx_start:search_idx_end]).enumerate(
            start=search_idx_start
        ):
            search_track_num = i + 1
            if search_track_num > 5:
                search_track_num = search_track_num % 5
            if search_track_num == 0:
                search_track_num = 5
            try:
                query = Query.process_input(track.uri, self.local_folder_current_path)
                if query.is_local:
                    search_list += "`{0}.` **{1}**\n[{2}]\n".format(
                        search_track_num,
                        discord.utils.escape_markdown(track.title),
                        discord.utils.escape_markdown(
                            LocalPath(track.uri, self.local_folder_current_path).to_string_user()
                        ),
                    )
                else:
                    search_list += "`{0}.` **[{1}]({2})**\n".format(
                        search_track_num, discord.utils.escape_markdown(track.title), track.uri
                    )
            except AttributeError:
                track = Query.process_input(track, self.local_folder_current_path)
                if track.is_local and command != "search":
                    search_list += "`{}.` **{}**\n".format(
                        search_track_num, discord.utils.escape_markdown(track.to_string_user())
                    )
                    if track.is_album:
                        folder = True
                else:
                    search_list += "`{}.` **{}**\n".format(
                        search_track_num, discord.utils.escape_markdown(track.to_string_user())
                    )
        if hasattr(tracks[0], "uri") and hasattr(tracks[0], "track_identifier"):
            title = _("Tracks Found:")
            footer = _("search results")
        elif folder:
            title = _("Folders Found:")
            footer = _("local folders")
        else:
            title = _("Files Found:")
            footer = _("local tracks")
        embed = discord.Embed(
            colour=await ctx.embed_colour(), title=title, description=search_list
        )
        embed.set_footer(
            text=(_("Page {page_num}/{total_pages}") + " | {num_results} {footer}").format(
                page_num=page_num,
                total_pages=search_num_pages,
                num_results=len(tracks),
                footer=footer,
            )
        )
        return embed

    async def get_track_description(
        self, track, local_folder_current_path, shorten=False
    ) -> Optional[str]:
        """Get the user facing formatted track name."""
        string = None
        if track and getattr(track, "uri", None):
            query = Query.process_input(track.uri, local_folder_current_path)
            if query.is_local or "localtracks/" in track.uri:
                if (
                    hasattr(track, "title")
                    and track.title != "Unknown title"
                    and hasattr(track, "author")
                    and track.author != "Unknown artist"
                ):
                    if shorten:
                        string = f"{track.author} - {track.title}"
                        if len(string) > 40:
                            string = f"{(string[:40]).rstrip(' ')}..."
                        string = f'**{escape(f"{string}", formatting=True)}**'
                    else:
                        string = (
                            f'**{escape(f"{track.author} - {track.title}", formatting=True)}**'
                            + escape(f"\n{query.to_string_user()} ", formatting=True)
                        )
                elif hasattr(track, "title") and track.title != "Unknown title":
                    if shorten:
                        string = f"{track.title}"
                        if len(string) > 40:
                            string = f"{(string[:40]).rstrip(' ')}..."
                        string = f'**{escape(f"{string}", formatting=True)}**'
                    else:
                        string = f'**{escape(f"{track.title}", formatting=True)}**' + escape(
                            f"\n{query.to_string_user()} ", formatting=True
                        )
                else:
                    string = query.to_string_user()
                    if shorten and len(string) > 40:
                        string = f"{(string[:40]).rstrip(' ')}..."
                    string = f'**{escape(f"{string}", formatting=True)}**'
            else:
                if track.is_stream:
                    icy = await self.icyparser(track.uri)
                    if icy:
                        title = icy
                    else:
                        title = f"{track.title} - {track.author}"
                elif track.author.lower() not in track.title.lower():
                    title = f"{track.title} - {track.author}"
                else:
                    title = track.title
                string = f"{title}"
                if shorten and len(string) > 40:
                    string = f"{(string[:40]).rstrip(' ')}..."
                    string = re.sub(RE_SQUARE, "", string)
                string = f"**[{escape(string, formatting=True)}]({track.uri}) **"
        elif hasattr(track, "to_string_user") and track.is_local:
            string = track.to_string_user() + " "
            if shorten and len(string) > 40:
                string = f"{(string[:40]).rstrip(' ')}..."
            string = f'**{escape(f"{string}", formatting=True)}**'
        return string

    async def get_track_description_unformatted(
        self, track, local_folder_current_path
    ) -> Optional[str]:
        """Get the user facing unformatted track name."""
        if track and hasattr(track, "uri"):
            query = Query.process_input(track.uri, local_folder_current_path)
            if query.is_local or "localtracks/" in track.uri:
                if (
                    hasattr(track, "title")
                    and track.title != "Unknown title"
                    and hasattr(track, "author")
                    and track.author != "Unknown artist"
                ):
                    return f"{track.author} - {track.title}"
                elif hasattr(track, "title") and track.title != "Unknown title":
                    return f"{track.title}"
                else:
                    return query.to_string_user()
            else:
                if track.is_stream:
                    icy = await self.icyparser(track.uri)
                    if icy:
                        title = icy
                    else:
                        title = f"{track.title} - {track.author}"
                elif track.author.lower() not in track.title.lower():
                    title = f"{track.title} - {track.author}"
                else:
                    title = track.title
                return f"{title}"
        elif hasattr(track, "to_string_user") and track.is_local:
            return track.to_string_user() + " "
        return None

    def format_playlist_picker_data(self, pid, pname, ptracks, pauthor, scope) -> str:
        """Format the values into a prettified codeblock."""
        author = self.bot.get_user(pauthor) or pauthor or _("Unknown")
        line = _(
            " - Name:   <{pname}>\n"
            " - Scope:  < {scope} >\n"
            " - ID:     < {pid} >\n"
            " - Tracks: < {ptracks} >\n"
            " - Author: < {author} >\n\n"
        ).format(
            pname=pname, scope=self.humanize_scope(scope), pid=pid, ptracks=ptracks, author=author
        )
        return box(line, lang="md")

    async def draw_time(self, ctx) -> str:
        player = lavalink.get_player(ctx.guild.id)
        paused = player.paused
        pos = player.position or 1
        dur = getattr(player.current, "length", player.position or 1)
        sections = 12
        loc_time = round((pos / dur if dur != 0 else pos) * sections)
        bar = "\N{BOX DRAWINGS HEAVY HORIZONTAL}"
        seek = "\N{RADIO BUTTON}"
        if paused:
            msg = "\N{DOUBLE VERTICAL BAR}\N{VARIATION SELECTOR-16}"
        else:
            msg = "\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}"
        for i in range(sections):
            if i == loc_time:
                msg += seek
            else:
                msg += bar
        return msg
