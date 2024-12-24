import asyncio
import json
import math
import os
import tarfile
import time

from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from typing import cast

import discord
import lavalink
from red_commons.logging import getLogger

from redbot.core import commands
from redbot.core.commands import UserInputOptional
from redbot.core.data_manager import cog_data_path
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import bold, pagify
from redbot.core.utils.menus import menu
from redbot.core.utils.predicates import MessagePredicate

from ...apis.api_utils import FakePlaylist
from ...apis.playlist_interface import Playlist, create_playlist, delete_playlist, get_all_playlist
from ...audio_dataclasses import LocalPath, Query
from ...converters import ComplexScopeParser, ScopeParser
from ...errors import MissingGuild, TooManyMatches, TrackEnqueueError
from ...utils import PlaylistScope
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass, LazyGreedyConverter, PlaylistConverter

log = getLogger("red.cogs.Audio.cog.Commands.playlist")
_ = Translator("Audio", Path(__file__))


class PlaylistCommands(MixinMeta, metaclass=CompositeMetaClass):
    @commands.group(name="playlist")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.bot_can_react()
    async def command_playlist(self, ctx: commands.Context):
        """Playlist configuration options.

        Scope info:
        ​ ​ ​ ​ **Global**:
        ​ ​ ​ ​ ​ ​ ​ ​ Visible to all users of this bot.
        ​ ​ ​ ​ ​ ​ ​ ​ Only editable by bot owner.
        ​ ​ ​ ​ **Guild**:
        ​ ​ ​ ​ ​ ​ ​ ​ Visible to all users in this guild.
        ​ ​ ​ ​ ​ ​ ​ ​ Editable by bot owner, guild owner, guild admins, guild mods, DJ role and playlist creator.
        ​ ​ ​ ​ **User**:
        ​ ​ ​ ​ ​ ​ ​ ​ Visible to all bot users, if --author is passed.
        ​ ​ ​ ​ ​ ​ ​ ​ Editable by bot owner and the playlist creator.
        """

    @command_playlist.command(
        name="append", usage="<playlist_name_OR_id> <track_name_OR_url> [args]"
    )
    async def command_playlist_append(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        query: LazyGreedyConverter,
        *,
        scope_data: ScopeParser = None,
    ):
        """Add a track URL, playlist link, or quick search to a playlist.

        The track(s) will be appended to the end of the playlist.

        **Usage**:
        ​ ​ ​ ​ `[p]playlist append playlist_name_OR_id track_name_OR_url [args]`

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        **Scope** is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        **Author** can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        **Guild** can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ `[p]playlist append MyGuildPlaylist Hello by Adele`
        ​ ​ ​ ​ `[p]playlist append MyGlobalPlaylist Hello by Adele --scope Global`
        ​ ​ ​ ​ `[p]playlist append MyGlobalPlaylist Hello by Adele --scope Global --Author Draper#6666`
        """
        if self.playlist_api is None:
            return await self.send_embed_msg(
                ctx,
                title=_("Playlists Are Not Available"),
                description=_("The playlist section of Audio is currently unavailable"),
                footer=None if not await self.bot.is_owner(ctx.author) else _("Check your logs."),
            )
        if scope_data is None:
            scope_data = [None, ctx.author, ctx.guild, False]
        (scope, author, guild, specified_user) = scope_data
        if not await self._playlist_check(ctx):
            return
        async with ctx.typing():
            try:
                (playlist, playlist_arg, scope) = await self.get_playlist_match(
                    ctx, playlist_matches, scope, author, guild, specified_user
                )
            except TooManyMatches as e:
                return await self.send_embed_msg(ctx, title=str(e))
            if playlist is None:
                return await self.send_embed_msg(
                    ctx,
                    title=_("Playlist Not Found"),
                    description=_("Could not match '{arg}' to a playlist").format(
                        arg=playlist_arg
                    ),
                )
            if not await self.can_manage_playlist(scope, playlist, ctx, author, guild):
                return
            player = lavalink.get_player(ctx.guild.id)
            to_append = await self.fetch_playlist_tracks(
                ctx, player, Query.process_input(query, self.local_folder_current_path)
            )

            if isinstance(to_append, discord.Message):
                return None

            if not to_append:
                return await self.send_embed_msg(
                    ctx, title=_("Could not find a track matching your query.")
                )
            track_list = playlist.tracks
            current_count = len(track_list)
            to_append_count = len(to_append)
            tracks_obj_list = playlist.tracks_obj
            not_added = 0
            if current_count + to_append_count > 10000:
                to_append = to_append[: 10000 - current_count]
                not_added = to_append_count - len(to_append)
                to_append_count = len(to_append)
            scope_name = self.humanize_scope(
                scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
            )
            appended = 0

            if to_append and to_append_count == 1:
                to = lavalink.Track(to_append[0])
                if to in tracks_obj_list:
                    return await self.send_embed_msg(
                        ctx,
                        title=_("Skipping track"),
                        description=_(
                            "{track} is already in {playlist} (`{id}`) [**{scope}**]."
                        ).format(
                            track=to.title,
                            playlist=playlist.name,
                            id=playlist.id,
                            scope=scope_name,
                        ),
                        footer=_("Playlist limit reached: Could not add track.").format(not_added)
                        if not_added > 0
                        else None,
                    )
                else:
                    appended += 1
            if to_append and to_append_count > 1:
                to_append_temp = []
                async for t in AsyncIter(to_append):
                    to = lavalink.Track(t)
                    if to not in tracks_obj_list:
                        appended += 1
                        to_append_temp.append(t)
                to_append = to_append_temp
            if appended > 0:
                track_list.extend(to_append)
                update = {"tracks": track_list, "url": None}
                await playlist.edit(update)

            if to_append_count == 1 and appended == 1:
                track_title = to_append[0]["info"]["title"]
                return await self.send_embed_msg(
                    ctx,
                    title=_("Track added"),
                    description=_("{track} appended to {playlist} (`{id}`) [**{scope}**].").format(
                        track=track_title, playlist=playlist.name, id=playlist.id, scope=scope_name
                    ),
                )

            desc = _("{num} tracks appended to {playlist} (`{id}`) [**{scope}**].").format(
                num=appended, playlist=playlist.name, id=playlist.id, scope=scope_name
            )
            if to_append_count > appended:
                diff = to_append_count - appended
                desc += _(
                    "\n{existing} {plural} already in the playlist and were skipped."
                ).format(existing=diff, plural=_("tracks are") if diff != 1 else _("track is"))

            embed = discord.Embed(title=_("Playlist Modified"), description=desc)
            await self.send_embed_msg(
                ctx,
                embed=embed,
                footer=_("Playlist limit reached: Could not add track.").format(not_added)
                if not_added > 0
                else None,
            )

    @commands.cooldown(1, 150, commands.BucketType.member)
    @command_playlist.command(
        name="copy", usage="<id_or_name> [args]", cooldown_after_parsing=True
    )
    async def command_playlist_copy(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        *,
        scope_data: ComplexScopeParser = None,
    ):
        """Copy a playlist from one scope to another.

        **Usage**:
        ​ ​ ​ ​ `[p]playlist copy playlist_name_OR_id [args]`

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --from-scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --from-author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --from-guild [guild] **Only the bot owner can use this**

        ​ ​ ​ ​ ​ ​ ​ ​ --to-scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --to-author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --to-guild [guild] **Only the bot owner can use this**

        **Scope** is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        **Author** can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        **Guild** can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ `[p]playlist copy MyGuildPlaylist --from-scope Guild --to-scope Global`
        ​ ​ ​ ​ `[p]playlist copy MyGlobalPlaylist --from-scope Global --to-author Draper#6666 --to-scope User`
        ​ ​ ​ ​ `[p]playlist copy MyPersonalPlaylist --from-scope user --to-author Draper#6666 --to-scope Guild --to-guild Red - Discord Bot`
        """
        if self.playlist_api is None:
            return await self.send_embed_msg(
                ctx,
                title=_("Playlists Are Not Available"),
                description=_("The playlist section of Audio is currently unavailable"),
                footer=None if not await self.bot.is_owner(ctx.author) else _("Check your logs."),
            )
        if scope_data is None:
            scope_data = [
                PlaylistScope.GUILD.value,
                ctx.author,
                ctx.guild,
                False,
                PlaylistScope.GUILD.value,
                ctx.author,
                ctx.guild,
                False,
            ]
        (
            from_scope,
            from_author,
            from_guild,
            specified_from_user,
            to_scope,
            to_author,
            to_guild,
            specified_to_user,
        ) = scope_data
        to_scope = to_scope or PlaylistScope.GUILD.value
        async with ctx.typing():
            try:
                from_playlist, playlist_arg, from_scope = await self.get_playlist_match(
                    ctx, playlist_matches, from_scope, from_author, from_guild, specified_from_user
                )
            except TooManyMatches as e:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(ctx, title=str(e))

            if from_playlist is None:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Playlist Not Found"),
                    description=_("Could not match '{arg}' to a playlist.").format(
                        arg=playlist_arg
                    ),
                )

            temp_playlist = cast(Playlist, FakePlaylist(to_author.id, to_scope))
            if not await self.can_manage_playlist(
                to_scope, temp_playlist, ctx, to_author, to_guild
            ):
                ctx.command.reset_cooldown(ctx)
                return

            to_playlist = await create_playlist(
                ctx,
                self.playlist_api,
                to_scope,
                from_playlist.name,
                from_playlist.url,
                from_playlist.tracks,
                to_author,
                to_guild,
            )
            if to_scope == PlaylistScope.GLOBAL.value:
                to_scope_name = _("the Global")
            elif to_scope == PlaylistScope.USER.value:
                to_scope_name = to_author
            else:
                to_scope_name = to_guild

            if from_scope == PlaylistScope.GLOBAL.value:
                from_scope_name = _("the Global")
            elif from_scope == PlaylistScope.USER.value:
                from_scope_name = from_author
            else:
                from_scope_name = from_guild

            return await self.send_embed_msg(
                ctx,
                title=_("Playlist Copied"),
                description=_(
                    "Playlist {name} (`{from_id}`) copied from {from_scope} to {to_scope} (`{to_id}`)."
                ).format(
                    name=from_playlist.name,
                    from_id=from_playlist.id,
                    from_scope=self.humanize_scope(from_scope, ctx=from_scope_name),
                    to_scope=self.humanize_scope(to_scope, ctx=to_scope_name),
                    to_id=to_playlist.id,
                ),
            )

    @command_playlist.command(name="create", usage="<name> [args]")
    async def command_playlist_create(
        self, ctx: commands.Context, playlist_name: str, *, scope_data: ScopeParser = None
    ):
        """Create an empty playlist.

        **Usage**:
        ​ ​ ​ ​ `[p]playlist create playlist_name [args]`

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        **Scope** is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        **Author** can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        **Guild** can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ `[p]playlist create MyGuildPlaylist`
        ​ ​ ​ ​ `[p]playlist create MyGlobalPlaylist --scope Global`
        ​ ​ ​ ​ `[p]playlist create MyPersonalPlaylist --scope User`
        """
        if self.playlist_api is None:
            return await self.send_embed_msg(
                ctx,
                title=_("Playlists Are Not Available"),
                description=_("The playlist section of Audio is currently unavailable"),
                footer=None if not await self.bot.is_owner(ctx.author) else _("Check your logs."),
            )
        if scope_data is None:
            scope_data = [None, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data
        scope = scope or PlaylistScope.GUILD.value
        temp_playlist = cast(Playlist, FakePlaylist(author.id, scope))
        scope_name = self.humanize_scope(
            scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
        )
        async with ctx.typing():
            if not await self.can_manage_playlist(scope, temp_playlist, ctx, author, guild):
                return
            playlist_name = playlist_name.split(" ")[0].strip('"')[:32]
            if playlist_name.isnumeric():
                return await self.send_embed_msg(
                    ctx,
                    title=_("Invalid Playlist Name"),
                    description=_(
                        "Playlist names must be a single word (up to 32 "
                        "characters) and not numbers only."
                    ),
                )
            playlist = await create_playlist(
                ctx, self.playlist_api, scope, playlist_name, None, None, author, guild
            )
            return await self.send_embed_msg(
                ctx,
                title=_("Playlist Created"),
                description=_("Empty playlist {name} (`{id}`) [**{scope}**] created.").format(
                    name=playlist.name, id=playlist.id, scope=scope_name
                ),
            )

    @command_playlist.command(name="delete", aliases=["del"], usage="<playlist_name_OR_id> [args]")
    async def command_playlist_delete(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        *,
        scope_data: ScopeParser = None,
    ):
        """Delete a saved playlist.

        **Usage**:
        ​ ​ ​ ​ `[p]playlist delete playlist_name_OR_id [args]`

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        **Scope** is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        **Author** can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        **Guild** can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ `[p]playlist delete MyGuildPlaylist`
        ​ ​ ​ ​ `[p]playlist delete MyGlobalPlaylist --scope Global`
        ​ ​ ​ ​ `[p]playlist delete MyPersonalPlaylist --scope User`
        """
        if self.playlist_api is None:
            return await self.send_embed_msg(
                ctx,
                title=_("Playlists Are Not Available"),
                description=_("The playlist section of Audio is currently unavailable"),
                footer=None if not await self.bot.is_owner(ctx.author) else _("Check your logs."),
            )
        if scope_data is None:
            scope_data = [None, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data
        async with ctx.typing():
            try:
                playlist, playlist_arg, scope = await self.get_playlist_match(
                    ctx, playlist_matches, scope, author, guild, specified_user
                )
            except TooManyMatches as e:
                return await self.send_embed_msg(ctx, title=str(e))
            if playlist is None:
                return await self.send_embed_msg(
                    ctx,
                    title=_("Playlist Not Found"),
                    description=_("Could not match '{arg}' to a playlist.").format(
                        arg=playlist_arg
                    ),
                )
            if not await self.can_manage_playlist(scope, playlist, ctx, author, guild):
                return
            scope_name = self.humanize_scope(
                scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
            )
            await delete_playlist(
                self.bot,
                self.playlist_api,
                scope,
                playlist.id,
                guild or ctx.guild,
                author or ctx.author,
            )

            await self.send_embed_msg(
                ctx,
                title=_("Playlist Deleted"),
                description=_("{name} (`{id}`) [**{scope}**] playlist deleted.").format(
                    name=playlist.name, id=playlist.id, scope=scope_name
                ),
            )

    @commands.cooldown(1, 30, commands.BucketType.member)
    @command_playlist.command(
        name="dedupe", usage="<playlist_name_OR_id> [args]", cooldown_after_parsing=True
    )
    async def command_playlist_remdupe(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        *,
        scope_data: ScopeParser = None,
    ):
        """Remove duplicate tracks from a saved playlist.

        **Usage**:
        ​ ​ ​ ​ `[p]playlist dedupe playlist_name_OR_id [args]`

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        **Scope** is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        **Author** can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        **Guild** can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ `[p]playlist dedupe MyGuildPlaylist`
        ​ ​ ​ ​ `[p]playlist dedupe MyGlobalPlaylist --scope Global`
        ​ ​ ​ ​ `[p]playlist dedupe MyPersonalPlaylist --scope User`
        """
        if self.playlist_api is None:
            return await self.send_embed_msg(
                ctx,
                title=_("Playlists Are Not Available"),
                description=_("The playlist section of Audio is currently unavailable"),
                footer=None if not await self.bot.is_owner(ctx.author) else _("Check your logs."),
            )
        async with ctx.typing():
            if scope_data is None:
                scope_data = [None, ctx.author, ctx.guild, False]
            scope, author, guild, specified_user = scope_data

            try:
                playlist, playlist_arg, scope = await self.get_playlist_match(
                    ctx, playlist_matches, scope, author, guild, specified_user
                )
            except TooManyMatches as e:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(ctx, title=str(e))
            scope_name = self.humanize_scope(
                scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
            )
            if playlist is None:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Playlist Not Found"),
                    description=_("Could not match '{arg}' to a playlist.").format(
                        arg=playlist_arg
                    ),
                )
            if not await self.can_manage_playlist(scope, playlist, ctx, author, guild):
                ctx.command.reset_cooldown(ctx)
                return

            track_objects = playlist.tracks_obj
            original_count = len(track_objects)
            unique_tracks = set()
            unique_tracks_add = unique_tracks.add
            track_objects = [
                x for x in track_objects if not (x in unique_tracks or unique_tracks_add(x))
            ]

            tracklist = []
            async for track in AsyncIter(track_objects):
                track_keys = track._info.keys()
                track_values = track._info.values()
                track_id = track.track_identifier
                track_info = {}
                for k, v in zip(track_keys, track_values):
                    track_info[k] = v
                keys = ["track", "info"]
                values = [track_id, track_info]
                track_obj = {}
                for key, value in zip(keys, values):
                    track_obj[key] = value
                tracklist.append(track_obj)

        final_count = len(tracklist)
        if original_count - final_count != 0:
            await playlist.edit({"tracks": tracklist})
            await self.send_embed_msg(
                ctx,
                title=_("Playlist Modified"),
                description=_(
                    "Removed {track_diff} duplicated "
                    "tracks from {name} (`{id}`) [**{scope}**] playlist."
                ).format(
                    name=playlist.name,
                    id=playlist.id,
                    track_diff=original_count - final_count,
                    scope=scope_name,
                ),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title=_("Playlist Has Not Been Modified"),
                description=_(
                    "{name} (`{id}`) [**{scope}**] playlist has no duplicate tracks."
                ).format(name=playlist.name, id=playlist.id, scope=scope_name),
            )

    @command_playlist.command(
        name="download",
        usage="<playlist_name_OR_id> [v2=False] [args]",
        cooldown_after_parsing=True,
    )
    @commands.is_owner()
    @commands.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def command_playlist_download(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        v2: UserInputOptional[bool] = False,
        *,
        scope_data: ScopeParser = None,
    ):
        """Download a copy of a playlist.

        These files can be used with the `[p]playlist upload` command.
        Red v2-compatible playlists can be generated by passing True
        for the v2 variable.

        **Usage**:
        ​ ​ ​ ​ `[p]playlist download playlist_name_OR_id [v2=True_OR_False] [args]`

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        **Scope** is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        **Author** can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        **Guild** can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ `[p]playlist download MyGuildPlaylist True`
        ​ ​ ​ ​ `[p]playlist download MyGlobalPlaylist False --scope Global`
        ​ ​ ​ ​ `[p]playlist download MyPersonalPlaylist --scope User`
        """
        if self.playlist_api is None:
            return await self.send_embed_msg(
                ctx,
                title=_("Playlists Are Not Available"),
                description=_("The playlist section of Audio is currently unavailable"),
                footer=None if not await self.bot.is_owner(ctx.author) else _("Check your logs."),
            )
        if scope_data is None:
            scope_data = [None, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data
        async with ctx.typing():
            try:
                playlist, playlist_arg, scope = await self.get_playlist_match(
                    ctx, playlist_matches, scope, author, guild, specified_user
                )
            except TooManyMatches as e:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(ctx, title=str(e))
            if playlist is None:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Playlist Not Found"),
                    description=_("Could not match '{arg}' to a playlist.").format(
                        arg=playlist_arg
                    ),
                )

            schema = 2
            version = "v3" if v2 is False else "v2"

            if not playlist.tracks:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(ctx, title=_("That playlist has no tracks."))
            if version == "v2":
                v2_valid_urls = ["https://www.youtube.com/watch?v=", "https://soundcloud.com/"]
                song_list = []
                async for track in AsyncIter(playlist.tracks):
                    if track["info"]["uri"].startswith(tuple(v2_valid_urls)):
                        song_list.append(track["info"]["uri"])
                playlist_data = {
                    "author": playlist.author,
                    "link": playlist.url,
                    "playlist": song_list,
                    "name": playlist.name,
                }
                file_name = playlist.name
            else:
                # TODO: Keep new playlists backwards compatible, Remove me in a few releases
                playlist_data = playlist.to_json()
                playlist_songs_backwards_compatible = [
                    track["info"]["uri"] for track in playlist.tracks
                ]
                playlist_data["playlist"] = playlist_songs_backwards_compatible
                playlist_data["link"] = playlist.url
                file_name = playlist.id
            playlist_data.update({"schema": schema, "version": version})
            playlist_data = json.dumps(playlist_data).encode("utf-8")
            to_write = BytesIO()
            to_write.write(playlist_data)
            to_write.seek(0)
            if to_write.getbuffer().nbytes > ctx.guild.filesize_limit - 10000:
                datapath = cog_data_path(raw_name="Audio")
                temp_file = datapath / f"{file_name}.txt"
                temp_tar = datapath / f"{file_name}.tar.gz"
                with temp_file.open("wb") as playlist_file:
                    playlist_file.write(to_write.read())

                with tarfile.open(str(temp_tar), "w:gz") as tar:
                    tar.add(
                        str(temp_file),
                        arcname=str(temp_file.relative_to(datapath)),
                        recursive=False,
                    )
                try:
                    if os.path.getsize(str(temp_tar)) > ctx.guild.filesize_limit - 10000:
                        await ctx.send(_("This playlist is too large to be send in this server."))
                    else:
                        await ctx.send(
                            content=_("Playlist is too large, here is the compressed version."),
                            file=discord.File(str(temp_tar)),
                        )
                except Exception as exc:
                    log.verbose("Failed to send playlist to channel", exc_info=exc)
                temp_file.unlink()
                temp_tar.unlink()
            else:
                await ctx.send(file=discord.File(to_write, filename=f"{file_name}.txt"))
            to_write.close()

    @commands.cooldown(1, 10, commands.BucketType.member)
    @command_playlist.command(
        name="info", usage="<playlist_name_OR_id> [args]", cooldown_after_parsing=True
    )
    async def command_playlist_info(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        *,
        scope_data: ScopeParser = None,
    ):
        """Retrieve information from a saved playlist.

        **Usage**:
        ​ ​ ​ ​ `[p]playlist info playlist_name_OR_id [args]`

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        **Scope** is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        **Author** can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        **Guild** can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ `[p]playlist info MyGuildPlaylist`
        ​ ​ ​ ​ `[p]playlist info MyGlobalPlaylist --scope Global`
        ​ ​ ​ ​ `[p]playlist info MyPersonalPlaylist --scope User`
        """
        if self.playlist_api is None:
            return await self.send_embed_msg(
                ctx,
                title=_("Playlists Are Not Available"),
                description=_("The playlist section of Audio is currently unavailable"),
                footer=None if not await self.bot.is_owner(ctx.author) else _("Check your logs."),
            )
        if scope_data is None:
            scope_data = [None, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data
        async with ctx.typing():
            try:
                playlist, playlist_arg, scope = await self.get_playlist_match(
                    ctx, playlist_matches, scope, author, guild, specified_user
                )
            except TooManyMatches as e:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(ctx, title=str(e))
            scope_name = self.humanize_scope(
                scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
            )

            if playlist is None:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Playlist Not Found"),
                    description=_("Could not match '{arg}' to a playlist.").format(
                        arg=playlist_arg
                    ),
                )
            track_len = len(playlist.tracks)

            msg = "​"
            if track_len > 0:
                spaces = "\N{EN SPACE}" * (len(str(len(playlist.tracks))) + 2)
                async for track_idx, track in AsyncIter(playlist.tracks).enumerate(start=1):
                    query = Query.process_input(
                        track["info"]["uri"], self.local_folder_current_path
                    )
                    if query.is_local:
                        if track["info"]["title"] != "Unknown title":
                            msg += "`{}.` **{} - {}**\n{}{}\n".format(
                                track_idx,
                                track["info"]["author"],
                                track["info"]["title"],
                                spaces,
                                query.to_string_user(),
                            )
                        else:
                            msg += "`{}.` {}\n".format(track_idx, query.to_string_user())
                    else:
                        msg += "`{}.` **[{}]({})**\n".format(
                            track_idx, track["info"]["title"], track["info"]["uri"]
                        )

            else:
                msg = "No tracks."

            if not playlist.url:
                embed_title = _(
                    "Playlist info for {playlist_name} (`{id}`) [**{scope}**]:\n"
                ).format(playlist_name=playlist.name, id=playlist.id, scope=scope_name)
            else:
                embed_title = _(
                    "Playlist info for {playlist_name} (`{id}`) [**{scope}**]:\nURL: {url}"
                ).format(
                    playlist_name=playlist.name, url=playlist.url, id=playlist.id, scope=scope_name
                )

            page_list = []
            pages = list(pagify(msg, delims=["\n"], page_length=2000))
            total_pages = len(pages)
            async for numb, page in AsyncIter(pages).enumerate(start=1):
                embed = discord.Embed(
                    colour=await ctx.embed_colour(), title=embed_title, description=page
                )
                author_obj = self.bot.get_user(playlist.author) or playlist.author or _("Unknown")
                embed.set_footer(
                    text=_("Page {page}/{pages} | Author: {author_name} | {num} track(s)").format(
                        author_name=author_obj, num=track_len, pages=total_pages, page=numb
                    )
                )
                page_list.append(embed)
        await menu(ctx, page_list)

    @commands.cooldown(1, 15, commands.BucketType.guild)
    @command_playlist.command(name="list", usage="[args]", cooldown_after_parsing=True)
    async def command_playlist_list(
        self, ctx: commands.Context, *, scope_data: ScopeParser = None
    ):
        """List saved playlists.

        **Usage**:
        ​ ​ ​ ​ `[p]playlist list [args]`

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        **Scope** is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        **Author** can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        **Guild** can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ `[p]playlist list`
        ​ ​ ​ ​ `[p]playlist list --scope Global`
        ​ ​ ​ ​ `[p]playlist list --scope User`
        """
        if self.playlist_api is None:
            return await self.send_embed_msg(
                ctx,
                title=_("Playlists Are Not Available"),
                description=_("The playlist section of Audio is currently unavailable"),
                footer=None if not await self.bot.is_owner(ctx.author) else _("Check your logs."),
            )
        if scope_data is None:
            scope_data = [None, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data
        async with ctx.typing():
            if scope is None:
                global_matches = await get_all_playlist(
                    scope=PlaylistScope.GLOBAL.value,
                    bot=self.bot,
                    guild=guild,
                    author=author,
                    specified_user=specified_user,
                    playlist_api=self.playlist_api,
                )
                guild_matches = await get_all_playlist(
                    scope=PlaylistScope.GUILD.value,
                    bot=self.bot,
                    guild=guild,
                    author=author,
                    specified_user=specified_user,
                    playlist_api=self.playlist_api,
                )
                user_matches = await get_all_playlist(
                    scope=PlaylistScope.USER.value,
                    bot=self.bot,
                    guild=guild,
                    author=author,
                    specified_user=specified_user,
                    playlist_api=self.playlist_api,
                )
                playlists = [*global_matches, *guild_matches, *user_matches]
                name = None
                if not playlists:
                    ctx.command.reset_cooldown(ctx)
                    return await self.send_embed_msg(
                        ctx,
                        title=_("Playlist Not Found"),
                        description=_("No saved playlists available in this server.").format(
                            scope=name
                        ),
                    )
            else:
                try:
                    playlists = await get_all_playlist(
                        scope=scope,
                        bot=self.bot,
                        guild=guild,
                        author=author,
                        specified_user=specified_user,
                        playlist_api=self.playlist_api,
                    )
                except MissingGuild:
                    ctx.command.reset_cooldown(ctx)
                    return await self.send_embed_msg(
                        ctx,
                        title=_("Missing Arguments"),
                        description=_("You need to specify the Guild ID for the guild to lookup."),
                    )

                if scope == PlaylistScope.GUILD.value:
                    name = f"{guild.name}"
                elif scope == PlaylistScope.USER.value:
                    name = f"{author}"
                else:
                    name = _("Global")

                if not playlists and specified_user:
                    ctx.command.reset_cooldown(ctx)
                    return await self.send_embed_msg(
                        ctx,
                        title=_("Playlist Not Found"),
                        description=_(
                            "No saved playlists for {scope} created by {author}."
                        ).format(scope=name, author=author),
                    )
                elif not playlists:
                    ctx.command.reset_cooldown(ctx)
                    return await self.send_embed_msg(
                        ctx,
                        title=_("Playlist Not Found"),
                        description=_("No saved playlists for {scope}.").format(scope=name),
                    )

            playlist_list = []
            space = "\N{EN SPACE}"
            async for playlist in AsyncIter(playlists):
                playlist_list.append(
                    ("\n" + space * 4).join(
                        (
                            bold(playlist.name),
                            _("ID: {id}").format(id=playlist.id),
                            _("Tracks: {num}").format(num=len(playlist.tracks)),
                            _("Author: {name}").format(
                                name=self.bot.get_user(playlist.author)
                                or playlist.author
                                or _("Unknown")
                            ),
                            _("Scope: {scope}\n").format(
                                scope=self.humanize_scope(playlist.scope)
                            ),
                        )
                    )
                )
            abc_names = sorted(playlist_list, key=str.lower)
            len_playlist_list_pages = math.ceil(len(abc_names) / 5)
            playlist_embeds = []

            async for page_num in AsyncIter(range(1, len_playlist_list_pages + 1)):
                embed = await self._build_playlist_list_page(ctx, page_num, abc_names, name)
                playlist_embeds.append(embed)
        await menu(ctx, playlist_embeds)

    @command_playlist.command(name="queue", usage="<name> [args]", cooldown_after_parsing=True)
    @commands.cooldown(1, 300, commands.BucketType.member)
    async def command_playlist_queue(
        self, ctx: commands.Context, playlist_name: str, *, scope_data: ScopeParser = None
    ):
        """Save the queue to a playlist.

        **Usage**:
        ​ ​ ​ ​ `[p]playlist queue playlist_name [args]`

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        **Scope** is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        **Author** can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        **Guild** can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ `[p]playlist queue MyGuildPlaylist`
        ​ ​ ​ ​ `[p]playlist queue MyGlobalPlaylist --scope Global`
        ​ ​ ​ ​ `[p]playlist queue MyPersonalPlaylist --scope User`
        """
        if self.playlist_api is None:
            return await self.send_embed_msg(
                ctx,
                title=_("Playlists Are Not Available"),
                description=_("The playlist section of Audio is currently unavailable"),
                footer=None if not await self.bot.is_owner(ctx.author) else _("Check your logs."),
            )
        async with ctx.typing():
            if scope_data is None:
                scope_data = [None, ctx.author, ctx.guild, False]
            scope, author, guild, specified_user = scope_data
            scope = scope or PlaylistScope.GUILD.value
            scope_name = self.humanize_scope(
                scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
            )
            temp_playlist = cast(Playlist, FakePlaylist(author.id, scope))
            if not await self.can_manage_playlist(scope, temp_playlist, ctx, author, guild):
                ctx.command.reset_cooldown(ctx)
                return
            playlist_name = playlist_name.split(" ")[0].strip('"')[:32]
            if playlist_name.isnumeric():
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Invalid Playlist Name"),
                    description=_(
                        "Playlist names must be a single word "
                        "(up to 32 characters) and not numbers only."
                    ),
                )
            if not self._player_check(ctx):
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(ctx, title=_("Nothing playing."))

            player = lavalink.get_player(ctx.guild.id)
            if not player.queue:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(ctx, title=_("There's nothing in the queue."))
            tracklist = []
            np_song = self.get_track_json(player, "np")
            tracklist.append(np_song)
            queue_length = len(player.queue)
            to_add = player.queue
            not_added = 0
            if queue_length > 10000:
                to_add = player.queue[:10000]
                not_added = queue_length - 10000

            async for track in AsyncIter(to_add):
                queue_idx = player.queue.index(track)
                track_obj = self.get_track_json(player, queue_idx)
                tracklist.append(track_obj)
                playlist = await create_playlist(
                    ctx, self.playlist_api, scope, playlist_name, None, tracklist, author, guild
                )
        await self.send_embed_msg(
            ctx,
            title=_("Playlist Created"),
            description=_(
                "Playlist {name} (`{id}`) [**{scope}**] "
                "saved from current queue: {num} tracks added."
            ).format(
                name=playlist.name, num=len(playlist.tracks), id=playlist.id, scope=scope_name
            ),
            footer=_("Playlist limit reached: Could not add {} tracks.").format(not_added)
            if not_added > 0
            else None,
        )

    @command_playlist.command(name="remove", usage="<playlist_name_OR_id> <url> [args]")
    async def command_playlist_remove(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        url: str,
        *,
        scope_data: ScopeParser = None,
    ):
        """Remove a track from a playlist by url.

         **Usage**:
        ​ ​ ​ ​ `[p]playlist remove playlist_name_OR_id url [args]`

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        **Scope** is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        **Author** can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        **Guild** can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ `[p]playlist remove MyGuildPlaylist https://www.youtube.com/watch?v=MN3x-kAbgFU`
        ​ ​ ​ ​ `[p]playlist remove MyGlobalPlaylist https://www.youtube.com/watch?v=MN3x-kAbgFU --scope Global`
        ​ ​ ​ ​ `[p]playlist remove MyPersonalPlaylist https://www.youtube.com/watch?v=MN3x-kAbgFU --scope User`
        """
        if self.playlist_api is None:
            return await self.send_embed_msg(
                ctx,
                title=_("Playlists Are Not Available"),
                description=_("The playlist section of Audio is currently unavailable"),
                footer=None if not await self.bot.is_owner(ctx.author) else _("Check your logs."),
            )
        if scope_data is None:
            scope_data = [None, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data
        async with ctx.typing():
            try:
                playlist, playlist_arg, scope = await self.get_playlist_match(
                    ctx, playlist_matches, scope, author, guild, specified_user
                )
            except TooManyMatches as e:
                return await self.send_embed_msg(ctx, title=str(e))
            scope_name = self.humanize_scope(
                scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
            )
            if playlist is None:
                return await self.send_embed_msg(
                    ctx,
                    title=_("Playlist Not Found"),
                    description=_("Could not match '{arg}' to a playlist.").format(
                        arg=playlist_arg
                    ),
                )
            if not await self.can_manage_playlist(scope, playlist, ctx, author, guild):
                return

            track_list = playlist.tracks
            clean_list = [track for track in track_list if url != track["info"]["uri"]]
            if len(track_list) == len(clean_list):
                return await self.send_embed_msg(ctx, title=_("URL not in playlist."))
            del_count = len(track_list) - len(clean_list)
            if not clean_list:
                await delete_playlist(
                    playlist_api=self.playlist_api,
                    bot=self.bot,
                    scope=playlist.scope,
                    playlist_id=playlist.id,
                    guild=guild,
                    author=playlist.author,
                )
                return await self.send_embed_msg(
                    ctx, title=_("No tracks left, removing playlist.")
                )
            update = {"tracks": clean_list, "url": None}
            await playlist.edit(update)
            if del_count > 1:
                await self.send_embed_msg(
                    ctx,
                    title=_("Playlist Modified"),
                    description=_(
                        "{num} entries have been removed "
                        "from the playlist {playlist_name} (`{id}`) [**{scope}**]."
                    ).format(
                        num=del_count,
                        playlist_name=playlist.name,
                        id=playlist.id,
                        scope=scope_name,
                    ),
                )
            else:
                await self.send_embed_msg(
                    ctx,
                    title=_("Playlist Modified"),
                    description=_(
                        "The track has been removed from the playlist: "
                        "{playlist_name} (`{id}`) [**{scope}**]."
                    ).format(playlist_name=playlist.name, id=playlist.id, scope=scope_name),
                )

    @command_playlist.command(
        name="save", usage="<name> <url> [args]", cooldown_after_parsing=True
    )
    @commands.cooldown(1, 60, commands.BucketType.member)
    async def command_playlist_save(
        self,
        ctx: commands.Context,
        playlist_name: str,
        playlist_url: str,
        *,
        scope_data: ScopeParser = None,
    ):
        """Save a playlist from a url.

        **Usage**:
        ​ ​ ​ ​ `[p]playlist save name url [args]`

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        **Scope** is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        **Author** can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        **Guild** can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ `[p]playlist save MyGuildPlaylist https://www.youtube.com/playlist?list=PLx0sYbCqOb8Q_CLZC2BdBSKEEB59BOPUM`
        ​ ​ ​ ​ `[p]playlist save MyGlobalPlaylist https://www.youtube.com/playlist?list=PLx0sYbCqOb8Q_CLZC2BdBSKEEB59BOPUM --scope Global`
        ​ ​ ​ ​ `[p]playlist save MyPersonalPlaylist https://open.spotify.com/playlist/1RyeIbyFeIJVnNzlGr5KkR --scope User`
        """
        if self.playlist_api is None:
            return await self.send_embed_msg(
                ctx,
                title=_("Playlists Are Not Available"),
                description=_("The playlist section of Audio is currently unavailable"),
                footer=None if not await self.bot.is_owner(ctx.author) else _("Check your logs."),
            )
        if scope_data is None:
            scope_data = [None, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data
        scope = scope or PlaylistScope.GUILD.value
        scope_name = self.humanize_scope(
            scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
        )
        async with ctx.typing():
            temp_playlist = cast(Playlist, FakePlaylist(author.id, scope))
            if not await self.can_manage_playlist(scope, temp_playlist, ctx, author, guild):
                return ctx.command.reset_cooldown(ctx)
            playlist_name = playlist_name.split(" ")[0].strip('"')[:32]
            if playlist_name.isnumeric():
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Invalid Playlist Name"),
                    description=_(
                        "Playlist names must be a single word (up to 32 "
                        "characters) and not numbers only."
                    ),
                )
            if not await self._playlist_check(ctx):
                ctx.command.reset_cooldown(ctx)
                return
            player = lavalink.get_player(ctx.guild.id)
            tracklist = await self.fetch_playlist_tracks(
                ctx, player, Query.process_input(playlist_url, self.local_folder_current_path)
            )
            if isinstance(tracklist, discord.Message):
                return None
            if tracklist is not None:
                playlist_length = len(tracklist)
                not_added = 0
                if playlist_length > 10000:
                    tracklist = tracklist[:10000]
                    not_added = playlist_length - 10000

                playlist = await create_playlist(
                    ctx,
                    self.playlist_api,
                    scope,
                    playlist_name,
                    playlist_url,
                    tracklist,
                    author,
                    guild,
                )
                if playlist is not None:
                    return await self.send_embed_msg(
                        ctx,
                        title=_("Playlist Created"),
                        description=_(
                            "Playlist {name} (`{id}`) [**{scope}**] saved: {num} tracks added."
                        ).format(
                            name=playlist.name,
                            num=len(tracklist),
                            id=playlist.id,
                            scope=scope_name,
                        ),
                        footer=_("Playlist limit reached: Could not add {} tracks.").format(
                            not_added
                        )
                        if not_added > 0
                        else None,
                    )
                else:
                    return await self.send_embed_msg(
                        ctx,
                        title=_("Playlist Couldn't be created"),
                        description=_("Unable to create your playlist."),
                    )

    @commands.cooldown(1, 30, commands.BucketType.member)
    @command_playlist.command(
        name="start",
        aliases=["play"],
        usage="<playlist_name_OR_id> [args]",
        cooldown_after_parsing=True,
    )
    async def command_playlist_start(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        *,
        scope_data: ScopeParser = None,
    ):
        """Load a playlist into the queue.

        **Usage**:
        ​ ​ ​ ​` [p]playlist start playlist_name_OR_id [args]`

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        **Scope** is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        **Author** can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        **Guild** can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ `[p]playlist start MyGuildPlaylist`
        ​ ​ ​ ​ `[p]playlist start MyGlobalPlaylist --scope Global`
        ​ ​ ​ ​ `[p]playlist start MyPersonalPlaylist --scope User`
        """
        if self.playlist_api is None:
            return await self.send_embed_msg(
                ctx,
                title=_("Playlists Are Not Available"),
                description=_("The playlist section of Audio is currently unavailable"),
                footer=None if not await self.bot.is_owner(ctx.author) else _("Check your logs."),
            )
        if scope_data is None:
            scope_data = [None, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        if dj_enabled and not await self._can_instaskip(ctx, ctx.author):
            ctx.command.reset_cooldown(ctx)
            await self.send_embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("You need the DJ role to start playing playlists."),
            )
            return False
        async with ctx.typing():
            try:
                playlist, playlist_arg, scope = await self.get_playlist_match(
                    ctx, playlist_matches, scope, author, guild, specified_user
                )
            except TooManyMatches as e:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(ctx, title=str(e))
            if playlist is None:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Playlist Not Found"),
                    description=_("Could not match '{arg}' to a playlist").format(
                        arg=playlist_arg
                    ),
                )

            if not await self._playlist_check(ctx):
                ctx.command.reset_cooldown(ctx)
                return
            jukebox_price = await self.config.guild(ctx.guild).jukebox_price()
            if not await self.maybe_charge_requester(ctx, jukebox_price):
                ctx.command.reset_cooldown(ctx)
                return
            maxlength = await self.config.guild(ctx.guild).maxlength()
            author_obj = self.bot.get_user(ctx.author.id)
            track_len = 0
            try:
                player = lavalink.get_player(ctx.guild.id)
                tracks = playlist.tracks_obj
                empty_queue = not player.queue
                async for track in AsyncIter(tracks):
                    if len(player.queue) >= 10000:
                        continue
                    query = Query.process_input(track, self.local_folder_current_path)
                    if not await self.is_query_allowed(
                        self.config,
                        ctx,
                        f"{track.title} {track.author} {track.uri} " f"{str(query)}",
                        query_obj=query,
                    ):
                        log.debug("Query is not allowed in %r (%s)", ctx.guild.name, ctx.guild.id)
                        continue
                    query = Query.process_input(track.uri, self.local_folder_current_path)
                    if query.is_local:
                        local_path = LocalPath(track.uri, self.local_folder_current_path)
                        if not await self.localtracks_folder_exists(ctx):
                            pass
                        if not local_path.exists() and not local_path.is_file():
                            continue
                    if maxlength > 0 and not self.is_track_length_allowed(track, maxlength):
                        continue
                    track.extras.update(
                        {
                            "enqueue_time": int(time.time()),
                            "vc": player.channel.id,
                            "requester": ctx.author.id,
                        }
                    )
                    player.add(author_obj, track)
                    self.bot.dispatch("red_audio_track_enqueue", player.guild, track, ctx.author)
                    track_len += 1
                player.maybe_shuffle(0 if empty_queue else 1)
                if len(tracks) > track_len:
                    maxlength_msg = _(" {bad_tracks} tracks cannot be queued.").format(
                        bad_tracks=(len(tracks) - track_len)
                    )
                else:
                    maxlength_msg = ""
                if scope == PlaylistScope.GUILD.value:
                    scope_name = f"{guild.name}"
                elif scope == PlaylistScope.USER.value:
                    scope_name = f"{author}"
                else:
                    scope_name = "Global"

                embed = discord.Embed(
                    title=_("Playlist Enqueued"),
                    description=_(
                        "{name} - (`{id}`) [**{scope}**]\nAdded {num} "
                        "tracks to the queue.{maxlength_msg}"
                    ).format(
                        num=track_len,
                        maxlength_msg=maxlength_msg,
                        name=playlist.name,
                        id=playlist.id,
                        scope=scope_name,
                    ),
                )
                await self.send_embed_msg(ctx, embed=embed)
                if not player.current:
                    await player.play()
                return
            except RuntimeError:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Playlist Not Found"),
                    description=_("Playlist {id} does not exist in {scope} scope.").format(
                        id=playlist_arg, scope=self.humanize_scope(scope, the=True)
                    ),
                )
            except MissingGuild:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Missing Arguments"),
                    description=_("You need to specify the Guild ID for the guild to lookup."),
                )
            except TypeError:
                if playlist:
                    return await ctx.invoke(self.command_play, query=playlist.url)

    @commands.cooldown(1, 60, commands.BucketType.member)
    @command_playlist.command(
        name="update", usage="<playlist_name_OR_id> [args]", cooldown_after_parsing=True
    )
    async def command_playlist_update(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        *,
        scope_data: ScopeParser = None,
    ):
        """Updates all tracks in a playlist.

        **Usage**:
        ​ ​ ​ ​ `[p]playlist update playlist_name_OR_id [args]`

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        **Scope** is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        **Author** can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        **Guild** can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ `[p]playlist update MyGuildPlaylist`
        ​ ​ ​ ​ `[p]playlist update MyGlobalPlaylist --scope Global`
        ​ ​ ​ ​ `[p]playlist update MyPersonalPlaylist --scope User`
        """
        if self.playlist_api is None:
            return await self.send_embed_msg(
                ctx,
                title=_("Playlists Are Not Available"),
                description=_("The playlist section of Audio is currently unavailable"),
                footer=None if not await self.bot.is_owner(ctx.author) else _("Check your logs."),
            )
        if scope_data is None:
            scope_data = [None, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data
        embeds = None
        async with ctx.typing():
            try:
                playlist, playlist_arg, scope = await self.get_playlist_match(
                    ctx, playlist_matches, scope, author, guild, specified_user
                )
            except TooManyMatches as e:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(ctx, title=str(e))

            if playlist is None:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Playlist Not Found"),
                    description=_("Could not match '{arg}' to a playlist.").format(
                        arg=playlist_arg
                    ),
                )

            if not await self._playlist_check(ctx):
                ctx.command.reset_cooldown(ctx)
                return
            try:
                if not await self.can_manage_playlist(
                    scope, playlist, ctx, author, guild, bypass=True
                ):
                    return
                if playlist.url or getattr(playlist, "id", 0) == 42069:
                    player = lavalink.get_player(ctx.guild.id)
                    added, removed, playlist = await self._maybe_update_playlist(
                        ctx, player, playlist
                    )
                else:
                    ctx.command.reset_cooldown(ctx)
                    return await self.send_embed_msg(
                        ctx,
                        title=_("Invalid Playlist"),
                        description=_("Custom playlists cannot be updated."),
                    )
            except RuntimeError:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Playlist Not Found"),
                    description=_("Playlist {id} does not exist in {scope} scope.").format(
                        id=playlist_arg, scope=self.humanize_scope(scope, the=True)
                    ),
                )
            except MissingGuild:
                return await self.send_embed_msg(
                    ctx,
                    title=_("Missing Arguments"),
                    description=_("You need to specify the Guild ID for the guild to lookup."),
                )
            else:
                scope_name = self.humanize_scope(
                    scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
                )
                if added or removed:
                    _colour = await ctx.embed_colour()
                    removed_embeds = []
                    added_embeds = []
                    total_added = len(added)
                    total_removed = len(removed)
                    total_pages = math.ceil(total_removed / 10) + math.ceil(total_added / 10)
                    page_count = 0
                    if removed:
                        removed_text = ""
                        async for i, track in AsyncIter(removed).enumerate(start=1):
                            if len(track.title) > 40:
                                track_title = str(track.title).replace("[", "")
                                track_title = "{}...".format((track_title[:40]).rstrip(" "))
                            else:
                                track_title = track.title
                            removed_text += f"`{i}.` **[{track_title}]({track.uri})**\n"
                            if i % 10 == 0 or i == total_removed:
                                page_count += 1
                                embed = discord.Embed(
                                    title=_("Tracks removed"),
                                    colour=_colour,
                                    description=removed_text,
                                )
                                text = _("Page {page_num}/{total_pages}").format(
                                    page_num=page_count, total_pages=total_pages
                                )
                                embed.set_footer(text=text)
                                removed_embeds.append(embed)
                                removed_text = ""
                    if added:
                        added_text = ""
                        async for i, track in AsyncIter(added).enumerate(start=1):
                            if len(track.title) > 40:
                                track_title = str(track.title).replace("[", "")
                                track_title = "{}...".format((track_title[:40]).rstrip(" "))
                            else:
                                track_title = track.title
                            added_text += f"`{i}.` **[{track_title}]({track.uri})**\n"
                            if i % 10 == 0 or i == total_added:
                                page_count += 1
                                embed = discord.Embed(
                                    title=_("Tracks added"), colour=_colour, description=added_text
                                )
                                text = _("Page {page_num}/{total_pages}").format(
                                    page_num=page_count, total_pages=total_pages
                                )
                                embed.set_footer(text=text)
                                added_embeds.append(embed)
                                added_text = ""
                    embeds = removed_embeds + added_embeds
                else:
                    return await self.send_embed_msg(
                        ctx,
                        title=_("Playlist Has Not Been Modified"),
                        description=_("No changes for {name} (`{id}`) [**{scope}**].").format(
                            id=playlist.id, name=playlist.name, scope=scope_name
                        ),
                    )
        if embeds:
            await menu(ctx, embeds)

    @command_playlist.command(name="upload", usage="[args]")
    @commands.is_owner()
    async def command_playlist_upload(
        self, ctx: commands.Context, *, scope_data: ScopeParser = None
    ):
        """Uploads a playlist file as a playlist for the bot.

        V2 and old V3 playlist will be slow.
        V3 Playlist made with `[p]playlist download` will load a lot faster.

        **Usage**:
        ​ ​ ​ ​ `[p]playlist upload [args]`

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        **Scope** is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        **Author** can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        **Guild** can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ `[p]playlist upload`
        ​ ​ ​ ​ `[p]playlist upload --scope Global`
        ​ ​ ​ ​ `[p]playlist upload --scope User`
        """
        if self.playlist_api is None:
            return await self.send_embed_msg(
                ctx,
                title=_("Playlists Are Not Available"),
                description=_("The playlist section of Audio is currently unavailable"),
                footer=None if not await self.bot.is_owner(ctx.author) else _("Check your logs."),
            )
        if scope_data is None:
            scope_data = [None, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data
        scope = scope or PlaylistScope.GUILD.value
        temp_playlist = cast(Playlist, FakePlaylist(author.id, scope))
        async with ctx.typing():
            if not await self.can_manage_playlist(scope, temp_playlist, ctx, author, guild):
                return
            if not await self._playlist_check(ctx):
                return
            player = lavalink.get_player(ctx.guild.id)

            if not ctx.message.attachments:
                await self.send_embed_msg(
                    ctx,
                    title=_(
                        "Please upload the playlist file. Any other message will cancel this "
                        "operation."
                    ),
                )
                try:
                    file_message = await self.bot.wait_for(
                        "message", timeout=30.0, check=MessagePredicate.same_context(ctx)
                    )
                except asyncio.TimeoutError:
                    return await self.send_embed_msg(
                        ctx, title=_("No file detected, try again later.")
                    )
            else:
                file_message = ctx.message
            try:
                file_url = file_message.attachments[0].url
            except IndexError:
                return await self.send_embed_msg(ctx, title=_("Upload cancelled."))
            file_suffix = urlparse(file_url).path.rsplit(".", 1)[1]
            if file_suffix != "txt":
                return await self.send_embed_msg(
                    ctx, title=_("Only Red playlist files can be uploaded.")
                )
            try:
                async with self.session.request("GET", file_url) as r:
                    uploaded_playlist = await r.json(
                        content_type="text/plain", encoding="utf-8", loads=json.loads
                    )
            except UnicodeDecodeError:
                return await self.send_embed_msg(ctx, title=_("Not a valid playlist file."))

            new_schema = uploaded_playlist.get("schema", 1) >= 2
            version = uploaded_playlist.get("version", "v2")

            if new_schema and version == "v3":
                uploaded_playlist_url = uploaded_playlist.get("playlist_url", None)
                track_list = uploaded_playlist.get("tracks", [])
            else:
                uploaded_playlist_url = uploaded_playlist.get("link", None)
                track_list = uploaded_playlist.get("playlist", [])
            if len(track_list) > 10000:
                return await self.send_embed_msg(ctx, title=_("This playlist is too large."))
            uploaded_playlist_name = uploaded_playlist.get(
                "name", (urlparse(file_url).path.split("/")[-1]).rsplit(".", 1)[0]
            )
            try:
                if self.api_interface is not None and (
                    not uploaded_playlist_url
                    or not self.match_yt_playlist(uploaded_playlist_url)
                    or not (
                        await self.api_interface.fetch_track(
                            ctx,
                            player,
                            Query.process_input(
                                uploaded_playlist_url, self.local_folder_current_path
                            ),
                        )
                    )[0].tracks
                ):
                    if version == "v3":
                        return await self._load_v3_playlist(
                            ctx,
                            scope,
                            uploaded_playlist_name,
                            uploaded_playlist_url,
                            track_list,
                            author,
                            guild,
                        )
                    return await self._load_v2_playlist(
                        ctx,
                        track_list,
                        player,
                        uploaded_playlist_url,
                        uploaded_playlist_name,
                        scope,
                        author,
                        guild,
                    )
                return await ctx.invoke(
                    self.command_playlist_save,
                    playlist_name=uploaded_playlist_name,
                    playlist_url=uploaded_playlist_url,
                    scope_data=(scope, author, guild, specified_user),
                )
            except TrackEnqueueError:
                self.update_player_lock(ctx, False)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable to Get Track"),
                    description=_(
                        "I'm unable to get a track from Lavalink node at the moment, try again in a few "
                        "minutes."
                    ),
                )
            except Exception as e:
                self.update_player_lock(ctx, False)
                raise e

    @commands.cooldown(1, 60, commands.BucketType.member)
    @command_playlist.command(
        name="rename", usage="<playlist_name_OR_id> <new_name> [args]", cooldown_after_parsing=True
    )
    async def command_playlist_rename(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        new_name: str,
        *,
        scope_data: ScopeParser = None,
    ):
        """Rename an existing playlist.

        **Usage**:
        ​ ​ ​ ​ `[p]playlist rename playlist_name_OR_id new_name [args]`

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        **Scope** is one of the following:
        ​ ​ ​ ​ Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        **Author** can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        **Guild** can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ `[p]playlist rename MyGuildPlaylist RenamedGuildPlaylist`
        ​ ​ ​ ​ `[p]playlist rename MyGlobalPlaylist RenamedGlobalPlaylist --scope Global`
        ​ ​ ​ ​ `[p]playlist rename MyPersonalPlaylist RenamedPersonalPlaylist --scope User`
        """
        if self.playlist_api is None:
            return await self.send_embed_msg(
                ctx,
                title=_("Playlists Are Not Available"),
                description=_("The playlist section of Audio is currently unavailable"),
                footer=None if not await self.bot.is_owner(ctx.author) else _("Check your logs."),
            )
        if scope_data is None:
            scope_data = [None, ctx.author, ctx.guild, False]
        scope, author, guild, specified_user = scope_data
        async with ctx.typing():
            new_name = new_name.split(" ")[0].strip('"')[:32]
            if new_name.isnumeric():
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Invalid Playlist Name"),
                    description=_(
                        "Playlist names must be a single word (up to 32 "
                        "characters) and not numbers only."
                    ),
                )
            try:
                playlist, playlist_arg, scope = await self.get_playlist_match(
                    ctx, playlist_matches, scope, author, guild, specified_user
                )
            except TooManyMatches as e:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(ctx, title=str(e))
            if playlist is None:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Playlist Not Found"),
                    description=_("Could not match '{arg}' to a playlist.").format(
                        arg=playlist_arg
                    ),
                )
            if not await self.can_manage_playlist(scope, playlist, ctx, author, guild):
                ctx.command.reset_cooldown(ctx)
                return
            scope_name = self.humanize_scope(
                scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
            )
            old_name = playlist.name
            update = {"name": new_name}
            await playlist.edit(update)
            msg = _("'{old}' playlist has been renamed to '{new}' (`{id}`) [**{scope}**]").format(
                old=bold(old_name), new=bold(playlist.name), id=playlist.id, scope=scope_name
            )
            await self.send_embed_msg(ctx, title=_("Playlist Modified"), description=msg)
