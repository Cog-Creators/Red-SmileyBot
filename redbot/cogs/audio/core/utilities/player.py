import time
from pathlib import Path

from typing import List, Optional, Tuple, Union

import aiohttp
import discord
import lavalink
from red_commons.logging import getLogger

from lavalink import NodeNotFound, PlayerNotFound

from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import bold, escape

from ...audio_dataclasses import _PARTIALLY_SUPPORTED_MUSIC_EXT, Query
from ...errors import QueryUnauthorized, SpotifyFetchError, TrackEnqueueError
from ...utils import Notifier
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = getLogger("red.cogs.Audio.cog.Utilities.player")
_ = Translator("Audio", Path(__file__))


class PlayerUtilities(MixinMeta, metaclass=CompositeMetaClass):
    async def maybe_reset_error_counter(self, player: lavalink.Player) -> None:
        guild = self.rgetattr(player, "channel.guild.id", None)
        if not guild:
            return
        now = time.time()
        seconds_allowed = 10
        last_error = self._error_timer.setdefault(guild, now)
        if now - seconds_allowed > last_error:
            self._error_timer[guild] = 0
            self._error_counter[guild] = 0

    async def increase_error_counter(self, player: lavalink.Player) -> bool:
        guild = self.rgetattr(player, "channel.guild.id", None)
        if not guild:
            return False
        now = time.time()
        self._error_counter[guild] += 1
        self._error_timer[guild] = now
        return self._error_counter[guild] >= 5

    async def get_active_player_count(self) -> Tuple[Optional[str], int]:
        try:
            current = next(
                (
                    player.current
                    for player in lavalink.active_players()
                    if player.current is not None
                ),
                None,
            )
            get_single_title = await self.get_track_description_unformatted(
                current, self.local_folder_current_path
            )
            playing_servers = len(lavalink.active_players())
        except (IndexError, NodeNotFound, PlayerNotFound):
            get_single_title = None
            playing_servers = 0
        return get_single_title, playing_servers

    async def update_bot_presence(self, track: Optional[str], playing_servers: int) -> None:
        if playing_servers == 0:
            await self.bot.change_presence(activity=None)
        elif playing_servers == 1:
            await self.bot.change_presence(
                activity=discord.Activity(name=track, type=discord.ActivityType.listening)
            )
        elif playing_servers > 1:
            await self.bot.change_presence(
                activity=discord.Activity(
                    name=_("music in {} servers").format(playing_servers),
                    type=discord.ActivityType.playing,
                )
            )

    async def _can_instaskip(self, ctx: commands.Context, member: discord.Member) -> bool:
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )

        if member.bot:
            return True

        if member.id == ctx.guild.owner_id:
            return True

        if dj_enabled and await self._has_dj_role(ctx, member):
            return True

        if await self.bot.is_owner(member):
            return True

        if await self.bot.is_mod(member):
            return True

        if await self.maybe_move_player(ctx):
            return True

        return False

    async def is_requester_alone(self, ctx: commands.Context) -> bool:
        channel_members = self.rgetattr(ctx, "guild.me.voice.channel.members", [])
        nonbots = sum(m.id != ctx.author.id for m in channel_members if not m.bot)
        return not nonbots

    async def _has_dj_role(self, ctx: commands.Context, member: discord.Member) -> bool:
        dj_role = self._dj_role_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_role()
        )
        return member.get_role(dj_role) is not None

    async def is_requester(self, ctx: commands.Context, member: discord.Member) -> bool:
        try:
            player = lavalink.get_player(ctx.guild.id)
            log.debug("Current requester is %s", player.current.requester)
            return player.current.requester.id == member.id
        except Exception as exc:
            log.trace("Caught error in `is_requester`", exc_info=exc)
        return False

    async def _skip_action(self, ctx: commands.Context, skip_to_track: int = None) -> None:
        player = lavalink.get_player(ctx.guild.id)
        autoplay = await self.config.guild(player.guild).auto_play()
        if not player.current or (not player.queue and not autoplay):
            try:
                pos, dur = player.position, player.current.length
            except AttributeError:
                await self.send_embed_msg(ctx, title=_("There's nothing in the queue."))
                return
            time_remain = self.format_time(dur - pos)
            if player.current.is_stream:
                embed = discord.Embed(title=_("There's nothing in the queue."))
                embed.set_footer(
                    text=_("Currently livestreaming {track}").format(track=player.current.title)
                )
            else:
                embed = discord.Embed(title=_("There's nothing in the queue."))
                embed.set_footer(
                    text=_("{time} left on {track}").format(
                        time=time_remain, track=player.current.title
                    )
                )
            await self.send_embed_msg(ctx, embed=embed)
            return
        elif autoplay and not player.queue:
            embed = discord.Embed(
                title=_("Track Skipped"),
                description=await self.get_track_description(
                    player.current, self.local_folder_current_path
                ),
            )
            await self.send_embed_msg(ctx, embed=embed)
            await player.skip()
            return

        queue_to_append = []
        if skip_to_track is not None and skip_to_track != 1:
            if skip_to_track < 1:
                await self.send_embed_msg(
                    ctx, title=_("Track number must be equal to or greater than 1.")
                )
                return
            elif skip_to_track > len(player.queue):
                await self.send_embed_msg(
                    ctx,
                    title=_("There are only {queuelen} songs currently queued.").format(
                        queuelen=len(player.queue)
                    ),
                )
                return
            embed = discord.Embed(
                title=_("{skip_to_track} Tracks Skipped").format(skip_to_track=skip_to_track)
            )
            await self.send_embed_msg(ctx, embed=embed)
            if player.repeat:
                queue_to_append = player.queue[0 : min(skip_to_track - 1, len(player.queue) - 1)]
            player.queue = player.queue[
                min(skip_to_track - 1, len(player.queue) - 1) : len(player.queue)
            ]
        else:
            embed = discord.Embed(
                title=_("Track Skipped"),
                description=await self.get_track_description(
                    player.current, self.local_folder_current_path
                ),
            )
            await self.send_embed_msg(ctx, embed=embed)
        self.bot.dispatch("red_audio_skip_track", player.guild, player.current, ctx.author)
        await player.play()
        player.queue += queue_to_append

    def update_player_lock(self, ctx: commands.Context, true_or_false: bool) -> None:
        if true_or_false:
            self.play_lock[ctx.guild.id] = True
        else:
            self.play_lock[ctx.guild.id] = False

    def _player_check(self, ctx: commands.Context) -> bool:
        if self.lavalink_connection_aborted:
            return False
        try:
            lavalink.get_player(ctx.guild.id)
            return True
        except (NodeNotFound, PlayerNotFound):
            return False

    async def self_deafen(self, player: lavalink.Player) -> None:
        guild_id = self.rgetattr(player, "channel.guild.id", None)
        if not guild_id:
            return
        if not await self.config.guild_from_id(guild_id).auto_deafen():
            return
        await player.guild.change_voice_state(channel=player.channel, self_deaf=True)

    async def _get_spotify_tracks(
        self, ctx: commands.Context, query: Query, forced: bool = False
    ) -> Union[discord.Message, List[lavalink.Track], lavalink.Track]:
        if ctx.invoked_with in ["play", "genre"]:
            enqueue_tracks = True
        else:
            enqueue_tracks = False
        player = lavalink.get_player(ctx.guild.id)
        api_data = await self._check_api_tokens()
        if any([not api_data["spotify_client_id"], not api_data["spotify_client_secret"]]):
            return await self.send_embed_msg(
                ctx,
                title=_("Invalid Environment"),
                description=_(
                    "The owner needs to set the Spotify client ID and Spotify client secret, "
                    "before Spotify URLs or codes can be used. "
                    "\nSee `{prefix}audioset spotifyapi` for instructions."
                ).format(prefix=ctx.prefix),
            )
        elif not api_data["youtube_api"]:
            return await self.send_embed_msg(
                ctx,
                title=_("Invalid Environment"),
                description=_(
                    "The owner needs to set the YouTube API key before Spotify URLs or "
                    "codes can be used.\nSee `{prefix}audioset youtubeapi` for instructions."
                ).format(prefix=ctx.prefix),
            )
        try:
            if self.play_lock[ctx.guild.id]:
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Get Tracks"),
                    description=_("Wait until the playlist has finished loading."),
                )
        except KeyError:
            pass

        if query.single_track:
            try:
                res = await self.api_interface.spotify_query(
                    ctx, "track", query.id, skip_youtube=True, notifier=None
                )
                if not res:
                    title = _("Nothing found.")
                    embed = discord.Embed(title=title)
                    if query.is_local and query.suffix in _PARTIALLY_SUPPORTED_MUSIC_EXT:
                        title = _("Track is not playable.")
                        description = _(
                            "**{suffix}** is not a fully supported "
                            "format and some tracks may not play."
                        ).format(suffix=query.suffix)
                        embed = discord.Embed(title=title, description=description)
                    return await self.send_embed_msg(ctx, embed=embed)
            except SpotifyFetchError as error:
                self.update_player_lock(ctx, False)
                return await self.send_embed_msg(
                    ctx, title=error.message.format(prefix=ctx.prefix)
                )
            except Exception as e:
                self.update_player_lock(ctx, False)
                raise e
            self.update_player_lock(ctx, False)
            try:
                if enqueue_tracks:
                    new_query = Query.process_input(res[0], self.local_folder_current_path)
                    new_query.start_time = query.start_time
                    return await self._enqueue_tracks(ctx, new_query)
                else:
                    query = Query.process_input(res[0], self.local_folder_current_path)
                    try:
                        result, called_api = await self.api_interface.fetch_track(
                            ctx, player, query
                        )
                    except TrackEnqueueError:
                        self.update_player_lock(ctx, False)
                        return await self.send_embed_msg(
                            ctx,
                            title=_("Unable to Get Track"),
                            description=_(
                                "I'm unable to get a track from the Lavalink node at the moment, "
                                "try again in a few minutes."
                            ),
                        )
                    tracks = result.tracks
                    if not tracks:
                        embed = discord.Embed(title=_("Nothing found."))
                        if query.is_local and query.suffix in _PARTIALLY_SUPPORTED_MUSIC_EXT:
                            embed = discord.Embed(title=_("Track is not playable."))
                            embed.description = _(
                                "**{suffix}** is not a fully supported format and some "
                                "tracks may not play."
                            ).format(suffix=query.suffix)
                        return await self.send_embed_msg(ctx, embed=embed)
                    single_track = tracks[0]
                    single_track.start_timestamp = query.start_time * 1000
                    single_track = [single_track]

                    return single_track

            except KeyError:
                self.update_player_lock(ctx, False)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Invalid Environment"),
                    description=_(
                        "The Spotify API key or client secret has not been set properly. "
                        "\nUse `{prefix}audioset spotifyapi` for instructions."
                    ).format(prefix=ctx.prefix),
                )
            except Exception as e:
                self.update_player_lock(ctx, False)
                raise e
        elif query.is_album or query.is_playlist:
            try:
                self.update_player_lock(ctx, True)
                track_list = await self.fetch_spotify_playlist(
                    ctx,
                    "album" if query.is_album else "playlist",
                    query,
                    enqueue_tracks,
                    forced=forced,
                )
            finally:
                self.update_player_lock(ctx, False)
            return track_list
        else:
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Find Tracks"),
                description=_("This doesn't seem to be a supported Spotify URL or code."),
            )

    async def _enqueue_tracks(
        self, ctx: commands.Context, query: Union[Query, list], enqueue: bool = True
    ) -> Union[discord.Message, List[lavalink.Track], lavalink.Track]:
        player = lavalink.get_player(ctx.guild.id)
        try:
            if self.play_lock[ctx.guild.id]:
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Get Tracks"),
                    description=_("Wait until the playlist has finished loading."),
                )
        except KeyError:
            self.update_player_lock(ctx, True)
        guild_data = await self.config.guild(ctx.guild).all()
        first_track_only = False
        single_track = None
        index = None
        playlist_data = None
        playlist_url = None
        seek = 0
        if type(query) is not list:
            if not await self.is_query_allowed(self.config, ctx, f"{query}", query_obj=query):
                raise QueryUnauthorized(
                    _("{query} is not an allowed query.").format(query=query.to_string_user())
                )
            if query.single_track:
                first_track_only = True
                index = query.track_index
                if query.start_time:
                    seek = query.start_time
            if query.is_url:
                playlist_url = query.uri
            try:
                result, called_api = await self.api_interface.fetch_track(ctx, player, query)
            except TrackEnqueueError:
                self.update_player_lock(ctx, False)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable to Get Track"),
                    description=_(
                        "I'm unable to get a track from Lavalink node at the moment, "
                        "try again in a few minutes."
                    ),
                )
            except Exception as e:
                self.update_player_lock(ctx, False)
                raise e
            tracks = result.tracks
            playlist_data = result.playlist_info
            if not enqueue:
                return tracks
            if not tracks:
                self.update_player_lock(ctx, False)
                title = _("Nothing found.")
                embed = discord.Embed(title=title)
                if result.exception_message:
                    if "Status Code" in result.exception_message:
                        embed.set_footer(text=result.exception_message[:2000])
                    else:
                        embed.set_footer(text=result.exception_message[:2000].replace("\n", ""))
                if await self.config.use_external_lavalink() and query.is_local:
                    embed.description = _(
                        "Local tracks will not work "
                        "if the `Lavalink.jar` cannot see the track.\n"
                        "This may be due to permissions or because Lavalink.jar is being run "
                        "in a different machine than the local tracks."
                    )
                elif query.is_local and query.suffix in _PARTIALLY_SUPPORTED_MUSIC_EXT:
                    title = _("Track is not playable.")
                    embed = discord.Embed(title=title)
                    embed.description = _(
                        "**{suffix}** is not a fully supported format and some "
                        "tracks may not play."
                    ).format(suffix=query.suffix)
                return await self.send_embed_msg(ctx, embed=embed)
        else:
            tracks = query
        queue_dur = await self.queue_duration(ctx)
        queue_total_duration = self.format_time(queue_dur)
        before_queue_length = len(player.queue)

        if not first_track_only and len(tracks) > 1:
            # a list of Tracks where all should be enqueued
            # this is a Spotify playlist already made into a list of Tracks or a
            # url where Lavalink handles providing all Track objects to use, like a
            # YouTube or SoundCloud playlist
            if len(player.queue) >= 10000:
                return await self.send_embed_msg(ctx, title=_("Queue size limit reached."))
            track_len = 0
            empty_queue = not player.queue
            async for track in AsyncIter(tracks):
                if len(player.queue) >= 10000:
                    continue
                track_query = Query.process_input(track, self.local_folder_current_path)
                if not await self.is_query_allowed(
                    self.config,
                    ctx,
                    f"{track.title} {track.author} {track.uri} " f"{str(track_query)}",
                    query_obj=track_query,
                ):
                    log.debug("Query is not allowed in %r (%s)", ctx.guild.name, ctx.guild.id)
                    continue
                elif guild_data["maxlength"] > 0:
                    if self.is_track_length_allowed(track, guild_data["maxlength"]):
                        track_len += 1
                        track.extras.update(
                            {
                                "enqueue_time": int(time.time()),
                                "vc": player.channel.id,
                                "requester": ctx.author.id,
                            }
                        )
                        player.add(ctx.author, track)
                        self.bot.dispatch(
                            "red_audio_track_enqueue", player.guild, track, ctx.author
                        )

                else:
                    track_len += 1
                    track.extras.update(
                        {
                            "enqueue_time": int(time.time()),
                            "vc": player.channel.id,
                            "requester": ctx.author.id,
                        }
                    )
                    player.add(ctx.author, track)
                    self.bot.dispatch("red_audio_track_enqueue", player.guild, track, ctx.author)
            player.maybe_shuffle(0 if empty_queue else 1)

            if len(tracks) > track_len:
                maxlength_msg = _(" {bad_tracks} tracks cannot be queued.").format(
                    bad_tracks=(len(tracks) - track_len)
                )
            else:
                maxlength_msg = ""
            playlist_name = escape(
                playlist_data.name if playlist_data else _("No Title"), formatting=True
            )
            title = _("Playlist Enqueued") if not query.is_album else _("Album Enqueued")
            embed = discord.Embed(
                description=bold(f"[{playlist_name}]({playlist_url})", False)
                if playlist_url
                else playlist_name,
                title=title,
            )
            embed.set_footer(
                text=_("Added {num} tracks to the queue.{maxlength_msg}").format(
                    num=track_len, maxlength_msg=maxlength_msg
                )
            )
            if not guild_data["shuffle"] and queue_dur > 0:
                embed.set_footer(
                    text=_(
                        "{time} until start of playlist playback: starts at #{position} in queue"
                    ).format(time=queue_total_duration, position=before_queue_length + 1)
                )
            if not player.current:
                await player.play()
            self.update_player_lock(ctx, False)
            message = await self.send_embed_msg(ctx, embed=embed)
            return tracks or message
        else:
            single_track = None
            # a ytsearch: prefixed item where we only need the first Track returned
            # this is in the case of [p]play <query>, a single Spotify url/code
            # or this is a localtrack item
            try:
                if len(player.queue) >= 10000:
                    return await self.send_embed_msg(ctx, title=_("Queue size limit reached."))

                single_track = (
                    tracks
                    if isinstance(tracks, lavalink.rest_api.Track)
                    else tracks[index]
                    if index
                    else tracks[0]
                )
                if seek and seek > 0:
                    single_track.start_timestamp = seek * 1000
                query = Query.process_input(single_track, self.local_folder_current_path)
                if not await self.is_query_allowed(
                    self.config,
                    ctx,
                    (
                        f"{single_track.title} {single_track.author} {single_track.uri} "
                        f"{str(query)}"
                    ),
                    query_obj=query,
                ):
                    log.debug("Query is not allowed in %r (%s)", ctx.guild.name, ctx.guild.id)
                    self.update_player_lock(ctx, False)
                    return await self.send_embed_msg(
                        ctx, title=_("This track is not allowed in this server.")
                    )
                elif guild_data["maxlength"] > 0:
                    if self.is_track_length_allowed(single_track, guild_data["maxlength"]):
                        single_track.extras.update(
                            {
                                "enqueue_time": int(time.time()),
                                "vc": player.channel.id,
                                "requester": ctx.author.id,
                            }
                        )
                        player.add(ctx.author, single_track)
                        player.maybe_shuffle()
                        self.bot.dispatch(
                            "red_audio_track_enqueue",
                            player.guild,
                            single_track,
                            ctx.author,
                        )
                    else:
                        self.update_player_lock(ctx, False)
                        return await self.send_embed_msg(
                            ctx, title=_("Track exceeds maximum length.")
                        )

                else:
                    single_track.extras.update(
                        {
                            "enqueue_time": int(time.time()),
                            "vc": player.channel.id,
                            "requester": ctx.author.id,
                        }
                    )
                    player.add(ctx.author, single_track)
                    player.maybe_shuffle()
                    self.bot.dispatch(
                        "red_audio_track_enqueue", player.guild, single_track, ctx.author
                    )
            except IndexError:
                self.update_player_lock(ctx, False)
                title = _("Nothing found")
                desc = None
                if await self.bot.is_owner(ctx.author):
                    desc = _("Please check your console or logs for details.")
                return await self.send_embed_msg(ctx, title=title, description=desc)
            except Exception as e:
                self.update_player_lock(ctx, False)
                raise e
            description = await self.get_track_description(
                single_track, self.local_folder_current_path
            )
            embed = discord.Embed(title=_("Track Enqueued"), description=description)
            if not guild_data["shuffle"] and queue_dur > 0:
                embed.set_footer(
                    text=_("{time} until track playback: #{position} in queue").format(
                        time=queue_total_duration, position=before_queue_length + 1
                    )
                )

        if not player.current:
            await player.play()
        self.update_player_lock(ctx, False)
        message = await self.send_embed_msg(ctx, embed=embed)
        return single_track or message

    async def fetch_spotify_playlist(
        self,
        ctx: commands.Context,
        stype: str,
        query: Query,
        enqueue: bool = False,
        forced: bool = False,
    ):
        player = lavalink.get_player(ctx.guild.id)
        try:
            embed1 = discord.Embed(title=_("Please wait, finding tracks..."))
            playlist_msg = await self.send_embed_msg(ctx, embed=embed1)
            notifier = Notifier(
                ctx,
                playlist_msg,
                {
                    "spotify": _("Getting track {num}/{total}..."),
                    "youtube": _("Matching track {num}/{total}..."),
                    "lavalink": _("Loading track {num}/{total}..."),
                    "lavalink_time": _("Approximate time remaining: {seconds}"),
                },
            )
            track_list = await self.api_interface.spotify_enqueue(
                ctx,
                stype,
                query.id,
                enqueue=enqueue,
                player=player,
                lock=self.update_player_lock,
                notifier=notifier,
                forced=forced,
                query_global=self.global_api_user.get("can_read"),
            )
        except SpotifyFetchError as error:
            self.update_player_lock(ctx, False)
            return await self.send_embed_msg(
                ctx,
                title=_("Invalid Environment"),
                description=error.message.format(prefix=ctx.prefix),
            )
        except TrackEnqueueError:
            self.update_player_lock(ctx, False)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable to Get Track"),
                description=_(
                    "I'm unable to get a track from Lavalink at the moment, "
                    "try again in a few minutes."
                ),
                error=True,
            )
        except (RuntimeError, aiohttp.ServerDisconnectedError):
            self.update_player_lock(ctx, False)
            error_embed = discord.Embed(
                title=_("The connection was reset while loading the playlist.")
            )
            await self.send_embed_msg(ctx, embed=error_embed)
            return None
        except Exception as e:
            self.update_player_lock(ctx, False)
            raise e
        finally:
            self.update_player_lock(ctx, False)
        return track_list

    async def set_player_settings(self, ctx: commands.Context) -> None:
        player = lavalink.get_player(ctx.guild.id)
        shuffle = await self.config.guild(ctx.guild).shuffle()
        repeat = await self.config.guild(ctx.guild).repeat()
        volume = await self.config.guild(ctx.guild).volume()
        shuffle_bumped = await self.config.guild(ctx.guild).shuffle_bumped()
        player.repeat = repeat
        player.shuffle = shuffle
        player.shuffle_bumped = shuffle_bumped
        if player.volume != volume:
            await player.set_volume(volume)

    async def maybe_move_player(self, ctx: commands.Context) -> bool:
        try:
            player = lavalink.get_player(ctx.guild.id)
        except PlayerNotFound:
            return False
        try:
            in_channel = sum(
                not m.bot for m in ctx.guild.get_member(self.bot.user.id).voice.channel.members
            )
        except AttributeError:
            return False

        if not ctx.author.voice:
            user_channel = None
        else:
            user_channel = ctx.author.voice.channel

        if in_channel == 0 and user_channel:
            if (
                (player.channel != user_channel)
                and not player.current
                and player.position == 0
                and len(player.queue) == 0
            ):
                await player.move_to(
                    user_channel,
                    self_deaf=await self.config.guild_from_id(ctx.guild.id).auto_deafen(),
                )
                return True
        else:
            return False

    def is_track_length_allowed(self, track: lavalink.Track, maxlength: int) -> bool:
        if track.is_stream:
            return True
        length = track.length / 1000
        if length > maxlength:
            return False
        return True
