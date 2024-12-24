import logging
import asyncio
from typing import Union, List, Literal
from datetime import timedelta
from copy import copy
import contextlib
import discord

from redbot.core import Config, commands
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import pagify, box
from redbot.core.utils.antispam import AntiSpam
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n, set_contextual_locales_from_guild
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.utils.tunnel import Tunnel


_ = Translator("Reports", __file__)

log = logging.getLogger("red.reports")


@cog_i18n(_)
class Reports(commands.Cog):
    """Create user reports that server staff can respond to.

    Users can open reports using `[p]report`. These are then sent
    to a channel in the server for staff, and the report creator
    gets a DM. Both can be used to communicate.
    """

    default_guild_settings = {"output_channel": None, "active": False, "next_ticket": 1}

    default_report = {"report": {}}

    # This can be made configurable later if it
    # becomes an issue.
    # Intervals should be a list of tuples in the form
    # (period: timedelta, max_frequency: int)
    # see redbot/core/utils/antispam.py for more details

    intervals = [
        (timedelta(seconds=5), 1),
        (timedelta(minutes=5), 3),
        (timedelta(hours=1), 10),
        (timedelta(days=1), 24),
    ]

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, 78631113035100160, force_registration=True)
        self.config.register_guild(**self.default_guild_settings)
        self.config.init_custom("REPORT", 2)
        self.config.register_custom("REPORT", **self.default_report)
        self.antispam = {}
        self.user_cache = []
        self.tunnel_store = {}
        # (guild, ticket#):
        #   {'tun': Tunnel, 'msgs': List[int]}

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        if requester != "discord_deleted_user":
            return

        all_reports = await self.config.custom("REPORT").all()

        steps = 0
        paths = []

        # this doesn't use async iter intentionally due to the nested iterations
        for guild_id_str, tickets in all_reports.items():
            for ticket_number, ticket in tickets.items():
                steps += 1
                if not steps % 100:
                    await asyncio.sleep(0)  # yield context

            if ticket.get("report", {}).get("user_id", 0) == user_id:
                paths.append((guild_id_str, ticket_number))

        async with self.config.custom("REPORT").all() as all_reports:
            async for guild_id_str, ticket_number in AsyncIter(paths, steps=100):
                r = all_reports[guild_id_str][ticket_number]["report"]
                r["user_id"] = 0xDE1
                # this might include EUD, and a report of a deleted user
                # that's been unhandled for long enough for the
                # user to be deleted and the bot receive a request like this...
                r["report"] = "[REPORT DELETED DUE TO DISCORD REQUEST]"

    @property
    def tunnels(self):
        return [x["tun"] for x in self.tunnel_store.values()]

    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group(name="reportset")
    async def reportset(self, ctx: commands.Context):
        """Manage Reports."""
        pass

    @commands.admin_or_permissions(manage_guild=True)
    @reportset.command(name="output")
    async def reportset_output(
        self,
        ctx: commands.Context,
        channel: Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel],
    ):
        """Set the channel where reports will be sent."""
        await self.config.guild(ctx.guild).output_channel.set(channel.id)
        await ctx.send(_("The report channel has been set."))

    @commands.admin_or_permissions(manage_guild=True)
    @reportset.command(name="toggle", aliases=["toggleactive"])
    async def reportset_toggle(self, ctx: commands.Context):
        """Enable or disable reporting for this server."""
        active = await self.config.guild(ctx.guild).active()
        active = not active
        await self.config.guild(ctx.guild).active.set(active)
        if active:
            await ctx.send(_("Reporting is now enabled"))
        else:
            await ctx.send(_("Reporting is now disabled."))

    async def internal_filter(self, m: discord.Member, mod=False, perms=None):
        if perms is not None and m.guild_permissions >= perms:
            return True
        if mod and await self.bot.is_mod(m):
            return True
        # The following line is for consistency with how perms are handled
        # in Red, though I'm not sure it makes sense to use here.
        if await self.bot.is_owner(m):
            return True

    async def discover_guild(
        self,
        author: discord.User,
        *,
        mod: bool = False,
        permissions: Union[discord.Permissions, dict] = None,
        prompt: str = "",
    ):
        """
        discovers which of shared guilds between the bot
        and provided user based on conditions (mod or permissions is an or)

        prompt is for providing a user prompt for selection
        """
        shared_guilds = []
        if permissions is None:
            perms = discord.Permissions()
        elif isinstance(permissions, discord.Permissions):
            perms = permissions
        else:
            perms = discord.Permissions(**permissions)

        async for guild in AsyncIter(self.bot.guilds, steps=100):
            x = guild.get_member(author.id)
            if x is not None:
                if await self.internal_filter(x, mod, perms):
                    shared_guilds.append(guild)
        if len(shared_guilds) == 0:
            raise ValueError("No Qualifying Shared Guilds")
        if len(shared_guilds) == 1:
            return shared_guilds[0]
        output = ""
        guilds = sorted(shared_guilds, key=lambda g: g.name)
        for i, guild in enumerate(guilds, 1):
            output += "{}: {}\n".format(i, guild.name)
        output += "\n{}".format(prompt)

        for page in pagify(output, delims=["\n"]):
            await author.send(box(page))

        try:
            message = await self.bot.wait_for(
                "message",
                check=MessagePredicate.same_context(channel=author.dm_channel, user=author),
                timeout=45,
            )
        except asyncio.TimeoutError:
            await author.send(_("You took too long to select. Try again later."))
            return None

        try:
            message = int(message.content.strip())
            guild = guilds[message - 1]
        except (ValueError, IndexError):
            await author.send(_("That wasn't a valid choice."))
            return None
        else:
            return guild

    async def send_report(self, ctx: commands.Context, msg: discord.Message, guild: discord.Guild):
        author = guild.get_member(msg.author.id)
        report = msg.clean_content

        channel_id = await self.config.guild(guild).output_channel()
        channel = guild.get_channel(channel_id)
        if channel is None:
            return None

        files: List[discord.File] = await Tunnel.files_from_attach(msg)

        ticket_number = await self.config.guild(guild).next_ticket()
        await self.config.guild(guild).next_ticket.set(ticket_number + 1)

        if await self.bot.embed_requested(channel):
            em = discord.Embed(description=report, colour=await ctx.embed_colour())
            em.set_author(
                name=_("Report from {author}{maybe_nick}").format(
                    author=author, maybe_nick=(f" ({author.nick})" if author.nick else "")
                ),
                icon_url=author.display_avatar,
            )
            em.set_footer(text=_("Report #{}").format(ticket_number))
            send_content = None
        else:
            em = None
            send_content = _("Report from {author.mention} (Ticket #{number})").format(
                author=author, number=ticket_number
            )
            send_content += "\n" + report

        try:
            await Tunnel.message_forwarder(
                destination=channel, content=send_content, embed=em, files=files
            )
        except (discord.Forbidden, discord.HTTPException):
            return None

        await self.config.custom("REPORT", guild.id, ticket_number).report.set(
            {"user_id": author.id, "report": report}
        )
        return ticket_number

    @commands.group(name="report", usage="[text]", invoke_without_command=True)
    async def report(self, ctx: commands.Context, *, _report: str = ""):
        """Send a report.

        Use without arguments for interactive reporting, or do
        `[p]report [text]` to use it non-interactively.
        """
        author = ctx.author
        guild = ctx.guild
        if guild is None:
            guild = await self.discover_guild(
                author, prompt=_("Select a server to make a report in by number.")
            )
        if guild is None:
            return
        g_active = await self.config.guild(guild).active()
        if not g_active:
            return await author.send(_("Reporting has not been enabled for this server"))
        if guild.id not in self.antispam:
            self.antispam[guild.id] = {}
        if author.id not in self.antispam[guild.id]:
            self.antispam[guild.id][author.id] = AntiSpam(self.intervals)
        if self.antispam[guild.id][author.id].spammy:
            return await author.send(
                _(
                    "You've sent too many reports recently. "
                    "Please contact a server admin if this is important matter, "
                    "or please wait and try again later."
                )
            )
        if author.id in self.user_cache:
            return await author.send(
                _(
                    "Please finish making your prior report before trying to make an "
                    "additional one!"
                )
            )
        self.user_cache.append(author.id)

        if _report:
            _m = copy(ctx.message)
            _m.content = _report
            _m.content = _m.clean_content
            val = await self.send_report(ctx, _m, guild)
        else:
            try:
                await author.send(
                    _(
                        "Please respond to this message with your Report."
                        "\nYour report should be a single message"
                    )
                )
            except discord.Forbidden:
                return await ctx.send(_("This requires DMs enabled."))

            try:
                message = await self.bot.wait_for(
                    "message",
                    check=MessagePredicate.same_context(ctx, channel=author.dm_channel),
                    timeout=180,
                )
            except asyncio.TimeoutError:
                return await author.send(_("You took too long. Try again later."))
            else:
                val = await self.send_report(ctx, message, guild)

        with contextlib.suppress(discord.Forbidden, discord.HTTPException):
            if val is None:
                if await self.config.guild(ctx.guild).output_channel() is None:
                    await author.send(
                        _(
                            "This server has no reports channel set up. Please contact a server admin."
                        )
                    )
                else:
                    await author.send(
                        _("There was an error sending your report, please contact a server admin.")
                    )
            else:
                await author.send(_("Your report was submitted. (Ticket #{})").format(val))
                self.antispam[guild.id][author.id].stamp()

    @report.after_invoke
    async def report_cleanup(self, ctx: commands.Context):
        """
        The logic is cleaner this way
        """
        if ctx.author.id in self.user_cache:
            self.user_cache.remove(ctx.author.id)
        if ctx.guild and ctx.invoked_subcommand is None:
            if ctx.bot_permissions.manage_messages:
                try:
                    await ctx.message.delete()
                except discord.NotFound:
                    pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """
        oh dear....
        """

        if not str(payload.emoji) == "\N{NEGATIVE SQUARED CROSS MARK}":
            return

        _id = payload.message_id
        t = next(filter(lambda x: _id in x[1]["msgs"], self.tunnel_store.items()), None)

        if t is None:
            return
        guild = t[0][0]
        tun = t[1]["tun"]
        if payload.user_id in [x.id for x in tun.members]:
            await set_contextual_locales_from_guild(self.bot, guild)
            await tun.react_close(
                uid=payload.user_id, message=_("{closer} has closed the correspondence")
            )
            self.tunnel_store.pop(t[0], None)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        to_remove = []

        for k, v in self.tunnel_store.items():
            guild, ticket_number = k
            if await self.bot.cog_disabled_in_guild(self, guild):
                to_remove.append(k)
                continue

            await set_contextual_locales_from_guild(self.bot, guild)
            topic = _("Re: ticket# {ticket_number} in {guild.name}").format(
                ticket_number=ticket_number, guild=guild
            )
            # Tunnels won't forward unintended messages, this is safe
            msgs = await v["tun"].communicate(message=message, topic=topic)
            if msgs:
                self.tunnel_store[k]["msgs"] = msgs

        for key in to_remove:
            if tun := self.tunnel_store.pop(key, None):
                guild, ticket = key
                await set_contextual_locales_from_guild(self.bot, guild)
                await tun["tun"].close_because_disabled(
                    _(
                        "Correspondence about ticket# {ticket_number} in "
                        "{guild.name} has been ended due "
                        "to reports being disabled in that server."
                    ).format(ticket_number=ticket, guild=guild)
                )

    @commands.guild_only()
    @commands.mod_or_permissions(manage_roles=True)
    @report.command(name="interact")
    async def response(self, ctx, ticket_number: int):
        """Open a message tunnel.

        This tunnel will forward things you say in this channel or thread
        to the ticket opener's direct messages.

        Tunnels do not persist across bot restarts.
        """

        guild = ctx.guild
        rec = await self.config.custom("REPORT", guild.id, ticket_number).report()

        try:
            user = guild.get_member(rec.get("user_id"))
        except KeyError:
            return await ctx.send(_("That ticket doesn't seem to exist"))

        if user is None:
            return await ctx.send(_("That user isn't here anymore."))

        tun = Tunnel(recipient=user, origin=ctx.channel, sender=ctx.author)

        if tun is None:
            return await ctx.send(
                _(
                    "Either you or the user you are trying to reach already "
                    "has an open communication."
                )
            )

        big_topic = _(
            " Anything you say or upload here "
            "(8MB file size limitation on uploads) "
            "will be forwarded to them until the communication is closed.\n"
            "You can close a communication at any point by reacting with "
            "the \N{NEGATIVE SQUARED CROSS MARK} to the last message received.\n"
            "Any message successfully forwarded will be marked with "
            "\N{WHITE HEAVY CHECK MARK}.\n"
            "Tunnels are not persistent across bot restarts."
        )
        topic = (
            _(
                "A moderator in the server `{guild.name}` has opened a 2-way communication about "
                "ticket number {ticket_number}."
            ).format(guild=guild, ticket_number=ticket_number)
            + big_topic
        )
        try:
            m = await tun.communicate(message=ctx.message, topic=topic, skip_message_content=True)
        except discord.Forbidden:
            await ctx.send(_("That user has DMs disabled."))
        else:
            self.tunnel_store[(guild, ticket_number)] = {"tun": tun, "msgs": m}
            await ctx.send(
                _(
                    "You have opened a 2-way communication about ticket number {ticket_number}."
                ).format(ticket_number=ticket_number)
                + big_topic
            )
