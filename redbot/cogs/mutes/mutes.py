import asyncio
import contextlib
import logging
from abc import ABC
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Literal, Optional, Tuple, Union, cast

import discord

from redbot.core.bot import Red
from redbot.core import commands, i18n, modlog, Config
from redbot.core.utils import AsyncIter, bounded_gather, can_user_react_in
from redbot.core.utils.chat_formatting import (
    bold,
    humanize_timedelta,
    humanize_list,
    inline,
    pagify,
)
from redbot.core.utils.mod import get_audit_reason
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.views import SimpleMenu
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate

from .converters import MuteTime
from .models import ChannelMuteResponse, MuteResponse
from .voicemutes import VoiceMutes

T_ = i18n.Translator("Mutes", __file__)

_ = lambda s: s

MUTE_UNMUTE_ISSUES = {
    "already_muted": _("That user is already muted in {location}."),
    "already_unmuted": _("That user is not muted in {location}."),
    "hierarchy_problem": _(
        "I cannot let you do that. You are not higher than the user in the role hierarchy."
    ),
    "assigned_role_hierarchy_problem": _(
        "I cannot let you do that. You are not higher than the mute role in the role hierarchy."
    ),
    "is_admin": _("That user cannot be (un)muted, as they have the Administrator permission."),
    "permissions_issue_role": _(
        "Failed to mute or unmute user. I need the Manage Roles "
        "permission and the user I'm muting must be "
        "lower than myself in the role hierarchy."
    ),
    "permissions_issue_guild": _(
        "Failed to mute or unmute user. I need the Timeout Members "
        "permission and the user I'm muting must be "
        "lower than myself in the role hierarchy."
    ),
    "permissions_issue_channel": _(
        "Failed to mute or unmute user. I need the Manage Permissions permission in {location}."
    ),
    "left_guild": _("The user has left the server while applying an overwrite."),
    "unknown_channel": _("The channel I tried to mute or unmute the user in isn't found."),
    "role_missing": _("The mute role no longer exists."),
    "voice_mute_permission": _(
        "Because I don't have the Move Members permission, this will take into effect when the user rejoins."
    ),
    "mute_is_too_long": _("Timeouts cannot be longer than 28 days."),
    "timeouts_require_time": _("You must provide a time for the timeout to end."),
    "is_not_voice_mute": _(
        "That user is channel muted in their current voice channel, not just voice muted."
        " If you want to fully unmute this user in the channel,"
        " use {command} in their voice channel's text channel instead."
    ),
}
_ = T_

log = logging.getLogger("red.cogs.mutes")

__version__ = "1.0.0"


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """

    pass


@i18n.cog_i18n(_)
class Mutes(VoiceMutes, commands.Cog, metaclass=CompositeMetaClass):
    """
    Mute users temporarily or indefinitely.
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, 49615220001, force_registration=True)
        default_guild = {
            "mute_role": None,
            "notification_channel": None,
            "muted_users": {},
            "default_time": 0,
            "dm": False,
            "show_mod": False,
        }
        self.config.register_global(schema_version=0)
        self.config.register_guild(**default_guild)
        self.config.register_member(perms_cache={})
        self.config.register_channel(muted_users={})
        self._server_mutes: Dict[int, Dict[int, dict]] = {}
        self._channel_mutes: Dict[int, Dict[int, dict]] = {}
        self._unmute_tasks: Dict[str, asyncio.Task] = {}
        self._unmute_task: Optional[asyncio.Task] = None
        self.mute_role_cache: Dict[int, int] = {}
        # this is a dict of guild ID's and asyncio.Events
        # to wait for a guild to finish channel unmutes before
        # checking for manual overwrites
        self._channel_mute_events: Dict[int, asyncio.Event] = {}
        self._ready = asyncio.Event()
        self._init_task: Optional[asyncio.Task] = None
        self._ready_raised = False

    def create_init_task(self) -> None:
        def _done_callback(task: asyncio.Task) -> None:
            try:
                exc = task.exception()
            except asyncio.CancelledError:
                pass
            else:
                if exc is None:
                    return
                log.error(
                    "An unexpected error occurred during Mutes's initialization.",
                    exc_info=exc,
                )
            self._ready_raised = True
            self._ready.set()

        self._init_task = asyncio.create_task(self.initialize())
        self._init_task.add_done_callback(_done_callback)

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        """Mutes are considered somewhat critical
        Therefore the only data that we should delete
        is that which comes from discord requesting us to
        remove data about a user
        """
        if requester != "discord_deleted_user":
            return

        await self._ready.wait()
        if self._ready_raised:
            raise RuntimeError(
                "Mutes cog is in a bad state, can't proceed with data deletion request."
            )
        all_members = await self.config.all_members()
        for g_id, data in all_members.items():
            for m_id, mutes in data.items():
                if m_id == user_id:
                    await self.config.member_from_ids(g_id, m_id).clear()

    async def initialize(self):
        await self.bot.wait_until_red_ready()
        await self._maybe_update_config()

        guild_data = await self.config.all_guilds()
        for g_id, mutes in guild_data.items():
            self._server_mutes[g_id] = {}
            if mutes["mute_role"]:
                self.mute_role_cache[g_id] = mutes["mute_role"]
            for user_id, mute in mutes["muted_users"].items():
                self._server_mutes[g_id][int(user_id)] = mute
        channel_data = await self.config.all_channels()
        for c_id, mutes in channel_data.items():
            self._channel_mutes[c_id] = {}
            for user_id, mute in mutes["muted_users"].items():
                self._channel_mutes[c_id][int(user_id)] = mute
        self._unmute_task = asyncio.create_task(self._handle_automatic_unmute())
        self._ready.set()

    async def _maybe_update_config(self):
        schema_version = await self.config.schema_version()

        if schema_version == 0:
            await self._schema_0_to_1()
            schema_version += 1
            await self.config.schema_version.set(schema_version)

    async def _schema_0_to_1(self):
        """This contains conversion that adds guild ID to channel mutes data."""
        all_channels = await self.config.all_channels()
        if not all_channels:
            return

        start = datetime.now()
        log.info(
            "Config conversion to schema_version 1 started. This may take a while to proceed..."
        )
        async for channel_id in AsyncIter(all_channels.keys()):
            try:
                if (channel := self.bot.get_channel(channel_id)) is None:
                    channel = await self.bot.fetch_channel(channel_id)
                async with self.config.channel_from_id(channel_id).muted_users() as muted_users:
                    for mute_id, mute_data in muted_users.items():
                        mute_data["guild"] = channel.guild.id
            except (discord.NotFound, discord.Forbidden):
                await self.config.channel_from_id(channel_id).clear()

        log.info(
            "Config conversion to schema_version 1 done. It took %s to proceed.",
            datetime.now() - start,
        )

    async def cog_before_invoke(self, ctx: commands.Context):
        if not self._ready.is_set():
            async with ctx.typing():
                await self._ready.wait()
        if self._ready_raised:
            await ctx.send(
                "There was an error during Mutes's initialization."
                " Check logs for more information."
            )
            raise commands.CheckFailure()

    def cog_unload(self):
        if self._init_task is not None:
            self._init_task.cancel()
        if self._unmute_task is not None:
            self._unmute_task.cancel()
        for task in self._unmute_tasks.values():
            task.cancel()

    async def is_allowed_by_hierarchy(
        self, guild: discord.Guild, mod: discord.Member, user: discord.Member
    ):
        is_special = mod == guild.owner or await self.bot.is_owner(mod)
        return mod.top_role > user.top_role or is_special

    async def _handle_automatic_unmute(self):
        """This is the core task creator and loop
        for automatic unmutes

        A resolution of 30 seconds seems appropriate
        to allow for decent resolution on low timed
        unmutes and without being too busy on our event loop
        """
        await self.bot.wait_until_red_ready()
        await self._ready.wait()
        if self._ready_raised:
            raise RuntimeError("Mutes cog is in a bad state, cancelling automatic unmute task.")
        while True:
            await self._clean_tasks()
            try:
                await self._handle_server_unmutes()
            except Exception:
                log.error("error checking server unmutes", exc_info=True)
            await asyncio.sleep(0.1)
            try:
                await self._handle_channel_unmutes()
            except Exception:
                log.error("error checking channel unmutes", exc_info=True)
            await asyncio.sleep(30)

    async def _clean_tasks(self):
        """This is here to cleanup our tasks
        and log when we have something going wrong
        inside our tasks.
        """
        log.debug("Cleaning unmute tasks")
        for task_id in list(self._unmute_tasks.keys()):
            task = self._unmute_tasks[task_id]

            if task.cancelled():
                self._unmute_tasks.pop(task_id, None)
                continue

            if task.done():
                try:
                    r = task.result()
                except Exception as exc:
                    log.error("An unexpected error occurred in the unmute task", exc_info=exc)
                self._unmute_tasks.pop(task_id, None)

    async def _handle_server_unmutes(self):
        """This is where the logic for role unmutes is taken care of"""
        log.debug("Checking server unmutes")
        for g_id in self._server_mutes:
            guild = self.bot.get_guild(g_id)
            if guild is None or await self.bot.cog_disabled_in_guild(self, guild):
                continue
            await i18n.set_contextual_locales_from_guild(self.bot, guild)
            for u_id in self._server_mutes[guild.id]:
                if self._server_mutes[guild.id][u_id]["until"] is None:
                    continue
                time_to_unmute = (
                    self._server_mutes[guild.id][u_id]["until"]
                    - datetime.now(timezone.utc).timestamp()
                )
                if time_to_unmute < 60.0:
                    task_name = f"server-unmute-{g_id}-{u_id}"
                    if task_name in self._unmute_tasks:
                        continue
                    log.debug(f"Creating task: {task_name}")
                    self._unmute_tasks[task_name] = asyncio.create_task(
                        self._auto_unmute_user(guild, self._server_mutes[guild.id][u_id])
                    )

    async def _auto_unmute_user(self, guild: discord.Guild, data: dict):
        """
        This handles role unmutes automatically

        Since channel overwrite mutes are handled under the separate
        _auto_channel_unmute_user methods here we don't
        need to worry about the dict response for message
        since only role based mutes get added here
        """
        delay = data["until"] - datetime.now(timezone.utc).timestamp()
        if delay < 1:
            delay = 0
        await asyncio.sleep(delay)

        member = guild.get_member(data["member"])
        author = guild.get_member(data["author"])
        if not member:
            async with self.config.guild(guild).muted_users() as muted_users:
                if str(data["member"]) in muted_users:
                    del muted_users[str(data["member"])]
            del self._server_mutes[guild.id][data["member"]]
            return
        result = await self.unmute_user(guild, None, member, _("Automatic unmute"))
        async with self.config.guild(guild).muted_users() as muted_users:
            if str(member.id) in muted_users:
                del muted_users[str(member.id)]
        if result.success:
            await modlog.create_case(
                self.bot,
                guild,
                datetime.now(timezone.utc),
                "sunmute",
                member,
                author,
                _("Automatic unmute"),
                until=None,
            )
            await self._send_dm_notification(
                member, author, guild, _("Server unmute"), _("Automatic unmute")
            )
        else:
            chan_id = await self.config.guild(guild).notification_channel()
            notification_channel = guild.get_channel(chan_id)
            if not notification_channel:
                return
            if not notification_channel.permissions_for(guild.me).send_messages:
                return
            error_msg = _(
                "I am unable to unmute {user} for the following reason:\n{reason}"
            ).format(user=member, reason=result.reason)
            try:
                await notification_channel.send(error_msg)
            except discord.errors.Forbidden:
                log.info(error_msg)
                return

    async def _handle_channel_unmutes(self):
        """This is where the logic for handling channel unmutes is taken care of"""
        log.debug("Checking channel unmutes")
        multiple_mutes = {}
        for c_id, c_data in self._channel_mutes.items():
            for u_id in self._channel_mutes[c_id]:
                if (
                    not self._channel_mutes[c_id][u_id]
                    or not self._channel_mutes[c_id][u_id]["until"]
                ):
                    continue
                guild = self.bot.get_guild(self._channel_mutes[c_id][u_id]["guild"])
                if guild is None or await self.bot.cog_disabled_in_guild(self, guild):
                    continue
                time_to_unmute = (
                    self._channel_mutes[c_id][u_id]["until"]
                    - datetime.now(timezone.utc).timestamp()
                )
                if time_to_unmute < 60.0:
                    if guild not in multiple_mutes:
                        multiple_mutes[guild] = {}
                    if u_id not in multiple_mutes[guild]:
                        multiple_mutes[guild][u_id] = {c_id: self._channel_mutes[c_id][u_id]}
                    else:
                        multiple_mutes[guild][u_id][c_id] = self._channel_mutes[c_id][u_id]

        for guild, users in multiple_mutes.items():
            await i18n.set_contextual_locales_from_guild(self.bot, guild)
            for user, channels in users.items():
                if len(channels) > 1:
                    task_name = f"server-unmute-channels-{guild.id}-{user}"
                    if task_name in self._unmute_tasks:
                        continue
                    log.debug(f"Creating task: {task_name}")
                    member = guild.get_member(user)
                    self._unmute_tasks[task_name] = asyncio.create_task(
                        self._auto_channel_unmute_user_multi(member, guild, channels)
                    )

                else:
                    for channel, mute_data in channels.items():
                        task_name = f"channel-unmute-{channel}-{user}"
                        log.debug(f"Creating task: {task_name}")
                        if task_name in self._unmute_tasks:
                            continue
                        if guild_channel := guild.get_channel(channel):
                            self._unmute_tasks[task_name] = asyncio.create_task(
                                self._auto_channel_unmute_user(guild_channel, mute_data)
                            )

        del multiple_mutes

    async def _auto_channel_unmute_user_multi(
        self, member: discord.Member, guild: discord.Guild, channels: Dict[int, dict]
    ):
        """This is meant to handle multiple channels all being unmuted at once"""
        if guild.id in self._channel_mute_events:
            self._channel_mute_events[guild.id].clear()
        else:
            self._channel_mute_events[guild.id] = asyncio.Event()
        tasks = []
        for channel, mute_data in channels.items():
            author = guild.get_member(mute_data["author"])
            tasks.append(
                self._auto_channel_unmute_user(guild.get_channel(channel), mute_data, False)
            )
        results = await bounded_gather(*tasks)
        unmuted_channels = [guild.get_channel(c) for c in channels.keys()]
        for result in results:
            if not result:
                continue
            _member, channel, reason = result
            unmuted_channels.remove(channel)
        modlog_reason = _("Automatic unmute")

        channel_list = humanize_list([c.mention for c in unmuted_channels if c is not None])
        if channel_list:
            modlog_reason += _("\nUnmuted in channels: ") + channel_list

        await modlog.create_case(
            self.bot,
            guild,
            datetime.now(timezone.utc),
            "sunmute",
            member,
            author,
            modlog_reason,
            until=None,
        )
        await self._send_dm_notification(
            member, author, guild, _("Server unmute"), _("Automatic unmute")
        )
        self._channel_mute_events[guild.id].set()
        if any(results):
            reasons = {}
            for result in results:
                if not result:
                    continue
                _member, channel, reason = result
                if reason not in reasons:
                    reasons[reason] = [channel]
                else:
                    reasons[reason].append(channel)
            error_msg = _("{member} could not be unmuted for the following reasons:\n").format(
                member=member
            )
            for reason, channel_list in reasons.items():
                error_msg += _("{reason} In the following channels: {channels}\n").format(
                    reason=reason,
                    channels=humanize_list([c.mention for c in channel_list]),
                )
            chan_id = await self.config.guild(guild).notification_channel()
            notification_channel = guild.get_channel(chan_id)
            if notification_channel is None:
                return None
            if not notification_channel.permissions_for(guild.me).send_messages:
                return None
            try:
                await notification_channel.send(error_msg)
            except discord.errors.Forbidden:
                log.info(error_msg)
                return None

    async def _auto_channel_unmute_user(
        self, channel: discord.abc.GuildChannel, data: dict, create_case: bool = True
    ) -> Optional[Tuple[discord.Member, discord.abc.GuildChannel, str]]:
        """This is meant to unmute a user in individual channels"""
        delay = data["until"] - datetime.now(timezone.utc).timestamp()
        if delay < 1:
            delay = 0
        await asyncio.sleep(delay)
        member = channel.guild.get_member(data["member"])
        author = channel.guild.get_member(data["author"])
        if not member:
            async with self.config.channel(channel).muted_users() as muted_users:
                if str(data["member"]) in muted_users:
                    del muted_users[str(data["member"])]
            if (
                channel.id in self._channel_mutes
                and data["member"] in self._channel_mutes[channel.id]
            ):
                del self._channel_mutes[channel.id][data["member"]]
            return None
        result = await self.channel_unmute_user(
            channel.guild, channel, None, member, _("Automatic unmute")
        )
        async with self.config.channel(channel).muted_users() as muted_users:
            if str(member.id) in muted_users:
                del muted_users[str(member.id)]
        if result.success:
            if create_case:
                if data.get("voice_mute", False):
                    unmute_type = "vunmute"
                    notification_title = _("Voice unmute")
                else:
                    unmute_type = "cunmute"
                    notification_title = _("Channel unmute")
                await modlog.create_case(
                    self.bot,
                    channel.guild,
                    datetime.now(timezone.utc),
                    unmute_type,
                    member,
                    channel.guild.me,
                    _("Automatic unmute"),
                    until=None,
                    channel=channel,
                )
                await self._send_dm_notification(
                    member, author, channel.guild, notification_title, _("Automatic unmute")
                )
            return None
        else:
            error_msg = _(
                "I am unable to unmute {user} in {channel} for the following reason:\n{reason}"
            ).format(user=member, channel=channel.mention, reason=result.reason)
            if create_case:
                chan_id = await self.config.guild(channel.guild).notification_channel()
                notification_channel = channel.guild.get_channel(chan_id)
                if not notification_channel:
                    return None
                if not notification_channel.permissions_for(channel.guild.me).send_messages:
                    return None
                try:
                    await notification_channel.send(error_msg)
                except discord.errors.Forbidden:
                    log.info(error_msg)
                    return None
            else:
                return (member, channel, result.reason)

    async def _send_dm_notification(
        self,
        user: Union[discord.User, discord.Member],
        moderator: Optional[Union[discord.User, discord.Member]],
        guild: discord.Guild,
        mute_type: str,
        reason: Optional[str],
        duration=None,
    ):
        if user.bot:
            return

        if not await self.config.guild(guild).dm():
            return

        show_mod = await self.config.guild(guild).show_mod()
        title = bold(mute_type)
        if duration:
            duration_str = humanize_timedelta(timedelta=duration)
            until = datetime.now(timezone.utc) + duration
            until_str = discord.utils.format_dt(until)

        if moderator is None:
            moderator_str = _("Unknown")
        else:
            moderator_str = str(moderator)

        if not reason:
            reason = _("No reason provided.")

        if await self.bot.embed_requested(user):
            em = discord.Embed(
                title=title,
                description=reason,
                color=await self.bot.get_embed_color(user),
            )
            em.timestamp = datetime.now(timezone.utc)
            if duration:
                em.add_field(name=_("Until"), value=until_str)
                em.add_field(name=_("Duration"), value=duration_str)
            em.add_field(name=_("Guild"), value=guild.name, inline=False)
            if show_mod:
                em.add_field(name=_("Moderator"), value=moderator_str)
            try:
                await user.send(embed=em)
            except discord.Forbidden:
                pass
        else:
            message = f"{title}\n>>> "
            message += reason
            message += (f"\n{bold(_('Moderator:'))} {moderator_str}") if show_mod else ""
            message += (
                (f"\n{bold(_('Until:'))} {until_str}\n{bold(_('Duration:'))} {duration_str}")
                if duration
                else ""
            )
            message += f"\n{bold(_('Guild:'))} {guild.name}"
            try:
                await user.send(message)
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """
        Used to handle the cache if a member manually has the muted role removed
        """
        guild = before.guild
        if await self.bot.cog_disabled_in_guild(self, guild):
            return
        if guild.id not in self.mute_role_cache:
            return
        should_save = False
        mute_role_id = self.mute_role_cache[guild.id]
        mute_role = guild.get_role(mute_role_id)
        if not mute_role:
            return
        b = set(before.roles)
        a = set(after.roles)
        roles_removed = list(b - a)
        roles_added = list(a - b)
        await i18n.set_contextual_locales_from_guild(self.bot, guild)
        if mute_role in roles_removed:
            # send modlog case for unmute and remove from cache
            if guild.id not in self._server_mutes:
                # they weren't a tracked mute so we can return early
                return
            if after.id in self._server_mutes[guild.id]:
                await modlog.create_case(
                    self.bot,
                    guild,
                    datetime.now(timezone.utc),
                    "sunmute",
                    after,
                    None,
                    _("Manually removed mute role"),
                )
                del self._server_mutes[guild.id][after.id]
                should_save = True
                await self._send_dm_notification(
                    after, None, guild, _("Server unmute"), _("Manually removed mute role")
                )
        elif mute_role in roles_added:
            # send modlog case for mute and add to cache
            if guild.id not in self._server_mutes:
                # initialize the guild in the cache to prevent keyerrors
                self._server_mutes[guild.id] = {}
            if after.id not in self._server_mutes[guild.id]:
                await modlog.create_case(
                    self.bot,
                    guild,
                    datetime.now(timezone.utc),
                    "smute",
                    after,
                    None,
                    _("Manually applied mute role"),
                )
                self._server_mutes[guild.id][after.id] = {
                    "author": None,
                    "member": after.id,
                    "until": None,
                }
                should_save = True
                await self._send_dm_notification(
                    after, None, guild, _("Server mute"), _("Manually applied mute role")
                )
        if should_save:
            await self.config.guild(guild).muted_users.set(self._server_mutes[guild.id])

    @commands.Cog.listener()
    async def on_guild_channel_update(
        self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel
    ):
        """
        This handles manually removing overwrites for a user that has been muted
        """
        if await self.bot.cog_disabled_in_guild(self, after.guild):
            return
        await i18n.set_contextual_locales_from_guild(self.bot, after.guild)
        if after.guild.id in self._channel_mute_events:
            await self._channel_mute_events[after.guild.id].wait()
        if after.id in self._channel_mutes:
            before_perms: Dict[int, Dict[str, Optional[bool]]] = {
                o.id: {name: attr for name, attr in p} for o, p in before.overwrites.items()
            }
            after_perms: Dict[int, Dict[str, Optional[bool]]] = {
                o.id: {name: attr for name, attr in p} for o, p in after.overwrites.items()
            }
            to_del: List[int] = []
            for user_id, mute_data in self._channel_mutes[after.id].items():
                unmuted = False
                voice_mute = mute_data.get("voice_mute", False)
                if user_id in after_perms:
                    perms_to_check = ["speak"]
                    if not voice_mute:
                        perms_to_check.extend(
                            (
                                "send_messages",
                                "send_messages_in_threads",
                                "create_public_threads",
                                "create_private_threads",
                            )
                        )
                    for perm_name in perms_to_check:
                        unmuted = unmuted or after_perms[user_id][perm_name] is not False
                # explicit is better than implicit :thinkies:
                if user_id in before_perms and (user_id not in after_perms or unmuted):
                    user = after.guild.get_member(user_id)
                    send_dm_notification = True
                    if not user:
                        send_dm_notification = False
                        user = discord.Object(id=user_id)
                    log.debug(f"{user} - {type(user)}")
                    to_del.append(user_id)
                    log.debug("creating case")
                    if voice_mute:
                        unmute_type = "vunmute"
                        notification_title = _("Voice unmute")
                    else:
                        unmute_type = "cunmute"
                        notification_title = _("Channel unmute")
                    if send_dm_notification:
                        await self._send_dm_notification(
                            user,
                            None,
                            after.guild,
                            notification_title,
                            _("Manually removed channel overwrites"),
                        )
                    await modlog.create_case(
                        self.bot,
                        after.guild,
                        datetime.now(timezone.utc),
                        unmute_type,
                        user,
                        None,
                        _("Manually removed channel overwrites"),
                        until=None,
                        channel=after,
                    )
                    log.debug("created case")
            if to_del:
                for u_id in to_del:
                    del self._channel_mutes[after.id][u_id]
                await self.config.channel(after).muted_users.set(self._channel_mutes[after.id])

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        if await self.bot.cog_disabled_in_guild(self, guild):
            return
        mute_role = await self.config.guild(guild).mute_role()
        if not mute_role:
            # timeouts already restore on rejoin
            return
        await i18n.set_contextual_locales_from_guild(self.bot, guild)
        if guild.id in self._server_mutes:
            if member.id in self._server_mutes[guild.id]:
                role = guild.get_role(mute_role)
                if not role:
                    return
                if self._server_mutes[guild.id][member.id]["until"]:
                    until = datetime.fromtimestamp(
                        self._server_mutes[guild.id][member.id]["until"]
                    )
                else:
                    until = None
                await self.mute_user(
                    guild, guild.me, member, until, _("Previously muted in this server.")
                )

    @commands.group()
    @commands.guild_only()
    async def muteset(self, ctx: commands.Context):
        """Mute settings."""
        pass

    @muteset.command()
    @commands.guild_only()
    @commands.mod_or_permissions(manage_channels=True)
    async def senddm(self, ctx: commands.Context, true_or_false: bool):
        """Set whether mute notifications should be sent to users in DMs."""
        await self.config.guild(ctx.guild).dm.set(true_or_false)
        if true_or_false:
            await ctx.send(_("I will now try to send mute notifications to users DMs."))
        else:
            await ctx.send(_("Mute notifications will no longer be sent to users DMs."))

    @muteset.command()
    @commands.guild_only()
    @commands.mod_or_permissions(manage_channels=True)
    async def showmoderator(self, ctx, true_or_false: bool):
        """Decide whether the name of the moderator muting a user should be included in the DM to that user."""
        await self.config.guild(ctx.guild).show_mod.set(true_or_false)
        if true_or_false:
            await ctx.send(
                _(
                    "I will include the name of the moderator who issued the mute when sending a DM to a user."
                )
            )
        else:
            await ctx.send(
                _(
                    "I will not include the name of the moderator who issued the mute when sending a DM to a user."
                )
            )

    @muteset.command(name="settings", aliases=["showsettings"])
    @commands.mod_or_permissions(manage_channels=True)
    async def show_mutes_settings(self, ctx: commands.Context):
        """
        Shows the current mute settings for this guild.
        """
        data = await self.config.guild(ctx.guild).all()

        mute_role = ctx.guild.get_role(data["mute_role"])
        notification_channel = ctx.guild.get_channel(data["notification_channel"])
        default_time = timedelta(seconds=data["default_time"])
        msg = _(
            "Mute Role: {role}\n"
            "Notification Channel: {channel}\n"
            "Default Time: {time}\n"
            "Send DM: {dm}\n"
            "Show moderator: {show_mod}"
        ).format(
            role=mute_role.mention if mute_role else _("None"),
            channel=notification_channel.mention if notification_channel else _("None"),
            time=humanize_timedelta(timedelta=default_time) if default_time else _("None"),
            dm=data["dm"],
            show_mod=data["show_mod"],
        )
        await ctx.maybe_send_embed(msg)

    @muteset.command(name="notification")
    @commands.admin_or_permissions(manage_channels=True)
    async def notification_channel_set(
        self,
        ctx: commands.Context,
        channel: Optional[
            Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel]
        ] = None,
    ):
        """
        Set the notification channel for automatic unmute issues.

        If no channel is provided this will be cleared and notifications
        about issues when unmuting users will not be sent anywhere.
        """
        if channel is None:
            await self.config.guild(ctx.guild).notification_channel.clear()
            await ctx.send(_("Notification channel for unmute issues has been cleared."))
        else:
            await self.config.guild(ctx.guild).notification_channel.set(channel.id)
            await ctx.send(
                _("I will post unmute issues in {channel}.").format(channel=channel.mention)
            )

    @muteset.command(name="role")
    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def mute_role(self, ctx: commands.Context, *, role: discord.Role = None):
        """Sets the role to be applied when muting a user.

        If no role is setup the bot will attempt to mute a user
        by utilizing server timeouts.

        Note: If no role is setup a user may be able to leave the server
        and rejoin no longer being muted.
        """
        if not role:
            await self.config.guild(ctx.guild).mute_role.set(None)
            if ctx.guild.id in self.mute_role_cache:
                del self.mute_role_cache[ctx.guild.id]
            await ctx.send(_("Discord Timeouts will be used for mutes instead."))
        else:
            if role >= ctx.author.top_role:
                await ctx.send(
                    _("You can't set this role as it is not lower than you in the role hierarchy.")
                )
                return
            await self.config.guild(ctx.guild).mute_role.set(role.id)
            self.mute_role_cache[ctx.guild.id] = role.id
            await ctx.send(_("Mute role set to {role}").format(role=role.name))
        if not await self.config.guild(ctx.guild).notification_channel():
            command_1 = f"`{ctx.clean_prefix}muteset notification`"
            await ctx.send(
                _(
                    "No notification channel has been setup, "
                    "use {command_1} to be updated when there's an issue in automatic unmutes."
                ).format(command_1=command_1)
            )

    @muteset.command(name="makerole")
    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def make_mute_role(self, ctx: commands.Context, *, name: str):
        """Create a Muted role.

        This will create a role and apply overwrites to all available channels
        to more easily setup muting a user.

        If you already have a muted role created on the server use
        `[p]muteset role ROLE_NAME_HERE`
        """
        if await self.config.guild(ctx.guild).mute_role():
            command = f"`{ctx.clean_prefix}muteset role`"
            return await ctx.send(
                _(
                    "There is already a mute role setup in this server. "
                    "Please remove it with {command} before trying to "
                    "create a new one."
                ).format(command=command)
            )
        async with ctx.typing():
            perms = discord.Permissions()
            perms.update(
                send_messages=False,
                send_messages_in_threads=False,
                create_public_threads=False,
                create_private_threads=False,
                use_application_commands=False,
                speak=False,
                add_reactions=False,
            )
            try:
                role = await ctx.guild.create_role(
                    name=name, permissions=perms, reason=_("Mute role setup")
                )
                await self.config.guild(ctx.guild).mute_role.set(role.id)
                # save the role early incase of issue later
            except discord.errors.Forbidden:
                return await ctx.send(_("I could not create a muted role in this server."))
            errors = []
            tasks = []
            for channel in ctx.guild.channels:
                tasks.append(self._set_mute_role_overwrites(role, channel))
            errors = await bounded_gather(*tasks)
            if any(errors):
                msg = _(
                    "I could not set overwrites for the following channels: {channels}"
                ).format(channels=humanize_list([i for i in errors if i]))
                for page in pagify(msg, delims=[" "]):
                    await ctx.send(page)

            await ctx.send(_("Mute role set to {role}").format(role=role.name))
        if not await self.config.guild(ctx.guild).notification_channel():
            command_1 = f"`{ctx.clean_prefix}muteset notification`"
            await ctx.send(
                _(
                    "No notification channel has been setup, "
                    "use {command_1} to be updated when there's an issue in automatic unmutes."
                ).format(command_1=command_1)
            )

    async def _set_mute_role_overwrites(
        self, role: discord.Role, channel: discord.abc.GuildChannel
    ) -> Optional[str]:
        """
        This sets the supplied role and channel overwrites to what we want
        by default for a mute role
        """
        if not channel.permissions_for(channel.guild.me).manage_permissions:
            return channel.mention
        overs = discord.PermissionOverwrite()
        overs.send_messages = False
        overs.send_messages_in_threads = False
        overs.create_public_threads = False
        overs.create_private_threads = False
        overs.use_application_commands = False
        overs.add_reactions = False
        overs.speak = False
        try:
            await channel.set_permissions(role, overwrite=overs, reason=_("Mute role setup"))
            return None
        except discord.errors.Forbidden:
            return channel.mention

    @muteset.command(name="defaulttime", aliases=["time"])
    @commands.mod_or_permissions(manage_messages=True)
    async def default_mute_time(self, ctx: commands.Context, *, time: Optional[MuteTime] = None):
        """
        Set the default mute time for the mute command.

        If no time interval is provided this will be cleared.
        """

        if not time:
            await self.config.guild(ctx.guild).default_time.clear()
            await ctx.send(_("Default mute time removed."))
        else:
            duration = time.get("duration", None)
            if not duration:
                return await ctx.send(_("Please provide a valid time format."))
            if duration >= timedelta(days=365000):
                # prevent setting a default time now that might eventually cause an overflow
                # later as the date goes up. 1000 years gives us approximately 8000 more years
                # of wiggle room.
                return await ctx.send(
                    _("The time provided is too long; use a more reasonable time.")
                )
            await self.config.guild(ctx.guild).default_time.set(duration.total_seconds())
            await ctx.send(
                _("Default mute time set to {time}.").format(
                    time=humanize_timedelta(timedelta=duration)
                )
            )

    async def _check_for_mute_role(self, ctx: commands.Context) -> bool:
        """
        This explains to the user whether or not mutes are setup correctly for
        automatic unmutes.
        """
        command_1 = f"{ctx.clean_prefix}muteset role"
        command_2 = f"{ctx.clean_prefix}muteset makerole"
        msg = _(
            "This server does not have a mute role setup and I do not have permission to timeout users. "
            " You can setup a mute role with {command_1} or"
            " {command_2} if you just want a basic role created setup.\n\n"
        ).format(
            command_1=inline(command_1),
            command_2=inline(command_2),
        )
        mute_role_id = await self.config.guild(ctx.guild).mute_role()
        mute_role = ctx.guild.get_role(mute_role_id)
        timeout_perms = ctx.channel.permissions_for(ctx.me).moderate_members
        if not timeout_perms and not mute_role:
            await ctx.send(msg)
            return False

        return True

    @commands.command()
    @commands.guild_only()
    @commands.mod_or_permissions(manage_roles=True)
    async def activemutes(self, ctx: commands.Context):
        """
        Displays active mutes on this server.
        """
        msg = ""
        if ctx.guild.id in self._server_mutes:
            mutes_data = self._server_mutes[ctx.guild.id]
            if mutes_data:
                msg += _("__Server Mutes__\n")
                for user_id, mutes in mutes_data.items():
                    if not mutes:
                        continue
                    user = ctx.guild.get_member(user_id)
                    if not user:
                        user_str = f"<@!{user_id}>"
                    else:
                        user_str = user.mention
                    if mutes["until"]:
                        timestamp = int(mutes["until"])
                        time_str = discord.utils.format_dt(datetime.fromtimestamp(timestamp))
                    else:
                        time_str = ""
                    msg += f"{user_str} "
                    if time_str:
                        msg += _("__Until__: {time_left}\n").format(time_left=time_str)
                    else:
                        msg += "\n"
        added_timeouts = False
        for member in ctx.guild.members:
            if member.is_timed_out():
                if not added_timeouts:
                    msg += _("__Server Timeouts__\n")
                    added_timeouts = True
                msg += f"{member.mention}"
                time_str = discord.utils.format_dt(member.timed_out_until)
                msg += _("__Until__: {time_left}\n").format(time_left=time_str)
        for channel_id, mutes_data in self._channel_mutes.items():
            if not mutes_data:
                continue
            if ctx.guild.get_channel(channel_id):
                msg += _("__<#{channel_id}> Mutes__\n").format(channel_id=channel_id)
                for user_id, mutes in mutes_data.items():
                    if not mutes:
                        continue
                    user = ctx.guild.get_member(user_id)
                    if not user:
                        user_str = f"<@!{user_id}>"
                    else:
                        user_str = user.mention
                    if mutes["until"]:
                        timestamp = int(mutes["until"])
                        time_str = discord.utils.format_dt(datetime.fromtimestamp(timestamp))
                    else:
                        time_str = ""
                    msg += f"{user_str} "
                    if time_str:
                        msg += _("__Until__: {time_left}\n").format(time_left=time_str)
                    else:
                        msg += "\n"

        if msg:
            msgs = []
            for page in pagify(msg):
                if await ctx.embed_requested():
                    msgs.append(discord.Embed(description=page, colour=await ctx.embed_colour()))
                else:
                    msgs.append(page)
            await SimpleMenu(msgs).start(ctx)
            return
        await ctx.maybe_send_embed(_("There are no mutes on this server right now."))

    @commands.command(usage="<users...> [time_and_reason]")
    @commands.guild_only()
    @commands.mod_or_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def timeout(
        self,
        ctx: commands.Context,
        users: commands.Greedy[discord.Member],
        *,
        time_and_reason: MuteTime = {},
    ):
        """Timeout users.

        `<users...>` is a space separated list of usernames, ID's, or mentions.
        `[time_and_reason]` is the time to timeout for and reason. Time is
        any valid time length such as `30 minutes` or `2 days`. If nothing
        is provided the timeout will use the set default time or give an error if not set.

        Examples:
        `[p]timeout @member1 @member2 spam 5 hours`
        `[p]timeout @member1 3 days`

        """
        if not users:
            return await ctx.send_help()
        if ctx.me in users:
            return await ctx.send(_("You cannot mute me."))
        if ctx.author in users:
            return await ctx.send(_("You cannot mute yourself."))
        until = time_and_reason.get("until", None)
        reason = time_and_reason.get("reason", None)
        time = ""
        duration = None
        if until:
            duration = time_and_reason.get("duration")
            if duration and duration > timedelta(days=28):
                await ctx.send(_(MUTE_UNMUTE_ISSUES["mute_is_too_long"]))
                return
            length = humanize_timedelta(timedelta=duration)
            time = _(" for {length} until {duration}").format(
                length=length, duration=discord.utils.format_dt(until)
            )

        else:
            default_duration = await self.config.guild(ctx.guild).default_time()
            if default_duration:
                duration = timedelta(seconds=default_duration)
                until = ctx.message.created_at + duration
                length = humanize_timedelta(seconds=default_duration)
                time = _(" for {length} until {duration}").format(
                    length=length, duration=discord.utils.format_dt(until)
                )

        success_list = []
        issues_list = []
        for member in users:
            ret = MuteResponse(success=False, reason=None, user=member)
            if member.guild_permissions >= ctx.author.guild_permissions:
                ret.reason = _(MUTE_UNMUTE_ISSUES["hierarchy_problem"])
                issues_list.append(ret)
                continue
            if member.guild_permissions.administrator:
                ret.reason = _(MUTE_UNMUTE_ISSUES["is_admin"])
                issues_list.append(ret)
                continue

            try:
                await member.edit(timed_out_until=until, reason=reason)
                success_list.append(member)
            except Exception:
                pass
        if success_list:
            msg = _("{users} has been timed out in this server{time}.")
            if len(success_list) > 1:
                msg = _("{users} have been timed out in this server{time}.")
            await ctx.send(
                msg.format(users=humanize_list([f"`{u}`" for u in success_list]), time=time)
            )
        else:
            await ctx.send(_("None of the users provided could be muted properly."))
        if issues_list:
            await self.handle_issues(ctx, issues_list)

    @commands.command(usage="<users...> [time_and_reason]")
    @commands.guild_only()
    @commands.mod_or_permissions(manage_roles=True, moderate_members=True)
    async def mute(
        self,
        ctx: commands.Context,
        users: commands.Greedy[discord.Member],
        *,
        time_and_reason: MuteTime = {},
    ):
        """Mute users.

        `<users...>` is a space separated list of usernames, ID's, or mentions.
        `[time_and_reason]` is the time to mute for and reason. Time is
        any valid time length such as `30 minutes` or `2 days`. If nothing
        is provided the mute will use the set default time or indefinite if not set.

        Examples:
        `[p]mute @member1 @member2 spam 5 hours`
        `[p]mute @member1 3 days`

        """
        if not users:
            return await ctx.send_help()
        if ctx.me in users:
            return await ctx.send(_("You cannot mute me."))
        if ctx.author in users:
            return await ctx.send(_("You cannot mute yourself."))

        if not await self._check_for_mute_role(ctx):
            return
        async with ctx.typing():
            until = time_and_reason.get("until", None)
            reason = time_and_reason.get("reason", None)
            time = ""
            duration = None
            if until:
                duration = time_and_reason.get("duration")
                length = humanize_timedelta(timedelta=duration)
                time = _(" for {length} until {duration}").format(
                    length=length, duration=discord.utils.format_dt(until)
                )

            else:
                default_duration = await self.config.guild(ctx.guild).default_time()
                if default_duration:
                    duration = timedelta(seconds=default_duration)
                    until = ctx.message.created_at + duration
                    length = humanize_timedelta(seconds=default_duration)
                    time = _(" for {length} until {duration}").format(
                        length=length, duration=discord.utils.format_dt(until)
                    )

            author = ctx.message.author
            guild = ctx.guild
            audit_reason = get_audit_reason(author, reason, shorten=True)
            success_list = []
            issue_list = []
            for user in users:
                response = await self.mute_user(guild, author, user, until, audit_reason)
                if response.success:
                    success_list.append(user)
                    await modlog.create_case(
                        self.bot,
                        guild,
                        ctx.message.created_at,
                        "smute",
                        user,
                        author,
                        reason,
                        until=until,
                        channel=None,
                    )
                    await self._send_dm_notification(
                        user, author, guild, _("Server mute"), reason, duration
                    )
                else:
                    issue_list.append(response)
        if success_list:
            if ctx.guild.id not in self._server_mutes:
                self._server_mutes[ctx.guild.id] = {}
            msg = _("{users} has been muted in this server{time}.")
            if len(success_list) > 1:
                msg = _("{users} have been muted in this server{time}.")
            await ctx.send(
                msg.format(users=humanize_list([f"`{u}`" for u in success_list]), time=time)
            )
        if issue_list:
            await self.handle_issues(ctx, issue_list)

    def parse_issues(self, issues: List[Union[MuteResponse, ChannelMuteResponse]]) -> str:
        users = set(issue.user for issue in issues)
        error_msg = ""

        for user in users:
            error_msg += _("{member} could not be (un)muted for the following reasons:\n").format(
                member=f"`{user}`"
            )
            # I would like to replace this with a user mention but send_interactive
            # does not support supressing mentions at this time. So in order to keep
            # this formatting consistent the username is escaped in a code block.
            for issue in issues:
                if issue.user.id != user.id:
                    continue
                if issue.reason:
                    error_msg += f"- {issue.reason}\n"

        return error_msg

    async def handle_issues(
        self, ctx: commands.Context, issue_list: List[Union[MuteResponse, ChannelMuteResponse]]
    ) -> None:
        """
        This is to handle the various issues that can return for each user/channel
        """
        message = _(
            "Some users could not be properly muted or unmuted. Would you like to see who, where, and why?"
        )

        can_react = can_user_react_in(ctx.me, ctx.channel)
        if not can_react:
            message += " (y/n)"
        query: discord.Message = await ctx.send(message)
        if can_react:
            # noinspection PyAsyncCall
            start_adding_reactions(query, ReactionPredicate.YES_OR_NO_EMOJIS)
            pred = ReactionPredicate.yes_or_no(query, ctx.author)
            event = "reaction_add"
        else:
            pred = MessagePredicate.yes_or_no(ctx)
            event = "message"
        try:
            await ctx.bot.wait_for(event, check=pred, timeout=30)
        except asyncio.TimeoutError:
            with contextlib.suppress(discord.NotFound):
                await query.delete()
            return

        if not pred.result:
            if can_react:
                with contextlib.suppress(discord.NotFound):
                    await query.delete()
            else:
                await ctx.send(_("OK then."))
            return
        else:
            if can_react:
                with contextlib.suppress(discord.Forbidden):
                    await query.clear_reactions()
            issue = self.parse_issues(issue_list)
            resp = pagify(issue)
            await ctx.send_interactive(resp)

    @commands.command(
        name="mutechannel", aliases=["channelmute"], usage="<users...> [time_and_reason]"
    )
    @commands.mod_or_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(manage_permissions=True)
    async def channel_mute(
        self,
        ctx: commands.Context,
        users: commands.Greedy[discord.Member],
        *,
        time_and_reason: MuteTime = {},
    ):
        """Mute a user in the current text channel (or in the parent of the current thread).

        `<users...>` is a space separated list of usernames, ID's, or mentions.
        `[time_and_reason]` is the time to mute for and reason. Time is
        any valid time length such as `30 minutes` or `2 days`. If nothing
        is provided the mute will use the set default time or indefinite if not set.

        Examples:
        `[p]mutechannel @member1 @member2 spam 5 hours`
        `[p]mutechannel @member1 3 days`
        """
        if not users:
            return await ctx.send_help()
        if ctx.me in users:
            return await ctx.send(_("You cannot mute me."))
        if ctx.author in users:
            return await ctx.send(_("You cannot mute yourself."))
        async with ctx.typing():
            until = time_and_reason.get("until", None)
            reason = time_and_reason.get("reason", None)
            time = ""
            duration = None
            if until:
                duration = time_and_reason.get("duration")
                length = humanize_timedelta(timedelta=duration)
                time = _(" for {length} until {duration}").format(
                    length=length, duration=discord.utils.format_dt(until)
                )

            else:
                default_duration = await self.config.guild(ctx.guild).default_time()
                if default_duration:
                    duration = timedelta(seconds=default_duration)
                    until = ctx.message.created_at + duration
                    length = humanize_timedelta(seconds=default_duration)
                    time = _(" for {length} until {duration}").format(
                        length=length, duration=discord.utils.format_dt(until)
                    )
            author = ctx.message.author
            channel = ctx.message.channel
            if isinstance(channel, discord.Thread):
                channel = channel.parent
            guild = ctx.guild
            audit_reason = get_audit_reason(author, reason, shorten=True)
            issue_list = []
            success_list = []
            for user in users:
                response = await self.channel_mute_user(
                    guild, channel, author, user, until, audit_reason
                )
                if response.success:
                    success_list.append(user)
                    if response.reason:
                        # This is incase we couldn't move the user from voice channels
                        issue_list.append(response)
                    await modlog.create_case(
                        self.bot,
                        guild,
                        ctx.message.created_at,
                        "cmute",
                        user,
                        author,
                        reason,
                        until=until,
                        channel=channel,
                    )
                    await self._send_dm_notification(
                        user, author, guild, _("Channel mute"), reason, duration
                    )
                    async with self.config.member(user).perms_cache() as cache:
                        cache[channel.id] = response.old_overs
                else:
                    issue_list.append(response)

        if success_list:
            msg = _("{users} has been muted in this channel{time}.")
            if len(success_list) > 1:
                msg = _("{users} have been muted in this channel{time}.")
            await ctx.send(
                msg.format(users=humanize_list([f"`{u}`" for u in success_list]), time=time)
            )
        if issue_list:
            msg = _("The following users could not be muted:\n")
            for issue in issue_list:
                msg += f"- `{issue.user}`: {issue.reason}\n"
            await ctx.send_interactive(pagify(msg))

    @commands.command(usage="<users...> [reason]")
    @commands.guild_only()
    @commands.mod_or_permissions(manage_roles=True)
    async def unmute(
        self,
        ctx: commands.Context,
        users: commands.Greedy[discord.Member],
        *,
        reason: Optional[str] = None,
    ):
        """Unmute users.

        `<users...>` is a space separated list of usernames, ID's, or mentions.
        `[reason]` is the reason for the unmute.
        """
        if not users:
            return await ctx.send_help()
        if ctx.me in users:
            return await ctx.send(_("You cannot unmute me."))
        if ctx.author in users:
            return await ctx.send(_("You cannot unmute yourself."))
        if not await self._check_for_mute_role(ctx):
            return
        async with ctx.typing():
            guild = ctx.guild
            author = ctx.author
            audit_reason = get_audit_reason(author, reason, shorten=True)
            issue_list = []
            success_list = []
            if guild.id in self._channel_mute_events:
                self._channel_mute_events[guild.id].clear()
            else:
                self._channel_mute_events[guild.id] = asyncio.Event()
            for user in users:
                response = await self.unmute_user(guild, author, user, audit_reason)

                if response.success:
                    if response.reason:
                        # This is incase we couldn't move the user from voice channels
                        issue_list.append(response)
                    success_list.append(user)
                    await modlog.create_case(
                        self.bot,
                        guild,
                        ctx.message.created_at,
                        "sunmute",
                        user,
                        author,
                        reason,
                        until=None,
                    )
                    await self._send_dm_notification(
                        user, author, guild, _("Server unmute"), reason
                    )
                else:
                    issue_list.append(response)
        self._channel_mute_events[guild.id].set()
        if success_list:
            if ctx.guild.id in self._server_mutes and self._server_mutes[ctx.guild.id]:
                await self.config.guild(ctx.guild).muted_users.set(
                    self._server_mutes[ctx.guild.id]
                )
            else:
                await self.config.guild(ctx.guild).muted_users.clear()
            await ctx.send(
                _("{users} unmuted in this server.").format(
                    users=humanize_list([f"`{u}`" for u in success_list])
                )
            )
        if issue_list:
            await self.handle_issues(ctx, issue_list)

    @commands.command(usage="<users...> [reason]", hidden=True)
    @commands.guild_only()
    @commands.mod_or_permissions(manage_roles=True)
    async def forceunmute(
        self,
        ctx: commands.Context,
        users: commands.Greedy[discord.Member],
        *,
        reason: Optional[str] = None,
    ):
        """Force Unmute users who have had channel overwrite mutes in every channel.

        `<users...>` is a space separated list of usernames, ID's, or mentions.
        `[reason]` is the reason for the unmute.
        """
        if not users:
            return await ctx.send_help()
        if ctx.me in users:
            return await ctx.send(_("You cannot unmute me."))
        if ctx.author in users:
            return await ctx.send(_("You cannot unmute yourself."))
        async with ctx.typing():
            guild = ctx.guild
            author = ctx.author
            audit_reason = get_audit_reason(author, reason, shorten=True)
            issue_list = []
            success_list = []
            if guild.id in self._channel_mute_events:
                self._channel_mute_events[guild.id].clear()
            else:
                self._channel_mute_events[guild.id] = asyncio.Event()
            for user in users:
                tasks = []
                for channel in guild.channels:
                    tasks.append(
                        self.channel_unmute_user(guild, channel, author, user, audit_reason)
                    )
                results = await bounded_gather(*tasks)
                for result in results:
                    if not result.success:
                        issue_list.append(result)
                if any(t.success for t in results):
                    success_list.append(user)
                    await modlog.create_case(
                        self.bot,
                        guild,
                        ctx.message.created_at,
                        "sunmute",
                        user,
                        author,
                        reason,
                        until=None,
                    )
                    await self._send_dm_notification(
                        user, author, guild, _("Server unmute"), reason
                    )
                await self.config.member(user).clear()

        self._channel_mute_events[guild.id].set()
        if success_list:
            if ctx.guild.id in self._server_mutes and self._server_mutes[ctx.guild.id]:
                await self.config.guild(ctx.guild).muted_users.set(
                    self._server_mutes[ctx.guild.id]
                )
            else:
                await self.config.guild(ctx.guild).muted_users.clear()
            await ctx.send(
                _("{users} unmuted in this server.").format(
                    users=humanize_list([f"`{u}`" for u in success_list])
                )
            )
        if issue_list:
            await self.handle_issues(ctx, issue_list)

    @commands.mod_or_permissions(manage_roles=True)
    @commands.command(name="unmutechannel", aliases=["channelunmute"], usage="<users...> [reason]")
    @commands.bot_has_guild_permissions(manage_permissions=True)
    async def unmute_channel(
        self,
        ctx: commands.Context,
        users: commands.Greedy[discord.Member],
        *,
        reason: Optional[str] = None,
    ):
        """Unmute a user in this channel (or in the parent of this thread).

        `<users...>` is a space separated list of usernames, ID's, or mentions.
        `[reason]` is the reason for the unmute.
        """
        if not users:
            return await ctx.send_help()
        if ctx.me in users:
            return await ctx.send(_("You cannot unmute me."))
        if ctx.author in users:
            return await ctx.send(_("You cannot unmute yourself."))
        async with ctx.typing():
            channel = ctx.channel
            if isinstance(channel, discord.Thread):
                channel = channel.parent
            author = ctx.author
            guild = ctx.guild
            audit_reason = get_audit_reason(author, reason, shorten=True)
            success_list = []
            issue_list = []
            for user in users:
                response = await self.channel_unmute_user(
                    guild, channel, author, user, audit_reason
                )

                if response.success:
                    success_list.append(user)
                    await modlog.create_case(
                        self.bot,
                        guild,
                        ctx.message.created_at,
                        "cunmute",
                        user,
                        author,
                        reason,
                        until=None,
                        channel=channel,
                    )
                    await self._send_dm_notification(
                        user, author, guild, _("Channel unmute"), reason
                    )
                else:
                    issue_list.append(response)
        if success_list:
            if channel.id in self._channel_mutes and self._channel_mutes[channel.id]:
                await self.config.channel(channel).muted_users.set(self._channel_mutes[channel.id])
            else:
                await self.config.channel(channel).muted_users.clear()
            await ctx.send(
                _("{users} unmuted in this channel.").format(
                    users=humanize_list([f"`{u}`" for u in success_list])
                )
            )
        if issue_list:
            msg = _("The following users could not be unmuted:\n")
            for issue in issue_list:
                msg += f"- `{issue.user}`: {issue.reason}\n"
            await ctx.send_interactive(pagify(msg))

    async def mute_user(
        self,
        guild: discord.Guild,
        author: discord.Member,
        user: discord.Member,
        until: Optional[datetime] = None,
        reason: Optional[str] = None,
    ) -> MuteResponse:
        """
        Handles muting users
        """
        permissions = user.guild_permissions
        ret: MuteResponse = MuteResponse(success=False, reason=None, user=user)

        if permissions.administrator:
            ret.reason = _(MUTE_UNMUTE_ISSUES["is_admin"])
            return ret
        if not await self.is_allowed_by_hierarchy(guild, author, user):
            ret.reason = _(MUTE_UNMUTE_ISSUES["hierarchy_problem"])
            return ret
        mute_role = await self.config.guild(guild).mute_role()

        if mute_role:
            role = guild.get_role(mute_role)
            if not role:
                ret.reason = _(MUTE_UNMUTE_ISSUES["role_missing"])
                return ret
            if author != guild.owner and role >= author.top_role:
                ret.reason = _(MUTE_UNMUTE_ISSUES["assigned_role_hierarchy_problem"])
                return ret
            if not guild.me.guild_permissions.manage_roles or role >= guild.me.top_role:
                ret.reason = _(MUTE_UNMUTE_ISSUES["permissions_issue_role"])
                return ret
            # This is here to prevent the modlog case from happening on role updates
            # we need to update the cache early so it's there before we receive the member_update event
            if guild.id not in self._server_mutes:
                self._server_mutes[guild.id] = {}

            self._server_mutes[guild.id][user.id] = {
                "author": author.id,
                "member": user.id,
                "until": until.timestamp() if until else None,
            }
            try:
                await user.add_roles(role, reason=reason)
                await self.config.guild(guild).muted_users.set(self._server_mutes[guild.id])
            except discord.errors.Forbidden:
                if guild.id in self._server_mutes and user.id in self._server_mutes[guild.id]:
                    del self._server_mutes[guild.id][user.id]
                ret.reason = _(MUTE_UNMUTE_ISSUES["permissions_issue_role"])
                return ret
            if user.voice:
                try:
                    await user.move_to(user.voice.channel)
                except discord.HTTPException:
                    # catch all discord errors because the result will be the same
                    # we successfully muted by this point but can't move the user
                    ret.reason = _(MUTE_UNMUTE_ISSUES["voice_mute_permission"])
            ret.success = True
            return ret
        else:
            if until and (until - datetime.now(tz=timezone.utc)) > timedelta(days=28):
                ret.reason = _(MUTE_UNMUTE_ISSUES["mute_is_too_long"])
                return ret
            if not until:
                ret.reason = _(MUTE_UNMUTE_ISSUES["timeouts_require_time"])
                return ret
            if guild.me.guild_permissions.moderate_members:
                try:
                    await user.edit(timed_out_until=until, reason=reason)
                    ret.success = True
                except Exception:
                    ret.reason = _(MUTE_UNMUTE_ISSUES["permissions_issue_guild"])
            else:
                ret.reason = _("I lack the moderate members permission.")
            return ret

    async def unmute_user(
        self,
        guild: discord.Guild,
        author: Optional[discord.Member],
        user: discord.Member,
        reason: Optional[str] = None,
    ) -> MuteResponse:
        """
        Handles unmuting users
        """
        ret: MuteResponse = MuteResponse(success=False, reason=None, user=user)

        mute_role_id = await self.config.guild(guild).mute_role()
        if author is not None and not await self.is_allowed_by_hierarchy(guild, author, user):
            ret.reason = _(MUTE_UNMUTE_ISSUES["hierarchy_problem"])
            return ret

        reasons = []
        mute_role = guild.get_role(mute_role_id)

        if mute_role and mute_role in user.roles:
            if guild.id in self._server_mutes:
                if user.id in self._server_mutes[guild.id]:
                    del self._server_mutes[guild.id][user.id]
            if not guild.me.guild_permissions.manage_roles or mute_role >= guild.me.top_role:
                reasons.append(_(MUTE_UNMUTE_ISSUES["permissions_issue_role"]))
            else:
                try:
                    await user.remove_roles(mute_role, reason=reason)
                    ret.success = True
                except discord.errors.Forbidden:
                    reasons.append(_(MUTE_UNMUTE_ISSUES["permissions_issue_role"]))

        if user.is_timed_out():
            if guild.me.guild_permissions.moderate_members:
                try:
                    await user.edit(timed_out_until=None, reason=reason)
                    ret.success = True
                except Exception:
                    reasons.append(_(MUTE_UNMUTE_ISSUES["permissions_issue_guild"]))
            else:
                reasons.append(_("I lack the timeout members permission."))

        if not reasons and not ret.success:
            ret.reason = _(MUTE_UNMUTE_ISSUES["already_unmuted"]).format(location=_("this server"))
        elif reasons:
            ret.reason = "\n".join(reasons)

        return ret

    async def channel_mute_user(
        self,
        guild: discord.Guild,
        channel: discord.abc.GuildChannel,
        author: discord.Member,
        user: discord.Member,
        until: Optional[datetime] = None,
        reason: Optional[str] = None,
        *,
        voice_mute: bool = False,
    ) -> ChannelMuteResponse:
        """Mutes the specified user in the specified channel"""
        overwrites = channel.overwrites_for(user)
        permissions = channel.permissions_for(user)

        ret = ChannelMuteResponse(
            success=False,
            channel=channel,
            reason=None,
            user=user,
            old_overs={},
            voice_mute=voice_mute,
        )

        if permissions.administrator:
            ret.reason = _(MUTE_UNMUTE_ISSUES["is_admin"])
            return ret

        move_channel = False
        if user.voice and user.voice.channel == channel:
            if channel.permissions_for(guild.me).move_members:
                move_channel = True
            else:
                ret.reason = _(MUTE_UNMUTE_ISSUES["voice_mute_permission"])

        if not await self.is_allowed_by_hierarchy(guild, author, user):
            ret.reason = _(MUTE_UNMUTE_ISSUES["hierarchy_problem"])
            return ret

        if channel.id not in self._channel_mutes:
            self._channel_mutes[channel.id] = {}
        current_mute = self._channel_mutes[channel.id].get(user.id)

        # Determine if this is voice mute -> channel mute upgrade
        is_mute_upgrade = (
            current_mute is not None and not voice_mute and current_mute.get("voice_mute", False)
        )
        # We want to continue if this is a new mute or a mute upgrade,
        # otherwise we should return with failure.
        if current_mute is not None and not is_mute_upgrade:
            ret.reason = _(MUTE_UNMUTE_ISSUES["already_muted"]).format(location=channel.mention)
            return ret
        new_overs: Dict[str, Optional[bool]] = {"speak": False}
        if not voice_mute:
            new_overs.update(
                send_messages=False,
                send_messages_in_threads=False,
                create_public_threads=False,
                create_private_threads=False,
                use_application_commands=False,
                add_reactions=False,
            )
        old_overs = {k: getattr(overwrites, k) for k in new_overs}
        if is_mute_upgrade:
            perms_cache = await self.config.member(user).perms_cache()
            if "speak" in perms_cache:
                old_overs["speak"] = perms_cache["speak"]
        ret.old_overs = old_overs
        overwrites.update(**new_overs)
        if not channel.permissions_for(guild.me).manage_permissions:
            ret.reason = _(MUTE_UNMUTE_ISSUES["permissions_issue_channel"]).format(
                location=channel.mention
            )
            return ret

        self._channel_mutes[channel.id][user.id] = {
            "author": author.id,
            "guild": guild.id,
            "member": user.id,
            "until": until.timestamp() if until else None,
            "voice_mute": voice_mute,
        }
        try:
            await channel.set_permissions(user, overwrite=overwrites, reason=reason)
            async with self.config.channel(channel).muted_users() as muted_users:
                muted_users[str(user.id)] = self._channel_mutes[channel.id][user.id]
        except discord.NotFound as e:
            if channel.id in self._channel_mutes and user.id in self._channel_mutes[channel.id]:
                del self._channel_mutes[channel.id][user.id]
            if e.code == 10003:
                if (
                    channel.id in self._channel_mutes
                    and user.id in self._channel_mutes[channel.id]
                ):
                    del self._channel_mutes[channel.id][user.id]
                ret.reason = _(MUTE_UNMUTE_ISSUES["unknown_channel"])
                return ret

            elif e.code == 10009:
                if (
                    channel.id in self._channel_mutes
                    and user.id in self._channel_mutes[channel.id]
                ):
                    del self._channel_mutes[channel.id][user.id]
                ret.reason = _(MUTE_UNMUTE_ISSUES["left_guild"])
                return ret

        except discord.Forbidden:
            ret.reason = _(MUTE_UNMUTE_ISSUES["permissions_issue_channel"]).format(
                location=channel.mention
            )
            return ret

        if move_channel:
            try:
                await user.move_to(channel)
            except discord.HTTPException:
                # catch all discord errors because the result will be the same
                # we successfully muted by this point but can't move the user
                ret.reason = _(MUTE_UNMUTE_ISSUES["voice_mute_permission"])
                ret.success = True
                return ret
        ret.success = True
        return ret

    async def channel_unmute_user(
        self,
        guild: discord.Guild,
        channel: discord.abc.GuildChannel,
        author: Optional[discord.Member],
        user: discord.Member,
        reason: Optional[str] = None,
        *,
        voice_mute: bool = False,
    ) -> ChannelMuteResponse:
        """Unmutes the specified user in a specified channel"""
        overwrites = channel.overwrites_for(user)
        perms_cache = await self.config.member(user).perms_cache()

        ret = ChannelMuteResponse(
            success=False,
            reason=None,
            user=user,
            channel=channel,
            old_overs={},
            voice_mute=voice_mute,
        )

        move_channel = False
        if channel.id in perms_cache:
            old_values = perms_cache[channel.id]
        else:
            old_values = {
                "send_messages": None,
                "send_messages_in_threads": None,
                "create_public_threads": None,
                "create_private_threads": None,
                "use_application_commands": None,
                "add_reactions": None,
                "speak": None,
            }

        if user.voice and user.voice.channel == channel:
            if channel.permissions_for(guild.me).move_members:
                move_channel = True

        if author is not None and not await self.is_allowed_by_hierarchy(guild, author, user):
            ret.reason = _(MUTE_UNMUTE_ISSUES["hierarchy_problem"])
            return ret

        overwrites.update(**old_values)
        if channel.id in self._channel_mutes and user.id in self._channel_mutes[channel.id]:
            current_mute = self._channel_mutes[channel.id].pop(user.id)
        else:
            ret.reason = _(MUTE_UNMUTE_ISSUES["already_unmuted"]).format(location=channel.mention)
            return ret

        if not current_mute["voice_mute"] and voice_mute:
            ret.reason = _(MUTE_UNMUTE_ISSUES["is_not_voice_mute"]).format(
                command=inline("unmutechannel")
            )
            return ret

        if not channel.permissions_for(guild.me).manage_permissions:
            ret.reason = _(MUTE_UNMUTE_ISSUES["permissions_issue_channel"]).format(
                location=channel.mention
            )
            return ret

        try:
            if overwrites.is_empty():
                await channel.set_permissions(
                    user, overwrite=cast(discord.PermissionOverwrite, None), reason=reason
                )
            else:
                await channel.set_permissions(user, overwrite=overwrites, reason=reason)
            async with self.config.channel(channel).muted_users() as muted_users:
                if str(user.id) in muted_users:
                    del muted_users[str(user.id)]
        except discord.NotFound as e:
            if e.code == 10003:
                ret.reason = _(MUTE_UNMUTE_ISSUES["unknown_channel"])
                return ret

            elif e.code == 10009:
                ret.reason = _(MUTE_UNMUTE_ISSUES["left_guild"])
                return ret

        if move_channel:
            try:
                await user.move_to(channel)
            except discord.HTTPException:
                # catch all discord errors because the result will be the same
                # we successfully muted by this point but can't move the user
                ret.success = True
                ret.reason = _(MUTE_UNMUTE_ISSUES["voice_mute_permission"])
                return ret
        ret.success = True
        return ret
