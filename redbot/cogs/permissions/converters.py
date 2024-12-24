import itertools
import re
from typing import NamedTuple, Union, Optional

import discord

from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter

_ = Translator("PermissionsConverters", __file__)

MENTION_RE = re.compile(r"^<?(?:(?:@[!&]?)?|#)(\d{15,20})>?$")


def _match_id(arg: str) -> Optional[int]:
    m = MENTION_RE.match(arg)
    if m:
        return int(m.group(1))


class GlobalUniqueObjectFinder(commands.Converter):
    async def convert(
        self, ctx: commands.Context, arg: str
    ) -> Union[discord.Guild, discord.abc.GuildChannel, discord.abc.User, discord.Role]:
        bot: commands.Bot = ctx.bot
        _id = _match_id(arg)

        if _id is not None:
            guild: discord.Guild = bot.get_guild(_id)
            if guild is not None:
                return guild
            channel: discord.abc.GuildChannel = bot.get_channel(_id)
            if channel is not None and not isinstance(channel, discord.Thread):
                return channel

            user: discord.User = bot.get_user(_id)
            if user is not None:
                return user

            async for guild in AsyncIter(bot.guilds, steps=100):
                role: discord.Role = guild.get_role(_id)
                if role is not None:
                    return role

        all_roles = [
            filter(lambda r: not r.is_default(), guild.roles)
            async for guild in AsyncIter(bot.guilds, steps=100)
        ]

        objects = itertools.chain(bot.get_all_channels(), bot.users, bot.guilds, *all_roles)

        maybe_matches = []
        async for obj in AsyncIter(objects, steps=100):
            if obj.name == arg or str(obj) == arg:
                maybe_matches.append(obj)

        if ctx.guild is not None:
            async for member in AsyncIter(ctx.guild.members, steps=100):
                if member.nick == arg and not any(obj.id == member.id for obj in maybe_matches):
                    maybe_matches.append(member)

        if not maybe_matches:
            raise commands.BadArgument(
                _(
                    '"{arg}" was not found. It must be the ID, mention, or name of a server, '
                    "channel, user or role which the bot can see."
                ).format(arg=arg)
            )
        elif len(maybe_matches) == 1:
            return maybe_matches[0]
        else:
            raise commands.BadArgument(
                _(
                    '"{arg}" does not refer to a unique server, channel, user or role. Please use '
                    "the ID for whatever/whoever you're trying to specify, or mention it/them."
                ).format(arg=arg)
            )


class GuildUniqueObjectFinder(commands.Converter):
    async def convert(
        self, ctx: commands.Context, arg: str
    ) -> Union[discord.abc.GuildChannel, discord.Member, discord.Role]:
        guild: discord.Guild = ctx.guild
        _id = _match_id(arg)

        if _id is not None:
            channel: discord.abc.GuildChannel = guild.get_channel(_id)
            if channel is not None:
                return channel

            member: discord.Member = guild.get_member(_id)
            if member is not None:
                return member

            role: discord.Role = guild.get_role(_id)
            if role is not None and not role.is_default():
                return role

        objects = itertools.chain(
            guild.channels, guild.members, filter(lambda r: not r.is_default(), guild.roles)
        )

        maybe_matches = []
        async for obj in AsyncIter(objects, steps=100):
            if obj.name == arg or str(obj) == arg:
                maybe_matches.append(obj)
            try:
                if obj.nick == arg:
                    maybe_matches.append(obj)
            except AttributeError:
                pass

        if not maybe_matches:
            raise commands.BadArgument(
                _(
                    '"{arg}" was not found. It must be the ID, mention, or name of a channel, '
                    "user or role in this server."
                ).format(arg=arg)
            )
        elif len(maybe_matches) == 1:
            return maybe_matches[0]
        else:
            raise commands.BadArgument(
                _(
                    '"{arg}" does not refer to a unique channel, user or role. Please use the ID '
                    "for whatever/whoever you're trying to specify, or mention it/them."
                ).format(arg=arg)
            )


class CogOrCommand(NamedTuple):
    type: str
    name: str
    obj: Union[commands.Command, commands.Cog]

    # noinspection PyArgumentList
    @classmethod
    async def convert(cls, ctx: commands.Context, arg: str) -> "CogOrCommand":
        ret = None
        if cog := ctx.bot.get_cog(arg):
            ret = cls(type="COG", name=cog.qualified_name, obj=cog)

        elif cmd := ctx.bot.get_command(arg):
            ret = cls(type="COMMAND", name=cmd.qualified_name, obj=cmd)

        if ret:
            if isinstance(ret.obj, commands.commands._RuleDropper):
                raise commands.BadArgument(
                    "You cannot apply permission rules to this cog or command."
                )
            return ret

        raise commands.BadArgument(
            _(
                'Cog or command "{name}" not found. Please note that this is case sensitive.'
            ).format(name=arg)
        )


def RuleType(arg: str) -> bool:
    if arg.lower() in ("allow", "whitelist", "allowed"):
        return True
    if arg.lower() in ("deny", "blacklist", "denied"):
        return False

    raise commands.BadArgument(
        _('"{arg}" is not a valid rule. Valid rules are "allow" or "deny"').format(arg=arg)
    )


def ClearableRuleType(arg: str) -> Optional[bool]:
    if arg.lower() in ("allow", "whitelist", "allowed"):
        return True
    if arg.lower() in ("deny", "blacklist", "denied"):
        return False
    if arg.lower() in ("clear", "reset"):
        return None

    raise commands.BadArgument(
        _(
            '"{arg}" is not a valid rule. Valid rules are "allow" or "deny", or "clear" to '
            "remove the rule"
        ).format(arg=arg)
    )
