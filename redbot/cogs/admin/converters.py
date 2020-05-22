import discord
from redbot.core import commands
from redbot.core.i18n import Translator

_ = Translator("AdminConverters", __file__)


class SelfRole(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> discord.Role:
        admin = ctx.command.cog.bot.get_cog("Admin")
        if admin is None:
            raise commands.BadArgument(_("The Admin cog is not loaded."))

        selfroles = await admin.config.guild(ctx.guild).selfroles()
        role_converter = commands.RoleConverter()

        pool = []
        for role_id in selfroles:
            role = ctx.guild.get_role(role_id)
            if role is None:
                continue
            if role.name.lower() == arg.lower():
                pool.append(role)

        if len(pool) == 0:
            role = await role_converter.convert(ctx, arg)
            if role.id not in selfroles:
                raise commands.BadArgument(_("The provided role is not a valid selfrole."))
        elif len(pool) > 1:
            raise commands.BadArgument(
                _(
                    "This selfrole has more than one capitalization"
                    " possibilities.  Please inform a moderator."
                )
            )
        else:
            role = pool[0]

        return role
