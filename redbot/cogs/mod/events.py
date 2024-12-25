import logging
from datetime import timezone
from collections import defaultdict, deque
from typing import List, Optional

import discord
from redbot.core import i18n, modlog, commands
from redbot.core.utils.mod import is_mod_or_superior
from .abc import MixinMeta

_ = i18n.Translator("Mod", __file__)
log = logging.getLogger("red.mod")


class Events(MixinMeta):
    """
    This is a mixin for the core mod cog
    Has a bunch of things split off to here.
    """

    async def check_duplicates(self, message):
        guild = message.guild
        author = message.author

        guild_cache = self.cache.get(guild.id, None)
        if guild_cache is None:
            repeats = await self.config.guild(guild).delete_repeats()
            if repeats == -1:
                return False
            guild_cache = self.cache[guild.id] = defaultdict(lambda: deque(maxlen=repeats))

        if not message.content:
            return False

        guild_cache[author].append(message.content)
        msgs = guild_cache[author]
        if len(msgs) == msgs.maxlen and len(set(msgs)) == 1:
            try:
                await message.delete()
                return True
            except discord.HTTPException:
                pass
        return False

    async def check_mention_spam(self, message):
        guild, author = message.guild, message.author
        mention_spam = await self.config.guild(guild).mention_spam.all()

        if mention_spam["strict"]:  # if strict is enabled
            mentions = len(message.raw_mentions) + len(message.raw_role_mentions)
        else:  # if not enabled
            mentions = len(set(message.mentions)) + len(set(message.role_mentions))

        if mention_spam["ban"]:
            if mentions >= mention_spam["ban"]:
                try:
                    await guild.ban(author, reason=_("Mention spam (Autoban)"))
                except discord.HTTPException:
                    log.warning(
                        "Failed to ban a member ({member}) for mention spam in server {guild}.".format(
                            member=author.id, guild=guild.id
                        )
                    )
                else:
                    await modlog.create_case(
                        self.bot,
                        guild,
                        message.created_at,
                        "ban",
                        author,
                        guild.me,
                        _("Mention spam (Autoban)"),
                        until=None,
                        channel=None,
                    )
                    return True

        if mention_spam["kick"]:
            if mentions >= mention_spam["kick"]:
                try:
                    await guild.kick(author, reason=_("Mention Spam (Autokick)"))
                except discord.HTTPException:
                    log.warning(
                        "Failed to kick a member ({member}) for mention spam in server {guild}".format(
                            member=author.id, guild=guild.id
                        )
                    )
                else:
                    await modlog.create_case(
                        self.bot,
                        guild,
                        message.created_at,
                        "kick",
                        author,
                        guild.me,
                        _("Mention spam (Autokick)"),
                        until=None,
                        channel=None,
                    )
                    return True

        if mention_spam["warn"]:
            if mentions >= mention_spam["warn"]:
                try:
                    await author.send(_("Please do not mass mention people!"))
                except (discord.HTTPException, discord.Forbidden):
                    try:
                        await message.channel.send(
                            _("{member}, Please do not mass mention people!").format(
                                member=author.mention
                            )
                        )
                    except (discord.HTTPException, discord.Forbidden):
                        log.warning(
                            "Failed to warn a member ({member}) for mention spam in server {guild}".format(
                                member=author.id, guild=guild.id
                            )
                        )
                        return False

                await modlog.create_case(
                    self.bot,
                    guild,
                    message.created_at,
                    "warning",
                    author,
                    guild.me,
                    _("Mention spam (Autowarn)"),
                    until=None,
                    channel=None,
                )
                return True
        return False

    @commands.Cog.listener()
    async def on_message(self, message):
        author = message.author
        if message.guild is None or self.bot.user == author:
            return

        if await self.bot.cog_disabled_in_guild(self, message.guild):
            return

        valid_user = isinstance(author, discord.Member) and not author.bot
        if not valid_user:
            return

        #  Bots and mods or superior are ignored from the filter
        mod_or_superior = await is_mod_or_superior(self.bot, obj=author)
        if mod_or_superior:
            return
        # As are anyone configured to be
        if await self.bot.is_automod_immune(message):
            return

        await i18n.set_contextual_locales_from_guild(self.bot, message.guild)

        deleted = await self.check_duplicates(message)
        if not deleted:
            await self.check_mention_spam(message)

    @staticmethod
    def _update_past_names(name: str, name_list: List[Optional[str]]) -> None:
        while None in name_list:  # clean out null entries from a bug
            name_list.remove(None)
        if name in name_list:
            # Ensure order is maintained without duplicates occurring
            name_list.remove(name)
        name_list.append(name)
        while len(name_list) > 20:
            name_list.pop(0)

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        if before.name != after.name:
            track_all_names = await self.config.track_all_names()
            if not track_all_names:
                return
            async with self.config.user(before).past_names() as name_list:
                self._update_past_names(before.name, name_list)
        if before.display_name != after.display_name:
            track_all_names = await self.config.track_all_names()
            if not track_all_names:
                return
            async with self.config.user(before).past_display_names() as name_list:
                self._update_past_names(before.display_name, name_list)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick != after.nick and before.nick is not None:
            guild = after.guild
            if (not guild) or await self.bot.cog_disabled_in_guild(self, guild):
                return
            track_all_names = await self.config.track_all_names()
            track_nicknames = await self.config.guild(guild).track_nicknames()
            if (not track_all_names) or (not track_nicknames):
                return
            async with self.config.member(before).past_nicks() as nick_list:
                self._update_past_names(before.nick, nick_list)
