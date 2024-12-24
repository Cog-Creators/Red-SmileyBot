import contextlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Callable, List, Optional, Set, Union

import discord

from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.commands import positive_int, RawUserIdConverter
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import humanize_number
from redbot.core.utils.mod import slow_deletion, mass_purge
from redbot.core.utils.predicates import MessagePredicate
from .checks import check_self_permissions
from .converters import RawMessageIds

_ = Translator("Cleanup", __file__)

log = logging.getLogger("red.cleanup")


@cog_i18n(_)
class Cleanup(commands.Cog):
    """This cog contains commands used for "cleaning up" (deleting) messages.

    This is designed as a moderator tool and offers many convenient use cases.
    All cleanup commands only apply to the channel the command is executed in.

    Messages older than two weeks cannot be mass deleted.
    This is a limitation of the API.
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, 8927348724, force_registration=True)
        self.config.register_guild(notify=True)

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    @staticmethod
    async def check_100_plus(ctx: commands.Context, number: int) -> bool:
        """
        Called when trying to delete more than 100 messages at once.

        Prompts the user to choose whether they want to continue or not.

        Tries its best to cleanup after itself if the response is positive.
        """

        if ctx.assume_yes:
            return True

        if number > 2**63 - 1:
            return await ctx.send(_("Try a smaller number instead."))

        prompt = await ctx.send(
            _("Are you sure you want to delete {number} messages?").format(
                number=humanize_number(number)
            )
            + " (yes/no)"
        )
        response = await ctx.bot.wait_for("message", check=MessagePredicate.same_context(ctx))

        if response.content.lower().startswith("y"):
            with contextlib.suppress(discord.NotFound):
                await prompt.delete()
            with contextlib.suppress(discord.HTTPException):
                await response.delete()
            return True
        else:
            await ctx.send(_("Cancelled."))
            return False

    @staticmethod
    async def get_messages_for_deletion(
        *,
        channel: Union[
            discord.TextChannel,
            discord.VoiceChannel,
            discord.StageChannel,
            discord.DMChannel,
            discord.Thread,
        ],
        number: Optional[int] = None,
        check: Callable[[discord.Message], bool] = lambda x: True,
        limit: Optional[int] = None,
        before: Union[discord.Message, datetime] = None,
        after: Union[discord.Message, datetime] = None,
        delete_pinned: bool = False,
    ) -> List[discord.Message]:
        """
        Gets a list of messages meeting the requirements to be deleted.
        Generally, the requirements are:
        - We don't have the number of messages to be deleted already
        - The message passes a provided check (if no check is provided,
          this is automatically true)
        - The message is less than 14 days old
        - The message is not pinned

        Warning: Due to the way the API hands messages back in chunks,
        passing after and a number together is not advisable.
        If you need to accomplish this, you should filter messages on
        the entire applicable range, rather than use this utility.
        """

        # This isn't actually two weeks ago to allow some wiggle room on API limits
        two_weeks_ago = datetime.now(timezone.utc) - timedelta(days=14, minutes=-5)

        def message_filter(message):
            return (
                check(message)
                and message.created_at > two_weeks_ago
                and (delete_pinned or not message.pinned)
            )

        if after:
            if isinstance(after, discord.Message):
                after = after.created_at
            after = max(after, two_weeks_ago)

        collected = []
        async for message in channel.history(
            limit=limit, before=before, after=after, oldest_first=False
        ):
            if message.created_at < two_weeks_ago:
                break
            if message_filter(message):
                collected.append(message)
                if number is not None and number <= len(collected):
                    break

        return collected

    async def send_optional_notification(
        self,
        num: int,
        channel: Union[
            discord.TextChannel,
            discord.VoiceChannel,
            discord.StageChannel,
            discord.DMChannel,
            discord.Thread,
        ],
        *,
        subtract_invoking: bool = False,
    ) -> None:
        """
        Sends a notification to the channel that a certain number of messages have been deleted.
        """
        if not channel.guild or await self.config.guild(channel.guild).notify():
            if subtract_invoking:
                num -= 1
            if num == 1:
                await channel.send(_("1 message was deleted."), delete_after=5)
            else:
                await channel.send(
                    _("{num} messages were deleted.").format(num=humanize_number(num)),
                    delete_after=5,
                )

    @staticmethod
    async def get_message_from_reference(
        channel: Union[
            discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread
        ],
        reference: discord.MessageReference,
    ) -> Optional[discord.Message]:
        message = None
        resolved = reference.resolved
        if resolved and isinstance(resolved, discord.Message):
            message = resolved
        elif message := reference.cached_message:
            pass
        else:
            try:
                message = await channel.fetch_message(reference.message_id)
            except discord.NotFound:
                pass
        return message

    @commands.group()
    async def cleanup(self, ctx: commands.Context):
        """Base command for deleting messages."""
        pass

    @cleanup.command()
    @commands.guild_only()
    @commands.mod_or_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def text(
        self, ctx: commands.Context, text: str, number: positive_int, delete_pinned: bool = False
    ):
        """Delete the last X messages matching the specified text in the current channel.

        Example:
        - `[p]cleanup text "test" 5`

        Remember to use double quotes.

        **Arguments:**

        - `<number>` The max number of messages to cleanup. Must be a positive integer.
        - `<delete_pinned>` Whether to delete pinned messages or not. Defaults to False
        """

        channel = ctx.channel

        author = ctx.author

        if number > 100:
            cont = await self.check_100_plus(ctx, number)
            if not cont:
                return

        def check(m):
            if text in m.content:
                return True
            else:
                return False

        to_delete = await self.get_messages_for_deletion(
            channel=channel,
            number=number,
            check=check,
            before=ctx.message,
            delete_pinned=delete_pinned,
        )
        to_delete.append(ctx.message)

        reason = "{} ({}) deleted {} messages containing '{}' in channel #{}.".format(
            author,
            author.id,
            humanize_number(len(to_delete), override_locale="en_us"),
            text,
            channel.id,
        )
        log.info(reason)

        await mass_purge(to_delete, channel, reason=reason)
        await self.send_optional_notification(len(to_delete), channel, subtract_invoking=True)

    @cleanup.command()
    @commands.guild_only()
    @commands.mod_or_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def user(
        self,
        ctx: commands.Context,
        user: Union[discord.Member, RawUserIdConverter],
        number: positive_int,
        delete_pinned: bool = False,
    ):
        """Delete the last X messages from a specified user in the current channel.

        Examples:
        - `[p]cleanup user @Twentysix 2`
        - `[p]cleanup user Red 6`

        **Arguments:**

        - `<user>` The user whose messages are to be cleaned up.
        - `<number>` The max number of messages to cleanup. Must be a positive integer.
        - `<delete_pinned>` Whether to delete pinned messages or not. Defaults to False
        """
        channel = ctx.channel

        member = None
        if isinstance(user, discord.Member):
            member = user
            _id = member.id
        else:
            _id = user

        author = ctx.author

        if number > 100:
            cont = await self.check_100_plus(ctx, number)
            if not cont:
                return

        def check(m):
            if m.author.id == _id:
                return True
            else:
                return False

        to_delete = await self.get_messages_for_deletion(
            channel=channel,
            number=number,
            check=check,
            before=ctx.message,
            delete_pinned=delete_pinned,
        )
        to_delete.append(ctx.message)

        reason = (
            "{} ({}) deleted {} messages"
            " made by {} ({}) in channel #{}."
            "".format(
                author,
                author.id,
                humanize_number(len(to_delete), override_locale="en_US"),
                member or "???",
                _id,
                channel.name,
            )
        )
        log.info(reason)

        await mass_purge(to_delete, channel, reason=reason)
        await self.send_optional_notification(len(to_delete), channel, subtract_invoking=True)

    @cleanup.command()
    @commands.guild_only()
    @commands.mod_or_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def after(
        self,
        ctx: commands.Context,
        message_id: Optional[RawMessageIds],
        delete_pinned: bool = False,
    ):
        """Delete all messages after a specified message.

        To get a message id, enable developer mode in Discord's
        settings, 'appearance' tab. Then right click a message
        and copy its id.
        Replying to a message will cleanup all messages after it.

        **Arguments:**

        - `<message_id>` The id of the message to cleanup after. This message won't be deleted.
        - `<delete_pinned>` Whether to delete pinned messages or not. Defaults to False
        """

        channel = ctx.channel
        author = ctx.author
        after = None

        if message_id:
            try:
                after = await channel.fetch_message(message_id)
            except discord.NotFound:
                return await ctx.send(_("Message not found."))
        elif ref := ctx.message.reference:
            after = await self.get_message_from_reference(channel, ref)

        if after is None:
            raise commands.BadArgument

        to_delete = await self.get_messages_for_deletion(
            channel=channel, number=None, after=after, delete_pinned=delete_pinned
        )

        reason = "{} ({}) deleted {} messages in channel #{}.".format(
            author,
            author.id,
            humanize_number(len(to_delete), override_locale="en_US"),
            channel.name,
        )
        log.info(reason)

        await mass_purge(to_delete, channel, reason=reason)
        await self.send_optional_notification(len(to_delete), channel)

    @cleanup.command()
    @commands.guild_only()
    @commands.mod_or_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def before(
        self,
        ctx: commands.Context,
        message_id: Optional[RawMessageIds],
        number: positive_int,
        delete_pinned: bool = False,
    ):
        """Deletes X messages before the specified message.

        To get a message id, enable developer mode in Discord's
        settings, 'appearance' tab. Then right click a message
        and copy its id.
        Replying to a message will cleanup all messages before it.

        **Arguments:**

        - `<message_id>` The id of the message to cleanup before. This message won't be deleted.
        - `<number>` The max number of messages to cleanup. Must be a positive integer.
        - `<delete_pinned>` Whether to delete pinned messages or not. Defaults to False
        """

        channel = ctx.channel
        author = ctx.author
        before = None

        if message_id:
            try:
                before = await channel.fetch_message(message_id)
            except discord.NotFound:
                return await ctx.send(_("Message not found."))
        elif ref := ctx.message.reference:
            before = await self.get_message_from_reference(channel, ref)

        if before is None:
            raise commands.BadArgument

        to_delete = await self.get_messages_for_deletion(
            channel=channel, number=number, before=before, delete_pinned=delete_pinned
        )
        to_delete.append(ctx.message)

        reason = "{} ({}) deleted {} messages in channel #{}.".format(
            author,
            author.id,
            humanize_number(len(to_delete), override_locale="en_US"),
            channel.name,
        )
        log.info(reason)

        await mass_purge(to_delete, channel, reason=reason)
        await self.send_optional_notification(len(to_delete), channel, subtract_invoking=True)

    @cleanup.command()
    @commands.guild_only()
    @commands.mod_or_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def between(
        self,
        ctx: commands.Context,
        one: RawMessageIds,
        two: RawMessageIds,
        delete_pinned: bool = False,
    ):
        """Delete the messages between Message One and Message Two, providing the messages IDs.

        The first message ID should be the older message and the second one the newer.

        Example:
        - `[p]cleanup between 123456789123456789 987654321987654321`

        **Arguments:**

        - `<one>` The id of the message to cleanup after. This message won't be deleted.
        - `<two>` The id of the message to cleanup before. This message won't be deleted.
        - `<delete_pinned>` Whether to delete pinned messages or not. Defaults to False
        """
        channel = ctx.channel
        author = ctx.author
        try:
            mone = await channel.fetch_message(one)
        except discord.errors.NotFound:
            return await ctx.send(
                _("Could not find a message with the ID of {id}.".format(id=one))
            )
        try:
            mtwo = await channel.fetch_message(two)
        except discord.errors.NotFound:
            return await ctx.send(
                _("Could not find a message with the ID of {id}.".format(id=two))
            )
        to_delete = await self.get_messages_for_deletion(
            channel=channel, before=mtwo, after=mone, delete_pinned=delete_pinned
        )
        to_delete.append(ctx.message)
        reason = "{} ({}) deleted {} messages in channel #{}.".format(
            author,
            author.id,
            humanize_number(len(to_delete), override_locale="en_US"),
            channel.name,
        )
        log.info(reason)

        await mass_purge(to_delete, channel, reason=reason)
        await self.send_optional_notification(len(to_delete), channel, subtract_invoking=True)

    @cleanup.command()
    @commands.guild_only()
    @commands.mod_or_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def messages(
        self, ctx: commands.Context, number: positive_int, delete_pinned: bool = False
    ):
        """Delete the last X messages in the current channel.

        Example:
        - `[p]cleanup messages 26`

        **Arguments:**

        - `<number>` The max number of messages to cleanup. Must be a positive integer.
        - `<delete_pinned>` Whether to delete pinned messages or not. Defaults to False
        """

        channel = ctx.channel
        author = ctx.author

        if number > 100:
            cont = await self.check_100_plus(ctx, number)
            if not cont:
                return

        to_delete = await self.get_messages_for_deletion(
            channel=channel, number=number, before=ctx.message, delete_pinned=delete_pinned
        )
        to_delete.append(ctx.message)

        reason = "{} ({}) deleted {} messages in channel #{}.".format(
            author, author.id, len(to_delete), channel.name
        )
        log.info(reason)

        await mass_purge(to_delete, channel, reason=reason)
        await self.send_optional_notification(len(to_delete), channel, subtract_invoking=True)

    @cleanup.command(name="bot")
    @commands.guild_only()
    @commands.mod_or_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def cleanup_bot(
        self, ctx: commands.Context, number: positive_int, delete_pinned: bool = False
    ):
        """Clean up command messages and messages from the bot in the current channel.

        Can only cleanup custom commands and alias commands if those cogs are loaded.

        **Arguments:**

        - `<number>` The max number of messages to cleanup. Must be a positive integer.
        - `<delete_pinned>` Whether to delete pinned messages or not. Defaults to False
        """

        channel = ctx.channel
        author = ctx.message.author

        if number > 100:
            cont = await self.check_100_plus(ctx, number)
            if not cont:
                return

        prefixes = await self.bot.get_prefix(ctx.message)  # This returns all server prefixes
        if isinstance(prefixes, str):
            prefixes = [prefixes]

        # In case some idiot sets a null prefix
        if "" in prefixes:
            prefixes.remove("")

        cc_cog = self.bot.get_cog("CustomCommands")
        if cc_cog is not None:
            command_names: Set[str] = await cc_cog.get_command_names(ctx.guild)
            is_cc = lambda name: name in command_names
        else:
            is_cc = lambda name: False
        alias_cog = self.bot.get_cog("Alias")
        if alias_cog is not None:
            alias_names: Set[str] = set(
                a.name for a in await alias_cog._aliases.get_global_aliases()
            ) | set(a.name for a in await alias_cog._aliases.get_guild_aliases(ctx.guild))
            is_alias = lambda name: name in alias_names
        else:
            is_alias = lambda name: False

        bot_id = self.bot.user.id

        def check(m):
            if m.author.id == bot_id:
                return True
            elif m == ctx.message:
                return True
            p = discord.utils.find(m.content.startswith, prefixes)
            if p and len(p) > 0:
                cmd_name = m.content[len(p) :].split(" ")[0]
                return (
                    bool(self.bot.get_command(cmd_name)) or is_alias(cmd_name) or is_cc(cmd_name)
                )
            return False

        to_delete = await self.get_messages_for_deletion(
            channel=channel,
            number=number,
            check=check,
            before=ctx.message,
            delete_pinned=delete_pinned,
        )
        to_delete.append(ctx.message)

        reason = (
            "{} ({}) deleted {}"
            " command messages in channel #{}."
            "".format(
                author,
                author.id,
                humanize_number(len(to_delete), override_locale="en_US"),
                channel.name,
            )
        )
        log.info(reason)

        await mass_purge(to_delete, channel, reason=reason)
        await self.send_optional_notification(len(to_delete), channel, subtract_invoking=True)

    @cleanup.command(name="self")
    @check_self_permissions()
    async def cleanup_self(
        self,
        ctx: commands.Context,
        number: positive_int,
        match_pattern: str = None,
        delete_pinned: bool = False,
    ):
        """Clean up messages owned by the bot in the current channel.

        By default, all messages are cleaned. If a second argument is specified,
        it is used for pattern matching - only messages containing the given text will be deleted.

        Examples:
        - `[p]cleanup self 6`
        - `[p]cleanup self 10 Pong`
        - `[p]cleanup self 7 "" True`

        **Arguments:**

        - `<number>` The max number of messages to cleanup. Must be a positive integer.
        - `<match_pattern>` The text that messages must contain to be deleted. Use "" to skip this.
        - `<delete_pinned>` Whether to delete pinned messages or not. Defaults to False
        """
        channel = ctx.channel
        author = ctx.message.author

        if number > 100:
            cont = await self.check_100_plus(ctx, number)
            if not cont:
                return

        # You can always delete your own messages, this is needed to purge
        can_mass_purge = False
        if type(author) is discord.Member:
            me = ctx.guild.me
            can_mass_purge = ctx.bot_permissions.manage_messages

        if match_pattern:

            def content_match(c):
                return match_pattern in c

        else:

            def content_match(_):
                return True

        def check(m):
            if m.author.id != self.bot.user.id:
                return False
            elif content_match(m.content):
                return True
            return False

        to_delete = await self.get_messages_for_deletion(
            channel=channel,
            number=number,
            check=check,
            before=ctx.message,
            delete_pinned=delete_pinned,
        )
        if can_mass_purge:
            to_delete.append(ctx.message)

        if ctx.guild:
            channel_name = "channel " + channel.name
        else:
            channel_name = str(channel)

        reason = "{} ({}) deleted {} messages sent by the bot in {}.".format(
            author,
            author.id,
            humanize_number(len(to_delete), override_locale="en_US"),
            channel_name,
        )
        log.info(reason)

        if can_mass_purge:
            await mass_purge(to_delete, channel, reason=reason)
        else:
            await slow_deletion(to_delete)
        await self.send_optional_notification(
            len(to_delete), channel, subtract_invoking=can_mass_purge
        )

    @cleanup.command(name="duplicates", aliases=["spam"])
    @commands.guild_only()
    @commands.mod_or_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def cleanup_duplicates(self, ctx: commands.Context, number: positive_int = 50):
        """Deletes duplicate messages in the channel from the last X messages and keeps only one copy.

        Defaults to 50.

        **Arguments:**

        - `<number>` The number of messages to check for duplicates. Must be a positive integer.
        """
        msgs = []
        spam = []

        def check(m):
            if m.attachments:
                return False
            c = (
                m.author.id,
                m.content,
                [embed.to_dict() for embed in m.embeds],
                [sticker.id for sticker in m.stickers],
            )
            if c in msgs:
                spam.append(m)
                return True
            else:
                msgs.append(c)
                return False

        to_delete = await self.get_messages_for_deletion(
            channel=ctx.channel, limit=number, check=check, before=ctx.message
        )

        if len(to_delete) > 100:
            cont = await self.check_100_plus(ctx, len(to_delete))
            if not cont:
                return

        log.info(
            "%s (%s) deleted %s spam messages in channel %s (%s).",
            ctx.author,
            ctx.author.id,
            len(to_delete),
            ctx.channel,
            ctx.channel.id,
        )

        to_delete.append(ctx.message)
        await mass_purge(to_delete, ctx.channel, reason="Duplicate message cleanup")
        await self.send_optional_notification(len(to_delete), ctx.channel, subtract_invoking=True)

    @commands.group()
    @commands.admin_or_permissions(manage_messages=True)
    async def cleanupset(self, ctx: commands.Context):
        """Manage the settings for the cleanup command."""
        pass

    @commands.guild_only()
    @cleanupset.command(name="notify")
    async def cleanupset_notify(self, ctx: commands.Context):
        """Toggle clean up notification settings.

        When enabled, a message will be sent per cleanup, showing how many messages were deleted.
        This message will be deleted after 5 seconds.
        """
        toggle = await self.config.guild(ctx.guild).notify()
        if toggle:
            await self.config.guild(ctx.guild).notify.set(False)
            await ctx.send(_("I will no longer notify of message deletions."))
        else:
            await self.config.guild(ctx.guild).notify.set(True)
            await ctx.send(_("I will now notify of message deletions."))
