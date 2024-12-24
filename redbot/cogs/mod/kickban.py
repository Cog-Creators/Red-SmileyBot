import asyncio
import contextlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Union

import discord
from redbot.core import commands, i18n, modlog
from redbot.core.commands import RawUserIdConverter
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import (
    pagify,
    humanize_number,
    bold,
    humanize_list,
    format_perms_list,
)
from redbot.core.utils.mod import get_audit_reason
from .abc import MixinMeta
from .utils import is_allowed_by_hierarchy

log = logging.getLogger("red.mod")
_ = i18n.Translator("Mod", __file__)


class KickBanMixin(MixinMeta):
    """
    Kick and ban commands and tasks go here.
    """

    @staticmethod
    async def get_invite_for_reinvite(ctx: commands.Context, max_age: int = 86400) -> str:
        """Handles the reinvite logic for getting an invite to send the newly unbanned user"""
        guild = ctx.guild
        my_perms: discord.Permissions = guild.me.guild_permissions
        if my_perms.manage_guild or my_perms.administrator:
            if guild.vanity_url is not None:
                return guild.vanity_url
            invites = await guild.invites()
        else:
            invites = []
        for inv in invites:  # Loop through the invites for the guild
            if not (inv.max_uses or inv.max_age or inv.temporary):
                # Invite is for the guild's default channel,
                # has unlimited uses, doesn't expire, and
                # doesn't grant temporary membership
                # (i.e. they won't be kicked on disconnect)
                return inv.url
        else:  # No existing invite found that is valid
            channels_and_perms = (
                (channel, channel.permissions_for(guild.me)) for channel in guild.text_channels
            )
            channel = next(
                (channel for channel, perms in channels_and_perms if perms.create_instant_invite),
                None,
            )
            if channel is None:
                return ""
            try:
                # Create invite that expires after max_age
                return (await channel.create_invite(max_age=max_age)).url
            except discord.HTTPException:
                return ""

    @staticmethod
    async def _voice_perm_check(
        ctx: commands.Context, user_voice_state: Optional[discord.VoiceState], **perms: bool
    ) -> bool:
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
            await ctx.send(_("That user is not in a voice channel."))
            return False
        voice_channel: discord.VoiceChannel = user_voice_state.channel
        required_perms = discord.Permissions()
        required_perms.update(**perms)
        if not voice_channel.permissions_for(ctx.me) >= required_perms:
            await ctx.send(
                _("I require the {perms} permission(s) in that user's channel to do that.").format(
                    perms=format_perms_list(required_perms)
                )
            )
            return False
        if (
            ctx.permission_state is commands.PermState.NORMAL
            and not voice_channel.permissions_for(ctx.author) >= required_perms
        ):
            await ctx.send(
                _(
                    "You must have the {perms} permission(s) in that user's channel to use this "
                    "command."
                ).format(perms=format_perms_list(required_perms))
            )
            return False
        return True

    async def ban_user(
        self,
        user: Union[discord.Member, discord.User, discord.Object],
        ctx: commands.Context,
        days: int = 0,
        reason: str = None,
        create_modlog_case=False,
    ) -> Tuple[bool, str]:
        author = ctx.author
        guild = ctx.guild

        removed_temp = False

        if reason is None and await self.config.guild(guild).require_reason():
            return False, _("You must provide a reason for the ban.")

        if not (0 <= days <= 7):
            return False, _("Invalid days. Must be between 0 and 7.")

        if isinstance(user, discord.Member):
            if author == user:
                return (
                    False,
                    _("I cannot let you do that. Self-harm is bad {}").format("\N{PENSIVE FACE}"),
                )
            elif not await is_allowed_by_hierarchy(self.bot, self.config, guild, author, user):
                return (
                    False,
                    _(
                        "I cannot let you do that. You are "
                        "not higher than the user in the role "
                        "hierarchy."
                    ),
                )
            elif guild.me.top_role <= user.top_role or user == guild.owner:
                return False, _("I cannot do that due to Discord hierarchy rules.")

            toggle = await self.config.guild(guild).dm_on_kickban()
            if toggle:
                with contextlib.suppress(discord.HTTPException):
                    em = discord.Embed(
                        title=bold(_("You have been banned from {guild}.").format(guild=guild)),
                        color=await self.bot.get_embed_color(user),
                    )
                    em.add_field(
                        name=_("**Reason**"),
                        value=reason if reason is not None else _("No reason was given."),
                        inline=False,
                    )
                    await user.send(embed=em)

            ban_type = "ban"
        else:
            tempbans = await self.config.guild(guild).current_tempbans()

            try:
                await guild.fetch_ban(user)
            except discord.NotFound:
                pass
            else:
                if user.id in tempbans:
                    async with self.config.guild(guild).current_tempbans() as tempbans:
                        tempbans.remove(user.id)
                    removed_temp = True
                else:
                    return (
                        False,
                        _("User with ID {user_id} is already banned.").format(user_id=user.id),
                    )

            ban_type = "hackban"

        audit_reason = get_audit_reason(author, reason, shorten=True)

        if removed_temp:
            log.info(
                "%s (%s) upgraded the tempban for %s to a permaban.", author, author.id, user.id
            )
            success_message = _(
                "User with ID {user_id} was upgraded from a temporary to a permanent ban."
            ).format(user_id=user.id)
        else:
            user_handle = str(user) if isinstance(user, discord.abc.User) else "Unknown"
            try:
                await guild.ban(user, reason=audit_reason, delete_message_seconds=days * 86400)
                log.info(
                    "%s (%s) %sned %s (%s), deleting %s days worth of messages.",
                    author,
                    author.id,
                    ban_type,
                    user_handle,
                    user.id,
                    days,
                )
                success_message = _("Done. That felt good.")
            except discord.Forbidden:
                return False, _("I'm not allowed to do that.")
            except discord.NotFound:
                return False, _("User with ID {user_id} not found").format(user_id=user.id)
            except Exception:
                log.exception(
                    "%s (%s) attempted to %s %s (%s), but an error occurred.",
                    author,
                    author.id,
                    ban_type,
                    user_handle,
                    user.id,
                )
                return False, _("An unexpected error occurred.")

        if create_modlog_case:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                ban_type,
                user,
                author,
                reason,
                until=None,
                channel=None,
            )

        return True, success_message

    async def tempban_expirations_task(self) -> None:
        while True:
            try:
                await self._check_tempban_expirations()
            except Exception:
                log.exception("Something went wrong in check_tempban_expirations:")

            await asyncio.sleep(60)

    async def _check_tempban_expirations(self) -> None:
        guilds_data = await self.config.all_guilds()
        async for guild_id, guild_data in AsyncIter(guilds_data.items(), steps=100):
            if not (guild := self.bot.get_guild(guild_id)):
                continue
            if guild.unavailable or not guild.me.guild_permissions.ban_members:
                continue
            if await self.bot.cog_disabled_in_guild(self, guild):
                continue

            guild_tempbans = guild_data["current_tempbans"]
            if not guild_tempbans:
                continue
            async with self.config.guild(guild).current_tempbans.get_lock():
                if await self._check_guild_tempban_expirations(guild, guild_tempbans):
                    await self.config.guild(guild).current_tempbans.set(guild_tempbans)

    async def _check_guild_tempban_expirations(
        self, guild: discord.Guild, guild_tempbans: List[int]
    ) -> bool:
        changed = False
        for uid in guild_tempbans.copy():
            unban_time = datetime.fromtimestamp(
                await self.config.member_from_ids(guild.id, uid).banned_until(),
                timezone.utc,
            )
            if datetime.now(timezone.utc) > unban_time:
                try:
                    await guild.unban(discord.Object(id=uid), reason=_("Tempban finished"))
                except discord.NotFound:
                    # user is not banned anymore
                    guild_tempbans.remove(uid)
                    changed = True
                except discord.HTTPException as e:
                    # 50013: Missing permissions error code or 403: Forbidden status
                    if e.code == 50013 or e.status == 403:
                        log.info(
                            f"Failed to unban ({uid}) user from "
                            f"{guild.name}({guild.id}) guild due to permissions."
                        )
                        break  # skip the rest of this guild
                    log.info(f"Failed to unban member: error code: {e.code}")
                else:
                    # user unbanned successfully
                    guild_tempbans.remove(uid)
                    changed = True
        return changed

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(kick_members=True)
    @commands.admin_or_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        """
        Kick a user.

        Examples:
        - `[p]kick 428675506947227648 wanted to be kicked.`
            This will kick the user with ID 428675506947227648 from the server.
        - `[p]kick @Twentysix wanted to be kicked.`
            This will kick Twentysix from the server.

        If a reason is specified, it will be the reason that shows up
        in the audit log.
        """
        author = ctx.author
        guild = ctx.guild

        if reason is None and await self.config.guild(guild).require_reason():
            await ctx.send(_("You must provide a reason for the kick."))
            return

        if author == member:
            await ctx.send(
                _("I cannot let you do that. Self-harm is bad {emoji}").format(
                    emoji="\N{PENSIVE FACE}"
                )
            )
            return
        elif not await is_allowed_by_hierarchy(self.bot, self.config, guild, author, member):
            await ctx.send(
                _(
                    "I cannot let you do that. You are "
                    "not higher than the user in the role "
                    "hierarchy."
                )
            )
            return
        elif ctx.guild.me.top_role <= member.top_role or member == ctx.guild.owner:
            await ctx.send(_("I cannot do that due to Discord hierarchy rules."))
            return
        audit_reason = get_audit_reason(author, reason, shorten=True)
        toggle = await self.config.guild(guild).dm_on_kickban()
        if toggle:
            with contextlib.suppress(discord.HTTPException):
                em = discord.Embed(
                    title=bold(_("You have been kicked from {guild}.").format(guild=guild)),
                    color=await self.bot.get_embed_color(member),
                )
                em.add_field(
                    name=_("**Reason**"),
                    value=reason if reason is not None else _("No reason was given."),
                    inline=False,
                )
                await member.send(embed=em)
        try:
            await guild.kick(member, reason=audit_reason)
            log.info("%s (%s) kicked %s (%s)", author, author.id, member, member.id)
        except discord.errors.Forbidden:
            await ctx.send(_("I'm not allowed to do that."))
        except Exception:
            log.exception(
                "%s (%s) attempted to kick %s (%s), but an error occurred.",
                author,
                author.id,
                member,
                member.id,
            )
        else:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "kick",
                member,
                author,
                reason,
                until=None,
                channel=None,
            )
            await ctx.send(_("Done. That felt good."))

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    @commands.admin_or_permissions(ban_members=True)
    async def ban(
        self,
        ctx: commands.Context,
        user: Union[discord.Member, RawUserIdConverter],
        days: Optional[int] = None,
        *,
        reason: str = None,
    ):
        """Ban a user from this server and optionally delete days of messages.

        `days` is the amount of days of messages to cleanup on ban.

        Examples:
        - `[p]ban 428675506947227648 7 Continued to spam after told to stop.`
            This will ban the user with ID 428675506947227648 and it will delete 7 days worth of messages.
        - `[p]ban @Twentysix 7 Continued to spam after told to stop.`
            This will ban Twentysix and it will delete 7 days worth of messages.

        A user ID should be provided if the user is not a member of this server.
        If days is not a number, it's treated as the first word of the reason.
        Minimum 0 days, maximum 7. If not specified, the defaultdays setting will be used instead.
        """
        guild = ctx.guild
        if days is None:
            days = await self.config.guild(guild).default_days()
        if isinstance(user, int):
            user = self.bot.get_user(user) or discord.Object(id=user)

        success_, message = await self.ban_user(
            user=user, ctx=ctx, days=days, reason=reason, create_modlog_case=True
        )

        await ctx.send(message)

    @commands.command(aliases=["hackban"], usage="<user_ids...> [days] [reason]")
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    @commands.admin_or_permissions(ban_members=True)
    async def massban(
        self,
        ctx: commands.Context,
        user_ids: commands.Greedy[RawUserIdConverter],
        days: Optional[int] = None,
        *,
        reason: str = None,
    ):
        """Mass bans user(s) from the server.

        `days` is the amount of days of messages to cleanup on massban.

        Example:
           - `[p]massban 345628097929936898 57287406247743488 7 they broke all rules.`
            This will ban all the added userids and delete 7 days worth of their messages.

        User IDs need to be provided in order to ban
        using this command.
        """
        banned = []
        errors = {}
        upgrades = []

        if reason is None and await self.config.guild(ctx.guild).require_reason():
            await ctx.send(_("You must provide a reason for the massban."))
            return

        async def show_results():
            text = _("Banned {num} users from the server.").format(
                num=humanize_number(len(banned))
            )
            if errors:
                text += _("\nErrors:\n")
                text += "\n".join(errors.values())
            if upgrades:
                text += _(
                    "\nFollowing user IDs have been upgraded from a temporary to a permanent ban:\n"
                )
                text += humanize_list(upgrades)

            for p in pagify(text):
                await ctx.send(p)

        def remove_processed(ids):
            return [_id for _id in ids if _id not in banned and _id not in errors]

        user_ids = list(set(user_ids))  # No dupes

        author = ctx.author
        guild = ctx.guild

        if not user_ids:
            await ctx.send_help()
            return

        if days is None:
            days = await self.config.guild(guild).default_days()

        if not (0 <= days <= 7):
            await ctx.send(_("Invalid days. Must be between 0 and 7."))
            return

        if not guild.me.guild_permissions.ban_members:
            return await ctx.send(_("I lack the permissions to do this."))

        tempbans = await self.config.guild(guild).current_tempbans()

        for user_id in user_ids:
            if user_id in tempbans:
                # We need to check if a user is tempbanned here because otherwise they won't be processed later on.
                continue
            try:
                await guild.fetch_ban(discord.Object(user_id))
            except discord.NotFound:
                pass
            else:
                errors[user_id] = _("User with ID {user_id} is already banned.").format(
                    user_id=user_id
                )

        user_ids = remove_processed(user_ids)

        if not user_ids:
            await show_results()
            return

        # We need to check here, if any of the users isn't a member and if they are,
        # we need to use our `ban_user()` method to do hierarchy checks.
        members: Dict[int, discord.Member] = {}
        to_query: List[int] = []

        for user_id in user_ids:
            member = guild.get_member(user_id)
            if member is not None:
                members[user_id] = member
            elif not guild.chunked:
                to_query.append(user_id)

        # If guild isn't chunked, we might possibly be missing the member from cache,
        # so we need to make sure that isn't the case by querying the user IDs for such guilds.
        while to_query:
            queried_members = await guild.query_members(user_ids=to_query[:100], limit=100)
            members.update((member.id, member) for member in queried_members)
            to_query = to_query[100:]

        # Call `ban_user()` method for all users that turned out to be guild members.
        for user_id, member in members.items():
            try:
                # using `reason` here would shadow the reason passed to command
                success, failure_reason = await self.ban_user(
                    user=member, ctx=ctx, days=days, reason=reason, create_modlog_case=True
                )
                if success:
                    banned.append(user_id)
                else:
                    errors[user_id] = _("Failed to ban user {user_id}: {reason}").format(
                        user_id=user_id, reason=failure_reason
                    )
            except Exception as e:
                errors[user_id] = _("Failed to ban user {user_id}: {reason}").format(
                    user_id=user_id, reason=e
                )

        user_ids = remove_processed(user_ids)

        if not user_ids:
            await show_results()
            return

        for user_id in user_ids:
            user = discord.Object(id=user_id)
            audit_reason = get_audit_reason(author, reason, shorten=True)
            async with self.config.guild(guild).current_tempbans() as tempbans:
                if user_id in tempbans:
                    tempbans.remove(user_id)
                    upgrades.append(str(user_id))
                    log.info(
                        "%s (%s) upgraded the tempban for %s to a permaban.",
                        author,
                        author.id,
                        user_id,
                    )
                    banned.append(user_id)
                else:
                    try:
                        await guild.ban(
                            user, reason=audit_reason, delete_message_seconds=days * 86400
                        )
                        log.info("%s (%s) hackbanned %s", author, author.id, user_id)
                    except discord.NotFound:
                        errors[user_id] = _("User with ID {user_id} not found").format(
                            user_id=user_id
                        )
                        continue
                    except discord.Forbidden:
                        errors[user_id] = _(
                            "Could not ban user with ID {user_id}: missing permissions."
                        ).format(user_id=user_id)
                        continue
                    else:
                        banned.append(user_id)

            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "hackban",
                user_id,
                author,
                reason,
                until=None,
                channel=None,
            )
        await show_results()

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    @commands.admin_or_permissions(ban_members=True)
    async def tempban(
        self,
        ctx: commands.Context,
        member: discord.Member,
        duration: Optional[commands.TimedeltaConverter] = None,
        days: Optional[int] = None,
        *,
        reason: str = None,
    ):
        """Temporarily ban a user from this server.

        `duration` is the amount of time the user should be banned for.
        `days` is the amount of days of messages to cleanup on tempban.

        Examples:
        - `[p]tempban @Twentysix Because I say so`
            This will ban Twentysix for the default amount of time set by an administrator.
        - `[p]tempban @Twentysix 15m You need a timeout`
            This will ban Twentysix for 15 minutes.
        - `[p]tempban 428675506947227648 1d2h15m 5 Evil person`
            This will ban the user with ID 428675506947227648 for 1 day 2 hours 15 minutes and will delete the last 5 days of their messages.
        """
        guild = ctx.guild
        author = ctx.author

        if reason is None and await self.config.guild(guild).require_reason():
            await ctx.send(_("You must provide a reason for the temporary ban."))
            return

        if author == member:
            await ctx.send(
                _("I cannot let you do that. Self-harm is bad {}").format("\N{PENSIVE FACE}")
            )
            return
        elif not await is_allowed_by_hierarchy(self.bot, self.config, guild, author, member):
            await ctx.send(
                _(
                    "I cannot let you do that. You are "
                    "not higher than the user in the role "
                    "hierarchy."
                )
            )
            return
        elif guild.me.top_role <= member.top_role or member == guild.owner:
            await ctx.send(_("I cannot do that due to Discord hierarchy rules."))
            return

        guild_data = await self.config.guild(guild).all()

        if duration is None:
            duration = timedelta(seconds=guild_data["default_tempban_duration"])
        unban_time = datetime.now(timezone.utc) + duration

        if days is None:
            days = guild_data["default_days"]

        if not (0 <= days <= 7):
            await ctx.send(_("Invalid days. Must be between 0 and 7."))
            return
        invite = await self.get_invite_for_reinvite(ctx, int(duration.total_seconds() + 86400))

        await self.config.member(member).banned_until.set(unban_time.timestamp())
        async with self.config.guild(guild).current_tempbans() as current_tempbans:
            current_tempbans.append(member.id)

        with contextlib.suppress(discord.HTTPException):
            # We don't want blocked DMs preventing us from banning
            msg = _("You have been temporarily banned from {server_name} until {date}.").format(
                server_name=guild.name, date=discord.utils.format_dt(unban_time)
            )
            if guild_data["dm_on_kickban"] and reason:
                msg += _("\n\n**Reason:** {reason}").format(reason=reason)
            if invite:
                msg += _("\n\nHere is an invite for when your ban expires: {invite_link}").format(
                    invite_link=invite
                )
            await member.send(msg)

        audit_reason = get_audit_reason(author, reason, shorten=True)

        try:
            await guild.ban(member, reason=audit_reason, delete_message_seconds=days * 86400)
        except discord.Forbidden:
            await ctx.send(_("I can't do that for some reason."))
        except discord.HTTPException:
            await ctx.send(_("Something went wrong while banning."))
        else:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "tempban",
                member,
                author,
                reason,
                unban_time,
            )
            await ctx.send(_("Done. Enough chaos for now."))

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    @commands.admin_or_permissions(ban_members=True)
    async def softban(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        """Kick a user and delete 1 day's worth of their messages."""
        guild = ctx.guild
        author = ctx.author

        if reason is None and await self.config.guild(guild).require_reason():
            await ctx.send(_("You must provide a reason for the softban."))
            return

        if author == member:
            await ctx.send(
                _("I cannot let you do that. Self-harm is bad {emoji}").format(
                    emoji="\N{PENSIVE FACE}"
                )
            )
            return
        elif not await is_allowed_by_hierarchy(self.bot, self.config, guild, author, member):
            await ctx.send(
                _(
                    "I cannot let you do that. You are "
                    "not higher than the user in the role "
                    "hierarchy."
                )
            )
            return

        audit_reason = get_audit_reason(author, reason, shorten=True)

        invite = await self.get_invite_for_reinvite(ctx)

        try:  # We don't want blocked DMs preventing us from banning
            msg = await member.send(
                _(
                    "You have been banned and "
                    "then unbanned as a quick way to delete your messages.\n"
                    "You can now join the server again. {invite_link}"
                ).format(invite_link=invite)
            )
        except discord.HTTPException:
            msg = None
        try:
            await guild.ban(member, reason=audit_reason, delete_message_seconds=86400)
        except discord.errors.Forbidden:
            await ctx.send(_("My role is not high enough to softban that user."))
            if msg is not None:
                await msg.delete()
            return
        except discord.HTTPException:
            log.exception(
                "%s (%s) attempted to softban %s (%s), but an error occurred trying to ban them.",
                author,
                author.id,
                member,
                member.id,
            )
            return
        try:
            await guild.unban(member)
        except discord.HTTPException:
            log.exception(
                "%s (%s) attempted to softban %s (%s),"
                " but an error occurred trying to unban them.",
                author,
                author.id,
                member,
                member.id,
            )
            return
        else:
            log.info(
                "%s (%s) softbanned %s (%s), deleting 1 day worth of messages.",
                author,
                author.id,
                member,
                member.id,
            )
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "softban",
                member,
                author,
                reason,
                until=None,
                channel=None,
            )
            await ctx.send(_("Done. Enough chaos."))

    @commands.command()
    @commands.guild_only()
    @commands.mod_or_permissions(move_members=True)
    async def voicekick(
        self, ctx: commands.Context, member: discord.Member, *, reason: str = None
    ):
        """Kick a member from a voice channel."""
        if reason is None and await self.config.guild(ctx.guild).require_reason():
            await ctx.send(_("You must provide a reason for the voice kick."))
            return

        author = ctx.author
        guild = ctx.guild
        user_voice_state: discord.VoiceState = member.voice

        if await self._voice_perm_check(ctx, user_voice_state, move_members=True) is False:
            return
        elif not await is_allowed_by_hierarchy(self.bot, self.config, guild, author, member):
            await ctx.send(
                _(
                    "I cannot let you do that. You are "
                    "not higher than the user in the role "
                    "hierarchy."
                )
            )
            return
        case_channel = member.voice.channel
        # Store this channel for the case channel.

        try:
            await member.move_to(None)
        except discord.Forbidden:  # Very unlikely that this will ever occur
            await ctx.send(_("I am unable to kick this member from the voice channel."))
            return
        except discord.HTTPException:
            await ctx.send(_("Something went wrong while attempting to kick that member."))
            return
        else:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "vkick",
                member,
                author,
                reason,
                until=None,
                channel=case_channel,
            )
            await ctx.send(_("User has been kicked from the voice channel."))

    @commands.command()
    @commands.guild_only()
    @commands.admin_or_permissions(mute_members=True, deafen_members=True)
    async def voiceunban(
        self, ctx: commands.Context, member: discord.Member, *, reason: str = None
    ):
        """Unban a user from speaking and listening in the server's voice channels."""
        if reason is None and await self.config.guild(ctx.guild).require_reason():
            await ctx.send(_("You must provide a reason for the voice unban."))
            return

        user_voice_state = member.voice
        if (
            await self._voice_perm_check(
                ctx, user_voice_state, deafen_members=True, mute_members=True
            )
            is False
        ):
            return
        needs_unmute = True if user_voice_state.mute else False
        needs_undeafen = True if user_voice_state.deaf else False
        audit_reason = get_audit_reason(ctx.author, reason, shorten=True)
        if needs_unmute and needs_undeafen:
            await member.edit(mute=False, deafen=False, reason=audit_reason)
        elif needs_unmute:
            await member.edit(mute=False, reason=audit_reason)
        elif needs_undeafen:
            await member.edit(deafen=False, reason=audit_reason)
        else:
            await ctx.send(_("That user isn't muted or deafened by the server."))
            return

        guild = ctx.guild
        author = ctx.author
        await modlog.create_case(
            self.bot,
            guild,
            ctx.message.created_at,
            "voiceunban",
            member,
            author,
            reason,
            until=None,
            channel=None,
        )
        await ctx.send(_("User is now allowed to speak and listen in voice channels."))

    @commands.command()
    @commands.guild_only()
    @commands.admin_or_permissions(mute_members=True, deafen_members=True)
    async def voiceban(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        """Ban a user from speaking and listening in the server's voice channels."""
        if reason is None and await self.config.guild(ctx.guild).require_reason():
            await ctx.send(_("You must provide a reason for the voice ban."))
            return

        user_voice_state: discord.VoiceState = member.voice
        if (
            await self._voice_perm_check(
                ctx, user_voice_state, deafen_members=True, mute_members=True
            )
            is False
        ):
            return
        needs_mute = True if user_voice_state.mute is False else False
        needs_deafen = True if user_voice_state.deaf is False else False
        audit_reason = get_audit_reason(ctx.author, reason, shorten=True)
        author = ctx.author
        guild = ctx.guild
        if needs_mute and needs_deafen:
            await member.edit(mute=True, deafen=True, reason=audit_reason)
        elif needs_mute:
            await member.edit(mute=True, reason=audit_reason)
        elif needs_deafen:
            await member.edit(deafen=True, reason=audit_reason)
        else:
            await ctx.send(_("That user is already muted and deafened server-wide."))
            return

        await modlog.create_case(
            self.bot,
            guild,
            ctx.message.created_at,
            "voiceban",
            member,
            author,
            reason,
            until=None,
            channel=None,
        )
        await ctx.send(_("User has been banned from speaking or listening in voice channels."))

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    @commands.admin_or_permissions(ban_members=True)
    async def unban(
        self, ctx: commands.Context, user_id: RawUserIdConverter, *, reason: str = None
    ):
        """Unban a user from this server.

        Requires specifying the target user's ID. To find this, you may either:
        1. Copy it from the mod log case (if one was created), or
        2. Enable Developer Mode, go to Bans in this server's settings, right-click the user and select 'Copy ID'.
        """
        if reason is None and await self.config.guild(ctx.guild).require_reason():
            await ctx.send(_("You must provide a reason for the unban."))
            return

        guild = ctx.guild
        author = ctx.author
        audit_reason = get_audit_reason(ctx.author, reason, shorten=True)
        try:
            ban_entry = await guild.fetch_ban(discord.Object(user_id))
        except discord.NotFound:
            await ctx.send(_("It seems that user isn't banned!"))
            return
        try:
            await guild.unban(ban_entry.user, reason=audit_reason)
        except discord.HTTPException:
            await ctx.send(_("Something went wrong while attempting to unban that user."))
            return
        else:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "unban",
                ban_entry.user,
                author,
                reason,
                until=None,
                channel=None,
            )
            await ctx.send(_("Unbanned that user from this server."))

        if await self.config.guild(guild).reinvite_on_unban():
            user = ctx.bot.get_user(user_id)
            if not user:
                await ctx.send(
                    _("I don't share another server with this user. I can't reinvite them.")
                )
                return

            invite = await self.get_invite_for_reinvite(ctx)
            if invite:
                try:
                    await user.send(
                        _(
                            "You've been unbanned from {server}.\n"
                            "Here is an invite for that server: {invite_link}"
                        ).format(server=guild.name, invite_link=invite)
                    )
                except discord.Forbidden:
                    await ctx.send(
                        _(
                            "I failed to send an invite to that user. "
                            "Perhaps you may be able to send it for me?\n"
                            "Here's the invite link: {invite_link}"
                        ).format(invite_link=invite)
                    )
                except discord.HTTPException:
                    await ctx.send(
                        _(
                            "Something went wrong when attempting to send that user "
                            "an invite. Here's the link so you can try: {invite_link}"
                        ).format(invite_link=invite)
                    )
