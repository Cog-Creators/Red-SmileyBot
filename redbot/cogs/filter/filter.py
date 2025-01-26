import asyncio
import discord
import re
from datetime import timezone
from typing import Union, Set, Literal, Optional

from redbot.core import Config, modlog, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n, set_contextual_locales_from_guild
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import pagify, humanize_list

_ = Translator("Filter", __file__)


@cog_i18n(_)
class Filter(commands.Cog):
    """This cog is designed for "filtering" unwanted words and phrases from a server.

    It provides tools to manage a list of words or sentences, and to customize automatic actions to be taken against users who use those words in channels or in their name/nickname.

    This can be used to prevent inappropriate language, off-topic discussions, invite links, and more.
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, 4766951341)
        default_guild_settings = {
            "filter": [],
            "filterban_count": 0,
            "filterban_time": 0,
            "filter_names": False,
            "filter_default_name": "John Doe",
        }
        default_member_settings = {"filter_count": 0, "next_reset_time": 0}
        default_channel_settings = {"filter": []}
        self.config.register_guild(**default_guild_settings)
        self.config.register_member(**default_member_settings)
        self.config.register_channel(**default_channel_settings)
        self.pattern_cache = {}

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        if requester != "discord_deleted_user":
            return

        all_members = await self.config.all_members()

        async for guild_id, guild_data in AsyncIter(all_members.items(), steps=100):
            if user_id in guild_data:
                await self.config.member_from_ids(guild_id, user_id).clear()

    async def cog_load(self) -> None:
        await self.register_casetypes()

    @staticmethod
    async def register_casetypes() -> None:
        await modlog.register_casetypes(
            [
                {
                    "name": "filterban",
                    "default_setting": False,
                    "image": "\N{FILE CABINET}\N{VARIATION SELECTOR-16} \N{HAMMER}",
                    "case_str": "Filter ban",
                },
                {
                    "name": "filterhit",
                    "default_setting": False,
                    "image": "\N{FILE CABINET}\N{VARIATION SELECTOR-16}",
                    "case_str": "Filter hit",
                },
            ]
        )

    @commands.group()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def filterset(self, ctx: commands.Context):
        """Base command to manage filter settings."""
        pass

    @filterset.command(name="defaultname")
    async def filter_default_name(self, ctx: commands.Context, name: str):
        """Set the nickname for users with a filtered name.

        Note that this has no effect if filtering names is disabled
        (to toggle, run `[p]filter names`).

        The default name used is *John Doe*.

        Example:
        - `[p]filterset defaultname Missingno`

        **Arguments:**

        - `<name>` The new nickname to assign.
        """
        guild = ctx.guild
        await self.config.guild(guild).filter_default_name.set(name)
        await ctx.send(_("The name to use on filtered names has been set."))

    @filterset.command(name="ban")
    async def filter_ban(self, ctx: commands.Context, count: int, timeframe: int):
        """Set the filter's autoban conditions.

        Users will be banned if they send `<count>` filtered words in
        `<timeframe>` seconds.

        Set both to zero to disable autoban.

        Examples:
        - `[p]filterset ban 5 5` - Ban users who say 5 filtered words in 5 seconds.
        - `[p]filterset ban 2 20` - Ban users who say 2 filtered words in 20 seconds.

        **Arguments:**

        - `<count>` The amount of filtered words required to trigger a ban.
        - `<timeframe>` The period of time in which too many filtered words will trigger a ban.
        """
        if (count <= 0) != (timeframe <= 0):
            await ctx.send(
                _(
                    "Count and timeframe either both need to be 0 "
                    "or both need to be greater than 0!"
                )
            )
            return
        elif count == 0 and timeframe == 0:
            async with self.config.guild(ctx.guild).all() as guild_data:
                guild_data["filterban_count"] = 0
                guild_data["filterban_time"] = 0
            await ctx.send(_("Autoban disabled."))
        else:
            async with self.config.guild(ctx.guild).all() as guild_data:
                guild_data["filterban_count"] = count
                guild_data["filterban_time"] = timeframe
            await ctx.send(_("Count and time have been set."))

    @commands.group(name="filter")
    @commands.guild_only()
    @commands.mod_or_permissions(manage_messages=True)
    async def _filter(self, ctx: commands.Context):
        """Base command to add or remove words from the server filter.

        Use double quotes to add or remove sentences.
        """
        pass

    @_filter.command(name="clear")
    async def _filter_clear(self, ctx: commands.Context):
        """Clears this server's filter list."""
        guild = ctx.guild
        author = ctx.author
        filter_list = await self.config.guild(guild).filter()
        if not filter_list:
            return await ctx.send(_("The filter list for this server is empty."))
        await ctx.send(
            _("Are you sure you want to clear this server's filter list?") + " (yes/no)"
        )
        try:
            pred = MessagePredicate.yes_or_no(ctx, user=author)
            await ctx.bot.wait_for("message", check=pred, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send(_("You took too long to respond."))
            return
        if pred.result:
            await self.config.guild(guild).filter.clear()
            self.invalidate_cache(guild)
            await ctx.send(_("Server filter cleared."))
        else:
            await ctx.send(_("No changes have been made."))

    @_filter.command(name="list")
    async def _global_list(self, ctx: commands.Context):
        """Send a list of this server's filtered words."""
        server = ctx.guild
        author = ctx.author
        word_list = await self.config.guild(server).filter()
        if not word_list:
            await ctx.send(_("There are no current words setup to be filtered in this server."))
            return
        words = humanize_list(word_list)
        words = _("Filtered in this server:") + "\n\n" + words
        try:
            for page in pagify(words, delims=[" ", "\n"], shorten_by=8):
                await author.send(page)
        except discord.Forbidden:
            await ctx.send(_("I can't send direct messages to you."))

    @_filter.group(name="channel")
    async def _filter_channel(self, ctx: commands.Context):
        """Base command to add or remove words from the channel filter.

        Use double quotes to add or remove sentences.
        """
        pass

    @_filter_channel.command(name="clear")
    async def _channel_clear(self, ctx: commands.Context):
        """Clears this channel's filter list."""
        channel = ctx.channel
        if isinstance(channel, discord.Thread):
            await ctx.send(
                _(
                    "Threads can't have a filter list set up. If you want to clear this list for"
                    " the parent channel, send the command in that channel."
                )
            )
            return
        author = ctx.author
        filter_list = await self.config.channel(channel).filter()
        if not filter_list:
            return await ctx.send(_("The filter list for this channel is empty."))
        await ctx.send(
            _("Are you sure you want to clear this channel's filter list?") + " (yes/no)"
        )
        try:
            pred = MessagePredicate.yes_or_no(ctx, user=author)
            await ctx.bot.wait_for("message", check=pred, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send(_("You took too long to respond."))
            return
        if pred.result:
            await self.config.channel(channel).filter.clear()
            self.invalidate_cache(ctx.guild, channel)
            await ctx.send(_("Channel filter cleared."))
        else:
            await ctx.send(_("No changes have been made."))

    @_filter_channel.command(name="list")
    async def _channel_list(self, ctx: commands.Context):
        """Send a list of the channel's filtered words."""
        channel = ctx.channel.parent if isinstance(ctx.channel, discord.Thread) else ctx.channel
        author = ctx.author
        word_list = await self.config.channel(channel).filter()
        if not word_list:
            await ctx.send(_("There are no current words setup to be filtered in this channel."))
            return
        words = humanize_list(word_list)
        words = _("Filtered in this channel:") + "\n\n" + words
        try:
            for page in pagify(words, delims=[" ", "\n"], shorten_by=8):
                await author.send(page)
        except discord.Forbidden:
            await ctx.send(_("I can't send direct messages to you."))

    @_filter_channel.command(name="add", require_var_positional=True)
    async def filter_channel_add(
        self,
        ctx: commands.Context,
        channel: Union[
            discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.ForumChannel
        ],
        *words: str,
    ):
        """Add words to the filter.

        Use double quotes to add sentences.

        Examples:
        - `[p]filter channel add #channel word1 word2 word3`
        - `[p]filter channel add #channel "This is a sentence"`

        **Arguments:**

        - `<channel>` The text, voice, stage, or forum channel to add filtered words to.
        - `[words...]` The words or sentences to filter.
        """
        added = await self.add_to_filter(channel, words)
        if added:
            self.invalidate_cache(ctx.guild, ctx.channel)
            await ctx.send(_("Words added to filter."))
        else:
            await ctx.send(_("Words already in the filter."))

    @_filter_channel.command(name="delete", aliases=["remove", "del"], require_var_positional=True)
    async def filter_channel_remove(
        self,
        ctx: commands.Context,
        channel: Union[
            discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.ForumChannel
        ],
        *words: str,
    ):
        """Remove words from the filter.

        Use double quotes to remove sentences.

        Examples:
        - `[p]filter channel remove #channel word1 word2 word3`
        - `[p]filter channel remove #channel "This is a sentence"`

        **Arguments:**

        - `<channel>` The text, voice, stage, or forum channel to add filtered words to.
        - `[words...]` The words or sentences to no longer filter.
        """
        removed = await self.remove_from_filter(channel, words)
        if removed:
            await ctx.send(_("Words removed from filter."))
            self.invalidate_cache(ctx.guild, ctx.channel)
        else:
            await ctx.send(_("Those words weren't in the filter."))

    @_filter.command(name="add", require_var_positional=True)
    async def filter_add(self, ctx: commands.Context, *words: str):
        """Add words to the filter.

        Use double quotes to add sentences.

        Examples:
        - `[p]filter add word1 word2 word3`
        - `[p]filter add "This is a sentence"`

        **Arguments:**

        - `[words...]` The words or sentences to filter.
        """
        server = ctx.guild
        added = await self.add_to_filter(server, words)
        if added:
            self.invalidate_cache(ctx.guild)
            await ctx.send(_("Words successfully added to filter."))
        else:
            await ctx.send(_("Those words were already in the filter."))

    @_filter.command(name="delete", aliases=["remove", "del"], require_var_positional=True)
    async def filter_remove(self, ctx: commands.Context, *words: str):
        """Remove words from the filter.

        Use double quotes to remove sentences.

        Examples:
        - `[p]filter remove word1 word2 word3`
        - `[p]filter remove "This is a sentence"`

        **Arguments:**

        - `[words...]` The words or sentences to no longer filter.
        """
        server = ctx.guild
        removed = await self.remove_from_filter(server, words)
        if removed:
            self.invalidate_cache(ctx.guild)
            await ctx.send(_("Words successfully removed from filter."))
        else:
            await ctx.send(_("Those words weren't in the filter."))

    @_filter.command(name="names")
    async def filter_names(self, ctx: commands.Context):
        """Toggle name and nickname filtering.

        This is disabled by default.
        """
        guild = ctx.guild

        async with self.config.guild(guild).all() as guild_data:
            current_setting = guild_data["filter_names"]
            guild_data["filter_names"] = not current_setting
        if current_setting:
            await ctx.send(_("Names and nicknames will no longer be filtered."))
        else:
            await ctx.send(_("Names and nicknames will now be filtered."))

    def invalidate_cache(
        self,
        guild: discord.Guild,
        channel: Optional[
            Union[
                discord.TextChannel,
                discord.VoiceChannel,
                discord.StageChannel,
                discord.ForumChannel,
            ]
        ] = None,
    ) -> None:
        """Invalidate a cached pattern"""
        self.pattern_cache.pop((guild.id, channel and channel.id), None)
        if channel is None:
            for keyset in list(self.pattern_cache.keys()):  # cast needed, no remove
                if guild.id == keyset[0]:
                    self.pattern_cache.pop(keyset, None)

    async def add_to_filter(
        self,
        server_or_channel: Union[
            discord.Guild,
            discord.TextChannel,
            discord.VoiceChannel,
            discord.StageChannel,
            discord.ForumChannel,
        ],
        words: list,
    ) -> bool:
        added = False
        if isinstance(server_or_channel, discord.Guild):
            async with self.config.guild(server_or_channel).filter() as cur_list:
                for w in words:
                    if w.lower() not in cur_list and w:
                        cur_list.append(w.lower())
                        added = True

        else:
            async with self.config.channel(server_or_channel).filter() as cur_list:
                for w in words:
                    if w.lower() not in cur_list and w:
                        cur_list.append(w.lower())
                        added = True

        return added

    async def remove_from_filter(
        self,
        server_or_channel: Union[
            discord.Guild,
            discord.TextChannel,
            discord.VoiceChannel,
            discord.StageChannel,
            discord.ForumChannel,
        ],
        words: list,
    ) -> bool:
        removed = False
        if isinstance(server_or_channel, discord.Guild):
            async with self.config.guild(server_or_channel).filter() as cur_list:
                for w in words:
                    if w.lower() in cur_list:
                        cur_list.remove(w.lower())
                        removed = True

        else:
            async with self.config.channel(server_or_channel).filter() as cur_list:
                for w in words:
                    if w.lower() in cur_list:
                        cur_list.remove(w.lower())
                        removed = True

        return removed

    async def filter_hits(
        self,
        server_or_channel: Union[
            discord.Guild,
            discord.TextChannel,
            discord.VoiceChannel,
            discord.StageChannel,
            discord.Thread,
        ],
        *texts: str,
    ) -> Set[str]:
        if isinstance(server_or_channel, discord.Guild):
            guild = server_or_channel
            channel = None
        else:
            guild = server_or_channel.guild
            if isinstance(server_or_channel, discord.Thread):
                channel = server_or_channel.parent
            else:
                channel = server_or_channel

        hits: Set[str] = set()

        try:
            pattern = self.pattern_cache[(guild.id, channel and channel.id)]
        except KeyError:
            word_list = set(await self.config.guild(guild).filter())
            if channel:
                word_list |= set(await self.config.channel(channel).filter())

            if word_list:
                pattern = re.compile(
                    "|".join(rf"\b{re.escape(w)}\b" for w in word_list), flags=re.I
                )
            else:
                pattern = None

            self.pattern_cache[(guild.id, channel and channel.id)] = pattern

        if pattern:
            for text in texts:
                hits |= set(pattern.findall(text))
        return hits

    async def check_filter(self, message: discord.Message):
        guild = message.guild
        author = message.author
        guild_data = await self.config.guild(guild).all()
        member_data = await self.config.member(author).all()
        filter_count = guild_data["filterban_count"]
        filter_time = guild_data["filterban_time"]
        user_count = member_data["filter_count"]
        next_reset_time = member_data["next_reset_time"]
        created_at = message.created_at

        if filter_count > 0 and filter_time > 0:
            if created_at.timestamp() >= next_reset_time:
                next_reset_time = created_at.timestamp() + filter_time
                async with self.config.member(author).all() as member_data:
                    member_data["next_reset_time"] = next_reset_time
                    if user_count > 0:
                        user_count = 0
                        member_data["filter_count"] = user_count

        texts = [message.content]
        poll = message.poll
        if poll is not None:
            texts.append(poll.question or "")
            for answer in poll.answers:
                texts.append(answer.text or "")
        for attachment in message.attachments:
            texts.append(attachment.description or "")
        hits = await self.filter_hits(message.channel, *texts)

        if hits:
            # modlog doesn't accept PartialMessageable
            channel = (
                None
                if isinstance(message.channel, discord.PartialMessageable)
                else message.channel
            )
            await modlog.create_case(
                bot=self.bot,
                guild=guild,
                created_at=created_at,
                action_type="filterhit",
                user=author,
                moderator=guild.me,
                reason=(
                    _("Filtered words used: {words}").format(words=humanize_list(list(hits)))
                    if len(hits) > 1
                    else _("Filtered word used: {word}").format(word=list(hits)[0])
                ),
                channel=channel,
            )
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            else:
                self.bot.dispatch("filter_message_delete", message, hits)
                if filter_count > 0 and filter_time > 0:
                    user_count += 1
                    await self.config.member(author).filter_count.set(user_count)
                    if user_count >= filter_count and created_at.timestamp() < next_reset_time:
                        reason = _("Autoban (too many filtered messages.)")
                        try:
                            await guild.ban(author, reason=reason)
                        except discord.HTTPException:
                            pass
                        else:
                            await modlog.create_case(
                                self.bot,
                                guild,
                                message.created_at,
                                "filterban",
                                author,
                                guild.me,
                                reason,
                            )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return

        if await self.bot.cog_disabled_in_guild(self, message.guild):
            return

        author = message.author
        valid_user = isinstance(author, discord.Member) and not author.bot
        if not valid_user:
            return

        if await self.bot.is_automod_immune(message):
            return

        await set_contextual_locales_from_guild(self.bot, message.guild)

        await self.check_filter(message)

    @commands.Cog.listener()
    async def on_message_edit(self, _prior, message):
        # message content has to change for non-bot's currently.
        # if this changes, we should compare before passing it.
        await self.on_message(message)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.display_name != after.display_name:
            await self.maybe_filter_name(after)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.maybe_filter_name(member)

    async def maybe_filter_name(self, member: discord.Member):
        guild = member.guild
        if (not guild) or await self.bot.cog_disabled_in_guild(self, guild):
            return

        if not member.guild.me.guild_permissions.manage_nicknames:
            return  # No permissions to manage nicknames, so can't do anything
        if member.top_role >= member.guild.me.top_role:
            return  # Discord Hierarchy applies to nicks
        if await self.bot.is_automod_immune(member):
            return
        guild_data = await self.config.guild(member.guild).all()
        if not guild_data["filter_names"]:
            return

        await set_contextual_locales_from_guild(self.bot, guild)

        if await self.filter_hits(member.guild, member.display_name):
            name_to_use = guild_data["filter_default_name"]
            reason = _("Filtered nickname") if member.nick else _("Filtered name")
            try:
                await member.edit(nick=name_to_use, reason=reason)
            except discord.HTTPException:
                pass
            return
