import asyncio
import contextlib
import datetime
from pathlib import Path
from typing import Dict

import discord
import lavalink
from discord.backoff import ExponentialBackoff
from red_commons.logging import getLogger

from redbot.core.i18n import Translator, set_contextual_locales_from_guild
from ...errors import DatabaseError, TrackEnqueueError
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = getLogger("red.cogs.Audio.cog.Events.lavalink")
ws_audio_log = getLogger("red.Audio.WS.Audio")

_ = Translator("Audio", Path(__file__))


class LavalinkEvents(MixinMeta, metaclass=CompositeMetaClass):
    async def lavalink_update_handler(
        self, player: lavalink.Player, event_type: lavalink.enums.PlayerState, extra
    ):
        self._last_ll_update = datetime.datetime.now(datetime.timezone.utc)
        self._ll_guild_updates.add(int(extra.get("guildId", 0)))

    async def lavalink_event_handler(
        self, player: lavalink.Player, event_type: lavalink.LavalinkEvents, extra
    ) -> None:
        current_track = player.current
        current_channel = player.channel
        guild = self.rgetattr(current_channel, "guild", None)
        if not (current_channel and guild):
            player.store("autoplay_notified", False)
            await player.stop()
            await player.disconnect()
            return
        if await self.bot.cog_disabled_in_guild(self, guild):
            await player.stop()
            await player.disconnect()
            if guild:
                await self.config.guild_from_id(guild_id=guild.id).currently_auto_playing_in.set(
                    []
                )
            return
        guild_id = self.rgetattr(guild, "id", None)
        if not guild:
            return
        # This event is rather spammy during playback - specially if there's multiple player
        #  Lets move it to Verbose that way it still there if needed alongside the other more verbose content.
        guild_data = await self.config.guild(guild).all()
        disconnect = guild_data["disconnect"]
        if event_type == lavalink.LavalinkEvents.FORCED_DISCONNECT:
            self.bot.dispatch("red_audio_audio_disconnect", guild)
            self._ll_guild_updates.discard(guild.id)
            return
        if event_type == lavalink.LavalinkEvents.WEBSOCKET_CLOSED:
            deafen = guild_data["auto_deafen"]
            event_channel_id = extra.get("channelID")
            _error_code = extra.get("code")
            if _error_code in [1000] or not guild:
                if _error_code == 1000 and player.current is not None and player.is_playing:
                    await player.resume(player.current, start=player.position, replace=True)
                    by_remote = extra.get("byRemote", "")
                    reason = extra.get("reason", "No Specified Reason").strip()
                    ws_audio_log.info(
                        "WS EVENT - SIMPLE RESUME (Healthy Socket) | "
                        "Voice websocket closed event "
                        "Code: %s -- Remote: %s -- %s",
                        extra.get("code"),
                        by_remote,
                        reason,
                    )
                    ws_audio_log.debug(
                        "WS EVENT - SIMPLE RESUME (Healthy Socket) | "
                        "Voice websocket closed event "
                        "Code: %s -- Remote: %s -- %s, %r",
                        extra.get("code"),
                        by_remote,
                        reason,
                        player,
                    )
                return
            await self._ws_op_codes[guild_id].put((event_channel_id, _error_code))
            try:
                if guild_id not in self._ws_resume:
                    self._ws_resume[guild_id].set()

                await self._websocket_closed_handler(
                    guild=guild,
                    player=player,
                    extra=extra,
                    self_deaf=deafen,
                    disconnect=disconnect,
                )
            except Exception as exc:
                log.debug(
                    "Error in WEBSOCKET_CLOSED handling for guild: %s",
                    player.guild.id,
                    exc_info=exc,
                )
            return
        if not player.node.ready:
            log.debug("Player node is not ready discarding event")
            log.verbose(
                "Received a new discard lavalink event for %s: %s: %r", guild_id, event_type, extra
            )
            return
        log.verbose("Received a new lavalink event for %s: %s: %r", guild_id, event_type, extra)
        await set_contextual_locales_from_guild(self.bot, guild)
        current_requester = self.rgetattr(current_track, "requester", None)
        current_stream = self.rgetattr(current_track, "is_stream", None)
        current_length = self.rgetattr(current_track, "length", None)
        current_thumbnail = self.rgetattr(current_track, "thumbnail", None)
        current_id = self.rgetattr(current_track, "_info", {}).get("identifier")

        repeat = guild_data["repeat"]
        notify = guild_data["notify"]
        autoplay = guild_data["auto_play"]
        description = await self.get_track_description(
            current_track, self.local_folder_current_path
        )
        status = await self.config.status()
        prev_song: lavalink.Track = player.fetch("prev_song")
        await self.maybe_reset_error_counter(player)

        if event_type == lavalink.LavalinkEvents.TRACK_START:
            self.skip_votes[guild_id] = set()
            playing_song = player.fetch("playing_song")
            requester = player.fetch("requester")
            player.store("prev_song", playing_song)
            player.store("prev_requester", requester)
            player.store("playing_song", current_track)
            player.store("requester", current_requester)
            self.bot.dispatch("red_audio_track_start", guild, current_track, current_requester)
            if guild_id and current_track:
                await self.api_interface.persistent_queue_api.played(
                    guild_id=guild_id, track_id=current_track.track_identifier
                )
            notify_channel = player.fetch("notify_channel")
            if notify_channel and autoplay:
                await self.config.guild_from_id(guild_id=guild_id).currently_auto_playing_in.set(
                    [notify_channel, player.channel.id]
                )
            else:
                await self.config.guild_from_id(guild_id=guild_id).currently_auto_playing_in.set(
                    []
                )
        if event_type == lavalink.LavalinkEvents.TRACK_END:
            prev_requester = player.fetch("prev_requester")
            self.bot.dispatch("red_audio_track_end", guild, prev_song, prev_requester)
            player.store("resume_attempts", 0)
        if event_type == lavalink.LavalinkEvents.QUEUE_END:
            prev_requester = player.fetch("prev_requester")
            self.bot.dispatch("red_audio_queue_end", guild, prev_song, prev_requester)
            if guild_id:
                await self.api_interface.persistent_queue_api.drop(guild_id)
            if player.is_auto_playing or (
                autoplay
                and not player.queue
                and player.fetch("playing_song") is not None
                and self.playlist_api is not None
                and self.api_interface is not None
            ):
                notify_channel_id = player.fetch("notify_channel")
                try:
                    await self.api_interface.autoplay(player, self.playlist_api)
                except DatabaseError:
                    notify_channel = guild.get_channel_or_thread(notify_channel_id)
                    if notify_channel and self._has_notify_perms(notify_channel):
                        await self.send_embed_msg(
                            notify_channel, title=_("Couldn't get a valid track.")
                        )
                    return
                except TrackEnqueueError:
                    notify_channel = guild.get_channel_or_thread(notify_channel_id)
                    if notify_channel and self._has_notify_perms(notify_channel):
                        await self.send_embed_msg(
                            notify_channel,
                            title=_("Unable to Get Track"),
                            description=_(
                                "I'm unable to get a track from the Lavalink node at the moment, try again in a few "
                                "minutes."
                            ),
                        )
                    return
        if event_type == lavalink.LavalinkEvents.TRACK_START and notify:
            notify_channel_id = player.fetch("notify_channel")
            notify_channel = guild.get_channel_or_thread(notify_channel_id)
            if notify_channel and self._has_notify_perms(notify_channel):
                if player.fetch("notify_message") is not None:
                    with contextlib.suppress(discord.HTTPException):
                        await player.fetch("notify_message").delete()
                if not (description and notify_channel):
                    return
                if current_stream:
                    dur = "LIVE"
                else:
                    dur = self.format_time(current_length)

                thumb = None
                if await self.config.guild(guild).thumbnail() and current_thumbnail:
                    thumb = current_thumbnail

                notify_message = await self.send_embed_msg(
                    notify_channel,
                    title=_("Now Playing"),
                    description=description,
                    footer=_("Track length: {length} | Requested by: {user}").format(
                        length=dur, user=current_requester
                    ),
                    thumbnail=thumb,
                )
                player.store("notify_message", notify_message)
        if event_type == lavalink.LavalinkEvents.TRACK_START and status:
            log.debug("Track started for %s, updating bot status", guild_id)
            player_check = await self.get_active_player_count()
            await self.update_bot_presence(*player_check)

        if event_type == lavalink.LavalinkEvents.TRACK_END and status:
            await asyncio.sleep(1)
            if not player.is_playing:
                log.debug("Track ended for %s, updating bot status", guild_id)
                player_check = await self.get_active_player_count()
                await self.update_bot_presence(*player_check)

        if event_type == lavalink.LavalinkEvents.QUEUE_END:
            if not autoplay:
                notify_channel_id = player.fetch("notify_channel")
                notify_channel = guild.get_channel_or_thread(notify_channel_id)
                if notify_channel and notify and self._has_notify_perms(notify_channel):
                    await self.send_embed_msg(notify_channel, title=_("Queue ended."))
                if disconnect:
                    log.debug(
                        "Queue ended for %s, Disconnecting bot due to configuration", guild_id
                    )
                    self.bot.dispatch("red_audio_audio_disconnect", guild)
                    await self.config.guild_from_id(
                        guild_id=guild_id
                    ).currently_auto_playing_in.set([])
                    # let audio buffer run out on slower machines (GH-5158)
                    await asyncio.sleep(2)
                    await player.disconnect()
                    self._ll_guild_updates.discard(guild.id)
            if status:
                log.debug("Queue ended for %s, updating bot status", guild_id)
                player_check = await self.get_active_player_count()
                await self.update_bot_presence(*player_check)

        if event_type in [
            lavalink.LavalinkEvents.TRACK_EXCEPTION,
            lavalink.LavalinkEvents.TRACK_STUCK,
        ]:
            message_channel = player.fetch("notify_channel")
            while True:
                if current_track in player.queue:
                    player.queue.remove(current_track)
                else:
                    break
            if repeat:
                player.current = None
            if not guild_id:
                return
            guild_id = int(guild_id)
            self._error_counter.setdefault(guild_id, 0)
            if guild_id not in self._error_counter:
                self._error_counter[guild_id] = 0
            early_exit = await self.increase_error_counter(player)
            if early_exit:
                self._disconnected_players[guild_id] = True
                self.play_lock[guild_id] = False
                eq = player.fetch("eq")
                player.queue = []
                player.store("playing_song", None)
                player.store("autoplay_notified", False)
                if eq:
                    await self.config.custom("EQUALIZER", guild_id).eq_bands.set(eq.bands)
                await player.stop()
                await player.disconnect()
                await self.config.guild_from_id(guild_id=guild_id).currently_auto_playing_in.set(
                    []
                )
                self._ll_guild_updates.discard(guild_id)
                self.bot.dispatch("red_audio_audio_disconnect", guild)
            if message_channel:
                message_channel = guild.get_channel_or_thread(message_channel)
                if early_exit:
                    log.warning(
                        "Audio detected multiple continuous errors during playback "
                        "- terminating the player for guild: %s.",
                        guild_id,
                    )
                    log.verbose(
                        "Player has been terminated due to multiple playback failures: %r", player
                    )
                    embed = discord.Embed(
                        colour=await self.bot.get_embed_color(message_channel),
                        title=_("Multiple Errors Detected"),
                        description=_(
                            "Closing the audio player "
                            "due to multiple errors being detected. "
                            "If this persists, please inform the bot owner "
                            "as the Audio cog may be temporally unavailable."
                        ),
                    )
                    await message_channel.send(embed=embed)
                    return
                else:
                    description = description or ""
                    if event_type == lavalink.LavalinkEvents.TRACK_STUCK:
                        embed = discord.Embed(
                            colour=await self.bot.get_embed_color(message_channel),
                            title=_("Track Stuck"),
                            description=_(
                                "Playback of the song has stopped due to an unexpected error.\n{error}"
                            ).format(error=description),
                        )
                    else:
                        embed = discord.Embed(
                            title=_("Track Error"),
                            colour=await self.bot.get_embed_color(message_channel),
                            description="{}\n{}".format(
                                extra["message"].replace("\n", ""), description
                            ),
                        )
                        if current_id:
                            asyncio.create_task(
                                self.api_interface.global_cache_api.report_invalid(current_id)
                            )
                    await message_channel.send(embed=embed)
            if player.node.ready:
                await player.skip()

    async def _websocket_closed_handler(
        self,
        guild: discord.Guild,
        player: lavalink.Player,
        extra: Dict,
        self_deaf: bool,
        disconnect: bool,
    ) -> None:
        guild_id = guild.id
        shard = self.bot.shards[guild.shard_id]
        event_channel_id = extra.get("channelID")
        try:
            if not self._ws_resume[guild_id].is_set():
                await self._ws_resume[guild_id].wait()
            else:
                self._ws_resume[guild_id].clear()
            code = extra.get("code")
            by_remote = extra.get("byRemote", "")
            reason = extra.get("reason", "No Specified Reason").strip()
            channel_id = player.channel.id
            try:
                event_channel_id, to_handle_code = await self._ws_op_codes[guild_id].get()
            except asyncio.QueueEmpty:
                log.debug("Empty queue - Resuming Processor - Early exit")
                return

            if code != to_handle_code:
                code = to_handle_code
                if player.channel.id != event_channel_id:
                    code = 4014
            if event_channel_id != channel_id:
                ws_audio_log.debug(
                    "Received an op code for a channel that is no longer valid; %s "
                    "Reason: Error code %s & %s, %r",
                    event_channel_id,
                    code,
                    reason,
                    player,
                )
                self._ws_op_codes[guild_id]._init(self._ws_op_codes[guild_id]._maxsize)
                return
            if player.channel:
                has_perm = self.can_join_and_speak(player.channel)
            else:
                has_perm = False
            if code in (1000,) and has_perm and player.current and player.is_playing:
                player.store("resumes", player.fetch("resumes", 0) + 1)
                await player.resume(player.current, start=player.position, replace=True)
                ws_audio_log.info("Player resumed | Reason: Error code %s & %s", code, reason)
                ws_audio_log.debug(
                    "Player resumed | Reason: Error code %s & %s, %r", code, reason, player
                )
                self._ws_op_codes[guild_id]._init(self._ws_op_codes[guild_id]._maxsize)
                return

            if shard.is_closed():
                if player._con_delay:
                    delay = player._con_delay.delay()
                else:
                    player._con_delay = ExponentialBackoff(base=1)
                    delay = player._con_delay.delay()
                ws_audio_log.debug(
                    "YOU CAN IGNORE THIS UNLESS IT'S CONSISTENTLY REPEATING FOR THE SAME GUILD - "
                    "Voice websocket closed for guild %s -> "
                    "Socket Closed %s.  "
                    "Code: %s -- Remote: %s -- %s, %r",
                    guild_id,
                    shard.is_closed(),
                    code,
                    by_remote,
                    reason,
                    player,
                )
                ws_audio_log.info(
                    "Reconnecting to channel %s in guild: %s | %.2fs",
                    channel_id,
                    guild_id,
                    delay,
                )
                await asyncio.sleep(delay)
                while shard.is_closed():
                    await asyncio.sleep(0.1)

                if has_perm and player.current and player.is_playing:
                    player.store("resumes", player.fetch("resumes", 0) + 1)
                    await player.connect(self_deaf=self_deaf)
                    await player.resume(player.current, start=player.position, replace=True)
                    ws_audio_log.info(
                        "Voice websocket reconnected Reason: Error code %s & Currently playing",
                        code,
                    )
                    ws_audio_log.debug(
                        "Voice websocket reconnected "
                        "Reason: Error code %s & Currently playing, %r",
                        code,
                        player,
                    )
                elif has_perm and player.paused and player.current:
                    player.store("resumes", player.fetch("resumes", 0) + 1)
                    await player.connect(self_deaf=self_deaf)
                    await player.resume(
                        player.current, start=player.position, replace=True, pause=True
                    )
                    ws_audio_log.info(
                        "Voice websocket reconnected Reason: Error code %s & Currently Paused",
                        code,
                    )
                    ws_audio_log.debug(
                        "Voice websocket reconnected "
                        "Reason: Error code %s & Currently Paused, %r",
                        code,
                        player,
                    )
                elif has_perm and (not disconnect) and (not player.is_playing):
                    player.store("resumes", player.fetch("resumes", 0) + 1)
                    await player.connect(self_deaf=self_deaf)
                    ws_audio_log.info(
                        "Voice websocket reconnected "
                        "Reason: Error code %s & Not playing, but auto disconnect disabled",
                        code,
                    )
                    ws_audio_log.debug(
                        "Voice websocket reconnected "
                        "Reason: Error code %s & Not playing, but auto disconnect disabled, %r",
                        code,
                        player,
                    )
                    self._ll_guild_updates.discard(guild_id)
                elif not has_perm:
                    self.bot.dispatch("red_audio_audio_disconnect", guild)
                    ws_audio_log.info(
                        "Voice websocket disconnected "
                        "Reason: Error code %s & Missing permissions",
                        code,
                    )
                    ws_audio_log.debug(
                        "Voice websocket disconnected "
                        "Reason: Error code %s & Missing permissions, %r",
                        code,
                        player,
                    )
                    self._ll_guild_updates.discard(guild_id)
                    player.store("autoplay_notified", False)
                    await player.stop()
                    await player.disconnect()
                    await self.config.guild_from_id(
                        guild_id=guild_id
                    ).currently_auto_playing_in.set([])
                else:
                    self.bot.dispatch("red_audio_audio_disconnect", guild)
                    ws_audio_log.info(
                        "Voice websocket disconnected Reason: Error code %s & Unknown", code
                    )
                    ws_audio_log.debug(
                        "Voice websocket disconnected Reason: Error code %s & Unknown, %r",
                        code,
                        player,
                    )
                    self._ll_guild_updates.discard(guild_id)
                    player.store("autoplay_notified", False)
                    await player.stop()
                    await player.disconnect()
                    await self.config.guild_from_id(
                        guild_id=guild_id
                    ).currently_auto_playing_in.set([])
            elif code in (42069,) and has_perm and player.current and player.is_playing:
                player.store("resumes", player.fetch("resumes", 0) + 1)
                await player.connect(self_deaf=self_deaf)
                await player.resume(player.current, start=player.position, replace=True)
                ws_audio_log.info("Player resumed - Reason: Error code %s & %s", code, reason)
                ws_audio_log.debug(
                    "Player resumed - Reason: Error code %s & %s, %r", code, reason, player
                )
            elif code in (4015, 4009, 4006, 4000, 1006):
                if player._con_delay:
                    delay = player._con_delay.delay()
                else:
                    player._con_delay = ExponentialBackoff(base=1)
                    delay = player._con_delay.delay()
                ws_audio_log.debug(
                    "Reconnecting to channel %s in guild: %s | %.2fs", channel_id, guild_id, delay
                )
                await asyncio.sleep(delay)
                if has_perm and player.current and player.is_playing:
                    await player.connect(self_deaf=self_deaf)
                    await player.resume(player.current, start=player.position, replace=True)
                    ws_audio_log.info(
                        "Voice websocket reconnected Reason: Error code %s & Player is active",
                        code,
                    )
                    ws_audio_log.debug(
                        "Voice websocket reconnected "
                        "Reason: Error code %s & Player is active, %r",
                        code,
                        player,
                    )
                elif has_perm and player.paused and player.current:
                    player.store("resumes", player.fetch("resumes", 0) + 1)
                    await player.connect(self_deaf=self_deaf)
                    await player.resume(
                        player.current, start=player.position, replace=True, pause=True
                    )
                    ws_audio_log.info(
                        "Voice websocket reconnected Reason: Error code %s & Player is paused",
                        code,
                    )
                    ws_audio_log.debug(
                        "Voice websocket reconnected "
                        "Reason: Error code %s & Player is paused, %r",
                        code,
                        player,
                    )
                elif has_perm and (not disconnect) and (not player.is_playing):
                    player.store("resumes", player.fetch("resumes", 0) + 1)
                    await player.connect(self_deaf=self_deaf)
                    ws_audio_log.info(
                        "Voice websocket reconnected "
                        "to channel %s in guild: %s | "
                        "Reason: Error code %s & Not playing",
                        channel_id,
                        guild_id,
                        code,
                    )
                    ws_audio_log.debug(
                        "Voice websocket reconnected "
                        "to channel %s in guild: %s | "
                        "Reason: Error code %s & Not playing, %r",
                        channel_id,
                        guild_id,
                        code,
                        player,
                    )
                    self._ll_guild_updates.discard(guild_id)
                elif not has_perm:
                    self.bot.dispatch("red_audio_audio_disconnect", guild)
                    ws_audio_log.info(
                        "Voice websocket disconnected "
                        "Reason: Error code %s & Missing permissions",
                        code,
                    )
                    ws_audio_log.debug(
                        "Voice websocket disconnected "
                        "Reason: Error code %s & Missing permissions, %r",
                        code,
                        player,
                    )
                    self._ll_guild_updates.discard(guild_id)
                    player.store("autoplay_notified", False)
                    await player.stop()
                    await player.disconnect()
                    await self.config.guild_from_id(
                        guild_id=guild_id
                    ).currently_auto_playing_in.set([])
            else:
                if not player.paused and player.current:
                    player.store("resumes", player.fetch("resumes", 0) + 1)
                    await player.resume(player.current, start=player.position, replace=True)
                    ws_audio_log.info(
                        "WS EVENT - SIMPLE RESUME (Healthy Socket) | "
                        "Voice websocket closed event "
                        "Code: %s -- Remote: %s -- %s",
                        code,
                        by_remote,
                        reason,
                    )
                    ws_audio_log.debug(
                        "WS EVENT - SIMPLE RESUME (Healthy Socket) | "
                        "Voice websocket closed event "
                        "Code: %s -- Remote: %s -- %s, %r",
                        code,
                        by_remote,
                        reason,
                        player,
                    )
                else:
                    ws_audio_log.info(
                        "WS EVENT - IGNORED (Healthy Socket) | "
                        "Voice websocket closed event "
                        "Code: %s -- Remote: %s -- %s",
                        code,
                        by_remote,
                        reason,
                    )
                    ws_audio_log.debug(
                        "WS EVENT - IGNORED (Healthy Socket) | "
                        "Voice websocket closed event "
                        "Code: %s -- Remote: %s -- %s, %r",
                        code,
                        by_remote,
                        reason,
                        player,
                    )
        except Exception as exc:
            log.exception("Error in task", exc_info=exc)
        finally:
            self._ws_op_codes[guild_id]._init(self._ws_op_codes[guild_id]._maxsize)
            self._ws_resume[guild_id].set()
