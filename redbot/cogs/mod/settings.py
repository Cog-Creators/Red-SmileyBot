import asyncio
from collections import defaultdict, deque
from datetime import timedelta

from redbot.core import commands, i18n
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import box, humanize_timedelta, inline

from .abc import MixinMeta

_ = i18n.Translator("Mod", __file__)


class ModSettings(MixinMeta):
    """
    This is a mixin for the mod cog containing all settings commands.
    """

    @commands.group()
    @commands.guildowner_or_permissions(administrator=True)
    async def modset(self, ctx: commands.Context):
        """Manage server administration settings."""

    @modset.command(name="showsettings")
    async def modset_showsettings(self, ctx: commands.Context):
        """Show the current server administration settings."""
        globaldata = await self.config.all()
        track_all_names = globaldata["track_all_names"]
        msg = ""
        msg += _("Track name changes: {yes_or_no}\n").format(
            yes_or_no=_("Yes") if track_all_names else _("No")
        )
        guild = ctx.guild
        if not guild:
            await ctx.send(box(msg))
            return

        data = await self.config.guild(guild).all()
        track_nicknames = data["track_nicknames"]
        delete_repeats = data["delete_repeats"]
        warn_mention_spam = data["mention_spam"]["warn"]
        kick_mention_spam = data["mention_spam"]["kick"]
        ban_mention_spam = data["mention_spam"]["ban"]
        strict_mention_spam = data["mention_spam"]["strict"]
        respect_hierarchy = data["respect_hierarchy"]
        delete_delay = data["delete_delay"]
        reinvite_on_unban = data["reinvite_on_unban"]
        dm_on_kickban = data["dm_on_kickban"]
        default_days = data["default_days"]
        default_tempban_duration = data["default_tempban_duration"]
        if not track_all_names and track_nicknames:
            yes_or_no = _("Overridden by another setting")
        else:
            yes_or_no = _("Yes") if track_nicknames else _("No")
        msg += _("Track nickname changes: {yes_or_no}\n").format(yes_or_no=yes_or_no)
        msg += _("Delete repeats: {num_repeats}\n").format(
            num_repeats=_("after {num} repeats").format(num=delete_repeats)
            if delete_repeats != -1
            else _("No")
        )
        msg += _("Warn mention spam: {num_mentions}\n").format(
            num_mentions=_("{num} mentions").format(num=warn_mention_spam)
            if warn_mention_spam
            else _("No")
        )
        msg += _("Kick mention spam: {num_mentions}\n").format(
            num_mentions=_("{num} mentions").format(num=kick_mention_spam)
            if kick_mention_spam
            else _("No")
        )
        msg += _("Ban mention spam: {num_mentions}\n").format(
            num_mentions=_("{num} mentions").format(num=ban_mention_spam)
            if ban_mention_spam
            else _("No")
        )
        msg += (
            _("Mention Spam Strict: All mentions will count including duplicates\n")
            if strict_mention_spam
            else _("Mention Spam Strict: Only unique mentions will count\n")
        )
        msg += _("Respects hierarchy: {yes_or_no}\n").format(
            yes_or_no=_("Yes") if respect_hierarchy else _("No")
        )
        msg += _("Delete delay: {num_seconds}\n").format(
            num_seconds=_("{num} seconds").format(num=delete_delay)
            if delete_delay != -1
            else _("None")
        )
        msg += _("Reinvite on unban: {yes_or_no}\n").format(
            yes_or_no=_("Yes") if reinvite_on_unban else _("No")
        )
        msg += _("Send message to users on kick/ban: {yes_or_no}\n").format(
            yes_or_no=_("Yes") if dm_on_kickban else _("No")
        )
        if default_days:
            msg += _("Default message history delete on ban: Previous {num_days} days\n").format(
                num_days=default_days
            )
        else:
            msg += _("Default message history delete on ban: Don't delete any\n")
        msg += _("Default tempban duration: {duration}").format(
            duration=humanize_timedelta(seconds=default_tempban_duration)
        )
        await ctx.send(box(msg))

    @modset.command()
    @commands.guild_only()
    async def hierarchy(self, ctx: commands.Context):
        """Toggle role hierarchy check for mods and admins.

        **WARNING**: Disabling this setting will allow mods to take
        actions on users above them in the role hierarchy!

        This is enabled by default.
        """
        guild = ctx.guild
        toggled = await self.config.guild(guild).respect_hierarchy()
        if not toggled:
            await self.config.guild(guild).respect_hierarchy.set(True)
            await ctx.send(
                _("Role hierarchy will be checked when moderation commands are issued.")
            )
        else:
            await self.config.guild(guild).respect_hierarchy.set(False)
            await ctx.send(
                _("Role hierarchy will be ignored when moderation commands are issued.")
            )

    @modset.group()
    @commands.guild_only()
    async def mentionspam(self, ctx: commands.Context):
        """
        Manage the automoderation settings for mentionspam.
        """

    @mentionspam.command(name="strict")
    @commands.guild_only()
    async def mentionspam_strict(self, ctx: commands.Context, enabled: bool = None):
        """
        Setting to account for duplicate mentions.

        If enabled all mentions will count including duplicated mentions.
        If disabled only unique mentions will count.

        Use this command without any parameter to see current setting.
        """
        guild = ctx.guild
        if enabled is None:
            state = await self.config.guild(guild).mention_spam.strict()
            if state:
                msg = _("Mention spam currently accounts for multiple mentions of the same user.")
            else:
                msg = _("Mention spam currently only accounts for mentions of different users.")
            await ctx.send(msg)
            return

        if enabled:
            msg = _("Mention spam will now account for multiple mentions of the same user.")
        else:
            msg = _("Mention spam will only account for mentions of different users.")
        await self.config.guild(guild).mention_spam.strict.set(enabled)
        await ctx.send(msg)

    @mentionspam.command(name="warn")
    @commands.guild_only()
    async def mentionspam_warn(self, ctx: commands.Context, max_mentions: int):
        """
        Sets the autowarn conditions for mention spam.

        Users will be warned if they send any messages which contain more than
        `<max_mentions>` mentions.

        `<max_mentions>` Must be 0 or greater. Set to 0 to disable this feature.
        """
        mention_spam = await self.config.guild(ctx.guild).mention_spam.all()
        if not max_mentions:
            if not mention_spam["warn"]:
                return await ctx.send(_("Autowarn for mention spam is already disabled."))
            await self.config.guild(ctx.guild).mention_spam.warn.set(False)
            return await ctx.send(_("Autowarn for mention spam disabled."))

        if max_mentions < 1:
            return await ctx.send(_("`<max_mentions>` must be 1 or higher to autowarn."))

        mismatch_message = ""

        if mention_spam["kick"]:
            if max_mentions >= mention_spam["kick"]:
                mismatch_message += _("\nAutowarn is equal to or higher than autokick.")

        if mention_spam["ban"]:
            if max_mentions >= mention_spam["ban"]:
                mismatch_message += _("\nAutowarn is equal to or higher than autoban.")

        await self.config.guild(ctx.guild).mention_spam.warn.set(max_mentions)
        await ctx.send(
            _(
                "Autowarn for mention spam enabled. "
                "Anyone mentioning {max_mentions} or more people "
                "in a single message will be autowarned.\n{mismatch_message}"
            ).format(max_mentions=max_mentions, mismatch_message=mismatch_message)
        )

    @mentionspam.command(name="kick")
    @commands.guild_only()
    async def mentionspam_kick(self, ctx: commands.Context, max_mentions: int):
        """
        Sets the autokick conditions for mention spam.

        Users will be kicked if they send any messages which contain more than
        `<max_mentions>` mentions.

        `<max_mentions>` Must be 0 or greater. Set to 0 to disable this feature.
        """
        mention_spam = await self.config.guild(ctx.guild).mention_spam.all()
        if not max_mentions:
            if not mention_spam["kick"]:
                return await ctx.send(_("Autokick for mention spam is already disabled."))
            await self.config.guild(ctx.guild).mention_spam.kick.set(False)
            return await ctx.send(_("Autokick for mention spam disabled."))

        if max_mentions < 1:
            return await ctx.send(_("`<max_mentions>` must be 1 or higher to autokick."))

        mismatch_message = ""

        if mention_spam["warn"]:
            if max_mentions <= mention_spam["warn"]:
                mismatch_message += _("\nAutokick is equal to or lower than autowarn.")

        if mention_spam["ban"]:
            if max_mentions >= mention_spam["ban"]:
                mismatch_message += _("\nAutokick is equal to or higher than autoban.")

        await self.config.guild(ctx.guild).mention_spam.kick.set(max_mentions)
        await ctx.send(
            _(
                "Autokick for mention spam enabled. "
                "Anyone mentioning {max_mentions} or more people "
                "in a single message will be autokicked.\n{mismatch_message}"
            ).format(max_mentions=max_mentions, mismatch_message=mismatch_message)
        )

    @mentionspam.command(name="ban")
    @commands.guild_only()
    async def mentionspam_ban(self, ctx: commands.Context, max_mentions: int):
        """Set the autoban conditions for mention spam.

        Users will be banned if they send any message which contains more than
        `<max_mentions>` mentions.

        `<max_mentions>` Must be 0 or greater. Set to 0 to disable this feature.
        """
        mention_spam = await self.config.guild(ctx.guild).mention_spam.all()
        if not max_mentions:
            if not mention_spam["ban"]:
                return await ctx.send(_("Autoban for mention spam is already disabled."))
            await self.config.guild(ctx.guild).mention_spam.ban.set(False)
            return await ctx.send(_("Autoban for mention spam disabled."))

        if max_mentions < 1:
            return await ctx.send(_("`<max_mentions>` must be 1 or higher to autoban."))

        mismatch_message = ""

        if mention_spam["warn"]:
            if max_mentions <= mention_spam["warn"]:
                mismatch_message += _("\nAutoban is equal to or lower than autowarn.")

        if mention_spam["kick"]:
            if max_mentions <= mention_spam["kick"]:
                mismatch_message += _("\nAutoban is equal to or lower than autokick.")

        await self.config.guild(ctx.guild).mention_spam.ban.set(max_mentions)
        await ctx.send(
            _(
                "Autoban for mention spam enabled. "
                "Anyone mentioning {max_mentions} or more people "
                "in a single message will be autobanned.\n{mismatch_message}"
            ).format(max_mentions=max_mentions, mismatch_message=mismatch_message)
        )

    @modset.command()
    @commands.guild_only()
    async def deleterepeats(self, ctx: commands.Context, repeats: int = None):
        """Enable auto-deletion of repeated messages.

        Must be between 2 and 20.

        Set to -1 to disable this feature.
        """
        guild = ctx.guild
        if repeats is not None:
            if repeats == -1:
                await self.config.guild(guild).delete_repeats.set(repeats)
                self.cache.pop(guild.id, None)  # remove cache with old repeat limits
                await ctx.send(_("Repeated messages will be ignored."))
            elif 2 <= repeats <= 20:
                await self.config.guild(guild).delete_repeats.set(repeats)
                # purge and update cache to new repeat limits
                self.cache[guild.id] = defaultdict(lambda: deque(maxlen=repeats))
                await ctx.send(
                    _("Messages repeated up to {num} times will be deleted.").format(num=repeats)
                )
            else:
                await ctx.send(
                    _(
                        "Number of repeats must be between 2 and 20"
                        " or equal to -1 if you want to disable this feature!"
                    )
                )
        else:
            repeats = await self.config.guild(guild).delete_repeats()
            if repeats != -1:
                await ctx.send(
                    _(
                        "Bot will delete repeated messages after"
                        " {num} repeats. Set this value to -1 to"
                        " ignore repeated messages"
                    ).format(num=repeats)
                )
            else:
                await ctx.send(_("Repeated messages will be ignored."))

    @modset.command()
    @commands.guild_only()
    async def reinvite(self, ctx: commands.Context):
        """Toggle whether an invite will be sent to a user when unbanned.

        If this is True, the bot will attempt to create and send a single-use invite
        to the newly-unbanned user.
        """
        guild = ctx.guild
        cur_setting = await self.config.guild(guild).reinvite_on_unban()
        if not cur_setting:
            await self.config.guild(guild).reinvite_on_unban.set(True)
            await ctx.send(
                _("Users unbanned with {command} will be reinvited.").format(
                    command=inline(f"{ctx.clean_prefix}unban")
                )
            )
        else:
            await self.config.guild(guild).reinvite_on_unban.set(False)
            await ctx.send(
                _("Users unbanned with {command} will not be reinvited.").format(
                    command=inline(f"{ctx.clean_prefix}unban")
                )
            )

    @modset.command()
    @commands.guild_only()
    async def dm(self, ctx: commands.Context, enabled: bool = None):
        """Toggle whether a message should be sent to a user when they are kicked/banned.

        If this option is enabled, the bot will attempt to DM the user with the guild name
        and reason as to why they were kicked/banned.
        """
        guild = ctx.guild
        if enabled is None:
            setting = await self.config.guild(guild).dm_on_kickban()
            await ctx.send(
                _("DM when kicked/banned is currently set to: {setting}").format(setting=setting)
            )
            return
        await self.config.guild(guild).dm_on_kickban.set(enabled)
        if enabled:
            await ctx.send(_("Bot will now attempt to send a DM to user before kick and ban."))
        else:
            await ctx.send(
                _("Bot will no longer attempt to send a DM to user before kick and ban.")
            )

    @modset.command()
    @commands.guild_only()
    async def requirereason(self, ctx: commands.Context, enabled: bool = None):
        """
        Toggle whether a reason is required for mod actions.

        If this is enabled, the bot will require a reason to be provided for all mod actions.
        """
        guild = ctx.guild
        if enabled is None:
            setting = await self.config.guild(guild).require_reason()
            await ctx.send(
                _("Mod action reason requirement is currently set to: {setting}").format(
                    setting=setting
                )
            )
            return
        await self.config.guild(guild).require_reason.set(enabled)
        if enabled:
            await ctx.send(_("Bot will now require a reason for all mod actions."))
        else:
            await ctx.send(_("Bot will no longer require a reason for all mod actions."))

    @modset.command()
    @commands.guild_only()
    async def defaultdays(self, ctx: commands.Context, days: int = 0):
        """Set the default number of days worth of messages to be deleted when a user is banned.

        The number of days must be between 0 and 7.
        """
        guild = ctx.guild
        if not (0 <= days <= 7):
            return await ctx.send(_("Invalid number of days. Must be between 0 and 7."))
        await self.config.guild(guild).default_days.set(days)
        await ctx.send(
            _("{days} days worth of messages will be deleted when a user is banned.").format(
                days=days
            )
        )

    @modset.command()
    @commands.guild_only()
    async def defaultduration(
        self,
        ctx: commands.Context,
        *,
        duration: commands.TimedeltaConverter(
            minimum=timedelta(seconds=1), default_unit="seconds"
        ),
    ):
        """Set the default time to be used when a user is tempbanned.

        Accepts: seconds, minutes, hours, days, weeks
        `duration` must be greater than zero.

        Examples:
            `[p]modset defaultduration 7d12h10m`
            `[p]modset defaultduration 7 days 12 hours 10 minutes`
        """
        guild = ctx.guild
        await self.config.guild(guild).default_tempban_duration.set(duration.total_seconds())
        await ctx.send(
            _("The default duration for tempbanning a user is now {duration}.").format(
                duration=humanize_timedelta(timedelta=duration)
            )
        )

    @modset.command()
    @commands.guild_only()
    async def tracknicknames(self, ctx: commands.Context, enabled: bool = None):
        """
        Toggle whether server nickname changes should be tracked.

        This setting will be overridden if trackallnames is disabled.
        """
        guild = ctx.guild
        if enabled is None:
            state = await self.config.guild(guild).track_nicknames()
            if state:
                msg = _("Nickname changes are currently being tracked.")
            else:
                msg = _("Nickname changes are not currently being tracked.")
            await ctx.send(msg)
            return

        if enabled:
            msg = _("Nickname changes will now be tracked.")
        else:
            msg = _("Nickname changes will no longer be tracked.")
        await self.config.guild(guild).track_nicknames.set(enabled)
        await ctx.send(msg)

    @modset.command()
    @commands.is_owner()
    async def trackallnames(self, ctx: commands.Context, enabled: bool = None):
        """
        Toggle whether all name changes should be tracked.

        Toggling this off also overrides the tracknicknames setting.
        """
        if enabled is None:
            state = await self.config.track_all_names()
            if state:
                msg = _("Name changes are currently being tracked.")
            else:
                msg = _("All name changes are currently not being tracked.")
            await ctx.send(msg)
            return

        if enabled:
            msg = _("Name changes will now be tracked.")
        else:
            msg = _(
                "All name changes will no longer be tracked.\n"
                "To delete existing name data, use {command}."
            ).format(command=inline(f"{ctx.clean_prefix}modset deletenames"))
        await self.config.track_all_names.set(enabled)
        await ctx.send(msg)

    @modset.command()
    @commands.max_concurrency(1, commands.BucketType.default)
    @commands.is_owner()
    async def deletenames(self, ctx: commands.Context, confirmation: bool = False) -> None:
        """Delete all stored usernames, global display names, and server nicknames.

        Examples:
        - `[p]modset deletenames` - Did not confirm. Shows the help message.
        - `[p]modset deletenames yes` - Deletes all stored usernames, global display names, and server nicknames.

        **Arguments**

        - `<confirmation>` This will default to false unless specified.
        """
        if not confirmation:
            await ctx.send(
                _(
                    "This will delete all stored usernames, global display names,"
                    " and server nicknames the bot has stored.\nIf you're sure, type {command}"
                ).format(command=inline(f"{ctx.clean_prefix}modset deletenames yes"))
            )
            return

        async with ctx.typing():
            # Nickname data
            async with self.config._get_base_group(self.config.MEMBER).all() as mod_member_data:
                guilds_to_remove = []
                for guild_id, guild_data in mod_member_data.items():
                    await asyncio.sleep(0)
                    members_to_remove = []

                    async for member_id, member_data in AsyncIter(guild_data.items(), steps=100):
                        if "past_nicks" in member_data:
                            del member_data["past_nicks"]
                        if not member_data:
                            members_to_remove.append(member_id)

                    async for member_id in AsyncIter(members_to_remove, steps=100):
                        del guild_data[member_id]
                    if not guild_data:
                        guilds_to_remove.append(guild_id)

                async for guild_id in AsyncIter(guilds_to_remove, steps=100):
                    del mod_member_data[guild_id]

            # Username and global display name data
            async with self.config._get_base_group(self.config.USER).all() as mod_user_data:
                users_to_remove = []
                async for user_id, user_data in AsyncIter(mod_user_data.items(), steps=100):
                    if "past_names" in user_data:
                        del user_data["past_names"]
                    if "past_display_names" in user_data:
                        del user_data["past_display_names"]
                    if not user_data:
                        users_to_remove.append(user_id)

                async for user_id in AsyncIter(users_to_remove, steps=100):
                    del mod_user_data[user_id]

        await ctx.send(
            _(
                "Usernames, global display names, and server nicknames"
                " have been deleted from Mod config."
            )
        )
