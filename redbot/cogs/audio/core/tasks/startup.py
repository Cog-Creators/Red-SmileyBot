import asyncio
import itertools
from pathlib import Path

from typing import Optional

import lavalink
from lavalink import NodeNotFound, PlayerNotFound
from red_commons.logging import getLogger

from redbot.core.data_manager import cog_data_path
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter
from redbot.core.utils.dbtools import APSWConnectionWrapper

from ...apis.interface import AudioAPIInterface
from ...apis.playlist_wrapper import PlaylistWrapper
from ...errors import DatabaseError, TrackEnqueueError
from ..abc import MixinMeta
from ..cog_utils import _SCHEMA_VERSION, CompositeMetaClass

log = getLogger("red.cogs.Audio.cog.Tasks.startup")
_ = Translator("Audio", Path(__file__))


class StartUpTasks(MixinMeta, metaclass=CompositeMetaClass):
    def start_up_task(self):
        # There has to be a task since this requires the bot to be ready
        # If it waits for ready in startup, we cause a deadlock during initial load
        # as initial load happens before the bot can ever be ready.
        lavalink.set_logging_level(self.bot._cli_flags.logging_level)
        self.cog_init_task = asyncio.create_task(self.initialize())

    async def initialize(self) -> None:
        await self.bot.wait_until_red_ready()
        # Unlike most cases, we want the cache to exit before migration.
        try:
            self.db_conn = APSWConnectionWrapper(
                str(cog_data_path(self.bot.get_cog("Audio")) / "Audio.db")
            )
            self.api_interface = AudioAPIInterface(
                self.bot, self.config, self.session, self.db_conn, self.bot.get_cog("Audio")
            )
            self.playlist_api = PlaylistWrapper(self.bot, self.config, self.db_conn)
            await self.playlist_api.init()
            await self.api_interface.initialize()
            self.global_api_user = await self.api_interface.global_cache_api.get_perms()
            await self.data_schema_migration(
                from_version=await self.config.schema_version(), to_version=_SCHEMA_VERSION
            )
            await self.playlist_api.delete_scheduled()
            await self.api_interface.persistent_queue_api.delete_scheduled()
            await self._build_bundled_playlist()
            self.lavalink_restart_connect()
            self.player_automated_timer_task = asyncio.create_task(self.player_automated_timer())
        except Exception as exc:
            log.critical("Audio failed to start up, please report this issue.", exc_info=exc)
            return

        self.cog_ready_event.set()

    async def restore_players(self):
        log.debug("Starting new restore player task")
        tries = 0
        tracks_to_restore = await self.api_interface.persistent_queue_api.fetch_all()
        while not lavalink.get_all_nodes():
            await asyncio.sleep(1)
            log.trace("Waiting for node to be available")
            tries += 1
            if tries > 600:  # Give 10 minutes from node creation date.
                log.warning("Unable to restore players, couldn't connect to Lavalink node.")
                return
        try:
            for node in lavalink.get_all_nodes():
                if not node.ready:
                    log.trace("Waiting for node: %r", node)
                    await node.wait_until_ready(timeout=60)  # In theory this should be instant.
        except asyncio.TimeoutError:
            log.error(
                "Restoring player task aborted due to a timeout waiting for Lavalink node to be ready."
            )
            log.warning("Audio will attempt queue restore on next restart.")
            return
        metadata = {}
        all_guilds = await self.config.all_guilds()
        async for guild_id, guild_data in AsyncIter(all_guilds.items(), steps=100):
            if guild_data["auto_play"]:
                if guild_data["currently_auto_playing_in"]:
                    notify_channel, vc_id = guild_data["currently_auto_playing_in"]
                    metadata[guild_id] = (notify_channel, vc_id)
        if self.lavalink_connection_aborted:
            log.warning("Aborting player restore due to Lavalink connection being aborted.")
            return
        for guild_id, track_data in itertools.groupby(tracks_to_restore, key=lambda x: x.guild_id):
            await asyncio.sleep(0)
            tries = 0
            try:
                player: Optional[lavalink.Player] = None
                track_data = list(track_data)
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    log.verbose(
                        "Skipping player restore - Bot is no longer in Guild (%s)", guild_id
                    )
                    continue
                persist_cache = self._persist_queue_cache.setdefault(
                    guild_id, await self.config.guild(guild).persist_queue()
                )
                if not persist_cache:
                    log.verbose(
                        "Skipping player restore - Guild (%s) does not have a persist cache",
                        guild_id,
                    )
                    await self.api_interface.persistent_queue_api.drop(guild_id)
                    continue
                try:
                    player = lavalink.get_player(guild_id)
                except (NodeNotFound, PlayerNotFound):
                    player = None
                vc = 0
                guild_data = await self.config.guild_from_id(guild.id).all()
                shuffle = guild_data["shuffle"]
                repeat = guild_data["repeat"]
                volume = guild_data["volume"]
                shuffle_bumped = guild_data["shuffle_bumped"]
                auto_deafen = guild_data["auto_deafen"]

                if player is None:
                    while tries < 5 and vc is not None:
                        try:
                            notify_channel_id, vc_id = metadata.pop(
                                guild_id, (None, track_data[-1].room_id)
                            )
                            vc = guild.get_channel(vc_id)
                            if not vc:
                                break
                            perms = vc.permissions_for(guild.me)
                            if not (perms.connect and perms.speak):
                                vc = None
                                break
                            player = await lavalink.connect(vc, self_deaf=auto_deafen)
                            player.store("notify_channel", notify_channel_id)
                            break
                        except NodeNotFound:
                            await asyncio.sleep(5)
                            tries += 1
                        except Exception as exc:
                            tries += 1
                            log.debug(
                                "Failed to restore music voice channel %s", vc_id, exc_info=exc
                            )
                            if vc is None:
                                break
                            else:
                                await asyncio.sleep(1)

                if tries >= 5 or vc is None or player is None:
                    if tries >= 5:
                        log.verbose(
                            "Skipping player restore - Guild (%s), 5 attempts to restore player failed.",
                            guild_id,
                        )
                    elif vc is None:
                        log.verbose(
                            "Skipping player restore - Guild (%s), VC (%s) does not exist.",
                            guild_id,
                            vc_id,
                        )
                    else:
                        log.verbose(
                            "Skipping player restore - Guild (%s), Unable to create player for VC (%s).",
                            guild_id,
                            vc_id,
                        )
                    await self.api_interface.persistent_queue_api.drop(guild_id)
                    continue

                player.repeat = repeat
                player.shuffle = shuffle
                player.shuffle_bumped = shuffle_bumped
                if player.volume != volume:
                    await player.set_volume(volume)
                for track in track_data:
                    track = track.track_object
                    player.add(guild.get_member(track.extras.get("requester")) or guild.me, track)
                player.maybe_shuffle()
                if not player.is_playing:
                    await player.play()
                log.debug("Restored %r", player)
            except Exception as exc:
                log.debug("Error restoring player in %s", guild_id, exc_info=exc)
                await self.api_interface.persistent_queue_api.drop(guild_id)

        for guild_id, (notify_channel_id, vc_id) in metadata.items():
            guild = self.bot.get_guild(guild_id)
            player: Optional[lavalink.Player] = None
            vc = 0
            tries = 0
            if not guild:
                continue
            if self.lavalink_connection_aborted:
                player = None
            else:
                try:
                    player = lavalink.get_player(guild_id)
                except (NodeNotFound, PlayerNotFound):
                    player = None
            if player is None:
                guild_data = await self.config.guild_from_id(guild.id).all()
                shuffle = guild_data["shuffle"]
                repeat = guild_data["repeat"]
                volume = guild_data["volume"]
                shuffle_bumped = guild_data["shuffle_bumped"]
                auto_deafen = guild_data["auto_deafen"]

                while tries < 5 and vc is not None:
                    try:
                        vc = guild.get_channel(vc_id)
                        if not vc:
                            break
                        perms = vc.permissions_for(guild.me)
                        if not (perms.connect and perms.speak):
                            vc = None
                            break
                        player = await lavalink.connect(vc, self_deaf=auto_deafen)
                        player.store("notify_channel", notify_channel_id)
                        break
                    except NodeNotFound:
                        await asyncio.sleep(5)
                        tries += 1
                    except Exception as exc:
                        tries += 1
                        log.debug("Failed to restore music voice channel %s", vc_id, exc_info=exc)
                        if vc is None:
                            break
                        else:
                            await asyncio.sleep(1)
                if tries >= 5 or vc is None or player is None:
                    if tries >= 5:
                        log.verbose(
                            "Skipping player restore - Guild (%s), 5 attempts to restore player failed.",
                            guild_id,
                        )
                    elif vc is None:
                        log.verbose(
                            "Skipping player restore - Guild (%s), VC (%s) does not exist.",
                            guild_id,
                            vc_id,
                        )
                    else:
                        log.verbose(
                            "Skipping player restore - Guild (%s), Unable to create player for VC (%s).",
                            guild_id,
                            vc_id,
                        )
                    continue

                player.repeat = repeat
                player.shuffle = shuffle
                player.shuffle_bumped = shuffle_bumped
                if player.volume != volume:
                    await player.set_volume(volume)
                player.maybe_shuffle()
                log.debug("Restored %r", player)
                if not player.is_playing:
                    notify_channel = player.fetch("notify_channel")
                    try:
                        await self.api_interface.autoplay(player, self.playlist_api)
                    except DatabaseError:
                        notify_channel = guild.get_channel_or_thread(notify_channel)
                        if notify_channel:
                            await self.send_embed_msg(
                                notify_channel, title=_("Couldn't get a valid track.")
                            )
                        return
                    except TrackEnqueueError:
                        notify_channel = guild.get_channel_or_thread(notify_channel)
                        if notify_channel:
                            await self.send_embed_msg(
                                notify_channel,
                                title=_("Unable to Get Track"),
                                description=_(
                                    "I'm unable to get a track from the Lavalink node at the moment, "
                                    "try again in a few minutes."
                                ),
                            )
                        return
        del metadata
        del all_guilds
        log.debug("Player restore task completed successfully")
