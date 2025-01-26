from typing import Optional, Tuple
from datetime import timezone, timedelta, datetime
from .abc import MixinMeta

import discord
from redbot.core import commands, i18n, modlog
from redbot.core.utils.chat_formatting import (
    humanize_timedelta,
    humanize_list,
    pagify,
    format_perms_list,
)
from redbot.core.utils.mod import get_audit_reason

from .converters import MuteTime

_ = i18n.Translator("Mutes", __file__)


class VoiceMutes(MixinMeta):
    """
    This handles all voice channel related muting
    """

    @staticmethod
    async def _voice_perm_check(
        ctx: commands.Context, user_voice_state: Optional[discord.VoiceState], **perms: bool
    ) -> Tuple[bool, Optional[str]]:
        """Check if the bot and user have sufficient permissions for voicebans.

        This also verifies that the user's voice state and connected
        channel are not ``None``.

        Returns
        -------
        bool
            ``True`` if the permissions are sufficient and the user has
            a valid voice state.

        """
        if user_voice_state is None or user_voice_state.channel is None:
            return False, _("That user is not in a voice channel.")
        voice_channel: discord.VoiceChannel = user_voice_state.channel
        required_perms = discord.Permissions()
        required_perms.update(**perms)
        if not voice_channel.permissions_for(ctx.me) >= required_perms:
            return (
                False,
                _("I require the {perms} permission(s) in that user's channel to do that.").format(
                    perms=format_perms_list(required_perms)
                ),
            )
        if (
            ctx.permission_state is commands.PermState.NORMAL
            and not voice_channel.permissions_for(ctx.author) >= required_perms
        ):
            return (
                False,
                _(
                    "You must have the {perms} permission(s) in that user's channel to use this "
                    "command."
                ).format(perms=format_perms_list(required_perms)),
            )
        return True, None

    @commands.command(name="voicemute", usage="<users...> [reason]")
    @commands.guild_only()
    async def voice_mute(
        self,
        ctx: commands.Context,
        users: commands.Greedy[discord.Member],
        *,
        time_and_reason: MuteTime = {},
    ):
        """Mute a user in their current voice channel.

        `<users...>` is a space separated list of usernames, ID's, or mentions.
        `[time_and_reason]` is the time to mute for and reason. Time is
        any valid time length such as `30 minutes` or `2 days`. If nothing
        is provided the mute will use the set default time or indefinite if not set.

        Examples:
        `[p]voicemute @member1 @member2 spam 5 hours`
        `[p]voicemute @member1 3 days`"""
        if not users:
            return await ctx.send_help()
        if ctx.me in users:
            return await ctx.send(_("You cannot mute me."))
        if ctx.author in users:
            return await ctx.send(_("You cannot mute yourself."))
        async with ctx.typing():
            success_list = []
            issue_list = []
            for user in users:
                user_voice_state = user.voice
                can_move, perm_reason = await self._voice_perm_check(
                    ctx, user_voice_state, mute_members=True, manage_permissions=True
                )
                if not can_move:
                    issue_list.append((user, perm_reason))
                    continue
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
                guild = ctx.guild
                author = ctx.author
                channel = user_voice_state.channel
                audit_reason = get_audit_reason(author, reason, shorten=True)

                result = await self.channel_mute_user(
                    guild, channel, author, user, until, audit_reason, voice_mute=True
                )

                if result.success:
                    if result.reason:
                        issue_list.append((user, result.reason))
                    else:
                        success_list.append(user)
                    await modlog.create_case(
                        self.bot,
                        guild,
                        ctx.message.created_at,
                        "vmute",
                        user,
                        author,
                        reason,
                        until=until,
                        channel=channel,
                    )
                    await self._send_dm_notification(
                        user, author, guild, _("Voice mute"), reason, duration
                    )
                    async with self.config.member(user).perms_cache() as cache:
                        cache[channel.id] = result.old_overs
                else:
                    issue_list.append((user, result.reason))

        if success_list:
            msg = _("{users} has been muted in this channel{time}.")
            if len(success_list) > 1:
                msg = _("{users} have been muted in this channel{time}.")
            await ctx.send(
                msg.format(users=humanize_list([f"{u}" for u in success_list]), time=time)
            )
        if issue_list:
            msg = _("The following users could not be muted\n")
            for user, issue in issue_list:
                msg += f"{user}: {issue}\n"
            await ctx.send_interactive(pagify(msg))

    @commands.command(name="voiceunmute", usage="<users...> [reason]")
    @commands.guild_only()
    async def unmute_voice(
        self,
        ctx: commands.Context,
        users: commands.Greedy[discord.Member],
        *,
        reason: Optional[str] = None,
    ):
        """Unmute a user in their current voice channel.

        `<users...>` is a space separated list of usernames, ID's, or mentions.
        `[reason]` is the reason for the unmute."""
        if not users:
            return await ctx.send_help()
        if ctx.me in users:
            return await ctx.send(_("You cannot unmute me."))
        if ctx.author in users:
            return await ctx.send(_("You cannot unmute yourself."))
        async with ctx.typing():
            issue_list = []
            success_list = []
            for user in users:
                user_voice_state = user.voice
                can_move, perm_reason = await self._voice_perm_check(
                    ctx, user_voice_state, mute_members=True, manage_permissions=True
                )
                if not can_move:
                    issue_list.append((user, perm_reason))
                    continue
                guild = ctx.guild
                author = ctx.author
                channel = user_voice_state.channel
                audit_reason = get_audit_reason(author, reason, shorten=True)

                result = await self.channel_unmute_user(
                    guild, channel, author, user, audit_reason, voice_mute=True
                )

                if result.success:
                    if result.reason:
                        issue_list.append((user, result.reason))
                    else:
                        success_list.append(user)
                    await modlog.create_case(
                        self.bot,
                        guild,
                        ctx.message.created_at,
                        "vunmute",
                        user,
                        author,
                        reason,
                        until=None,
                        channel=channel,
                    )
                    await self._send_dm_notification(
                        user, author, guild, _("Voice unmute"), reason
                    )
                else:
                    issue_list.append((user, result.reason))
        if success_list:
            if channel.id in self._channel_mutes and self._channel_mutes[channel.id]:
                await self.config.channel(channel).muted_users.set(self._channel_mutes[channel.id])
            else:
                await self.config.channel(channel).muted_users.clear()
            await ctx.send(
                _("{users} unmuted in this channel.").format(
                    users=humanize_list([f"{u}" for u in success_list])
                )
            )
        if issue_list:
            msg = _("The following users could not be unmuted\n")
            for user, issue in issue_list:
                msg += f"{user}: {issue}\n"
            await ctx.send_interactive(pagify(msg))
