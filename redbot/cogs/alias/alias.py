import asyncio
import logging
from copy import copy
from re import search
from string import Formatter
from typing import List, Literal

import discord
from redbot.core import Config, commands
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.menus import menu

from redbot.core.bot import Red
from .alias_entry import AliasEntry, AliasCache, ArgParseError

_ = Translator("Alias", __file__)

log = logging.getLogger("red.cogs.alias")


class _TrackingFormatter(Formatter):
    def __init__(self):
        super().__init__()
        self.max = -1

    def get_value(self, key, args, kwargs):
        if isinstance(key, int):
            self.max = max((key, self.max))
        return super().get_value(key, args, kwargs)


@cog_i18n(_)
class Alias(commands.Cog):
    """Create aliases for commands.

    Aliases are alternative names/shortcuts for commands. They
    can act as both a lambda (storing arguments for repeated use)
    or as simply a shortcut to saying "x y z".

    When run, aliases will accept any additional arguments
    and append them to the stored alias.
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, 8927348724)

        self.config.register_global(entries=[], handled_string_creator=False)
        self.config.register_guild(entries=[])
        self._aliases: AliasCache = AliasCache(config=self.config, cache_enabled=True)

    async def cog_load(self) -> None:
        await self._maybe_handle_string_keys()

        if not self._aliases._loaded:
            await self._aliases.load_aliases()

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        if requester != "discord_deleted_user":
            return

        await self._aliases.anonymize_aliases(user_id)

    async def _maybe_handle_string_keys(self):
        # This isn't a normal schema migration because it's being added
        # after the fact for GH-3788
        if await self.config.handled_string_creator():
            return

        async with self.config.entries() as alias_list:
            bad_aliases = []
            for a in alias_list:
                for keyname in ("creator", "guild"):
                    if isinstance((val := a.get(keyname)), str):
                        try:
                            a[keyname] = int(val)
                        except ValueError:
                            # Because migrations weren't created as changes were made,
                            # and the prior form was a string of an ID,
                            # if this fails, there's nothing to go back to
                            bad_aliases.append(a)
                            break

            for a in bad_aliases:
                alias_list.remove(a)

        # if this was using a custom group of (guild_id, aliasname) it would be better but...
        all_guild_aliases = await self.config.all_guilds()

        for guild_id, guild_data in all_guild_aliases.items():
            to_set = []
            modified = False

            for a in guild_data.get("entries", []):
                for keyname in ("creator", "guild"):
                    if isinstance((val := a.get(keyname)), str):
                        try:
                            a[keyname] = int(val)
                        except ValueError:
                            break
                        finally:
                            modified = True
                else:
                    to_set.append(a)

            if modified:
                await self.config.guild_from_id(guild_id).entries.set(to_set)

            await asyncio.sleep(0)
            # control yielded per loop since this is most likely to happen
            # at bot startup, where this is most likely to have a performance
            # hit.

        await self.config.handled_string_creator.set(True)

    def is_command(self, alias_name: str) -> bool:
        """
        The logic here is that if this returns true, the name should not be used for an alias
        The function name can be changed when alias is reworked
        """
        command = self.bot.get_command(alias_name)
        return command is not None or alias_name in commands.RESERVED_COMMAND_NAMES

    @staticmethod
    def is_valid_alias_name(alias_name: str) -> bool:
        return not bool(search(r"\s", alias_name)) and alias_name.isprintable()

    async def get_prefix(self, message: discord.Message) -> str:
        """
        Tries to determine what prefix is used in a message object.
            Looks to identify from longest prefix to smallest.

            Will raise ValueError if no prefix is found.
        :param message: Message object
        :return:
        """
        content = message.content
        prefix_list = await self.bot.command_prefix(self.bot, message)
        prefixes = sorted(prefix_list, key=lambda pfx: len(pfx), reverse=True)
        for p in prefixes:
            if content.startswith(p):
                return p
        raise ValueError("No prefix found.")

    async def call_alias(self, message: discord.Message, prefix: str, alias: AliasEntry):
        new_message = self.translate_alias_message(message, prefix, alias)
        await self.bot.process_commands(new_message)

    def translate_alias_message(self, message: discord.Message, prefix: str, alias: AliasEntry):
        """
        Translates a discord message using an alias
        for a command to a discord message using the
        alias' base command.
        """
        new_message = copy(message)
        try:
            args = alias.get_extra_args_from_alias(message, prefix)
        except commands.BadArgument:
            return

        trackform = _TrackingFormatter()
        command = trackform.format(alias.command, *args)

        # noinspection PyDunderSlots
        new_message.content = "{}{} {}".format(
            prefix, command, " ".join(args[trackform.max + 1 :])
        ).strip()

        return new_message

    async def paginate_alias_list(
        self, ctx: commands.Context, alias_list: List[AliasEntry]
    ) -> None:
        names = sorted(["+ " + a.name for a in alias_list])
        message = "\n".join(names)
        temp = list(pagify(message, delims=["\n"], page_length=1850))
        alias_list = []
        count = 0
        for page in temp:
            count += 1
            page = page.lstrip("\n")
            page = (
                _("Aliases:\n")
                + page
                + _("\n\nPage {page}/{total}").format(page=count, total=len(temp))
            )
            alias_list.append(box("".join(page), "diff"))
        if len(alias_list) == 1:
            await ctx.send(alias_list[0])
            return
        await menu(ctx, alias_list)

    @commands.group()
    async def alias(self, ctx: commands.Context):
        """Manage command aliases."""
        pass

    @alias.group(name="global")
    async def global_(self, ctx: commands.Context):
        """Manage global aliases."""
        pass

    @commands.mod_or_permissions(manage_guild=True)
    @alias.command(name="add")
    @commands.guild_only()
    async def _add_alias(self, ctx: commands.Context, alias_name: str, *, command):
        """Add an alias for a command."""
        # region Alias Add Validity Checking
        is_command = self.is_command(alias_name)
        if is_command:
            await ctx.send(
                _(
                    "You attempted to create a new alias"
                    " with the name {name} but that"
                    " name is already a command on this bot."
                ).format(name=alias_name)
            )
            return

        alias = await self._aliases.get_alias(ctx.guild, alias_name)
        if alias:
            await ctx.send(
                _(
                    "You attempted to create a new alias"
                    " with the name {name} but that"
                    " alias already exists."
                ).format(name=alias_name)
            )
            return

        is_valid_name = self.is_valid_alias_name(alias_name)
        if not is_valid_name:
            await ctx.send(
                _(
                    "You attempted to create a new alias"
                    " with the name {name} but that"
                    " name is an invalid alias name. Alias"
                    " names may not contain spaces."
                ).format(name=alias_name)
            )
            return

        given_command_exists = self.bot.get_command(command.split(maxsplit=1)[0]) is not None
        if not given_command_exists:
            await ctx.send(
                _("You attempted to create a new alias for a command that doesn't exist.")
            )
            return
        # endregion

        # At this point we know we need to make a new alias
        #   and that the alias name is valid.

        try:
            await self._aliases.add_alias(ctx, alias_name, command)
        except ArgParseError as e:
            return await ctx.send(" ".join(e.args))

        await ctx.send(
            _("A new alias with the trigger `{name}` has been created.").format(name=alias_name)
        )

    @commands.is_owner()
    @global_.command(name="add")
    async def _add_global_alias(self, ctx: commands.Context, alias_name: str, *, command):
        """Add a global alias for a command."""
        # region Alias Add Validity Checking
        is_command = self.is_command(alias_name)
        if is_command:
            await ctx.send(
                _(
                    "You attempted to create a new global alias"
                    " with the name {name} but that"
                    " name is already a command on this bot."
                ).format(name=alias_name)
            )
            return

        alias = await self._aliases.get_alias(None, alias_name)
        if alias:
            await ctx.send(
                _(
                    "You attempted to create a new global alias"
                    " with the name {name} but that"
                    " alias already exists."
                ).format(name=alias_name)
            )
            return

        is_valid_name = self.is_valid_alias_name(alias_name)
        if not is_valid_name:
            await ctx.send(
                _(
                    "You attempted to create a new global alias"
                    " with the name {name} but that"
                    " name is an invalid alias name. Alias"
                    " names may not contain spaces."
                ).format(name=alias_name)
            )
            return

        given_command_exists = self.bot.get_command(command.split(maxsplit=1)[0]) is not None
        if not given_command_exists:
            await ctx.send(
                _("You attempted to create a new alias for a command that doesn't exist.")
            )
            return
        # endregion

        try:
            await self._aliases.add_alias(ctx, alias_name, command, global_=True)
        except ArgParseError as e:
            return await ctx.send(" ".join(e.args))

        await ctx.send(
            _("A new global alias with the trigger `{name}` has been created.").format(
                name=alias_name
            )
        )

    @commands.mod_or_permissions(manage_guild=True)
    @alias.command(name="edit")
    @commands.guild_only()
    async def _edit_alias(self, ctx: commands.Context, alias_name: str, *, command):
        """Edit an existing alias in this server."""
        # region Alias Add Validity Checking
        alias = await self._aliases.get_alias(ctx.guild, alias_name)
        if not alias:
            await ctx.send(
                _("The alias with the name {name} does not exist.").format(name=alias_name)
            )
            return

        given_command_exists = self.bot.get_command(command.split(maxsplit=1)[0]) is not None
        if not given_command_exists:
            await ctx.send(_("You attempted to edit an alias to a command that doesn't exist."))
            return
        # endregion

        # So we figured it is a valid alias and the command exists
        # we can go ahead editing the command
        try:
            if await self._aliases.edit_alias(ctx, alias_name, command):
                await ctx.send(
                    _("The alias with the trigger `{name}` has been edited successfully.").format(
                        name=alias_name
                    )
                )
            else:
                # This part should technically never be reached...
                await ctx.send(
                    _("Alias with the name `{name}` was not found.").format(name=alias_name)
                )
        except ArgParseError as e:
            return await ctx.send(" ".join(e.args))

    @commands.is_owner()
    @global_.command(name="edit")
    async def _edit_global_alias(self, ctx: commands.Context, alias_name: str, *, command):
        """Edit an existing global alias."""
        # region Alias Add Validity Checking
        alias = await self._aliases.get_alias(None, alias_name)
        if not alias:
            await ctx.send(
                _("The alias with the name {name} does not exist.").format(name=alias_name)
            )
            return

        given_command_exists = self.bot.get_command(command.split(maxsplit=1)[0]) is not None
        if not given_command_exists:
            await ctx.send(_("You attempted to edit an alias to a command that doesn't exist."))
            return
        # endregion

        try:
            if await self._aliases.edit_alias(ctx, alias_name, command, global_=True):
                await ctx.send(
                    _("The alias with the trigger `{name}` has been edited successfully.").format(
                        name=alias_name
                    )
                )
            else:
                # This part should technically never be reached...
                await ctx.send(
                    _("Alias with the name `{name}` was not found.").format(name=alias_name)
                )
        except ArgParseError as e:
            return await ctx.send(" ".join(e.args))

    @alias.command(name="help")
    async def _help_alias(self, ctx: commands.Context, alias_name: str):
        """Try to execute help for the base command of the alias."""
        alias = await self._aliases.get_alias(ctx.guild, alias_name=alias_name)
        if alias:
            await self.bot.send_help_for(ctx, alias.command)
        else:
            await ctx.send(_("No such alias exists."))

    @alias.command(name="show")
    async def _show_alias(self, ctx: commands.Context, alias_name: str):
        """Show what command the alias executes."""
        alias = await self._aliases.get_alias(ctx.guild, alias_name)

        if alias:
            await ctx.send(
                _("The `{alias_name}` alias will execute the command `{command}`").format(
                    alias_name=alias_name, command=alias.command
                )
            )
        else:
            await ctx.send(_("There is no alias with the name `{name}`").format(name=alias_name))

    @commands.mod_or_permissions(manage_guild=True)
    @alias.command(name="delete", aliases=["del", "remove"])
    @commands.guild_only()
    async def _del_alias(self, ctx: commands.Context, alias_name: str):
        """Delete an existing alias on this server."""
        if not await self._aliases.get_guild_aliases(ctx.guild):
            await ctx.send(_("There are no aliases on this server."))
            return

        if await self._aliases.delete_alias(ctx, alias_name):
            await ctx.send(
                _("Alias with the name `{name}` was successfully deleted.").format(name=alias_name)
            )
        else:
            await ctx.send(_("Alias with name `{name}` was not found.").format(name=alias_name))

    @commands.is_owner()
    @global_.command(name="delete", aliases=["del", "remove"])
    async def _del_global_alias(self, ctx: commands.Context, alias_name: str):
        """Delete an existing global alias."""
        if not await self._aliases.get_global_aliases():
            await ctx.send(_("There are no global aliases on this bot."))
            return

        if await self._aliases.delete_alias(ctx, alias_name, global_=True):
            await ctx.send(
                _("Alias with the name `{name}` was successfully deleted.").format(name=alias_name)
            )
        else:
            await ctx.send(_("Alias with name `{name}` was not found.").format(name=alias_name))

    @alias.command(name="list")
    @commands.guild_only()
    @commands.bot_can_react()
    async def _list_alias(self, ctx: commands.Context):
        """List the available aliases on this server."""
        guild_aliases = await self._aliases.get_guild_aliases(ctx.guild)
        if not guild_aliases:
            return await ctx.send(_("There are no aliases on this server."))
        await self.paginate_alias_list(ctx, guild_aliases)

    @global_.command(name="list")
    @commands.bot_can_react()
    async def _list_global_alias(self, ctx: commands.Context):
        """List the available global aliases on this bot."""
        global_aliases = await self._aliases.get_global_aliases()
        if not global_aliases:
            return await ctx.send(_("There are no global aliases."))
        await self.paginate_alias_list(ctx, global_aliases)

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if message.guild is not None:
            if await self.bot.cog_disabled_in_guild(self, message.guild):
                return

        try:
            prefix = await self.get_prefix(message)
        except ValueError:
            return

        try:
            potential_alias = message.content[len(prefix) :].split(" ")[0]
        except IndexError:
            return

        alias = await self._aliases.get_alias(message.guild, potential_alias)

        if alias:
            await self.call_alias(message, prefix, alias)
