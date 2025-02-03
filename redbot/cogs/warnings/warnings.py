import asyncio
import contextlib
from datetime import timezone
from collections import namedtuple
from copy import copy
from typing import Union, Literal

import discord

from redbot.cogs.warnings.helpers import (
    warning_points_add_check,
    get_command_for_exceeded_points,
    get_command_for_dropping_points,
    warning_points_remove_check,
)
from redbot.core import Config, commands, modlog
from redbot.core.bot import Red
from redbot.core.commands import UserInputOptional, RawUserIdConverter
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils import AsyncIter
from redbot.core.utils.views import ConfirmView
from redbot.core.utils.chat_formatting import warning, pagify
from redbot.core.utils.menus import menu


_ = Translator("Warnings", __file__)


@cog_i18n(_)
class Warnings(commands.Cog):
    """Warn misbehaving users and take automated actions."""

    default_guild = {
        "actions": [],
        "reasons": {},
        "allow_custom_reasons": False,
        "toggle_dm": True,
        "show_mod": False,
        "warn_channel": None,
        "toggle_channel": False,
    }

    default_member = {"total_points": 0, "status": "", "warnings": {}}

    def __init__(self, bot: Red):
        super().__init__()
        self.config = Config.get_conf(self, identifier=5757575755)
        self.config.register_guild(**self.default_guild)
        self.config.register_member(**self.default_member)
        self.bot = bot

    async def cog_load(self) -> None:
        await self.register_warningtype()

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        if requester != "discord_deleted_user":
            return

        all_members = await self.config.all_members()

        c = 0

        for guild_id, guild_data in all_members.items():
            c += 1
            if not c % 100:
                await asyncio.sleep(0)

            if user_id in guild_data:
                await self.config.member_from_ids(guild_id, user_id).clear()

            for remaining_user, user_warns in guild_data.items():
                c += 1
                if not c % 100:
                    await asyncio.sleep(0)

                for warn_id, warning in user_warns.get("warnings", {}).items():
                    c += 1
                    if not c % 100:
                        await asyncio.sleep(0)

                    if warning.get("mod", 0) == user_id:
                        grp = self.config.member_from_ids(guild_id, remaining_user)
                        await grp.set_raw("warnings", warn_id, "mod", value=0xDE1)

    # We're not utilising modlog yet - no need to register a casetype
    @staticmethod
    async def register_warningtype():
        casetypes_to_register = [
            {
                "name": "warning",
                "default_setting": True,
                "image": "\N{WARNING SIGN}\N{VARIATION SELECTOR-16}",
                "case_str": "Warning",
            },
            {
                "name": "unwarned",
                "default_setting": True,
                "image": "\N{WARNING SIGN}\N{VARIATION SELECTOR-16}",
                "case_str": "Unwarned",
            },
        ]
        try:
            await modlog.register_casetypes(casetypes_to_register)
        except RuntimeError:
            pass

    @commands.group()
    @commands.guild_only()
    @commands.guildowner_or_permissions(administrator=True)
    async def warningset(self, ctx: commands.Context):
        """Manage settings for Warnings."""
        pass

    @warningset.command()
    @commands.guild_only()
    async def allowcustomreasons(self, ctx: commands.Context, allowed: bool):
        """Enable or disable custom reasons for a warning."""
        guild = ctx.guild
        await self.config.guild(guild).allow_custom_reasons.set(allowed)
        if allowed:
            await ctx.send(_("Custom reasons have been enabled."))
        else:
            await ctx.send(_("Custom reasons have been disabled."))

    @warningset.command()
    @commands.guild_only()
    async def senddm(self, ctx: commands.Context, true_or_false: bool):
        """Set whether warnings should be sent to users in DMs."""
        await self.config.guild(ctx.guild).toggle_dm.set(true_or_false)
        if true_or_false:
            await ctx.send(_("I will now try to send warnings to users DMs."))
        else:
            await ctx.send(_("Warnings will no longer be sent to users DMs."))

    @warningset.command()
    @commands.guild_only()
    async def showmoderator(self, ctx, true_or_false: bool):
        """Decide whether the name of the moderator warning a user should be included in the DM to that user."""
        await self.config.guild(ctx.guild).show_mod.set(true_or_false)
        if true_or_false:
            await ctx.send(
                _(
                    "I will include the name of the moderator who issued the warning when sending a DM to a user."
                )
            )
        else:
            await ctx.send(
                _(
                    "I will not include the name of the moderator who issued the warning when sending a DM to a user."
                )
            )

    @warningset.command()
    @commands.guild_only()
    async def warnchannel(
        self,
        ctx: commands.Context,
        channel: Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel] = None,
    ):
        """Set the channel where warnings should be sent to.

        Leave empty to use the channel `[p]warn` command was called in.
        """
        guild = ctx.guild
        if channel:
            await self.config.guild(guild).warn_channel.set(channel.id)
            await ctx.send(
                _("The warn channel has been set to {channel}.").format(channel=channel.mention)
            )
        else:
            await self.config.guild(guild).warn_channel.set(channel)
            await ctx.send(_("Warnings will now be sent in the channel command was used in."))

    @warningset.command()
    @commands.guild_only()
    async def usewarnchannel(self, ctx: commands.Context, true_or_false: bool):
        """
        Set if warnings should be sent to a channel set with `[p]warningset warnchannel`.
        """
        await self.config.guild(ctx.guild).toggle_channel.set(true_or_false)
        channel = self.bot.get_channel(await self.config.guild(ctx.guild).warn_channel())
        if true_or_false:
            if channel:
                await ctx.send(
                    _("Warnings will now be sent to {channel}.").format(channel=channel.mention)
                )
            else:
                await ctx.send(_("Warnings will now be sent in the channel command was used in."))
        else:
            await ctx.send(_("Toggle channel has been disabled."))

    @commands.group()
    @commands.guild_only()
    @commands.guildowner_or_permissions(administrator=True)
    async def warnaction(self, ctx: commands.Context):
        """Manage automated actions for Warnings.

        Actions are essentially command macros. Any command can be run
        when the action is initially triggered, and/or when the action
        is lifted.
        Actions must be given a name and a points threshold. When a
        user is warned enough so that their points go over this
        threshold, the action will be executed.
        """
        pass

    @warnaction.command(name="add")
    @commands.guild_only()
    async def action_add(self, ctx: commands.Context, name: str, points: int):
        """Create an automated action.

        Duplicate action names are not allowed.
        """
        guild = ctx.guild

        exceed_command = await get_command_for_exceeded_points(ctx)
        drop_command = await get_command_for_dropping_points(ctx)

        to_add = {
            "action_name": name,
            "points": points,
            "exceed_command": exceed_command,
            "drop_command": drop_command,
        }

        # Have all details for the action, now save the action
        guild_settings = self.config.guild(guild)
        async with guild_settings.actions() as registered_actions:
            for act in registered_actions:
                if act["action_name"] == to_add["action_name"]:
                    await ctx.send(_("Duplicate action name found!"))
                    break
            else:
                registered_actions.append(to_add)
                # Sort in descending order by point count for ease in
                # finding the highest possible action to take
                registered_actions.sort(key=lambda a: a["points"], reverse=True)
                await ctx.send(_("Action {name} has been added.").format(name=name))

    @warnaction.command(name="delete", aliases=["del", "remove"])
    @commands.guild_only()
    async def action_del(self, ctx: commands.Context, action_name: str):
        """Delete the action with the specified name."""
        guild = ctx.guild
        guild_settings = self.config.guild(guild)
        async with guild_settings.actions() as registered_actions:
            to_remove = None
            for act in registered_actions:
                if act["action_name"] == action_name:
                    to_remove = act
                    break
            if to_remove:
                registered_actions.remove(to_remove)
                await ctx.tick()
            else:
                await ctx.send(_("No action named {name} exists!").format(name=action_name))

    @commands.group()
    @commands.guild_only()
    @commands.guildowner_or_permissions(administrator=True)
    async def warnreason(self, ctx: commands.Context):
        """Manage warning reasons.

        Reasons must be given a name, description and points value. The
        name of the reason must be given when a user is warned.
        """
        pass

    @warnreason.command(name="create", aliases=["add"])
    @commands.guild_only()
    async def reason_create(
        self, ctx: commands.Context, name: str, points: int, *, description: str
    ):
        """Create a warning reason."""
        guild = ctx.guild

        if name.lower() == "custom":
            await ctx.send(_("*Custom* cannot be used as a reason name!"))
            return
        to_add = {"points": points, "description": description}
        completed = {name.lower(): to_add}

        guild_settings = self.config.guild(guild)

        async with guild_settings.reasons() as registered_reasons:
            registered_reasons.update(completed)

        await ctx.send(_("The new reason has been registered."))

    @warnreason.command(name="delete", aliases=["remove", "del"])
    @commands.guild_only()
    async def reason_del(self, ctx: commands.Context, reason_name: str):
        """Delete a warning reason."""
        guild = ctx.guild
        guild_settings = self.config.guild(guild)
        async with guild_settings.reasons() as registered_reasons:
            if registered_reasons.pop(reason_name.lower(), None):
                await ctx.tick()
            else:
                await ctx.send(_("That is not a registered reason name."))

    @commands.command()
    @commands.guild_only()
    @commands.admin_or_permissions(ban_members=True)
    async def reasonlist(self, ctx: commands.Context):
        """List all configured reasons for Warnings."""
        guild = ctx.guild
        guild_settings = self.config.guild(guild)
        msg_list = []
        async with guild_settings.reasons() as registered_reasons:
            for r, v in registered_reasons.items():
                if await ctx.embed_requested():
                    em = discord.Embed(
                        title=_("Reason: {name}").format(name=r),
                        description=v["description"],
                        color=await ctx.embed_colour(),
                    )
                    em.add_field(name=_("Points"), value=str(v["points"]))
                    msg_list.append(em)
                else:
                    msg_list.append(
                        _(
                            "Name: {reason_name}\nPoints: {points}\nDescription: {description}"
                        ).format(reason_name=r, **v)
                    )
        if msg_list:
            await menu(ctx, msg_list)
        else:
            await ctx.send(_("There are no reasons configured!"))

    @commands.command()
    @commands.guild_only()
    @commands.admin_or_permissions(ban_members=True)
    async def actionlist(self, ctx: commands.Context):
        """List all configured automated actions for Warnings."""
        guild = ctx.guild
        guild_settings = self.config.guild(guild)
        msg_list = []
        async with guild_settings.actions() as registered_actions:
            for r in registered_actions:
                if await ctx.embed_requested():
                    em = discord.Embed(
                        title=_("Action: {name}").format(name=r["action_name"]),
                        color=await ctx.embed_colour(),
                    )
                    em.add_field(name=_("Points"), value="{}".format(r["points"]), inline=False)
                    em.add_field(
                        name=_("Exceed command"),
                        value=r["exceed_command"],
                        inline=False,
                    )
                    em.add_field(name=_("Drop command"), value=r["drop_command"], inline=False)
                    msg_list.append(em)
                else:
                    msg_list.append(
                        _(
                            "Name: {action_name}\nPoints: {points}\n"
                            "Exceed command: {exceed_command}\nDrop command: {drop_command}"
                        ).format(**r)
                    )
        if msg_list:
            await menu(ctx, msg_list)
        else:
            await ctx.send(_("There are no actions configured!"))

    @commands.command()
    @commands.guild_only()
    @commands.admin_or_permissions(ban_members=True)
    async def warn(
        self,
        ctx: commands.Context,
        user: Union[discord.Member, RawUserIdConverter],
        points: UserInputOptional[int] = 1,
        *,
        reason: str,
    ):
        """Warn the user for the specified reason.

        `<points>` number of points the warning should be for. If no number is supplied
        1 point will be given. Pre-set warnings disregard this.
        `<reason>` is reason for the warning. This can be a registered reason,
        or a custom reason if ``[p]warningset allowcustomreasons`` is set.
        """
        guild = ctx.guild
        member = None
        if isinstance(user, discord.Member):
            member = user
        elif isinstance(user, int):
            if not ctx.channel.permissions_for(ctx.guild.me).ban_members:
                await ctx.send(_("User `{user}` is not in the server.").format(user=user))
                return
            user_obj = self.bot.get_user(user) or discord.Object(id=user)

            confirm = ConfirmView(ctx.author, timeout=30)
            confirm.message = await ctx.send(
                _(
                    "User `{user}` is not in the server. Would you like to ban them instead?"
                ).format(user=user),
                view=confirm,
            )
            await confirm.wait()
            if confirm.result:
                try:
                    await ctx.guild.ban(user_obj, reason=reason)
                    await modlog.create_case(
                        self.bot,
                        guild,
                        ctx.message.created_at,
                        "hackban",
                        user,
                        ctx.author,
                        reason,
                        until=None,
                        channel=None,
                    )
                except discord.HTTPException as error:
                    await ctx.send(
                        _("An error occurred while trying to ban the user. Error: {error}").format(
                            error=error
                        )
                    )
            else:
                confirm.message = await ctx.send(_("No action taken."))

            await ctx.tick()
            return

        if member == ctx.author:
            return await ctx.send(_("You cannot warn yourself."))
        if member.bot:
            return await ctx.send(_("You cannot warn other bots."))
        if member == ctx.guild.owner:
            return await ctx.send(_("You cannot warn the server owner."))
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send(
                _(
                    "The person you're trying to warn is equal or higher than you in the discord hierarchy, you cannot warn them."
                )
            )
        guild_settings = await self.config.guild(ctx.guild).all()
        custom_allowed = guild_settings["allow_custom_reasons"]

        reason_type = None
        async with self.config.guild(ctx.guild).reasons() as registered_reasons:
            if (reason_type := registered_reasons.get(reason.lower())) is None:
                msg = _("That is not a registered reason!")
                if custom_allowed:
                    if points < 0:
                        return await ctx.send(_("You cannot apply negative points."))
                    reason_type = {"description": reason, "points": points}
                else:
                    # logic taken from `[p]permissions canrun`
                    fake_message = copy(ctx.message)
                    fake_message.content = f"{ctx.prefix}warningset allowcustomreasons"
                    fake_context = await ctx.bot.get_context(fake_message)
                    try:
                        can = await self.allowcustomreasons.can_run(
                            fake_context, check_all_parents=True, change_permission_state=False
                        )
                    except commands.CommandError:
                        can = False
                    if can:
                        msg += " " + _(
                            "Do `{prefix}warningset allowcustomreasons true` to enable custom "
                            "reasons."
                        ).format(prefix=ctx.clean_prefix)
                    return await ctx.send(msg)
        if reason_type is None:
            return
        member_settings = self.config.member(member)
        current_point_count = await member_settings.total_points()
        warning_to_add = {
            str(ctx.message.id): {
                "points": reason_type["points"],
                "description": reason_type["description"],
                "mod": ctx.author.id,
            }
        }
        dm = guild_settings["toggle_dm"]
        showmod = guild_settings["show_mod"]
        dm_failed = False
        if dm:
            if showmod:
                title = _("Warning from {user}").format(user=ctx.author)
            else:
                title = _("Warning")
            em = discord.Embed(
                title=title, description=reason_type["description"], color=await ctx.embed_colour()
            )
            em.add_field(name=_("Points"), value=str(reason_type["points"]))
            try:
                await member.send(
                    _("You have received a warning in {guild_name}.").format(
                        guild_name=ctx.guild.name
                    ),
                    embed=em,
                )
            except discord.HTTPException:
                dm_failed = True

        if dm_failed:
            await ctx.send(
                _(
                    "A warning for {user} has been issued,"
                    " but I wasn't able to send them a warn message."
                ).format(user=member.mention)
            )
        async with member_settings.warnings() as user_warnings:
            user_warnings.update(warning_to_add)
        current_point_count += reason_type["points"]
        await member_settings.total_points.set(current_point_count)
        await warning_points_add_check(self.config, ctx, member, current_point_count)

        toggle_channel = guild_settings["toggle_channel"]
        if toggle_channel:
            if showmod:
                title = _("Warning from {user}").format(user=ctx.author)
            else:
                title = _("Warning")
            em = discord.Embed(
                title=title, description=reason_type["description"], color=await ctx.embed_colour()
            )
            em.add_field(name=_("Points"), value=str(reason_type["points"]))
            warn_channel = self.bot.get_channel(guild_settings["warn_channel"])
            if warn_channel:
                if warn_channel.permissions_for(guild.me).send_messages:
                    with contextlib.suppress(discord.HTTPException):
                        await warn_channel.send(
                            _("{user} has been warned.").format(user=member.mention),
                            embed=em,
                        )

            if not dm_failed:
                if warn_channel:
                    await ctx.tick()
                else:
                    await ctx.send(
                        _("{user} has been warned.").format(user=member.mention), embed=em
                    )
        else:
            if not dm_failed:
                await ctx.tick()
        reason_msg = _(
            "{reason}\n\nUse `{prefix}unwarn {user} {message}` to remove this warning."
        ).format(
            reason=_("{description}\nPoints: {points}").format(
                description=reason_type["description"], points=reason_type["points"]
            ),
            prefix=ctx.clean_prefix,
            user=member.id,
            message=ctx.message.id,
        )
        await modlog.create_case(
            self.bot,
            ctx.guild,
            ctx.message.created_at,
            "warning",
            member,
            ctx.message.author,
            reason_msg,
            until=None,
            channel=None,
        )

    @commands.command()
    @commands.guild_only()
    @commands.admin()
    async def warnings(self, ctx: commands.Context, member: Union[discord.Member, int]):
        """List the warnings for the specified user."""

        try:
            userid: int = member.id
        except AttributeError:
            userid: int = member
            member = ctx.guild.get_member(userid)
            member = member or namedtuple("Member", "id guild")(userid, ctx.guild)

        msg = ""
        member_settings = self.config.member(member)
        async with member_settings.warnings() as user_warnings:
            if not user_warnings.keys():  # no warnings for the user
                await ctx.send(_("That user has no warnings!"))
            else:
                for key in user_warnings.keys():
                    mod_id = user_warnings[key]["mod"]
                    if mod_id == 0xDE1:
                        mod = _("Deleted Moderator")
                    else:
                        bot = ctx.bot
                        mod = bot.get_user(mod_id) or _("Unknown Moderator ({})").format(mod_id)
                    msg += _(
                        "{num_points} point warning {reason_name} issued by {user} for "
                        "{description}\n"
                    ).format(
                        num_points=user_warnings[key]["points"],
                        reason_name=key,
                        user=mod,
                        description=user_warnings[key]["description"],
                    )
                await ctx.send_interactive(
                    pagify(msg, shorten_by=58),
                    box_lang=_("Warnings for {user}").format(
                        user=member if isinstance(member, discord.Member) else member.id
                    ),
                )

    @commands.command()
    @commands.guild_only()
    async def mywarnings(self, ctx: commands.Context):
        """List warnings for yourself."""

        user = ctx.author

        msg = ""
        member_settings = self.config.member(user)
        async with member_settings.warnings() as user_warnings:
            if not user_warnings.keys():  # no warnings for the user
                await ctx.send(_("You have no warnings!"))
            else:
                for key in user_warnings.keys():
                    mod_id = user_warnings[key]["mod"]
                    if mod_id == 0xDE1:
                        mod = _("Deleted Moderator")
                    else:
                        bot = ctx.bot
                        mod = bot.get_user(mod_id) or _("Unknown Moderator ({})").format(mod_id)
                    msg += _(
                        "{num_points} point warning {reason_name} issued by {user} for "
                        "{description}\n"
                    ).format(
                        num_points=user_warnings[key]["points"],
                        reason_name=key,
                        user=mod,
                        description=user_warnings[key]["description"],
                    )
                await ctx.send_interactive(
                    pagify(msg, shorten_by=58),
                    box_lang=_("Warnings for {user}").format(user=user),
                )

    @commands.command()
    @commands.guild_only()
    @commands.admin_or_permissions(ban_members=True)
    async def unwarn(
        self,
        ctx: commands.Context,
        member: Union[discord.Member, int],
        warn_id: str,
        *,
        reason: str = None,
    ):
        """Remove a warning from a user."""

        guild = ctx.guild

        try:
            user_id = member.id
            member = member
        except AttributeError:
            user_id = member
            member = guild.get_member(user_id)
            member = member or namedtuple("Member", "guild id")(guild, user_id)

        if user_id == ctx.author.id:
            return await ctx.send(_("You cannot remove warnings from yourself."))

        member_settings = self.config.member(member)
        current_point_count = await member_settings.total_points()
        await warning_points_remove_check(self.config, ctx, member, current_point_count)
        async with member_settings.warnings() as user_warnings:
            if warn_id not in user_warnings.keys():
                return await ctx.send(_("That warning doesn't exist!"))
            else:
                current_point_count -= user_warnings[warn_id]["points"]
                await member_settings.total_points.set(current_point_count)
                user_warnings.pop(warn_id)
        await modlog.create_case(
            self.bot,
            ctx.guild,
            ctx.message.created_at,
            "unwarned",
            member,
            ctx.message.author,
            reason,
            until=None,
            channel=None,
        )

        await ctx.tick()
