import asyncio
import contextlib
import random
import re

from collections import OrderedDict
from pathlib import Path
from string import ascii_letters, digits
from typing import Final, Pattern

import discord
import lavalink
from red_commons.logging import getLogger

from aiohttp import ClientConnectorError
from discord.ext.commands import CheckFailure
from lavalink import NodeNotFound, PlayerNotFound

from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils import can_user_send_messages_in
from redbot.core.utils.antispam import AntiSpam
from redbot.core.utils.chat_formatting import box, humanize_list, underline, bold

from ...errors import TrackEnqueueError, AudioError
from ...managed_node import version_pins
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = getLogger("red.cogs.Audio.cog.Events.dpy")
_T = Translator("Audio", Path(__file__))
_ = lambda s: s
RE_CONVERSION: Final[Pattern] = re.compile('Converting to "(.*)" failed for parameter "(.*)".')
HUMANIZED_PERM = {
    "create_instant_invite": _("Create Instant Invite"),
    "kick_members": _("Kick Members"),
    "ban_members": _("Ban Members"),
    "administrator": _("Administrator"),
    "manage_channels": _("Manage Channels"),
    "manage_guild": _("Manage Server"),
    "add_reactions": _("Add Reactions"),
    "view_audit_log": _("View Audit Log"),
    "priority_speaker": _("Priority Speaker"),
    "stream": _("Video"),
    "read_messages": _("Read Text Channels & See Voice Channels"),
    "send_messages": _("Send Messages"),
    "send_tts_messages": _("Send Text-to-speech Messages"),
    "manage_messages": _("Manage Messages"),
    "embed_links": _("Embed Links"),
    "attach_files": _("Attach Files"),
    "read_message_history": _("Read Message History"),
    "mention_everyone": _("Mention @everyone, @here, and All Roles"),
    "external_emojis": _("Use External Emojis"),
    "view_guild_insights": _("View Server Insights"),
    "connect": _("Connect"),
    "speak": _("Speak"),
    "mute_members": _("Mute Members"),
    "deafen_members": _("Deafen Members"),
    "move_members": _("Move Members"),
    "use_voice_activation": _("Use Voice Activity"),
    "change_nickname": _("Change Nickname"),
    "manage_nicknames": _("Manage Nicknames"),
    "manage_roles": _("Manage Roles"),
    "manage_webhooks": _("Manage Webhooks"),
    "manage_expressions": _("Manage Expressions"),
    "use_application_commands": _("Use Application Commands"),
    "request_to_speak": _("Request to Speak"),
    "manage_events": _("Manage Events"),
    "manage_threads": _("Manage Threads"),
    "create_public_threads": _("Create Public Threads"),
    "create_private_threads": _("Create Private Threads"),
    "external_stickers": _("Use External Stickers"),
    "send_messages_in_threads": _("Send Messages in Threads"),
    "use_embedded_activities": _("Use Activities"),
    "moderate_members": _("Time out members"),
    "view_creator_monetization_analytics": _("View Creator Monetization Analytics"),
    "use_soundboard": _("Use Soundboard"),
    "create_expressions": _("Create Expressions"),
    "create_events": _("Create Events"),
    "use_external_sounds": _("Use External Sounds"),
    "send_voice_messages": _("Send Voice Messages"),
    "send_polls": _("Create Polls"),
    "use_external_apps": _("Use External Apps"),
}

DANGEROUS_COMMANDS = {
    "command_llset_java": _(
        "This command will change the executable path of Java, "
        "this is useful if you have multiple installations of Java and the default one is causing issues. "
        "Please don't change this unless you are certain that the Java version you are specifying is supported by Red. "
        "The supported versions are currently Java {supported_java_versions}."
    ),
    "command_llset_heapsize": _(
        "This command will change the maximum RAM allocation for the managed Lavalink node, "
        "usually you will never have to change this, "
        "before considering changing it please consult our support team."
    ),
    "command_llset_unmanaged": _(
        "This command will disable the managed Lavalink node, "
        "if you toggle this command you must specify an external Lavalink node to connect to, "
        "if you do not do so Audio will stop working."
    ),
    "command_llset_host": _(
        "This command is used to specify the IP which will be used by Red to connect to an external Lavalink node. "
    ),
    "command_llset_password": _(
        "This command is used to specify the authentication password used by Red to connect to an "
        "external Lavalink node."
    ),
    "command_llset_secured": _(
        "This command is used toggle between secured and unsecured connections to an external Lavalink node."
    ),
    "command_llset_wsport": _(
        "This command is used to specify the connection port used by Red to connect to an external Lavalink node."
    ),
    "command_llset_config_host": _(
        "This command specifies which network interface and IP the managed Lavalink node will bind to, "
        "by default this is 'localhost', "
        "only change this if you want the managed Lavalink node to bind to a specific IP/interface."
    ),
    "command_llset_config_token": _(
        "This command changes the authentication password required to connect to this managed node."
        "The default value is 'youshallnotpass'."
    ),
    "command_llset_config_port": _(
        "This command changes the connection port used to connect to this managed node, "
        "only change this if the default port '2333' is causing conflicts with existing applications."
    ),
    "command_llset_config_source_http": _(
        "This command toggles the support of direct url streams like Icecast or Shoutcast streams. "
        "An example is <http://ice1.somafm.com/gsclassic-128-mp3>; "
        "disabling this will make the bot unable to play any direct url steam content."
    ),
    "command_llset_config_source_bandcamp": _(
        "This command toggles the support of Bandcamp audio playback. "
        "An example is <http://deaddiskdrive.bandcamp.com/track/crystal-glass>; "
        "disabling this will make the bot unable to play any Bandcamp content",
    ),
    "command_llset_config_source_local": _(
        "This command toggles the support of local track audio playback. "
        "An example is `/mnt/data/my_super_funky_track.mp3`; "
        "disabling this will make the bot unable to play any local track content."
    ),
    "command_llset_config_source_soundcloud": _(
        "This command toggles the support of SoundCloud playback. "
        "An example is <https://soundcloud.com/user-103858850/tilla>; "
        "disabling this will make the bot unable to play any SoundCloud content."
    ),
    "command_llset_config_source_youtube": _(
        "This command toggles the support of YouTube playback (Spotify depends on YouTube). "
        "Disabling this will make the bot unable to play any YouTube content: "
        "this includes Spotify."
    ),
    "command_llset_config_source_twitch": _(
        "This command toggles the support of Twitch playback. "
        "An example of this is <https://twitch.tv/monstercat>; "
        "disabling this will make the bot unable to play any Twitch content."
    ),
    "command_llset_config_source_vimeo": _(
        "This command toggles the support of Vimeo playback. "
        "An example of this is <https://vimeo.com/157743578>; "
        "disabling this will make the bot unable to play any Vimeo content."
    ),
    "command_llset_config_server_framebuffer": _(
        "This setting controls the managed node's framebuffer, "
        "do not change this unless instructed."
    ),
    "command_llset_config_server_buffer": _(
        "This setting controls the managed node's JDA-NAS buffer, "
        "do not change this unless instructed."
    ),
    "command_llset_reset": _("This command will reset every setting changed by `[p]llset`."),
}

_ = _T


class DpyEvents(MixinMeta, metaclass=CompositeMetaClass):
    async def cog_before_invoke(self, ctx: commands.Context) -> None:
        await self.cog_ready_event.wait()
        # check for unsupported arch
        # Check on this needs refactoring at a later date
        # so that we have a better way to handle the tasks
        if self.command_llset in [ctx.command, ctx.command.root_parent]:
            pass

        elif self.lavalink_connect_task and self.lavalink_connect_task.cancelled():
            await ctx.send(
                _(
                    "You have attempted to run Audio's managed Lavalink node on an unsupported"
                    " architecture. Only settings related commands will be available."
                )
            )
            raise AudioError(
                "Not running Audio command due to invalid machine architecture for the managed Lavalink node."
            )

        surpass_ignore = (
            ctx.guild is None
            or await ctx.bot.is_owner(ctx.author)
            or await ctx.bot.is_admin(ctx.author)
        )
        guild = ctx.guild
        if guild and not can_user_send_messages_in(ctx.me, ctx.channel):
            log.debug(
                "Missing perms to send messages in %d, Owner ID: %d",
                guild.id,
                guild.owner.id,
            )
            if not surpass_ignore:
                text = _(
                    "I'm missing permissions to send messages in this server. "
                    "Please address this as soon as possible."
                )
                log.info(
                    "Missing write permission in %d, Owner ID: %d",
                    guild.id,
                    guild.owner.id,
                )
                raise CheckFailure(message=text)

        current_perms = ctx.bot_permissions
        if guild and not current_perms.is_superset(self.permission_cache):
            current_perms_set = set(iter(current_perms))
            expected_perms_set = set(iter(self.permission_cache))
            diff = expected_perms_set - current_perms_set
            missing_perms = dict((i for i in diff if i[-1] is not False))
            missing_perms = OrderedDict(sorted(missing_perms.items()))
            missing_permissions = missing_perms.keys()
            log.debug(
                "Missing the following perms in %s, Owner ID: %s: %s",
                ctx.guild.id,
                ctx.guild.owner.id,
                humanize_list(list(missing_permissions)),
            )
            if not surpass_ignore:
                text = _(
                    "I'm missing permissions in this server, "
                    "Please address this as soon as possible.\n\n"
                    "Expected Permissions:\n"
                )
                for perm, value in missing_perms.items():
                    text += "{perm}: [{status}]\n".format(
                        status=_("Enabled") if value else _("Disabled"),
                        perm=_(HUMANIZED_PERM.get(perm, perm)),
                    )
                text = text.strip()
                await ctx.send(box(text=text, lang="ini"))
                raise CheckFailure(message=text)

        with contextlib.suppress(Exception):
            player = lavalink.get_player(ctx.guild.id)
            notify_channel = player.fetch("notify_channel")
            if not notify_channel:
                player.store("notify_channel", ctx.channel.id)

        self._daily_global_playlist_cache.setdefault(
            self.bot.user.id, await self.config.daily_playlists()
        )
        if self.local_folder_current_path is None:
            self.local_folder_current_path = Path(await self.config.localpath())

        if ctx.command.callback.__name__ in DANGEROUS_COMMANDS and await ctx.bot.is_owner(
            ctx.author
        ):
            if ctx.command.callback.__name__ not in self.antispam[ctx.author.id]:
                self.antispam[ctx.author.id][ctx.command.callback.__name__] = AntiSpam(
                    self.llset_captcha_intervals
                )
            if not self.antispam[ctx.author.id][ctx.command.callback.__name__].spammy:
                token = random.choices((*ascii_letters, *digits), k=4)
                confirm_token = "  ".join(i for i in token)
                token = confirm_token.replace(" ", "")
                message = bold(
                    underline(_("You should not be running this command.")),
                    escape_formatting=False,
                )
                message += _(
                    "\n{template}\n"
                    "If you wish to continue, enter this case sensitive token without spaces as your next message."
                    "\n\n{confirm_token}"
                ).format(
                    template=_(DANGEROUS_COMMANDS[ctx.command.callback.__name__]).format(
                        supported_java_versions=humanize_list(
                            list(map(str, version_pins.SUPPORTED_JAVA_VERSIONS))
                        ),
                    ),
                    confirm_token=box(confirm_token, lang="py"),
                )
                sent = await ctx.send(message)
                try:
                    message = await ctx.bot.wait_for(
                        "message",
                        check=lambda m: m.channel.id == ctx.channel.id
                        and m.author.id == ctx.author.id,
                        timeout=120,
                    )
                except asyncio.TimeoutError:
                    with contextlib.suppress(discord.HTTPException):
                        await sent.add_reaction("\N{CROSS MARK}")
                    raise commands.CheckFailure
                else:
                    if message.content.strip() != token:
                        with contextlib.suppress(discord.HTTPException):
                            await sent.add_reaction("\N{CROSS MARK}")
                        raise commands.CheckFailure
                    with contextlib.suppress(discord.HTTPException):
                        await sent.add_reaction("\N{WHITE HEAVY CHECK MARK}")
                    self.antispam[ctx.author.id][ctx.command.callback.__name__].stamp()

        if not guild:
            return
        guild_data = await self.config.guild(ctx.guild).all()
        dj_enabled = self._dj_status_cache.setdefault(ctx.guild.id, guild_data["dj_enabled"])
        self._daily_playlist_cache.setdefault(ctx.guild.id, guild_data["daily_playlists"])
        self._persist_queue_cache.setdefault(ctx.guild.id, guild_data["persist_queue"])
        if dj_enabled:
            dj_role = self._dj_role_cache.setdefault(ctx.guild.id, guild_data["dj_role"])
            dj_role_obj = ctx.guild.get_role(dj_role)
            if not dj_role_obj:
                async with self.config.guild(ctx.guild).all() as write_guild_data:
                    write_guild_data["dj_enabled"] = None
                    write_guild_data["dj_role"] = None
                self._dj_status_cache[ctx.guild.id] = None
                self._dj_role_cache[ctx.guild.id] = None
                await self.send_embed_msg(ctx, title=_("No DJ role found. Disabling DJ mode."))

    async def cog_after_invoke(self, ctx: commands.Context) -> None:
        await self.maybe_run_pending_db_tasks(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: Exception) -> None:
        error = getattr(error, "original", error)
        handled = False
        if isinstance(error, commands.ArgParserFailure):
            handled = True
            msg = _("`{user_input}` is not a valid value for `{command}`").format(
                user_input=error.user_input,
                command=error.cmd,
            )
            if error.custom_help_msg:
                msg += f"\n{error.custom_help_msg}"
            await self.send_embed_msg(
                ctx,
                title=_("Unable To Parse Argument"),
                description=msg,
                error=True,
            )
            if error.send_cmd_help:
                await ctx.send_help()
        elif isinstance(error, commands.BadArgument):
            handled = True
            if error.args:
                if match := RE_CONVERSION.search(error.args[0]):
                    await self.send_embed_msg(
                        ctx,
                        title=_("Invalid Argument"),
                        description=_(
                            "The argument you gave for `{}` is not valid: I was expecting a `{}`."
                        ).format(match.group(2), match.group(1)),
                        error=True,
                    )
                else:
                    await self.send_embed_msg(
                        ctx,
                        title=_("Invalid Argument"),
                        description=error.args[0],
                        error=True,
                    )
            else:
                await ctx.send_help()
        elif isinstance(error, (NodeNotFound, ClientConnectorError)):
            handled = True
            await self.send_embed_msg(
                ctx,
                title=_("Invalid Environment"),
                description=_("Connection to Lavalink node has been lost."),
                error=True,
            )
            log.trace("This is a handled error", exc_info=error)
        elif isinstance(error, PlayerNotFound):
            handled = True
            await self.send_embed_msg(
                ctx,
                title=_("No Player Available"),
                description=_("The bot is not connected to a voice channel."),
                error=True,
            )
            log.trace("This is a handled error", exc_info=error)
        elif isinstance(error, (TrackEnqueueError, asyncio.exceptions.TimeoutError)):
            handled = True
            await self.send_embed_msg(
                ctx,
                title=_("Unable to Get Track"),
                description=_(
                    "I'm unable to get a track from the Lavalink node at the moment, "
                    "try again in a few minutes."
                ),
                error=True,
            )
            log.trace("This is a handled error", exc_info=error)
        elif isinstance(error, discord.errors.HTTPException):
            handled = True
            await self.send_embed_msg(
                ctx,
                title=_("There was an issue communicating with Discord."),
                description=_("This error has been reported to the bot owner."),
                error=True,
            )
            log.exception(
                "This is not handled in the core Audio cog, please report it.", exc_info=error
            )
        if not isinstance(
            error,
            (
                commands.CheckFailure,
                commands.UserInputError,
                commands.DisabledCommand,
                commands.CommandOnCooldown,
                commands.MaxConcurrencyReached,
            ),
        ):
            self.update_player_lock(ctx, False)
            if self.api_interface is not None:
                await self.api_interface.run_tasks(ctx)
        if not handled:
            await self.bot.on_command_error(ctx, error, unhandled_by_cog=True)

    async def cog_unload(self) -> None:
        if not self.cog_cleaned_up:
            self.bot.dispatch("red_audio_unload", self)
            await self.session.close()
            if self.player_automated_timer_task:
                self.player_automated_timer_task.cancel()

            if self.lavalink_connect_task:
                self.lavalink_connect_task.cancel()

            if self.cog_init_task:
                self.cog_init_task.cancel()

            if self._restore_task:
                self._restore_task.cancel()

            lavalink.unregister_event_listener(self.lavalink_event_handler)
            lavalink.unregister_update_listener(self.lavalink_update_handler)
            await lavalink.close(self.bot)
            await self._close_database()
            if self.managed_node_controller is not None:
                await self.managed_node_controller.shutdown()

            self.cog_cleaned_up = True

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        if await self.bot.cog_disabled_in_guild(self, member.guild):
            return
        await self.cog_ready_event.wait()
        if after.channel != before.channel:
            try:
                self.skip_votes[before.channel.guild.id].discard(member.id)
            except (ValueError, KeyError, AttributeError):
                pass

        channel = self.rgetattr(member, "voice.channel", None)
        bot_voice_state = self.rgetattr(member, "guild.me.voice.self_deaf", None)
        if (
            channel
            and bot_voice_state is False
            and await self.config.guild(member.guild).auto_deafen()
        ):
            try:
                player = lavalink.get_player(channel.guild.id)
            except (NodeNotFound, PlayerNotFound, AttributeError):
                pass
            else:
                if player.channel.id == channel.id:
                    await self.self_deafen(player)

    @commands.Cog.listener()
    async def on_shard_disconnect(self, shard_id):
        self._disconnected_shard.add(shard_id)

    @commands.Cog.listener()
    async def on_shard_ready(self, shard_id):
        self._disconnected_shard.discard(shard_id)

    @commands.Cog.listener()
    async def on_shard_resumed(self, shard_id):
        self._disconnected_shard.discard(shard_id)
