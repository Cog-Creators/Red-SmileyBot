from datetime import datetime, timezone

from typing import Optional, Union

import discord

from redbot.core import commands, modlog
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import bold, box, pagify
from redbot.core.utils.menus import menu
from redbot.core.utils.predicates import MessagePredicate

_ = Translator("ModLog", __file__)


@cog_i18n(_)
class ModLog(commands.Cog):
    """Browse and manage modlog cases. To manage modlog settings, use `[p]modlogset`."""

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    @commands.command()
    @commands.guild_only()
    async def case(self, ctx: commands.Context, number: int):
        """Show the specified case."""
        try:
            case = await modlog.get_case(number, ctx.guild, self.bot)
        except RuntimeError:
            await ctx.send(_("That case does not exist for this server."))
            return
        else:
            if await ctx.embed_requested():
                await ctx.send(embed=await case.message_content(embed=True))
            else:
                created_at = datetime.fromtimestamp(case.created_at, tz=timezone.utc)
                message = (
                    f"{await case.message_content(embed=False)}\n"
                    f"{bold(_('Timestamp:'))} {discord.utils.format_dt(created_at)}"
                )
                await ctx.send(message)

    @commands.command()
    @commands.guild_only()
    async def casesfor(self, ctx: commands.Context, *, member: Union[discord.Member, int]):
        """Display cases for the specified member."""
        async with ctx.typing():
            try:
                if isinstance(member, int):
                    cases = await modlog.get_cases_for_member(
                        bot=ctx.bot, guild=ctx.guild, member_id=member
                    )
                else:
                    cases = await modlog.get_cases_for_member(
                        bot=ctx.bot, guild=ctx.guild, member=member
                    )
            except discord.NotFound:
                return await ctx.send(_("That user does not exist."))
            except discord.HTTPException:
                return await ctx.send(
                    _("Something unexpected went wrong while fetching that user by ID.")
                )

            if not cases:
                return await ctx.send(_("That user does not have any cases."))

            embed_requested = await ctx.embed_requested()
            if embed_requested:
                rendered_cases = [await case.message_content(embed=True) for case in cases]
            else:
                rendered_cases = []
                for case in cases:
                    created_at = datetime.fromtimestamp(case.created_at, tz=timezone.utc)
                    message = (
                        f"{await case.message_content(embed=False)}\n"
                        f"{bold(_('Timestamp:'))} {discord.utils.format_dt(created_at)}"
                    )
                    rendered_cases.append(message)

        await menu(ctx, rendered_cases)

    @commands.command()
    @commands.guild_only()
    async def listcases(self, ctx: commands.Context, *, member: Union[discord.Member, int]):
        """List cases for the specified member."""
        async with ctx.typing():
            try:
                if isinstance(member, int):
                    cases = await modlog.get_cases_for_member(
                        bot=ctx.bot, guild=ctx.guild, member_id=member
                    )
                else:
                    cases = await modlog.get_cases_for_member(
                        bot=ctx.bot, guild=ctx.guild, member=member
                    )
            except discord.NotFound:
                return await ctx.send(_("That user does not exist."))
            except discord.HTTPException:
                return await ctx.send(
                    _("Something unexpected went wrong while fetching that user by ID.")
                )
            if not cases:
                return await ctx.send(_("That user does not have any cases."))

            rendered_cases = []
            message = ""
            for case in cases:
                created_at = datetime.fromtimestamp(case.created_at, tz=timezone.utc)
                message += (
                    f"{await case.message_content(embed=False)}\n"
                    f"{bold(_('Timestamp:'))} {discord.utils.format_dt(created_at)}\n\n"
                )
            for page in pagify(message, ["\n\n", "\n"], priority=True):
                rendered_cases.append(page)
        await menu(ctx, rendered_cases)

    @commands.command()
    @commands.guild_only()
    async def reason(self, ctx: commands.Context, case: Optional[int], *, reason: str):
        """Specify a reason for a modlog case.

        Please note that you can only edit cases you are
        the owner of unless you are a mod, admin or server owner.

        If no case number is specified, the latest case will be used.
        """
        author = ctx.author
        guild = ctx.guild
        if case is None:
            # get the latest case
            case_obj = await modlog.get_latest_case(guild, self.bot)
            if case_obj is None:
                await ctx.send(_("There are no modlog cases in this server."))
                return
        else:
            try:
                case_obj = await modlog.get_case(case, guild, self.bot)
            except RuntimeError:
                await ctx.send(_("That case does not exist!"))
                return

        is_guild_owner = author == guild.owner
        is_case_author = author == case_obj.moderator
        author_is_mod = await ctx.bot.is_mod(author)
        if not (is_guild_owner or is_case_author or author_is_mod):
            await ctx.send(_("You are not authorized to modify that case!"))
            return
        to_modify = {"reason": reason}
        if case_obj.moderator != author:
            to_modify["amended_by"] = author
        to_modify["modified_at"] = ctx.message.created_at.timestamp()
        await case_obj.edit(to_modify)
        await ctx.send(
            _("Reason for case #{num} has been updated.").format(num=case_obj.case_number)
        )
