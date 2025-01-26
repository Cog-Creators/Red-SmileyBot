import asyncio
import logging
from typing import Tuple, Union

import discord
from redbot.core import Config, commands
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import box
from redbot.core.utils.mod import get_audit_reason
from redbot.core.utils.predicates import MessagePredicate

from .announcer import Announcer
from .converters import SelfRole

log = logging.getLogger("red.admin")

T_ = Translator("Admin", __file__)

_ = lambda s: s
GENERIC_FORBIDDEN = _(
    "I attempted to do something that Discord denied me permissions for."
    " Your command failed to successfully complete."
)

HIERARCHY_ISSUE_ADD = _(
    "I can not give {role.name} to {member.display_name}"
    " because that role is higher than or equal to my highest role"
    " in the Discord hierarchy."
)

HIERARCHY_ISSUE_REMOVE = _(
    "I can not remove {role.name} from {member.display_name}"
    " because that role is higher than or equal to my highest role"
    " in the Discord hierarchy."
)

ROLE_HIERARCHY_ISSUE = _(
    "I can not edit {role.name}"
    " because that role is higher than my or equal to highest role"
    " in the Discord hierarchy."
)

USER_HIERARCHY_ISSUE_ADD = _(
    "I can not let you give {role.name} to {member.display_name}"
    " because that role is higher than or equal to your highest role"
    " in the Discord hierarchy."
)

USER_HIERARCHY_ISSUE_REMOVE = _(
    "I can not let you remove {role.name} from {member.display_name}"
    " because that role is higher than or equal to your highest role"
    " in the Discord hierarchy."
)

ROLE_USER_HIERARCHY_ISSUE = _(
    "I can not let you edit {role.name}"
    " because that role is higher than or equal to your highest role"
    " in the Discord hierarchy."
)

NEED_MANAGE_ROLES = _('I need the "Manage Roles" permission to do that.')

RUNNING_ANNOUNCEMENT = _(
    "I am already announcing something. If you would like to make a"
    " different announcement please use `{prefix}announce cancel`"
    " first."
)
_ = T_


@cog_i18n(_)
class Admin(commands.Cog):
    """A collection of server administration utilities."""

    def __init__(self, bot):
        self.bot = bot

        self.config = Config.get_conf(self, 8237492837454039, force_registration=True)

        self.config.register_global(serverlocked=False, schema_version=0)

        self.config.register_guild(
            announce_channel=None,  # Integer ID
            selfroles=[],  # List of integer ID's
        )

        self.__current_announcer = None

    async def cog_load(self) -> None:
        await self.handle_migrations()

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    async def handle_migrations(self):
        lock = self.config.get_guilds_lock()
        async with lock:
            # This prevents the edge case of someone loading admin,
            # unloading it, loading it again during a migration
            current_schema = await self.config.schema_version()

            if current_schema == 0:
                await self.migrate_config_from_0_to_1()
                await self.config.schema_version.set(1)

    async def migrate_config_from_0_to_1(self) -> None:
        all_guilds = await self.config.all_guilds()

        for guild_id, guild_data in all_guilds.items():
            if guild_data.get("announce_ignore", False):
                async with self.config.guild_from_id(guild_id).all(
                    acquire_lock=False
                ) as guild_config:
                    guild_config.pop("announce_channel", None)
                    guild_config.pop("announce_ignore", None)

    def cog_unload(self):
        try:
            self.__current_announcer.cancel()
        except AttributeError:
            pass

    def is_announcing(self) -> bool:
        """
        Is the bot currently announcing something?
        :return:
        """
        if self.__current_announcer is None:
            return False

        return self.__current_announcer.active or False

    @staticmethod
    def pass_hierarchy_check(ctx: commands.Context, role: discord.Role) -> bool:
        """
        Determines if the bot has a higher role than the given one.
        :param ctx:
        :param role: Role object.
        :return:
        """
        return ctx.guild.me.top_role > role

    @staticmethod
    def pass_user_hierarchy_check(ctx: commands.Context, role: discord.Role) -> bool:
        """
        Determines if a user is allowed to add/remove/edit the given role.
        :param ctx:
        :param role:
        :return:
        """
        return ctx.author.top_role > role or ctx.author == ctx.guild.owner

    async def _addrole(
        self, ctx: commands.Context, member: discord.Member, role: discord.Role, *, check_user=True
    ):
        if member.get_role(role.id) is not None:
            await ctx.send(
                _("{member.display_name} already has the role {role.name}.").format(
                    role=role, member=member
                )
            )
            return
        if check_user and not self.pass_user_hierarchy_check(ctx, role):
            await ctx.send(_(USER_HIERARCHY_ISSUE_ADD).format(role=role, member=member))
            return
        if not self.pass_hierarchy_check(ctx, role):
            await ctx.send(_(HIERARCHY_ISSUE_ADD).format(role=role, member=member))
            return
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send(_(NEED_MANAGE_ROLES))
            return
        try:
            reason = get_audit_reason(ctx.author)
            await member.add_roles(role, reason=reason)
        except discord.Forbidden:
            await ctx.send(_(GENERIC_FORBIDDEN))
        else:
            await ctx.send(
                _("I successfully added {role.name} to {member.display_name}").format(
                    role=role, member=member
                )
            )

    async def _removerole(
        self, ctx: commands.Context, member: discord.Member, role: discord.Role, *, check_user=True
    ):
        if member.get_role(role.id) is None:
            await ctx.send(
                _("{member.display_name} does not have the role {role.name}.").format(
                    role=role, member=member
                )
            )
            return
        if check_user and not self.pass_user_hierarchy_check(ctx, role):
            await ctx.send(_(USER_HIERARCHY_ISSUE_REMOVE).format(role=role, member=member))
            return
        if not self.pass_hierarchy_check(ctx, role):
            await ctx.send(_(HIERARCHY_ISSUE_REMOVE).format(role=role, member=member))
            return
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send(_(NEED_MANAGE_ROLES))
            return
        try:
            reason = get_audit_reason(ctx.author)
            await member.remove_roles(role, reason=reason)
        except discord.Forbidden:
            await ctx.send(_(GENERIC_FORBIDDEN))
        else:
            await ctx.send(
                _("I successfully removed {role.name} from {member.display_name}").format(
                    role=role, member=member
                )
            )

    @commands.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_roles=True)
    async def addrole(
        self,
        ctx: commands.Context,
        rolename: discord.Role,
        *,
        user: discord.Member = commands.Author,
    ):
        """
        Add a role to a user.

        Use double quotes if the role contains spaces.
        If user is left blank it defaults to the author of the command.
        """
        await self._addrole(ctx, user, rolename)

    @commands.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_roles=True)
    async def removerole(
        self,
        ctx: commands.Context,
        rolename: discord.Role,
        *,
        user: discord.Member = commands.Author,
    ):
        """
        Remove a role from a user.

        Use double quotes if the role contains spaces.
        If user is left blank it defaults to the author of the command.
        """
        await self._removerole(ctx, user, rolename)

    @commands.group()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_roles=True)
    async def editrole(self, ctx: commands.Context):
        """Edit role settings."""
        pass

    @editrole.command(name="colour", aliases=["color"])
    async def editrole_colour(
        self, ctx: commands.Context, role: discord.Role, value: discord.Colour
    ):
        """
        Edit a role's colour.

        Use double quotes if the role contains spaces.
        Colour must be in hexadecimal format.
        [Online colour picker](http://www.w3schools.com/colors/colors_picker.asp)

        Examples:
            `[p]editrole colour "The Transistor" #ff0000`
            `[p]editrole colour Test #ff9900`
        """
        author = ctx.author
        reason = _("{author} ({author.id}) changed the colour of role '{role.name}'").format(
            author=author, role=role
        )

        if not self.pass_user_hierarchy_check(ctx, role):
            await ctx.send(_(ROLE_USER_HIERARCHY_ISSUE).format(role=role))
            return
        if not self.pass_hierarchy_check(ctx, role):
            await ctx.send(_(ROLE_HIERARCHY_ISSUE).format(role=role))
            return
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send(_(NEED_MANAGE_ROLES))
            return
        try:
            await role.edit(reason=reason, color=value)
        except discord.Forbidden:
            await ctx.send(_(GENERIC_FORBIDDEN))
        else:
            log.info(reason)
            await ctx.send(_("Done."))

    @editrole.command(name="name")
    async def edit_role_name(self, ctx: commands.Context, role: discord.Role, name: str):
        """
        Edit a role's name.

        Use double quotes if the role or the name contain spaces.

        Example:
            `[p]editrole name \"The Transistor\" Test`
        """
        author = ctx.message.author
        old_name = role.name
        reason = _(
            "{author} ({author.id}) changed the name of role '{old_name}' to '{name}'"
        ).format(author=author, old_name=old_name, name=name)

        if not self.pass_user_hierarchy_check(ctx, role):
            await ctx.send(_(ROLE_USER_HIERARCHY_ISSUE).format(role=role))
            return
        if not self.pass_hierarchy_check(ctx, role):
            await ctx.send(_(ROLE_HIERARCHY_ISSUE).format(role=role))
            return
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send(_(NEED_MANAGE_ROLES))
            return
        try:
            await role.edit(reason=reason, name=name)
        except discord.Forbidden:
            await ctx.send(_(GENERIC_FORBIDDEN))
        else:
            log.info(reason)
            await ctx.send(_("Done."))

    @commands.group(invoke_without_command=True)
    @commands.is_owner()
    async def announce(self, ctx: commands.Context, *, message: str):
        """Announce a message to all servers the bot is in."""
        if not self.is_announcing():
            announcer = Announcer(ctx, message, config=self.config)
            announcer.start()

            self.__current_announcer = announcer

            await ctx.send(_("The announcement has begun."))
        else:
            prefix = ctx.clean_prefix
            await ctx.send(_(RUNNING_ANNOUNCEMENT).format(prefix=prefix))

    @announce.command(name="cancel")
    async def announce_cancel(self, ctx):
        """Cancel a running announce."""
        if not self.is_announcing():
            await ctx.send(_("There is no currently running announcement."))
            return
        self.__current_announcer.cancel()
        await ctx.send(_("The current announcement has been cancelled."))

    @commands.group()
    @commands.guild_only()
    @commands.guildowner_or_permissions(administrator=True)
    async def announceset(self, ctx):
        """Change how announcements are sent in this guild."""
        pass

    @announceset.command(name="channel")
    async def announceset_channel(
        self,
        ctx,
        *,
        channel: Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel],
    ):
        """Change the channel where the bot will send announcements."""
        await self.config.guild(ctx.guild).announce_channel.set(channel.id)
        await ctx.send(
            _("The announcement channel has been set to {channel.mention}").format(channel=channel)
        )

    @announceset.command(name="clearchannel")
    async def announceset_clear_channel(self, ctx):
        """Unsets the channel for announcements."""
        await self.config.guild(ctx.guild).announce_channel.clear()
        await ctx.tick()

    async def _valid_selfroles(self, guild: discord.Guild) -> Tuple[discord.Role]:
        """
        Returns a tuple of valid selfroles
        :param guild:
        :return:
        """
        selfrole_ids = set(await self.config.guild(guild).selfroles())
        guild_roles = guild.roles

        valid_roles = tuple(r for r in guild_roles if r.id in selfrole_ids)
        valid_role_ids = set(r.id for r in valid_roles)

        if selfrole_ids != valid_role_ids:
            await self.config.guild(guild).selfroles.set(list(valid_role_ids))

        # noinspection PyTypeChecker
        return valid_roles

    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    async def selfrole(self, ctx: commands.Context, *, selfrole: SelfRole):
        """
        Add or remove a selfrole from yourself.

        Server admins must have configured the role as user settable.
        NOTE: The role is case sensitive!
        """
        if ctx.author.get_role(selfrole.id) is not None:
            return await self._removerole(ctx, ctx.author, selfrole, check_user=False)
        else:
            return await self._addrole(ctx, ctx.author, selfrole, check_user=False)

    @selfrole.command(name="add", hidden=True)
    async def selfrole_add(self, ctx: commands.Context, *, selfrole: SelfRole):
        """
        Add a selfrole to yourself.

        Server admins must have configured the role as user settable.
        NOTE: The role is case sensitive!
        """
        # noinspection PyTypeChecker
        await self._addrole(ctx, ctx.author, selfrole, check_user=False)

    @selfrole.command(name="remove", hidden=True)
    async def selfrole_remove(self, ctx: commands.Context, *, selfrole: SelfRole):
        """
        Remove a selfrole from yourself.

        Server admins must have configured the role as user settable.
        NOTE: The role is case sensitive!
        """
        # noinspection PyTypeChecker
        await self._removerole(ctx, ctx.author, selfrole, check_user=False)

    @selfrole.command(name="list")
    async def selfrole_list(self, ctx: commands.Context):
        """
        Lists all available selfroles.
        """
        selfroles = await self._valid_selfroles(ctx.guild)
        fmt_selfroles = "\n".join(["+ " + r.name for r in selfroles])

        if not fmt_selfroles:
            await ctx.send("There are currently no selfroles.")
            return

        msg = _("Available Selfroles:\n{selfroles}").format(selfroles=fmt_selfroles)
        await ctx.send(box(msg, "diff"))

    @commands.group()
    @commands.admin_or_permissions(manage_roles=True)
    async def selfroleset(self, ctx: commands.Context):
        """Manage selfroles."""
        pass

    @selfroleset.command(name="add", require_var_positional=True)
    async def selfroleset_add(self, ctx: commands.Context, *roles: discord.Role):
        """
        Add a role, or a selection of roles, to the list of available selfroles.

        NOTE: The role is case sensitive!
        """
        current_selfroles = await self.config.guild(ctx.guild).selfroles()
        for role in roles:
            if not self.pass_user_hierarchy_check(ctx, role):
                await ctx.send(
                    _(
                        "I cannot let you add {role.name} as a selfrole because that role is"
                        " higher than or equal to your highest role in the Discord hierarchy."
                    ).format(role=role)
                )
                return
            if role.id not in current_selfroles:
                current_selfroles.append(role.id)
            else:
                await ctx.send(
                    _('The role "{role.name}" is already a selfrole.').format(role=role)
                )
                return

        await self.config.guild(ctx.guild).selfroles.set(current_selfroles)
        if (count := len(roles)) > 1:
            message = _("Added {count} selfroles.").format(count=count)
        else:
            message = _("Added 1 selfrole.")

        await ctx.send(message)

    @selfroleset.command(name="remove", require_var_positional=True)
    async def selfroleset_remove(self, ctx: commands.Context, *roles: SelfRole):
        """
        Remove a role, or a selection of roles, from the list of available selfroles.

        NOTE: The role is case sensitive!
        """
        current_selfroles = await self.config.guild(ctx.guild).selfroles()
        for role in roles:
            if not self.pass_user_hierarchy_check(ctx, role):
                await ctx.send(
                    _(
                        "I cannot let you remove {role.name} from being a selfrole because that role is higher than or equal to your highest role in the Discord hierarchy."
                    ).format(role=role)
                )
                return
            current_selfroles.remove(role.id)

        await self.config.guild(ctx.guild).selfroles.set(current_selfroles)

        if (count := len(roles)) > 1:
            message = _("Removed {count} selfroles.").format(count=count)
        else:
            message = _("Removed 1 selfrole.")

        await ctx.send(message)

    @selfroleset.command(name="clear")
    async def selfroleset_clear(self, ctx: commands.Context):
        """Clear the list of available selfroles for this server."""
        current_selfroles = await self.config.guild(ctx.guild).selfroles()

        if not current_selfroles:
            return await ctx.send(_("There are currently no selfroles."))

        await ctx.send(
            _("Are you sure you want to clear this server's selfrole list?") + " (yes/no)"
        )
        try:
            pred = MessagePredicate.yes_or_no(ctx, user=ctx.author)
            await ctx.bot.wait_for("message", check=pred, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send(_("You took too long to respond."))
            return
        if pred.result:
            for role in current_selfroles:
                role = ctx.guild.get_role(role)
                if role is None:
                    continue
                if not self.pass_user_hierarchy_check(ctx, role):
                    await ctx.send(
                        _(
                            "I cannot clear the selfroles because the selfrole '{role.name}' is higher than or equal to your highest role in the Discord hierarchy."
                        ).format(role=role)
                    )
                    return
            await self.config.guild(ctx.guild).selfroles.clear()
            await ctx.send(_("Selfrole list cleared."))
        else:
            await ctx.send(_("No changes have been made."))

    @commands.command()
    @commands.is_owner()
    async def serverlock(self, ctx: commands.Context):
        """Lock a bot to its current servers only."""
        serverlocked = await self.config.serverlocked()
        await self.config.serverlocked.set(not serverlocked)

        if serverlocked:
            await ctx.send(_("The bot is no longer serverlocked."))
        else:
            await ctx.send(_("The bot is now serverlocked."))

    # region Event Handlers
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        if await self.config.serverlocked():
            if len(self.bot.guilds) == 1:  # will be 0 once left
                log.warning(
                    f"Leaving guild '{guild.name}' ({guild.id}) due to serverlock. You can "
                    "temporarily disable serverlock by starting up the bot with the --no-cogs flag."
                )
            else:
                log.info(f"Leaving guild '{guild.name}' ({guild.id}) due to serverlock.")
            await guild.leave()


# endregion
