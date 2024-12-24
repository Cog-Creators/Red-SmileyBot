import asyncio
import contextlib
import datetime
import json
import random
import time

from collections import namedtuple
from pathlib import Path
from typing import TYPE_CHECKING, Callable, List, MutableMapping, Optional, Tuple, Union, cast

import aiohttp
import discord
import lavalink
from red_commons.logging import getLogger

from lavalink.rest_api import LoadResult, LoadType
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands import Cog, Context
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter
from redbot.core.utils.dbtools import APSWConnectionWrapper

from ..audio_dataclasses import Query
from ..errors import DatabaseError, SpotifyFetchError, TrackEnqueueError, YouTubeApiError
from ..utils import CacheLevel, Notifier
from .api_utils import LavalinkCacheFetchForGlobalResult
from .global_db import GlobalCacheWrapper
from .local_db import LocalCacheWrapper
from .persist_queue_wrapper import QueueInterface
from .playlist_interface import get_playlist
from .playlist_wrapper import PlaylistWrapper
from .spotify import SpotifyWrapper
from .youtube import YouTubeWrapper

if TYPE_CHECKING:
    from .. import Audio

_ = Translator("Audio", Path(__file__))
log = getLogger("red.cogs.Audio.api.AudioAPIInterface")
_TOP_100_US = "https://www.youtube.com/playlist?list=PL4fGSI1pDJn5rWitrRWFKdm-ulaFiIyoK"
# TODO: Get random from global Cache


class AudioAPIInterface:
    """Handles music queries.

    Always tries the Local cache first, then Global cache before making API calls.
    """

    def __init__(
        self,
        bot: Red,
        config: Config,
        session: aiohttp.ClientSession,
        conn: APSWConnectionWrapper,
        cog: Union["Audio", Cog],
    ):
        self.bot = bot
        self.config = config
        self.conn = conn
        self.cog = cog
        self.spotify_api: SpotifyWrapper = SpotifyWrapper(self.bot, self.config, session, self.cog)
        self.youtube_api: YouTubeWrapper = YouTubeWrapper(self.bot, self.config, session, self.cog)
        self.local_cache_api = LocalCacheWrapper(self.bot, self.config, self.conn, self.cog)
        self.global_cache_api = GlobalCacheWrapper(self.bot, self.config, session, self.cog)
        self.persistent_queue_api = QueueInterface(self.bot, self.config, self.conn, self.cog)
        self._session: aiohttp.ClientSession = session
        self._tasks: MutableMapping = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialises the Local Cache connection."""
        await self.local_cache_api.lavalink.init()
        await self.persistent_queue_api.init()

    def close(self) -> None:
        """Closes the Local Cache connection."""
        self.local_cache_api.lavalink.close()

    async def get_random_track_from_db(self, tries=0) -> Optional[MutableMapping]:
        """Get a random track from the local database and return it."""
        track: Optional[MutableMapping] = {}
        try:
            query_data = {}
            date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
            date_timestamp = int(date.timestamp())
            query_data["day"] = date_timestamp
            max_age = await self.config.cache_age()
            maxage = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(
                days=max_age
            )
            maxage_int = int(time.mktime(maxage.timetuple()))
            query_data["maxage"] = maxage_int
            track = await self.local_cache_api.lavalink.fetch_random(query_data)
            if track is not None:
                if track.get("loadType") == "V2_COMPACT":
                    track["loadType"] = "V2_COMPAT"
                results = LoadResult(track)
                track = random.choice(list(results.tracks))
        except Exception as exc:
            log.trace("Failed to fetch a random track from database", exc_info=exc)
            track = {}

        if not track:
            return None

        return track

    async def route_tasks(
        self,
        action_type: str = None,
        data: Union[List[MutableMapping], MutableMapping] = None,
    ) -> None:
        """Separate the tasks and run them in the appropriate functions."""

        if not data:
            return
        if action_type == "insert" and isinstance(data, list):
            for table, d in data:
                if table == "lavalink":
                    await self.local_cache_api.lavalink.insert(d)
                elif table == "youtube":
                    await self.local_cache_api.youtube.insert(d)
                elif table == "spotify":
                    await self.local_cache_api.spotify.insert(d)
        elif action_type == "update" and isinstance(data, dict):
            for table, d in data:
                if table == "lavalink":
                    await self.local_cache_api.lavalink.update(data)
                elif table == "youtube":
                    await self.local_cache_api.youtube.update(data)
                elif table == "spotify":
                    await self.local_cache_api.spotify.update(data)
        elif action_type == "global" and isinstance(data, list):
            await asyncio.gather(*[self.global_cache_api.update_global(**d) for d in data])

    async def run_tasks(self, ctx: Optional[commands.Context] = None, message_id=None) -> None:
        """Run tasks for a specific context."""
        if message_id is not None:
            lock_id = message_id
        elif ctx is not None:
            lock_id = ctx.message.id
        else:
            return
        lock_author = ctx.author if ctx else None
        async with self._lock:
            if lock_id in self._tasks:
                log.trace("Running database writes for %s (%s)", lock_id, lock_author)
                try:
                    tasks = self._tasks[lock_id]
                    tasks = [self.route_tasks(a, tasks[a]) for a in tasks]
                    await asyncio.gather(*tasks, return_exceptions=False)
                    del self._tasks[lock_id]
                except Exception as exc:
                    log.verbose(
                        "Failed database writes for %s (%s)", lock_id, lock_author, exc_info=exc
                    )
                else:
                    log.trace("Completed database writes for %s (%s)", lock_id, lock_author)

    async def run_all_pending_tasks(self) -> None:
        """Run all pending tasks left in the cache, called on cog_unload."""
        async with self._lock:
            log.trace("Running pending writes to database")
            try:
                tasks: MutableMapping = {"update": [], "insert": [], "global": []}
                async for k, task in AsyncIter(self._tasks.items()):
                    async for t, args in AsyncIter(task.items()):
                        tasks[t].append(args)
                self._tasks = {}
                coro_tasks = [self.route_tasks(a, tasks[a]) for a in tasks]

                await asyncio.gather(*coro_tasks, return_exceptions=False)

            except Exception as exc:
                log.verbose("Failed database writes", exc_info=exc)
            else:
                log.trace("Completed pending writes to database have finished")

    def append_task(self, ctx: commands.Context, event: str, task: Tuple, _id: int = None) -> None:
        """Add a task to the cache to be run later."""
        lock_id = _id or ctx.message.id
        if lock_id not in self._tasks:
            self._tasks[lock_id] = {"update": [], "insert": [], "global": []}
        self._tasks[lock_id][event].append(task)

    async def fetch_spotify_query(
        self,
        ctx: commands.Context,
        query_type: str,
        uri: str,
        notifier: Optional[Notifier],
        skip_youtube: bool = False,
        current_cache_level: CacheLevel = CacheLevel.all(),
    ) -> List[str]:
        """Return youtube URLS for the spotify URL provided."""
        youtube_urls = []
        tracks = await self.fetch_from_spotify_api(
            query_type, uri, params=None, notifier=notifier, ctx=ctx
        )
        total_tracks = len(tracks)
        database_entries = []
        track_count = 0
        time_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        youtube_cache = CacheLevel.set_youtube().is_subset(current_cache_level)
        youtube_api_error = None
        global_api = self.cog.global_api_user.get("can_read")
        async for track in AsyncIter(tracks):
            if isinstance(track, str):
                break
            elif isinstance(track, dict) and track.get("error", {}).get("message") == "invalid id":
                continue
            (
                song_url,
                track_info,
                uri,
                artist_name,
                track_name,
                _id,
                _type,
            ) = await self.spotify_api.get_spotify_track_info(track, ctx)

            database_entries.append(
                {
                    "id": _id,
                    "type": _type,
                    "uri": uri,
                    "track_name": track_name,
                    "artist_name": artist_name,
                    "song_url": song_url,
                    "track_info": track_info,
                    "last_updated": time_now,
                    "last_fetched": time_now,
                }
            )
            if skip_youtube is False:
                val = None
                if youtube_cache:
                    try:
                        (val, last_update) = await self.local_cache_api.youtube.fetch_one(
                            {"track": track_info}
                        )
                    except Exception as exc:
                        log.verbose(
                            "Failed to fetch %r from YouTube table", track_info, exc_info=exc
                        )
                if val is None:
                    try:
                        val = await self.fetch_youtube_query(
                            ctx, track_info, current_cache_level=current_cache_level
                        )
                    except YouTubeApiError as exc:
                        val = None
                        youtube_api_error = exc.message
                if youtube_cache and val:
                    task = ("update", ("youtube", {"track": track_info}))
                    self.append_task(ctx, *task)
                if val:
                    youtube_urls.append(val)
            else:
                youtube_urls.append(track_info)
            track_count += 1
            if notifier is not None and ((track_count % 2 == 0) or (track_count == total_tracks)):
                await notifier.notify_user(current=track_count, total=total_tracks, key="youtube")
            if notifier is not None and (youtube_api_error and not global_api):
                error_embed = discord.Embed(
                    colour=await ctx.embed_colour(),
                    title=_("Failing to get tracks, skipping remaining."),
                )
                await notifier.update_embed(error_embed)
                break
            elif notifier is not None and (youtube_api_error and global_api):
                continue
        if CacheLevel.set_spotify().is_subset(current_cache_level):
            task = ("insert", ("spotify", database_entries))
            self.append_task(ctx, *task)
        return youtube_urls

    async def fetch_from_spotify_api(
        self,
        query_type: str,
        uri: str,
        recursive: Union[str, bool] = False,
        params: MutableMapping = None,
        notifier: Optional[Notifier] = None,
        ctx: Context = None,
    ) -> Union[List[MutableMapping], List[str]]:
        """Gets track info from spotify API."""

        if recursive is False:
            (call, params) = self.spotify_api.spotify_format_call(query_type, uri)
            results = await self.spotify_api.make_get_call(call, params)
        else:
            if isinstance(recursive, str):
                results = await self.spotify_api.make_get_call(recursive, params)
            else:
                results = {}
        try:
            if results["error"]["status"] == 401 and not recursive:
                raise SpotifyFetchError(
                    _(
                        "The Spotify API key or client secret has not been set properly. "
                        "\nUse `{prefix}audioset spotifyapi` for instructions."
                    )
                )
            elif recursive:
                return {"next": None}
        except KeyError:
            pass
        if recursive:
            return results
        tracks = []
        track_count = 0
        total_tracks = results.get("tracks", results).get("total", 1)
        while True:
            new_tracks: List = []
            if query_type == "track":
                new_tracks = results
                tracks.append(new_tracks)
            elif query_type == "album":
                tracks_raw = results.get("tracks", results).get("items", [])
                if tracks_raw:
                    new_tracks = tracks_raw
                    tracks.extend(new_tracks)
            else:
                tracks_raw = results.get("tracks", results).get("items", [])
                if tracks_raw:
                    new_tracks = [k["track"] for k in tracks_raw if k.get("track")]
                    tracks.extend(new_tracks)
            track_count += len(new_tracks)
            if notifier:
                await notifier.notify_user(current=track_count, total=total_tracks, key="spotify")
            try:
                if results.get("next") is not None:
                    results = await self.fetch_from_spotify_api(
                        query_type, uri, results["next"], params, notifier=notifier
                    )
                    continue
                else:
                    break
            except KeyError:
                raise SpotifyFetchError(
                    _("This doesn't seem to be a valid Spotify playlist/album URL or code.")
                )
        return tracks

    async def spotify_query(
        self,
        ctx: commands.Context,
        query_type: str,
        uri: str,
        skip_youtube: bool = False,
        notifier: Optional[Notifier] = None,
    ) -> List[str]:
        """Queries the Database then falls back to Spotify and YouTube APIs.

        Parameters
        ----------
        ctx: commands.Context
            The context this method is being called under.
        query_type : str
            Type of query to perform (Pl
        uri: str
            Spotify URL ID.
        skip_youtube:bool
            Whether or not to skip YouTube API Calls.
        notifier: Notifier
            A Notifier object to handle the user UI notifications while tracks are loaded.
        Returns
        -------
        List[str]
            List of Youtube URLs.
        """
        current_cache_level = CacheLevel(await self.config.cache_level())
        cache_enabled = CacheLevel.set_spotify().is_subset(current_cache_level)
        if query_type == "track" and cache_enabled:
            try:
                (val, last_update) = await self.local_cache_api.spotify.fetch_one(
                    {"uri": f"spotify:track:{uri}"}
                )
            except Exception as exc:
                log.verbose(
                    "Failed to fetch 'spotify:track:%s' from Spotify table", uri, exc_info=exc
                )
                val = None
        else:
            val = None
        youtube_urls = []
        if val is None:
            urls = await self.fetch_spotify_query(
                ctx,
                query_type,
                uri,
                notifier,
                skip_youtube,
                current_cache_level=current_cache_level,
            )
            youtube_urls.extend(urls)
        else:
            if query_type == "track" and cache_enabled:
                task = ("update", ("spotify", {"uri": f"spotify:track:{uri}"}))
                self.append_task(ctx, *task)
            youtube_urls.append(val)
        return youtube_urls

    async def spotify_enqueue(
        self,
        ctx: commands.Context,
        query_type: str,
        uri: str,
        enqueue: bool,
        player: lavalink.Player,
        lock: Callable,
        notifier: Optional[Notifier] = None,
        forced: bool = False,
        query_global: bool = True,
    ) -> List[lavalink.Track]:
        """Queries the Database then falls back to Spotify and YouTube APIs then Enqueued matched
        tracks.

        Parameters
        ----------
        ctx: commands.Context
            The context this method is being called under.
        query_type : str
            Type of query to perform (Pl
        uri: str
            Spotify URL ID.
        enqueue:bool
            Whether or not to enqueue the tracks
        player: lavalink.Player
            The current Player.
        notifier: Notifier
            A Notifier object to handle the user UI notifications while tracks are loaded.
        lock: Callable
            A callable handling the Track enqueue lock while spotify tracks are being added.
        query_global: bool
            Whether or not to query the global API.
        forced: bool
            Ignore Cache and make a fetch from API.
        Returns
        -------
        List[str]
            List of Youtube URLs.
        """
        await self.global_cache_api._get_api_key()
        globaldb_toggle = self.cog.global_api_user.get("can_read")
        global_entry = globaldb_toggle and query_global
        track_list: List = []
        has_not_allowed = False
        youtube_api_error = None
        skip_youtube_api = False
        try:
            current_cache_level = CacheLevel(await self.config.cache_level())
            guild_data = await self.config.guild(ctx.guild).all()
            enqueued_tracks = 0
            consecutive_fails = 0
            queue_dur = await self.cog.queue_duration(ctx)
            queue_total_duration = self.cog.format_time(queue_dur)
            before_queue_length = len(player.queue)
            tracks_from_spotify = await self.fetch_from_spotify_api(
                query_type, uri, params=None, notifier=notifier
            )
            total_tracks = len(tracks_from_spotify)
            if total_tracks < 1 and notifier is not None:
                lock(ctx, False)
                embed3 = discord.Embed(
                    colour=await ctx.embed_colour(),
                    title=_("This doesn't seem to be a supported Spotify URL or code."),
                )
                await notifier.update_embed(embed3)

                return track_list
            database_entries = []
            time_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
            youtube_cache = CacheLevel.set_youtube().is_subset(current_cache_level)
            spotify_cache = CacheLevel.set_spotify().is_subset(current_cache_level)
            async for track_count, track in AsyncIter(tracks_from_spotify).enumerate(start=1):
                (
                    song_url,
                    track_info,
                    uri,
                    artist_name,
                    track_name,
                    _id,
                    _type,
                ) = await self.spotify_api.get_spotify_track_info(track, ctx)

                database_entries.append(
                    {
                        "id": _id,
                        "type": _type,
                        "uri": uri,
                        "track_name": track_name,
                        "artist_name": artist_name,
                        "song_url": song_url,
                        "track_info": track_info,
                        "last_updated": time_now,
                        "last_fetched": time_now,
                    }
                )
                val = None
                llresponse = None
                if youtube_cache:
                    try:
                        (val, last_updated) = await self.local_cache_api.youtube.fetch_one(
                            {"track": track_info}
                        )
                    except Exception as exc:
                        log.verbose(
                            "Failed to fetch %r from YouTube table", track_info, exc_info=exc
                        )
                should_query_global = globaldb_toggle and query_global and val is None
                if should_query_global:
                    llresponse = await self.global_cache_api.get_spotify(track_name, artist_name)
                    if llresponse:
                        if llresponse.get("loadType") == "V2_COMPACT":
                            llresponse["loadType"] = "V2_COMPAT"
                        llresponse = LoadResult(llresponse)
                    val = llresponse or None
                if val is None and not skip_youtube_api:
                    try:
                        val = await self.fetch_youtube_query(
                            ctx, track_info, current_cache_level=current_cache_level
                        )
                    except YouTubeApiError as exc:
                        val = None
                        youtube_api_error = exc.message
                        skip_youtube_api = True
                if not youtube_api_error:
                    if youtube_cache and val and llresponse is None:
                        task = ("update", ("youtube", {"track": track_info}))
                        self.append_task(ctx, *task)

                    if isinstance(llresponse, LoadResult):
                        track_object = llresponse.tracks
                    elif val:
                        result = None
                        if should_query_global:
                            llresponse = await self.global_cache_api.get_call(val)
                            if llresponse:
                                if llresponse.get("loadType") == "V2_COMPACT":
                                    llresponse["loadType"] = "V2_COMPAT"
                                llresponse = LoadResult(llresponse)
                            result = llresponse or None
                        if not result:
                            try:
                                (result, called_api) = await self.fetch_track(
                                    ctx,
                                    player,
                                    Query.process_input(val, self.cog.local_folder_current_path),
                                    forced=forced,
                                    should_query_global=not should_query_global,
                                )
                            except (RuntimeError, aiohttp.ServerDisconnectedError):
                                lock(ctx, False)
                                error_embed = discord.Embed(
                                    colour=await ctx.embed_colour(),
                                    title=_(
                                        "The connection was reset while loading the playlist."
                                    ),
                                )
                                if notifier is not None:
                                    await notifier.update_embed(error_embed)
                                break
                            except asyncio.TimeoutError:
                                lock(ctx, False)
                                error_embed = discord.Embed(
                                    colour=await ctx.embed_colour(),
                                    title=_("Player timeout, skipping remaining tracks."),
                                )
                                if notifier is not None:
                                    await notifier.update_embed(error_embed)
                                break
                        track_object = result.tracks
                    else:
                        track_object = []
                else:
                    track_object = []
                if (track_count % 2 == 0) or (track_count == total_tracks):
                    key = "lavalink"
                    seconds = "???"
                    second_key = None
                    if notifier is not None:
                        await notifier.notify_user(
                            current=track_count,
                            total=total_tracks,
                            key=key,
                            seconds_key=second_key,
                            seconds=seconds,
                        )

                if (youtube_api_error and not global_entry) or consecutive_fails >= (
                    20 if global_entry else 10
                ):
                    error_embed = discord.Embed(
                        colour=await ctx.embed_colour(),
                        title=_("Failing to get tracks, skipping remaining."),
                    )
                    if notifier is not None:
                        await notifier.update_embed(error_embed)
                    if youtube_api_error:
                        lock(ctx, False)
                        raise SpotifyFetchError(message=youtube_api_error)
                    break
                if not track_object:
                    consecutive_fails += 1
                    continue
                consecutive_fails = 0
                single_track = track_object[0]
                query = Query.process_input(single_track, self.cog.local_folder_current_path)
                if not await self.cog.is_query_allowed(
                    self.config,
                    ctx,
                    f"{single_track.title} {single_track.author} {single_track.uri} {query}",
                    query_obj=query,
                ):
                    has_not_allowed = True
                    log.debug("Query is not allowed in %r (%s)", ctx.guild.name, ctx.guild.id)
                    continue
                track_list.append(single_track)
                if enqueue:
                    if len(player.queue) >= 10000:
                        continue
                    if guild_data["maxlength"] > 0:
                        if self.cog.is_track_length_allowed(single_track, guild_data["maxlength"]):
                            enqueued_tracks += 1
                            single_track.extras.update(
                                {
                                    "enqueue_time": int(time.time()),
                                    "vc": player.channel.id,
                                    "requester": ctx.author.id,
                                }
                            )
                            player.add(ctx.author, single_track)
                            self.bot.dispatch(
                                "red_audio_track_enqueue",
                                player.guild,
                                single_track,
                                ctx.author,
                            )
                    else:
                        enqueued_tracks += 1
                        single_track.extras.update(
                            {
                                "enqueue_time": int(time.time()),
                                "vc": player.channel.id,
                                "requester": ctx.author.id,
                            }
                        )
                        player.add(ctx.author, single_track)
                        self.bot.dispatch(
                            "red_audio_track_enqueue",
                            player.guild,
                            single_track,
                            ctx.author,
                        )

                    if not player.current:
                        await player.play()
            if enqueue and tracks_from_spotify:
                if total_tracks > enqueued_tracks:
                    maxlength_msg = _(" {bad_tracks} tracks cannot be queued.").format(
                        bad_tracks=(total_tracks - enqueued_tracks)
                    )
                else:
                    maxlength_msg = ""

                embed = discord.Embed(
                    colour=await ctx.embed_colour(),
                    title=_("Playlist Enqueued"),
                    description=_("Added {num} tracks to the queue.{maxlength_msg}").format(
                        num=enqueued_tracks, maxlength_msg=maxlength_msg
                    ),
                )
                if not guild_data["shuffle"] and queue_dur > 0:
                    embed.set_footer(
                        text=_(
                            "{time} until start of playlist"
                            " playback: starts at #{position} in queue"
                        ).format(time=queue_total_duration, position=before_queue_length + 1)
                    )

                if notifier is not None:
                    await notifier.update_embed(embed)
            lock(ctx, False)
            if not track_list and not has_not_allowed:
                raise SpotifyFetchError(
                    message=_(
                        "Nothing found.\nThe YouTube API key may be invalid "
                        "or you may be rate limited on YouTube's search service.\n"
                        "Check the YouTube API key again and follow the instructions "
                        "at `{prefix}audioset youtubeapi`."
                    )
                )
            player.maybe_shuffle()

            if spotify_cache:
                task = ("insert", ("spotify", database_entries))
                self.append_task(ctx, *task)
        except Exception as exc:
            lock(ctx, False)
            raise exc
        finally:
            lock(ctx, False)
        return track_list

    async def fetch_youtube_query(
        self,
        ctx: commands.Context,
        track_info: str,
        current_cache_level: CacheLevel = CacheLevel.all(),
    ) -> Optional[str]:
        """Call the Youtube API and returns the youtube URL that the query matched."""
        track_url = await self.youtube_api.get_call(track_info)
        if CacheLevel.set_youtube().is_subset(current_cache_level) and track_url:
            time_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
            task = (
                "insert",
                (
                    "youtube",
                    [
                        {
                            "track_info": track_info,
                            "track_url": track_url,
                            "last_updated": time_now,
                            "last_fetched": time_now,
                        }
                    ],
                ),
            )
            self.append_task(ctx, *task)
        return track_url

    async def fetch_from_youtube_api(
        self, ctx: commands.Context, track_info: str
    ) -> Optional[str]:
        """Gets an YouTube URL from for the query."""
        current_cache_level = CacheLevel(await self.config.cache_level())
        cache_enabled = CacheLevel.set_youtube().is_subset(current_cache_level)
        val = None
        if cache_enabled:
            try:
                (val, update) = await self.local_cache_api.youtube.fetch_one({"track": track_info})
            except Exception as exc:
                log.verbose("Failed to fetch %r from YouTube table", track_info, exc_info=exc)
        if val is None:
            try:
                youtube_url = await self.fetch_youtube_query(
                    ctx, track_info, current_cache_level=current_cache_level
                )
            except YouTubeApiError:
                youtube_url = None
        else:
            if cache_enabled:
                task = ("update", ("youtube", {"track": track_info}))
                self.append_task(ctx, *task)
            youtube_url = val
        return youtube_url

    async def fetch_track(
        self,
        ctx: commands.Context,
        player: lavalink.Player,
        query: Query,
        forced: bool = False,
        lazy: bool = False,
        should_query_global: bool = True,
    ) -> Tuple[LoadResult, bool]:
        """A replacement for :code:`lavalink.Player.load_tracks`. This will try to get a valid
        cached entry first if not found or if in valid it will then call the lavalink API.

        Parameters
        ----------
        ctx: commands.Context
            The context this method is being called under.
        player : lavalink.Player
            The player who's requesting the query.
        query: audio_dataclasses.Query
            The Query object for the query in question.
        forced:bool
            Whether or not to skip cache and call API first.
        lazy:bool
            If set to True, it will not call the api if a track is not found.
        should_query_global:bool
            If the method should query the global database.

        Returns
        -------
        Tuple[lavalink.LoadResult, bool]
            Tuple with the Load result and whether or not the API was called.
        """
        current_cache_level = CacheLevel(await self.config.cache_level())
        cache_enabled = CacheLevel.set_lavalink().is_subset(current_cache_level)
        val = None
        query = Query.process_input(query, self.cog.local_folder_current_path)
        query_string = str(query)
        globaldb_toggle = self.cog.global_api_user.get("can_read")
        valid_global_entry = False
        results = None
        called_api = False
        prefer_lyrics = await self.cog.get_lyrics_status(ctx)
        if prefer_lyrics and query.is_youtube and query.is_search:
            query_string = f"{query} - lyrics"
        if cache_enabled and not forced and not query.is_local:
            try:
                (val, last_updated) = await self.local_cache_api.lavalink.fetch_one(
                    {"query": query_string}
                )
            except Exception as exc:
                log.verbose("Failed to fetch %r from Lavalink table", query_string, exc_info=exc)

            if val and isinstance(val, dict):
                log.trace("Updating Local Database with %r", query_string)
                task = ("update", ("lavalink", {"query": query_string}))
                self.append_task(ctx, *task)
            else:
                val = None

            if val and not forced and isinstance(val, dict):
                valid_global_entry = False
                called_api = False
            else:
                val = None
        if (
            globaldb_toggle
            and not val
            and should_query_global
            and not forced
            and not query.is_local
            and not query.is_spotify
        ):
            valid_global_entry = False
            with contextlib.suppress(Exception):
                global_entry = await self.global_cache_api.get_call(query=query)
                if global_entry.get("loadType") == "V2_COMPACT":
                    global_entry["loadType"] = "V2_COMPAT"
                results = LoadResult(global_entry)
                if results.load_type in [
                    LoadType.PLAYLIST_LOADED,
                    LoadType.TRACK_LOADED,
                    LoadType.SEARCH_RESULT,
                    LoadType.V2_COMPAT,
                ]:
                    valid_global_entry = True
                if valid_global_entry:
                    log.trace("Querying Global DB api for %r", query)
                    results, called_api = results, False
        if valid_global_entry:
            pass
        elif lazy is True:
            called_api = False
        elif val and not forced and isinstance(val, dict):
            data = val
            data["query"] = query_string
            if data.get("loadType") == "V2_COMPACT":
                data["loadType"] = "V2_COMPAT"
            results = LoadResult(data)
            called_api = False
            if results.has_error:
                # If cached value has an invalid entry make a new call so that it gets updated
                results, called_api = await self.fetch_track(ctx, player, query, forced=True)
            valid_global_entry = False
        else:
            log.trace("Querying Lavalink api for %r", query_string)
            called_api = True
            try:
                results = await player.load_tracks(query_string)
            except KeyError:
                results = None
            except RuntimeError:
                raise TrackEnqueueError
        if results is None:
            results = LoadResult({"loadType": "LOAD_FAILED", "playlistInfo": {}, "tracks": []})
            valid_global_entry = False
        update_global = (
            globaldb_toggle and not valid_global_entry and self.global_cache_api.has_api_key
        )
        with contextlib.suppress(Exception):
            if (
                update_global
                and not query.is_local
                and not results.has_error
                and len(results.tracks) >= 1
            ):
                global_task = ("global", dict(llresponse=results, query=query))
                self.append_task(ctx, *global_task)
        if (
            cache_enabled
            and results.load_type
            and not results.has_error
            and not query.is_local
            and results.tracks
        ):
            try:
                time_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
                data = json.dumps(results._raw)
                if all(k in data for k in ["loadType", "playlistInfo", "isSeekable", "isStream"]):
                    task = (
                        "insert",
                        (
                            "lavalink",
                            [
                                {
                                    "query": query_string,
                                    "data": data,
                                    "last_updated": time_now,
                                    "last_fetched": time_now,
                                }
                            ],
                        ),
                    )
                    self.append_task(ctx, *task)
            except Exception as exc:
                log.verbose(
                    "Failed to enqueue write task for %r to Lavalink table",
                    query_string,
                    exc_info=exc,
                )
        return results, called_api

    async def autoplay(self, player: lavalink.Player, playlist_api: PlaylistWrapper):
        """Enqueue a random track."""
        autoplaylist = await self.config.guild(player.guild).autoplaylist()
        current_cache_level = CacheLevel(await self.config.cache_level())
        cache_enabled = CacheLevel.set_lavalink().is_subset(current_cache_level)
        notify_channel_id = player.fetch("notify_channel")
        playlist = None
        tracks = None
        if autoplaylist["enabled"]:
            try:
                playlist = await get_playlist(
                    autoplaylist["id"],
                    autoplaylist["scope"],
                    self.bot,
                    playlist_api,
                    player.guild,
                    player.guild.me,
                )
                tracks = playlist.tracks_obj
            except Exception as exc:
                log.verbose("Failed to fetch playlist for autoplay", exc_info=exc)

        if not tracks or not getattr(playlist, "tracks", None):
            if cache_enabled:
                track = await self.get_random_track_from_db()
                tracks = [] if not track else [track]
            if not tracks:
                ctx = namedtuple("Context", "message guild cog")
                (results, called_api) = await self.fetch_track(
                    cast(commands.Context, ctx(player.guild, player.guild, self.cog)),
                    player,
                    Query.process_input(_TOP_100_US, self.cog.local_folder_current_path),
                )
                tracks = list(results.tracks)
        if tracks:
            multiple = len(tracks) > 1
            valid = not multiple
            tries = len(tracks)
            track = tracks[0]
            while valid is False and multiple:
                tries -= 1
                if tries <= 0:
                    raise DatabaseError("No valid entry found")
                track = random.choice(tracks)
                query = Query.process_input(track, self.cog.local_folder_current_path)
                await asyncio.sleep(0.001)
                if (not query.valid) or (
                    query.is_local
                    and query.local_track_path is not None
                    and not query.local_track_path.exists()
                ):
                    continue
                notify_channel = player.guild.get_channel_or_thread(notify_channel_id)
                if not await self.cog.is_query_allowed(
                    self.config,
                    notify_channel,
                    f"{track.title} {track.author} {track.uri} {query}",
                    query_obj=query,
                ):
                    log.debug(
                        "Query is not allowed in %r (%s)", player.guild.name, player.guild.id
                    )
                    continue
                valid = True
            track.extras.update(
                {
                    "autoplay": True,
                    "enqueue_time": int(time.time()),
                    "vc": player.channel.id,
                    "requester": player.guild.me.id,
                }
            )
            player.add(player.guild.me, track)
            self.bot.dispatch(
                "red_audio_track_auto_play",
                player.guild,
                track,
                player.guild.me,
                player,
            )
            if notify_channel_id:
                await self.config.guild_from_id(
                    guild_id=player.guild.id
                ).currently_auto_playing_in.set([notify_channel_id, player.channel.id])
            else:
                await self.config.guild_from_id(
                    guild_id=player.guild.id
                ).currently_auto_playing_in.set([])
            if not player.current:
                await player.play()

    async def fetch_all_contribute(self) -> List[LavalinkCacheFetchForGlobalResult]:
        return await self.local_cache_api.lavalink.fetch_all_for_global()
