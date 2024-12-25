# Warning: The implementation below touches several private attributes.
# While this implementation will be updated, and public interfaces maintained,
# derived classes should not assume these private attributes are version safe,
# and use the provided HelpSettings class for these settings.

# This is a full replacement of discord.py's help command
#
# This exists due to deficiencies in discord.py which conflict
# with our needs for per-context help settings
# see https://github.com/Rapptz/discord.py/issues/2123
#
# While the issue above discusses this as theoretical, merely interacting with config within
# the help command preparation was enough to cause
# demonstrable breakage in 150 help invokes in a 2 minute window.
# This is not an unreasonable volume on some already existing Red instances,
# especially since help is invoked for command groups
# automatically when subcommands are not provided correctly as user feedback.
#
# The implemented fix is in
# https://github.com/Rapptz/discord.py/commit/ad5beed8dd75c00bd87492cac17fe877033a3ea1
#
# While this fix would handle our immediate specific issues, it's less appropriate to use
# Where we do not have a downstream consumer to consider.
# Simply modifying the design to not be susceptible to the issue,
# rather than adding copy and deepcopy use in multiple places is better for us
#
# Additionally, this gives our users a bit more customization options including by
# 3rd party cogs down the road.

import abc
import asyncio
from collections import namedtuple
from dataclasses import dataclass, asdict as dc_asdict
from enum import Enum
from typing import Union, List, AsyncIterator, Iterable, cast

import discord
from discord.ext import commands as dpy_commands

from . import commands
from .context import Context
from ..i18n import Translator
from ..utils.views import SimpleMenu
from ..utils import can_user_react_in, menus
from ..utils.mod import mass_purge
from ..utils._internal_utils import fuzzy_command_search, format_fuzzy_results
from ..utils.chat_formatting import (
    bold,
    box,
    humanize_list,
    humanize_number,
    humanize_timedelta,
    pagify,
    underline,
)

__all__ = ["red_help", "RedHelpFormatter", "HelpSettings", "HelpFormatterABC"]

_ = Translator("Help", __file__)

HelpTarget = Union[commands.Command, commands.Group, commands.Cog, dpy_commands.bot.BotBase, str]

# The below could be a protocol if we pulled in typing_extensions from mypy.
SupportsCanSee = Union[commands.Command, commands.Group, dpy_commands.bot.BotBase, commands.Cog]

EmbedField = namedtuple("EmbedField", "name value inline")
EMPTY_STRING = "\N{ZERO WIDTH SPACE}"


class HelpMenuSetting(Enum):
    disabled = 0
    reactions = 1
    buttons = 2
    select = 3
    selectonly = 4


@dataclass(frozen=True)
class HelpSettings:
    """
    A representation of help settings.

    .. warning::

        This class is `provisional <developer-guarantees-exclusions>`.

    """

    page_char_limit: int = 1000
    max_pages_in_guild: int = 2
    use_menus: HelpMenuSetting = HelpMenuSetting(0)
    show_hidden: bool = False
    show_aliases: bool = True
    verify_checks: bool = True
    verify_exists: bool = False
    tagline: str = ""
    delete_delay: int = 0
    use_tick: bool = False
    react_timeout: int = 30

    # Contrib Note: This is intentional to not accept the bot object
    # There are plans to allow guild and user specific help settings
    # Adding a non-context based method now would involve a breaking
    # change later.
    # At a later date, more methods should be exposed for
    # non-context based creation.
    #
    # This is also why we aren't just caching the
    # current state of these settings on the bot object.
    @classmethod
    async def from_context(cls, context: Context):
        """
        Get the HelpSettings for the current context
        """
        settings = await context.bot._config.help.all()
        menus = settings.pop("use_menus", 0)
        return cls(**settings, use_menus=HelpMenuSetting(menus))

    @property
    def pretty(self):
        """Returns a discord safe representation of the settings"""

        def bool_transformer(val):
            if val is False:
                return _("No")
            if val is True:
                return _("Yes")
            return val

        data = {k: bool_transformer(v) for k, v in dc_asdict(self).items()}

        if not self.delete_delay:
            data["delete_delay"] = _("Disabled")
        else:
            data["delete_delay"] = humanize_timedelta(seconds=self.delete_delay)

        if tag := data.pop("tagline", ""):
            tagline_info = _("\nCustom Tagline: {tag}").format(tag=tag)
        else:
            tagline_info = ""

        data["tagline_info"] = tagline_info
        menus_str = {
            HelpMenuSetting.disabled: _("No"),
            HelpMenuSetting.reactions: _("Yes, reactions"),
            HelpMenuSetting.buttons: _("Yes, buttons"),
            HelpMenuSetting.select: _("Yes, buttons with select menu"),
            HelpMenuSetting.selectonly: _("Yes, select menu only"),
        }
        data["use_menus"] = menus_str[self.use_menus]

        return _(
            "Maximum characters per page: {page_char_limit}"
            "\nMaximum pages per guild (only used if menus are not used): {max_pages_in_guild}"
            "\nHelp is a menu: {use_menus}"
            "\nHelp shows hidden commands: {show_hidden}"
            "\nHelp shows commands aliases: {show_aliases}"
            "\nHelp only shows commands which can be used: {verify_checks}"
            "\nHelp shows unusable commands when asked directly: {verify_exists}"
            "\nDelete delay: {delete_delay}"
            "\nReact with a checkmark when help is sent via DM: {use_tick}"
            "\nReaction timeout (only used if menus are used): {react_timeout} seconds"
            "{tagline_info}"
        ).format_map(data)


class NoCommand(Exception):
    pass


class NoSubCommand(Exception):
    def __init__(self, *, last, not_found):
        self.last = last
        self.not_found = not_found


class HelpFormatterABC(abc.ABC):
    """
    Describes the required interface of a help formatter.

    Additional notes for 3rd party developers are included in this class.

    .. note::
        You may define __init__ however you want
        (such as to include config),
        Red will not initialize a formatter for you,
        and must be passed an initialized formatter.

        If you want to use Red's existing settings, use ``HelpSettings.from_context``

    .. warning::

        This class is documented but `provisional <developer-guarantees-exclusions>` with expected changes.

        In the future, this class will receive changes to support
        invoking the help command without context.
    """

    @abc.abstractmethod
    async def send_help(
        self, ctx: Context, help_for: HelpTarget = None, *, from_help_command: bool = False
    ):
        """
        This is (currently) the only method you must implement.

        This method should handle any and all errors which may arise.

        The types subclasses must handle are defined as ``HelpTarget``
        """
        ...


class RedHelpFormatter(HelpFormatterABC):
    """
    Red's help implementation

    This is intended to be overridable in parts to only change some behavior.

    While this exists as a class for easy partial overriding,
    most implementations should not need or want a shared state.

    .. warning::

        This class is documented but may receive changes between
        versions without warning as needed.
        The supported way to modify help is to write a separate formatter.

        The primary reason for this class being documented is to allow
        the opaque use of the class as a fallback, as any method in base
        class which is intended for use will be present and implemented here.

    .. note::

        This class may use various internal methods which are not safe to
        use in third party code.
        The internal methods used here may change,
        with this class being updated at the same time.
    """

    async def send_help(
        self, ctx: Context, help_for: HelpTarget = None, *, from_help_command: bool = False
    ):
        """
        This delegates to other functions.

        For most cases, you should use this and only this directly.
        """

        help_settings = await HelpSettings.from_context(ctx)

        if help_for is None or isinstance(help_for, dpy_commands.bot.BotBase):
            await self.format_bot_help(ctx, help_settings=help_settings)
            return

        if isinstance(help_for, str):
            try:
                help_for = self.parse_command(ctx, help_for)
            except NoCommand:
                await self.command_not_found(ctx, help_for, help_settings=help_settings)
                return
            except NoSubCommand as exc:
                if help_settings.verify_exists:
                    await self.subcommand_not_found(
                        ctx, exc.last, exc.not_found, help_settings=help_settings
                    )
                    return
                help_for = exc.last

        if isinstance(help_for, commands.Cog):
            await self.format_cog_help(ctx, help_for, help_settings=help_settings)
        else:
            await self.format_command_help(ctx, help_for, help_settings=help_settings)

    async def get_cog_help_mapping(
        self, ctx: Context, obj: commands.Cog, help_settings: HelpSettings
    ):
        iterator = filter(lambda c: c.parent is None and c.cog is obj, ctx.bot.commands)
        return {
            com.name: com
            async for com in self.help_filter_func(ctx, iterator, help_settings=help_settings)
        }

    async def get_group_help_mapping(
        self, ctx: Context, obj: commands.Group, help_settings: HelpSettings
    ):
        return {
            com.name: com
            async for com in self.help_filter_func(
                ctx, obj.all_commands.values(), help_settings=help_settings
            )
        }

    async def get_bot_help_mapping(self, ctx, help_settings: HelpSettings):
        sorted_iterable = []
        for cogname, cog in (*sorted(ctx.bot.cogs.items()), (None, None)):
            cm = await self.get_cog_help_mapping(ctx, cog, help_settings=help_settings)
            if cm:
                sorted_iterable.append((cogname, cm))
        return sorted_iterable

    @staticmethod
    def get_default_tagline(ctx: Context):
        return _(
            "Type {command1} for more info on a command. "
            "You can also type {command2} for more info on a category."
        ).format(
            command1=f"{ctx.clean_prefix}help <command>",
            command2=f"{ctx.clean_prefix}help <category>",
        )

    @staticmethod
    def format_tagline(ctx: Context, tagline: str):
        if not tagline:
            return
        return tagline.replace("[p]", ctx.clean_prefix)

    @staticmethod
    def get_command_signature(ctx: Context, command: commands.Command) -> str:
        parent = command.parent
        entries = []
        while parent is not None:
            if not parent.signature or parent.invoke_without_command:
                entries.append(parent.name)
            else:
                entries.append(parent.name + " " + parent.signature)
            parent = parent.parent
        parent_sig = (" ".join(reversed(entries)) + " ") if entries else ""

        return f"{ctx.clean_prefix}{parent_sig}{command.name} {command.signature}"

    async def format_command_help(
        self, ctx: Context, obj: commands.Command, help_settings: HelpSettings
    ):
        send = help_settings.verify_exists
        if not send:
            async for __ in self.help_filter_func(
                ctx, (obj,), bypass_hidden=True, help_settings=help_settings
            ):
                # This is a really lazy option for not
                # creating a separate single case version.
                # It is efficient though
                #
                # We do still want to bypass the hidden requirement on
                # a specific command explicitly invoked here.
                send = True

        if not send:
            return

        command = obj

        description = command.description or ""

        tagline = self.format_tagline(ctx, help_settings.tagline) or self.get_default_tagline(ctx)
        signature = self.get_command_signature(ctx, command)

        aliases = command.aliases
        sig_description = bold(_("Syntax:\n")) + box(signature)
        if help_settings.show_aliases and aliases:
            alias_fmt = _("Aliases") if len(command.aliases) > 1 else _("Alias")
            aliases = sorted(aliases, key=len)

            a_counter = 0
            valid_alias_list = []
            for alias in aliases:
                if (a_counter := a_counter + len(alias)) < 500:
                    valid_alias_list.append(alias)
                else:
                    break

            a_diff = len(aliases) - len(valid_alias_list)
            aliases_list = [
                f"{ctx.clean_prefix}{command.parent.qualified_name + ' ' if command.parent else ''}{alias}"
                for alias in valid_alias_list
            ]
            if len(valid_alias_list) < 10:
                aliases_content = humanize_list(aliases_list)
            else:
                aliases_formatted_list = ", ".join(aliases_list)
                if a_diff > 1:
                    aliases_content = _("{aliases} and {number} more aliases.").format(
                        aliases=aliases_formatted_list, number=humanize_number(a_diff)
                    )
                else:
                    aliases_content = _("{aliases} and one more alias.").format(
                        aliases=aliases_formatted_list
                    )
            sig_description += bold(f"{alias_fmt}:") + box(f"{aliases_content}")

        subcommands = None
        if hasattr(command, "all_commands"):
            grp = cast(commands.Group, command)
            subcommands = await self.get_group_help_mapping(ctx, grp, help_settings=help_settings)

        if await self.embed_requested(ctx):
            emb = {"embed": {"title": "", "description": ""}, "footer": {"text": ""}, "fields": []}

            if description:
                emb["embed"]["title"] = f"*{description[:250]}*"

            emb["footer"]["text"] = tagline
            emb["embed"]["description"] = sig_description

            command_help = command.format_help_for_context(ctx)
            if command_help:
                splitted = filter(None, command_help.split("\n\n"))
                try:
                    name = next(splitted)
                except StopIteration:
                    # all parts are empty
                    pass
                else:
                    value = "\n\n".join(splitted)
                    if not value:
                        value = EMPTY_STRING
                    field = EmbedField(name[:250], value[:1024], False)
                    emb["fields"].append(field)

            if subcommands:

                def shorten_line(a_line: str) -> str:
                    if len(a_line) < 70:  # embed max width needs to be lower
                        return a_line
                    return a_line[:67].rstrip() + "..."

                subtext = "\n".join(
                    shorten_line(f"**{name}** {command.format_shortdoc_for_context(ctx)}")
                    for name, command in sorted(subcommands.items())
                )
                for i, page in enumerate(pagify(subtext, page_length=500, shorten_by=0)):
                    if i == 0:
                        title = bold(underline(_("Subcommands:")), escape_formatting=False)
                    else:
                        title = bold(underline(_("Subcommands:")), escape_formatting=False) + _(
                            " (continued)"
                        )
                    field = EmbedField(title, page, False)
                    emb["fields"].append(field)

            await self.make_and_send_embeds(ctx, emb, help_settings=help_settings)

        else:  # Code blocks:
            subtext = None
            subtext_header = None
            if subcommands:
                subtext_header = _("Subcommands:")
                max_width = max(discord.utils._string_width(name) for name in subcommands.keys())

                def width_maker(cmds):
                    doc_max_width = 80 - max_width
                    for nm, com in sorted(cmds):
                        width_gap = discord.utils._string_width(nm) - len(nm)
                        doc = com.format_shortdoc_for_context(ctx)
                        if len(doc) > doc_max_width:
                            doc = doc[: doc_max_width - 3].rstrip() + "..."
                        yield nm, doc, max_width - width_gap

                subtext = "\n".join(
                    f"  {name:<{width}} {doc}"
                    for name, doc, width in width_maker(subcommands.items())
                )

            to_page = "\n\n".join(
                filter(
                    None,
                    (
                        description,
                        signature,
                        command.format_help_for_context(ctx),
                        subtext_header,
                        subtext,
                    ),
                )
            )
            pages = [box(p) for p in pagify(to_page)]
            await self.send_pages(ctx, pages, embed=False, help_settings=help_settings)

    @staticmethod
    def group_embed_fields(fields: List[EmbedField], max_chars=1000):
        curr_group = []
        ret = []
        current_count = 0

        for i, f in enumerate(fields):
            f_len = len(f.value) + len(f.name)

            # Commands start at the 1st index of fields, i < 2 is a hacky workaround for now
            if not current_count or f_len + current_count < max_chars or i < 2:
                current_count += f_len
                curr_group.append(f)
            elif curr_group:
                ret.append(curr_group)
                current_count = f_len
                curr_group = [f]
        else:
            if curr_group:
                ret.append(curr_group)

        return ret

    async def make_and_send_embeds(self, ctx, embed_dict: dict, help_settings: HelpSettings):
        pages = []

        page_char_limit = help_settings.page_char_limit
        page_char_limit = min(page_char_limit, 5500)  # Just in case someone was manually...

        author_info = {
            "name": _("{ctx.me.display_name} Help Menu").format(ctx=ctx),
            "icon_url": ctx.me.display_avatar,
        }

        # Offset calculation here is for total embed size limit
        # 20 accounts for# *Page {i} of {page_count}*
        offset = len(author_info["name"]) + 20
        foot_text = embed_dict["footer"]["text"]
        if foot_text:
            offset += len(foot_text)
        offset += len(embed_dict["embed"]["description"])
        offset += len(embed_dict["embed"]["title"])

        # In order to only change the size of embeds when necessary for this rather
        # than change the existing behavior for people unaffected by this
        # we're only modifying the page char limit should they be impacted.
        # We could consider changing this to always just subtract the offset,
        # But based on when this is being handled (very end of 3.2 release)
        # I'd rather not stick a major visual behavior change in at the last moment.
        if page_char_limit + offset > 5500:
            # This is still necessary with the max interaction above
            # While we could subtract 100% of the time the offset from page_char_limit
            # the intent here is to shorten again
            # *only* when necessary, by the exact necessary amount
            # To retain a visual match with prior behavior.
            page_char_limit = 5500 - offset
        elif page_char_limit < 250:
            # Prevents an edge case where a combination of long cog help and low limit
            # Could prevent anything from ever showing up.
            # This lower bound is safe based on parts of embed in use.
            page_char_limit = 250

        field_groups = self.group_embed_fields(embed_dict["fields"], page_char_limit)

        color = await ctx.embed_color()
        page_count = len(field_groups)

        if not field_groups:  # This can happen on single command without a docstring
            embed = discord.Embed(color=color, **embed_dict["embed"])
            embed.set_author(**author_info)
            embed.set_footer(**embed_dict["footer"])
            pages.append(embed)

        for i, group in enumerate(field_groups, 1):
            embed = discord.Embed(color=color, **embed_dict["embed"])

            if page_count > 1:
                description = _("*Page {page_num} of {page_count}*\n{content_description}").format(
                    content_description=embed.description, page_num=i, page_count=page_count
                )
                embed.description = description

            embed.set_author(**author_info)

            for field in group:
                embed.add_field(**field._asdict())

            embed.set_footer(**embed_dict["footer"])

            pages.append(embed)

        await self.send_pages(ctx, pages, embed=True, help_settings=help_settings)

    async def format_cog_help(self, ctx: Context, obj: commands.Cog, help_settings: HelpSettings):
        coms = await self.get_cog_help_mapping(ctx, obj, help_settings=help_settings)
        if not (coms or help_settings.verify_exists):
            return

        description = obj.format_help_for_context(ctx)
        tagline = self.format_tagline(ctx, help_settings.tagline) or self.get_default_tagline(ctx)

        if await self.embed_requested(ctx):
            emb = {"embed": {"title": "", "description": ""}, "footer": {"text": ""}, "fields": []}

            emb["footer"]["text"] = tagline
            if description:
                splitted = filter(None, description.split("\n\n"))
                try:
                    name = next(splitted)
                except StopIteration:
                    # all parts are empty
                    pass
                else:
                    value = "\n\n".join(splitted)
                    if not value:
                        value = EMPTY_STRING
                    field = EmbedField(name[:252], value[:1024], False)
                    emb["fields"].append(field)

            if coms:

                def shorten_line(a_line: str) -> str:
                    if len(a_line) < 70:  # embed max width needs to be lower
                        return a_line
                    return a_line[:67].rstrip() + "..."

                command_text = "\n".join(
                    shorten_line(f"{bold(name)} {command.format_shortdoc_for_context(ctx)}")
                    for name, command in sorted(coms.items())
                )
                for i, page in enumerate(pagify(command_text, page_length=500, shorten_by=0)):
                    if i == 0:
                        title = underline(bold(_("Commands:")), escape_formatting=False)
                    else:
                        title = underline(bold(_("Commands:")), escape_formatting=False) + _(
                            " (continued)"
                        )
                    field = EmbedField(title, page, False)
                    emb["fields"].append(field)

            await self.make_and_send_embeds(ctx, emb, help_settings=help_settings)

        else:
            subtext = None
            subtext_header = None
            if coms:
                subtext_header = _("Commands:")
                max_width = max(discord.utils._string_width(name) for name in coms.keys())

                def width_maker(cmds):
                    doc_max_width = 80 - max_width
                    for nm, com in sorted(cmds):
                        width_gap = discord.utils._string_width(nm) - len(nm)
                        doc = com.format_shortdoc_for_context(ctx)
                        if len(doc) > doc_max_width:
                            doc = doc[: doc_max_width - 3].rstrip() + "..."
                        yield nm, doc, max_width - width_gap

                subtext = "\n".join(
                    f"  {name:<{width}} {doc}" for name, doc, width in width_maker(coms.items())
                )

            to_page = "\n\n".join(filter(None, (description, subtext_header, subtext)))
            pages = [box(p) for p in pagify(to_page)]
            await self.send_pages(ctx, pages, embed=False, help_settings=help_settings)

    async def format_bot_help(self, ctx: Context, help_settings: HelpSettings):
        coms = await self.get_bot_help_mapping(ctx, help_settings=help_settings)
        if not coms:
            return

        description = ctx.bot.description or ""
        tagline = self.format_tagline(ctx, help_settings.tagline) or self.get_default_tagline(ctx)

        if await self.embed_requested(ctx):
            emb = {"embed": {"title": "", "description": ""}, "footer": {"text": ""}, "fields": []}

            emb["footer"]["text"] = tagline
            if description:
                emb["embed"]["title"] = f"*{description[:250]}*"

            for cog_name, data in coms:
                if cog_name:
                    title = underline(bold(f"{cog_name}:"), escape_formatting=False)
                else:
                    title = underline(bold(_("No Category:")), escape_formatting=False)

                def shorten_line(a_line: str) -> str:
                    if len(a_line) < 70:  # embed max width needs to be lower
                        return a_line
                    return a_line[:67].rstrip() + "..."

                cog_text = "\n".join(
                    shorten_line(f"**{name}** {command.format_shortdoc_for_context(ctx)}")
                    for name, command in sorted(data.items())
                )

                for i, page in enumerate(pagify(cog_text, page_length=1000, shorten_by=0)):
                    title = title if i < 1 else _("{title} (continued)").format(title=title)
                    field = EmbedField(title, page, False)
                    emb["fields"].append(field)

            await self.make_and_send_embeds(ctx, emb, help_settings=help_settings)

        else:
            to_join = []
            if description:
                to_join.append(f"{description}\n")

            names = []
            for k, v in coms:
                names.extend(list(v.name for v in v.values()))

            max_width = max(
                discord.utils._string_width((name or _("No Category:"))) for name in names
            )

            def width_maker(cmds):
                doc_max_width = 80 - max_width
                for nm, com in cmds:
                    width_gap = discord.utils._string_width(nm) - len(nm)
                    doc = com.format_shortdoc_for_context(ctx)
                    if len(doc) > doc_max_width:
                        doc = doc[: doc_max_width - 3].rstrip() + "..."
                    yield nm, doc, max_width - width_gap

            for cog_name, data in coms:
                title = f"{cog_name}:" if cog_name else _("No Category:")
                to_join.append(title)

                for name, doc, width in width_maker(sorted(data.items())):
                    to_join.append(f"  {name:<{width}} {doc}")

            to_join.append(f"\n{tagline}")
            to_page = "\n".join(to_join)
            pages = [box(p) for p in pagify(to_page)]
            await self.send_pages(ctx, pages, embed=False, help_settings=help_settings)

    @staticmethod
    async def help_filter_func(
        ctx,
        objects: Iterable[SupportsCanSee],
        help_settings: HelpSettings,
        bypass_hidden=False,
    ) -> AsyncIterator[SupportsCanSee]:
        """
        This does most of actual filtering.
        """
        show_hidden = bypass_hidden or help_settings.show_hidden
        verify_checks = help_settings.verify_checks

        # TODO: Settings for this in core bot db
        for obj in objects:
            if verify_checks and not show_hidden:
                # Default Red behavior, can_see includes a can_run check.
                if await obj.can_see(ctx) and getattr(obj, "enabled", True):
                    yield obj
            elif verify_checks:
                try:
                    can_run = await obj.can_run(ctx)
                except discord.DiscordException:
                    can_run = False
                if can_run and getattr(obj, "enabled", True):
                    yield obj
            elif not show_hidden:
                if not getattr(obj, "hidden", False):  # Cog compatibility
                    yield obj
            else:
                yield obj

    async def embed_requested(self, ctx: Context) -> bool:
        return await ctx.bot.embed_requested(channel=ctx, command=red_help)

    async def command_not_found(self, ctx, help_for, help_settings: HelpSettings):
        """
        Sends an error, fuzzy help, or stays quiet based on settings
        """
        fuzzy_commands = await fuzzy_command_search(
            ctx,
            help_for,
            commands=self.help_filter_func(
                ctx, ctx.bot.walk_commands(), help_settings=help_settings
            ),
            min_score=75,
        )
        use_embeds = await self.embed_requested(ctx)
        if fuzzy_commands:
            ret = await format_fuzzy_results(ctx, fuzzy_commands, embed=use_embeds)
            if use_embeds:
                ret.set_author(
                    name=_("{ctx.me.display_name} Help Menu").format(ctx=ctx),
                    icon_url=ctx.me.display_avatar,
                )
                tagline = self.format_tagline(
                    ctx, help_settings.tagline
                ) or self.get_default_tagline(ctx)
                ret.set_footer(text=tagline)
                await ctx.send(embed=ret)
            else:
                await ctx.send(ret)
        elif help_settings.verify_exists:
            ret = _("Help topic for {command_name} not found.").format(command_name=bold(help_for))
            if use_embeds:
                ret = discord.Embed(color=(await ctx.embed_color()), description=ret)
                ret.set_author(
                    name=_("{ctx.me.display_name} Help Menu").format(ctx=ctx),
                    icon_url=ctx.me.display_avatar,
                )
                tagline = self.format_tagline(
                    ctx, help_settings.tagline
                ) or self.get_default_tagline(ctx)
                ret.set_footer(text=tagline)
                await ctx.send(embed=ret)
            else:
                await ctx.send(ret)

    async def subcommand_not_found(self, ctx, command, not_found, help_settings: HelpSettings):
        """
        Sends an error
        """
        ret = _("Command {command_name} has no subcommand named {not_found}.").format(
            command_name=bold(command.qualified_name), not_found=bold(not_found[0])
        )
        if await self.embed_requested(ctx):
            ret = discord.Embed(color=(await ctx.embed_color()), description=ret)
            ret.set_author(
                name=_("{ctx.me.display_name} Help Menu").format(ctx=ctx),
                icon_url=ctx.me.display_avatar,
            )
            tagline = self.format_tagline(ctx, help_settings.tagline) or self.get_default_tagline(
                ctx
            )
            ret.set_footer(text=tagline)
            await ctx.send(embed=ret)
        else:
            await ctx.send(ret)

    @staticmethod
    def parse_command(ctx, help_for: str):
        """
        Handles parsing
        """

        maybe_cog = ctx.bot.get_cog(help_for)
        if maybe_cog:
            return maybe_cog

        com = ctx.bot
        last = None

        clist = help_for.split()

        for index, item in enumerate(clist):
            try:
                com = com.all_commands[item]
                # TODO: This doesn't handle valid command aliases.
                # swap parsing method to use get_command.
            except (KeyError, AttributeError):
                if last:
                    raise NoSubCommand(last=last, not_found=clist[index:]) from None
                else:
                    raise NoCommand() from None
            else:
                last = com

        return com

    async def send_pages(
        self,
        ctx: Context,
        pages: List[Union[str, discord.Embed]],
        embed: bool = True,
        help_settings: HelpSettings = None,
    ):
        """
        Sends pages based on settings.
        """
        if help_settings.use_menus.value >= HelpMenuSetting.buttons.value:
            use_select = help_settings.use_menus.value == 3
            select_only = help_settings.use_menus.value == 4
            menu = SimpleMenu(
                pages,
                timeout=help_settings.react_timeout,
                use_select_menu=use_select,
                use_select_only=select_only,
            )
            # Send menu to DMs if max pages is 0
            if help_settings.max_pages_in_guild == 0:
                await menu.start_dm(ctx.author)
            else:
                await menu.start(ctx)

        elif (
            can_user_react_in(ctx.me, ctx.channel)
            and help_settings.use_menus is HelpMenuSetting.reactions
        ):
            use_DMs = help_settings.max_pages_in_guild == 0
            destination = ctx.author if use_DMs else ctx.channel
            # Specifically ensuring the menu's message is sent prior to returning
            m = await (destination.send(embed=pages[0]) if embed else destination.send(pages[0]))
            c = menus.DEFAULT_CONTROLS if len(pages) > 1 else {"\N{CROSS MARK}": menus.close_menu}
            # Allow other things to happen during menu timeout/interaction.
            asyncio.create_task(
                menus.menu(
                    ctx, pages, c, user=ctx.author, message=m, timeout=help_settings.react_timeout
                )
            )
            # menu needs reactions added manually since we fed it a message
            menus.start_adding_reactions(m, c.keys())

        else:
            max_pages_in_guild = help_settings.max_pages_in_guild
            use_DMs = len(pages) > max_pages_in_guild
            destination = ctx.author if use_DMs else ctx.channel
            delete_delay = help_settings.delete_delay

            messages: List[discord.Message] = []
            for page in pages:
                try:
                    if embed:
                        msg = await destination.send(embed=page)
                    else:
                        msg = await destination.send(page)
                except discord.Forbidden:
                    return await ctx.send(
                        _(
                            "I couldn't send the help message to you in DM. "
                            "Either you blocked me or you disabled DMs in this server."
                        )
                    )
                else:
                    messages.append(msg)
            if use_DMs and help_settings.use_tick:
                await ctx.tick()
            # The if statement takes into account that 'destination' will be
            # the context channel in non-DM context.
            if (
                not use_DMs  # we're not in DMs
                and delete_delay > 0  # delete delay is enabled
                and ctx.bot_permissions.manage_messages  # we can manage messages
            ):
                # We need to wrap this in a task to not block after-sending-help interactions.
                # The channel has to be TextChannel or Thread as we can't bulk-delete from DMs
                async def _delete_delay_help(
                    channel: Union[
                        discord.TextChannel,
                        discord.VoiceChannel,
                        discord.StageChannel,
                        discord.Thread,
                    ],
                    messages: List[discord.Message],
                    delay: int,
                ):
                    await asyncio.sleep(delay)
                    await mass_purge(messages, channel)

                asyncio.create_task(_delete_delay_help(destination, messages, delete_delay))


@commands.command(name="help", hidden=True, i18n=_)
async def red_help(ctx: Context, *, thing_to_get_help_for: str = None):
    """
    I need somebody
    (Help) not just anybody
    (Help) you know I need someone
    (Help!)
    """
    await ctx.bot.send_help_for(ctx, thing_to_get_help_for, from_help_command=True)
