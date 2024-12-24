import asyncio
import contextlib
import datetime
import functools
import json
import re
import struct
from pathlib import Path
from typing import Any, Final, Mapping, MutableMapping, Pattern, Union, cast

import discord
import lavalink
from red_commons.logging import getLogger

from redbot.core import bank, commands
from redbot.core.commands import Context
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter, can_user_send_messages_in
from redbot.core.utils.chat_formatting import humanize_number

from ...apis.playlist_interface import get_all_playlist_for_migration23
from ...utils import PlaylistScope
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass, DataReader

log = getLogger("red.cogs.Audio.cog.Utilities.miscellaneous")
_ = Translator("Audio", Path(__file__))
_RE_TIME_CONVERTER: Final[Pattern] = re.compile(r"(?:(\d+):)?([0-5]?[0-9]):([0-5][0-9])")
_prefer_lyrics_cache = {}


class MiscellaneousUtilities(MixinMeta, metaclass=CompositeMetaClass):
    async def _clear_react(
        self, message: discord.Message, emoji: MutableMapping = None
    ) -> asyncio.Task:
        """Non blocking version of clear_react."""
        return asyncio.create_task(self.clear_react(message, emoji))

    async def maybe_charge_requester(self, ctx: commands.Context, jukebox_price: int) -> bool:
        jukebox = await self.config.guild(ctx.guild).jukebox()
        if jukebox and not await self._can_instaskip(ctx, ctx.author):
            can_spend = await bank.can_spend(ctx.author, jukebox_price)
            if can_spend:
                await bank.withdraw_credits(ctx.author, jukebox_price)
            else:
                credits_name = await bank.get_currency_name(ctx.guild)
                bal = await bank.get_balance(ctx.author)
                await self.send_embed_msg(
                    ctx,
                    title=_("Not enough {currency}").format(currency=credits_name),
                    description=_(
                        "{required_credits} {currency} required, but you have {bal}."
                    ).format(
                        currency=credits_name,
                        required_credits=humanize_number(jukebox_price),
                        bal=humanize_number(bal),
                    ),
                )
            return can_spend
        else:
            return True

    async def send_embed_msg(
        self, ctx: commands.Context, author: Mapping[str, str] = None, **kwargs
    ) -> discord.Message:
        colour = kwargs.get("colour") or kwargs.get("color") or await self.bot.get_embed_color(ctx)
        title = kwargs.get("title") or None
        _type = kwargs.get("type", "rich") or "rich"
        url = kwargs.get("url") or None
        description = kwargs.get("description") or None
        timestamp = kwargs.get("timestamp")
        footer = kwargs.get("footer")
        thumbnail = kwargs.get("thumbnail")
        contents = dict(title=title, type=_type, url=url, description=description)
        if hasattr(kwargs.get("embed"), "to_dict"):
            embed = kwargs.get("embed")
            if embed is not None:
                embed = embed.to_dict()
        else:
            embed = {}
        colour = embed.get("color") if embed.get("color") else colour
        contents.update(embed)
        embed = discord.Embed.from_dict(contents)
        embed.color = colour
        if timestamp and isinstance(timestamp, datetime.datetime):
            embed.timestamp = timestamp
        else:
            embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
        if footer:
            embed.set_footer(text=footer)
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        if author:
            name = author.get("name")
            url = author.get("url")
            if name and url:
                embed.set_author(name=name, icon_url=url)
            elif name:
                embed.set_author(name=name)
        return await ctx.send(embed=embed)

    def _has_notify_perms(
        self,
        channel: Union[
            discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread
        ],
    ) -> bool:
        perms = channel.permissions_for(channel.guild.me)
        return all((can_user_send_messages_in(channel.guild.me, channel), perms.embed_links))

    async def maybe_run_pending_db_tasks(self, ctx: commands.Context) -> None:
        if self.api_interface is not None:
            await self.api_interface.run_tasks(ctx)

    async def _close_database(self) -> None:
        if self.api_interface is not None:
            await self.api_interface.run_all_pending_tasks()
            self.api_interface.close()

    async def _check_api_tokens(self) -> MutableMapping:
        spotify = await self.bot.get_shared_api_tokens("spotify")
        youtube = await self.bot.get_shared_api_tokens("youtube")
        return {
            "spotify_client_id": spotify.get("client_id", ""),
            "spotify_client_secret": spotify.get("client_secret", ""),
            "youtube_api": youtube.get("api_key", ""),
        }

    async def update_external_status(self) -> bool:
        external = await self.config.use_external_lavalink()
        if not external:
            if self.managed_node_controller is not None:
                await self.managed_node_controller.shutdown()
            await self.config.use_external_lavalink.set(True)
            return True
        else:
            return False

    def rsetattr(self, obj, attr, val) -> None:
        pre, _, post = attr.rpartition(".")
        setattr(self.rgetattr(obj, pre) if pre else obj, post, val)

    def rgetattr(self, obj, attr, *args) -> Any:
        def _getattr(obj2, attr2):
            return getattr(obj2, attr2, *args)

        return functools.reduce(_getattr, [obj] + attr.split("."))

    async def remove_react(
        self,
        message: discord.Message,
        react_emoji: Union[discord.Emoji, discord.Reaction, discord.PartialEmoji, str],
        react_user: discord.abc.User,
    ) -> None:
        with contextlib.suppress(discord.HTTPException):
            await message.remove_reaction(react_emoji, react_user)

    async def clear_react(self, message: discord.Message, emoji: MutableMapping = None) -> None:
        try:
            await message.clear_reactions()
        except discord.Forbidden:
            if not emoji:
                return
            with contextlib.suppress(discord.HTTPException):
                async for key in AsyncIter(emoji.values(), delay=0.2):
                    await message.remove_reaction(key, self.bot.user)
        except discord.HTTPException:
            return

    def get_track_json(
        self,
        player: lavalink.Player,
        position: Union[int, str] = None,
        other_track: lavalink.Track = None,
    ) -> MutableMapping:
        if position == "np":
            queued_track = player.current
        elif position is None:
            queued_track = other_track
        else:
            queued_track = player.queue[position]
        return self.track_to_json(queued_track)

    def track_to_json(self, track: lavalink.Track) -> MutableMapping:
        track_keys = track._info.keys()
        track_values = track._info.values()
        track_id = track.track_identifier
        track_info = {}
        for k, v in zip(track_keys, track_values):
            track_info[k] = v
        keys = ["track", "info", "extras"]
        values = [track_id, track_info]
        track_obj = {}
        for key, value in zip(keys, values):
            track_obj[key] = value
        return track_obj

    def time_convert(self, length: Union[int, str]) -> int:
        if isinstance(length, int):
            return length

        match = _RE_TIME_CONVERTER.match(length)
        if match is not None:
            hr = int(match.group(1)) if match.group(1) else 0
            mn = int(match.group(2)) if match.group(2) else 0
            sec = int(match.group(3)) if match.group(3) else 0
            pos = sec + (mn * 60) + (hr * 3600)
            return pos
        else:
            try:
                return int(length)
            except ValueError:
                return 0

    async def queue_duration(self, ctx: commands.Context) -> int:
        player = lavalink.get_player(ctx.guild.id)
        dur = [
            i.length
            async for i in AsyncIter(player.queue, steps=50).filter(lambda x: not x.is_stream)
        ]
        queue_dur = sum(dur)
        if not player.queue:
            queue_dur = 0
        try:
            if not player.current.is_stream:
                remain = player.current.length - player.position
            else:
                remain = 0
        except AttributeError:
            remain = 0
        queue_total_duration = remain + queue_dur
        return queue_total_duration

    async def track_remaining_duration(self, ctx: commands.Context) -> int:
        player = lavalink.get_player(ctx.guild.id)
        if not player.current:
            return 0
        try:
            if not player.current.is_stream:
                remain = player.current.length - player.position
            else:
                remain = 0
        except AttributeError:
            remain = 0
        return remain

    def get_time_string(self, seconds: int) -> str:
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)

        if d > 0:
            msg = "{0}d {1}h"
        elif d == 0 and h > 0:
            msg = "{1}h {2}m"
        elif d == 0 and h == 0 and m > 0:
            msg = "{2}m {3}s"
        elif d == 0 and h == 0 and m == 0 and s > 0:
            msg = "{3}s"
        else:
            msg = ""
        return msg.format(d, h, m, s)

    def format_time(self, time: int) -> str:
        """Formats the given time into DD:HH:MM:SS"""
        seconds = time / 1000
        days, seconds = divmod(seconds, 24 * 60 * 60)
        hours, seconds = divmod(seconds, 60 * 60)
        minutes, seconds = divmod(seconds, 60)
        day = ""
        hour = ""
        if days:
            day = "%02d:" % days
        if hours or day:
            hour = "%02d:" % hours
        minutes = "%02d:" % minutes
        sec = "%02d" % seconds
        return f"{day}{hour}{minutes}{sec}"

    async def get_lyrics_status(self, ctx: Context) -> bool:
        global _prefer_lyrics_cache
        prefer_lyrics = _prefer_lyrics_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).prefer_lyrics()
        )
        return prefer_lyrics

    async def data_schema_migration(self, from_version: int, to_version: int) -> None:
        database_entries = []
        time_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        if from_version == to_version:
            return
        if from_version < 2 <= to_version:
            all_guild_data = await self.config.all_guilds()
            all_playlist = {}
            async for guild_id, guild_data in AsyncIter(all_guild_data.items()):
                temp_guild_playlist = guild_data.pop("playlists", None)
                if temp_guild_playlist:
                    guild_playlist = {}
                    async for count, (name, data) in AsyncIter(
                        temp_guild_playlist.items()
                    ).enumerate(start=1000):
                        if not data or not name:
                            continue
                        playlist = {"id": count, "name": name, "guild": int(guild_id)}
                        playlist.update(data)
                        guild_playlist[str(count)] = playlist

                        tracks_in_playlist = data.get("tracks", []) or []
                        async for t in AsyncIter(tracks_in_playlist):
                            uri = t.get("info", {}).get("uri")
                            if uri:
                                t = {"loadType": "V2_COMPAT", "tracks": [t], "query": uri}
                                data = json.dumps(t)
                                if all(
                                    k in data
                                    for k in ["loadType", "playlistInfo", "isSeekable", "isStream"]
                                ):
                                    database_entries.append(
                                        {
                                            "query": uri,
                                            "data": data,
                                            "last_updated": time_now,
                                            "last_fetched": time_now,
                                        }
                                    )
                    if guild_playlist:
                        all_playlist[str(guild_id)] = guild_playlist
            await self.config.custom(PlaylistScope.GUILD.value).set(all_playlist)
            # new schema is now in place
            await self.config.schema_version.set(2)

            # migration done, now let's delete all the old stuff
            async for guild_id in AsyncIter(all_guild_data):
                await self.config.guild(
                    cast(discord.Guild, discord.Object(id=guild_id))
                ).clear_raw("playlists")
        if from_version < 3 <= to_version:
            for scope in PlaylistScope.list():
                scope_playlist = await get_all_playlist_for_migration23(
                    self.bot, self.playlist_api, self.config, scope
                )
                async for p in AsyncIter(scope_playlist):
                    await p.save()
                await self.config.custom(scope).clear()
            await self.config.schema_version.set(3)
        if from_version < 4 <= to_version:
            # At the time of the introduction of this schema migration,
            # none of these were settable by users even though they're registered in Config
            # so this shouldn't have ever been set but there's no real harm in doing this
            # and schema migrations are a good practice.
            global_data = await self.config.all()
            # We're intentionally not setting entire `global_data` to
            # avoid storing the default values when they were not already set.
            logging_data = global_data.get("yaml", {}).get("logging", {})
            max_history = logging_data.get("file", {}).pop("max_history", ...)
            if max_history is not ...:
                await self.config.yaml.logging.logback.rollingpolicy.max_history.set(max_history)
            max_size = logging_data.get("file", {}).pop("max_size", ...)
            if max_size is not ...:
                await self.config.yaml.logging.logback.rollingpolicy.max_size.set(max_size)
            path = logging_data.pop("path", ...)
            if path is not ...:
                await self.config.yaml.logging.file.path.set(path)
            await self.config.schema_version.set(4)

        if database_entries:
            await self.api_interface.local_cache_api.lavalink.insert(database_entries)

    def decode_track(self, track: str, decode_errors: str = "ignore") -> MutableMapping:
        """
        Decodes a base64 track string into an AudioTrack object.
        Parameters
        ----------
        track: :class:`str`
            The base64 track string.
        decode_errors: :class:`str`
            The action to take upon encountering erroneous characters within track titles.
        Returns
        -------
        :class:`AudioTrack`
        """
        reader = DataReader(track)

        flags = (reader.read_int() & 0xC0000000) >> 30
        (version,) = (
            struct.unpack("B", reader.read_byte()) if flags & 1 != 0 else 1
        )  # pylint: disable=unused-variable

        title = reader.read_utf().decode(errors=decode_errors)
        author = reader.read_utf().decode()
        length = reader.read_long()
        identifier = reader.read_utf().decode()
        is_stream = reader.read_boolean()
        uri = reader.read_utf().decode() if reader.read_boolean() else None
        source = reader.read_utf().decode()
        position = reader.read_long()  # noqa: F841 pylint: disable=unused-variable

        track_object = {
            "track": track,
            "info": {
                "title": title,
                "author": author,
                "length": length,
                "identifier": identifier,
                "isStream": is_stream,
                "uri": uri,
                "isSeekable": not is_stream,
            },
        }

        return track_object
