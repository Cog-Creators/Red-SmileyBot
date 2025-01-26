import argparse
import functools
import re
from pathlib import Path

from typing import Final, MutableMapping, Optional, Pattern, Tuple, Union

import discord

from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter

from .apis.api_utils import standardize_scope
from .apis.playlist_interface import get_all_playlist_converter
from .errors import NoMatchesFound, TooManyMatches
from .utils import PlaylistScope

_ = Translator("Audio", Path(__file__))

__all__ = [
    "ComplexScopeParser",
    "PlaylistConverter",
    "ScopeParser",
    "LazyGreedyConverter",
    "standardize_scope",
    "get_lazy_converter",
    "get_playlist_converter",
]

T_ = _
_ = lambda s: s

_SCOPE_HELP: Final[str] = _(
    """
Scope must be a valid version of one of the following:
​ ​ ​ ​ Global
​ ​ ​ ​ Guild
​ ​ ​ ​ User
"""
)
_USER_HELP: Final[str] = _(
    """
Author must be a valid version of one of the following:
​ ​ ​ ​ User ID
​ ​ ​ ​ User Mention
​ ​ ​ ​ User Name#123
"""
)
_GUILD_HELP: Final[str] = _(
    """
Guild must be a valid version of one of the following:
​ ​ ​ ​ Guild ID
​ ​ ​ ​ Exact guild name
"""
)

_ = T_

MENTION_RE: Final[Pattern] = re.compile(r"^<?(?:(?:@[!&]?)?|#)(\d{15,20})>?$")


def _match_id(arg: str) -> Optional[int]:
    m = MENTION_RE.match(arg)
    if m:
        return int(m.group(1))
    return None


async def global_unique_guild_finder(ctx: commands.Context, arg: str) -> discord.Guild:
    bot: Red = ctx.bot
    _id = _match_id(arg)

    if _id is not None:
        guild: discord.Guild = bot.get_guild(_id)
        if guild is not None:
            return guild

    maybe_matches = []
    async for obj in AsyncIter(bot.guilds):
        if obj.name == arg or str(obj) == arg:
            maybe_matches.append(obj)

    if not maybe_matches:
        raise NoMatchesFound(
            _(
                '"{arg}" was not found. It must be the ID or '
                "complete name of a server which the bot can see."
            ).format(arg=arg)
        )
    elif len(maybe_matches) == 1:
        return maybe_matches[0]
    else:
        raise TooManyMatches(
            _(
                '"{arg}" does not refer to a unique server. '
                "Please use the ID for the server you're trying to specify."
            ).format(arg=arg)
        )


async def global_unique_user_finder(
    ctx: commands.Context, arg: str, guild: discord.guild = None
) -> discord.abc.User:
    bot: Red = ctx.bot
    guild = guild or ctx.guild
    _id = _match_id(arg)

    if _id is not None:
        user: discord.User = bot.get_user(_id)
        if user is not None:
            return user

    maybe_matches = []
    async for user in AsyncIter(bot.users).filter(
        lambda u: u.name == arg or u.global_name == arg or f"{u}" == arg
    ):
        maybe_matches.append(user)

    if guild is not None:
        async for member in AsyncIter(guild.members).filter(
            lambda m: m.nick == arg and not any(obj.id == m.id for obj in maybe_matches)
        ):
            maybe_matches.append(member)

    if not maybe_matches:
        raise NoMatchesFound(
            _(
                '"{arg}" was not found. It must be the ID or name or '
                "mention a user which the bot can see."
            ).format(arg=arg)
        )
    elif len(maybe_matches) == 1:
        return maybe_matches[0]
    else:
        raise TooManyMatches(
            _(
                '"{arg}" does not refer to a unique server. '
                "Please use the ID for the server you're trying to specify."
            ).format(arg=arg)
        )


class PlaylistConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> MutableMapping:
        """Get playlist for all scopes that match the argument user provided"""
        cog = ctx.cog
        user_matches = []
        guild_matches = []
        global_matches = []
        if cog:
            global_matches = await get_all_playlist_converter(
                PlaylistScope.GLOBAL.value,
                ctx.bot,
                cog.playlist_api,
                arg,
                guild=ctx.guild,
                author=ctx.author,
            )
            guild_matches = await get_all_playlist_converter(
                PlaylistScope.GUILD.value,
                ctx.bot,
                cog.playlist_api,
                arg,
                guild=ctx.guild,
                author=ctx.author,
            )
            user_matches = await get_all_playlist_converter(
                PlaylistScope.USER.value,
                ctx.bot,
                cog.playlist_api,
                arg,
                guild=ctx.guild,
                author=ctx.author,
            )
        if not user_matches and not guild_matches and not global_matches:
            raise commands.BadArgument(_("Could not match '{}' to a playlist.").format(arg))
        return {
            PlaylistScope.GLOBAL.value: global_matches,
            PlaylistScope.GUILD.value: guild_matches,
            PlaylistScope.USER.value: user_matches,
            "all": [*global_matches, *guild_matches, *user_matches],
            "arg": arg,
        }


class NoExitParser(argparse.ArgumentParser):
    def error(self, message):
        raise commands.BadArgument()


class ScopeParser(commands.Converter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> Tuple[Optional[str], discord.User, Optional[discord.Guild], bool]:
        target_scope: Optional[str] = None
        target_user: Optional[Union[discord.Member, discord.User]] = None
        target_guild: Optional[discord.Guild] = None
        specified_user = False

        argument = argument.replace("—", "--")

        command, *arguments = argument.split(" -- ")
        if arguments:
            argument = " -- ".join(arguments)
        else:
            command = ""

        parser = NoExitParser(description="Playlist Scope Parsing.", add_help=False)
        parser.add_argument("--scope", nargs="*", dest="scope", default=[])
        parser.add_argument("--guild", nargs="*", dest="guild", default=[])
        parser.add_argument("--server", nargs="*", dest="guild", default=[])
        parser.add_argument("--author", nargs="*", dest="author", default=[])
        parser.add_argument("--user", nargs="*", dest="author", default=[])
        parser.add_argument("--member", nargs="*", dest="author", default=[])

        if not command:
            parser.add_argument("command", nargs="*")

        try:
            vals = vars(parser.parse_args(argument.split()))
        except Exception as exc:
            raise commands.BadArgument() from exc

        if vals["scope"]:
            scope_raw = " ".join(vals["scope"]).strip()
            scope = scope_raw.upper().strip()
            valid_scopes = PlaylistScope.list() + [
                "GLOBAL",
                "GUILD",
                "AUTHOR",
                "USER",
                "SERVER",
                "MEMBER",
                "BOT",
            ]
            if scope not in valid_scopes:
                raise commands.ArgParserFailure("--scope", scope_raw, custom_help=_(_SCOPE_HELP))
            target_scope = standardize_scope(scope)
        elif "--scope" in argument and not vals["scope"]:
            raise commands.ArgParserFailure("--scope", _("Nothing"), custom_help=_(_SCOPE_HELP))

        is_owner = await ctx.bot.is_owner(ctx.author)
        guild = vals.get("guild", None) or vals.get("server", None)
        if is_owner and guild:
            server_error = ""
            target_guild = None
            guild_raw = " ".join(guild).strip()
            try:
                target_guild = await global_unique_guild_finder(ctx, guild_raw)
            except TooManyMatches as exc:
                server_error = f"{exc}\n"
            except NoMatchesFound as exc:
                server_error = f"{exc}\n"
            if target_guild is None:
                raise commands.ArgParserFailure(
                    "--guild", guild_raw, custom_help=f"{server_error}{_(_GUILD_HELP)}"
                )

        elif not is_owner and (guild or any(x in argument for x in ["--guild", "--server"])):
            raise commands.BadArgument(_("You cannot use `--guild`"))
        elif any(x in argument for x in ["--guild", "--server"]):
            raise commands.ArgParserFailure("--guild", _("Nothing"), custom_help=_(_GUILD_HELP))

        author = vals.get("author", None) or vals.get("user", None) or vals.get("member", None)
        if author:
            user_error = ""
            target_user = None
            user_raw = " ".join(author).strip()
            try:
                target_user = await global_unique_user_finder(ctx, user_raw, guild=target_guild)
                specified_user = True
            except TooManyMatches as exc:
                user_error = f"{exc}\n"
            except NoMatchesFound as exc:
                user_error = f"{exc}\n"

            if target_user is None:
                raise commands.ArgParserFailure(
                    "--author", user_raw, custom_help=f"{user_error}{_(_USER_HELP)}"
                )
        elif any(x in argument for x in ["--author", "--user", "--member"]):
            raise commands.ArgParserFailure("--scope", _("Nothing"), custom_help=_(_USER_HELP))

        target_scope: Optional[str] = target_scope or None
        target_user: Union[discord.Member, discord.User] = target_user or ctx.author
        target_guild: discord.Guild = target_guild or ctx.guild

        return target_scope, target_user, target_guild, specified_user


class ComplexScopeParser(commands.Converter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> Tuple[
        str,
        discord.User,
        Optional[discord.Guild],
        bool,
        str,
        discord.User,
        Optional[discord.Guild],
        bool,
    ]:
        target_scope: Optional[str] = None
        target_user: Optional[Union[discord.Member, discord.User]] = None
        target_guild: Optional[discord.Guild] = None
        specified_target_user = False

        source_scope: Optional[str] = None
        source_user: Optional[Union[discord.Member, discord.User]] = None
        source_guild: Optional[discord.Guild] = None
        specified_source_user = False

        argument = argument.replace("—", "--")

        command, *arguments = argument.split(" -- ")
        if arguments:
            argument = " -- ".join(arguments)
        else:
            command = ""

        parser = NoExitParser(description="Playlist Scope Parsing.", add_help=False)

        parser.add_argument("--to-scope", nargs="*", dest="to_scope", default=[])
        parser.add_argument("--to-guild", nargs="*", dest="to_guild", default=[])
        parser.add_argument("--to-server", nargs="*", dest="to_server", default=[])
        parser.add_argument("--to-author", nargs="*", dest="to_author", default=[])
        parser.add_argument("--to-user", nargs="*", dest="to_user", default=[])
        parser.add_argument("--to-member", nargs="*", dest="to_member", default=[])

        parser.add_argument("--from-scope", nargs="*", dest="from_scope", default=[])
        parser.add_argument("--from-guild", nargs="*", dest="from_guild", default=[])
        parser.add_argument("--from-server", nargs="*", dest="from_server", default=[])
        parser.add_argument("--from-author", nargs="*", dest="from_author", default=[])
        parser.add_argument("--from-user", nargs="*", dest="from_user", default=[])
        parser.add_argument("--from-member", nargs="*", dest="from_member", default=[])

        if not command:
            parser.add_argument("command", nargs="*")

        try:
            vals = vars(parser.parse_args(argument.split()))
        except Exception as exc:
            raise commands.BadArgument() from exc

        is_owner = await ctx.bot.is_owner(ctx.author)
        valid_scopes = PlaylistScope.list() + [
            "GLOBAL",
            "GUILD",
            "AUTHOR",
            "USER",
            "SERVER",
            "MEMBER",
            "BOT",
        ]

        if vals["to_scope"]:
            to_scope_raw = " ".join(vals["to_scope"]).strip()
            to_scope = to_scope_raw.upper().strip()
            if to_scope not in valid_scopes:
                raise commands.ArgParserFailure(
                    "--to-scope", to_scope_raw, custom_help=_SCOPE_HELP
                )
            target_scope = standardize_scope(to_scope)
        elif "--to-scope" in argument and not vals["to_scope"]:
            raise commands.ArgParserFailure("--to-scope", _("Nothing"), custom_help=_(_SCOPE_HELP))

        if vals["from_scope"]:
            from_scope_raw = " ".join(vals["from_scope"]).strip()
            from_scope = from_scope_raw.upper().strip()

            if from_scope not in valid_scopes:
                raise commands.ArgParserFailure(
                    "--from-scope", from_scope_raw, custom_help=_SCOPE_HELP
                )
            source_scope = standardize_scope(from_scope)
        elif "--from-scope" in argument and not vals["to_scope"]:
            raise commands.ArgParserFailure("--to-scope", _("Nothing"), custom_help=_(_SCOPE_HELP))

        to_guild = vals.get("to_guild", None) or vals.get("to_server", None)
        if is_owner and to_guild:
            target_server_error = ""
            target_guild = None
            to_guild_raw = " ".join(to_guild).strip()
            try:
                target_guild = await global_unique_guild_finder(ctx, to_guild_raw)
            except TooManyMatches as exc:
                target_server_error = f"{exc}\n"
            except NoMatchesFound as exc:
                target_server_error = f"{exc}\n"
            if target_guild is None:
                raise commands.ArgParserFailure(
                    "--to-guild",
                    to_guild_raw,
                    custom_help=f"{target_server_error}{_(_GUILD_HELP)}",
                )
        elif not is_owner and (
            to_guild or any(x in argument for x in ["--to-guild", "--to-server"])
        ):
            raise commands.BadArgument(_("You cannot use `--to-server`"))
        elif any(x in argument for x in ["--to-guild", "--to-server"]):
            raise commands.ArgParserFailure(
                "--to-server", _("Nothing"), custom_help=_(_GUILD_HELP)
            )

        from_guild = vals.get("from_guild", None) or vals.get("from_server", None)
        if is_owner and from_guild:
            source_server_error = ""
            source_guild = None
            from_guild_raw = " ".join(from_guild).strip()
            try:
                source_guild = await global_unique_guild_finder(ctx, from_guild_raw)
            except TooManyMatches as exc:
                source_server_error = f"{exc}\n"
            except NoMatchesFound as exc:
                source_server_error = f"{exc}\n"
            if source_guild is None:
                raise commands.ArgParserFailure(
                    "--from-guild",
                    from_guild_raw,
                    custom_help=f"{source_server_error}{_(_GUILD_HELP)}",
                )
        elif not is_owner and (
            from_guild or any(x in argument for x in ["--from-guild", "--from-server"])
        ):
            raise commands.BadArgument(_("You cannot use `--from-server`"))
        elif any(x in argument for x in ["--from-guild", "--from-server"]):
            raise commands.ArgParserFailure(
                "--from-server", _("Nothing"), custom_help=_(_GUILD_HELP)
            )

        to_author = (
            vals.get("to_author", None) or vals.get("to_user", None) or vals.get("to_member", None)
        )
        if to_author:
            target_user_error = ""
            target_user = None
            to_user_raw = " ".join(to_author).strip()
            try:
                target_user = await global_unique_user_finder(ctx, to_user_raw, guild=target_guild)
                specified_target_user = True
            except TooManyMatches as exc:
                target_user_error = f"{exc}\n"
            except NoMatchesFound as exc:
                target_user_error = f"{exc}\n"
            if target_user is None:
                raise commands.ArgParserFailure(
                    "--to-author", to_user_raw, custom_help=f"{target_user_error}{_(_USER_HELP)}"
                )
        elif any(x in argument for x in ["--to-author", "--to-user", "--to-member"]):
            raise commands.ArgParserFailure("--to-user", _("Nothing"), custom_help=_(_USER_HELP))

        from_author = (
            vals.get("from_author", None)
            or vals.get("from_user", None)
            or vals.get("from_member", None)
        )
        if from_author:
            source_user_error = ""
            source_user = None
            from_user_raw = " ".join(from_author).strip()
            try:
                source_user = await global_unique_user_finder(
                    ctx, from_user_raw, guild=target_guild
                )
                specified_target_user = True
            except TooManyMatches as exc:
                source_user_error = f"{exc}\n"
            except NoMatchesFound as exc:
                source_user_error = f"{exc}\n"
            if source_user is None:
                raise commands.ArgParserFailure(
                    "--from-author",
                    from_user_raw,
                    custom_help=f"{source_user_error}{_(_USER_HELP)}",
                )
        elif any(x in argument for x in ["--from-author", "--from-user", "--from-member"]):
            raise commands.ArgParserFailure("--from-user", _("Nothing"), custom_help=_(_USER_HELP))

        target_scope = target_scope or PlaylistScope.GUILD.value
        target_user = target_user or ctx.author
        target_guild = target_guild or ctx.guild

        source_scope = source_scope or PlaylistScope.GUILD.value
        source_user = source_user or ctx.author
        source_guild = source_guild or ctx.guild

        return (
            source_scope,
            source_user,
            source_guild,
            specified_source_user,
            target_scope,
            target_user,
            target_guild,
            specified_target_user,
        )


class LazyGreedyConverter(commands.Converter):
    def __init__(self, splitter: str):
        self.splitter_Value = splitter

    async def convert(self, ctx: commands.Context, argument: str) -> str:
        full_message = ctx.message.content.partition(f" {argument} ")
        if len(full_message) == 1:
            full_message = (
                (argument if argument not in full_message else "") + " " + full_message[0]
            )
        elif len(full_message) > 1:
            full_message = (
                (argument if argument not in full_message else "") + " " + full_message[-1]
            )
        greedy_output = (" " + full_message.replace("—", "--")).partition(
            f" {self.splitter_Value}"
        )[0]
        return f"{greedy_output}".strip()


def get_lazy_converter(splitter: str) -> type:
    """Returns a typechecking safe `LazyGreedyConverter` suitable for use with discord.py."""

    class PartialMeta(type(LazyGreedyConverter)):
        __call__ = functools.partialmethod(type(LazyGreedyConverter).__call__, splitter)

    class ValidatedConverter(LazyGreedyConverter, metaclass=PartialMeta):
        pass

    return ValidatedConverter


def get_playlist_converter() -> type:
    """Returns a typechecking safe `PlaylistConverter` suitable for use with discord.py."""

    class PartialMeta(type(PlaylistConverter)):
        __call__ = functools.partialmethod(type(PlaylistConverter).__call__)

    class ValidatedConverter(PlaylistConverter, metaclass=PartialMeta):
        pass

    return ValidatedConverter
