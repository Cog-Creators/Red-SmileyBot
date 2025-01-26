"""Module for Trivia cog."""
import asyncio
import math
import pathlib
from collections import Counter
from typing import Any, Dict, List, Literal, Union
import schema

import io
import yaml
import discord

from redbot.core import Config, commands, bank
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils import AsyncIter, can_user_react_in
from redbot.core.utils.chat_formatting import box, pagify, bold, inline, italics, humanize_number
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate

from .checks import trivia_stop_check
from .converters import finite_float
from .log import LOG
from .session import TriviaSession
from .schema import TRIVIA_LIST_SCHEMA, format_schema_error

__all__ = ("Trivia", "UNIQUE_ID", "InvalidListError", "get_core_lists", "get_list")

UNIQUE_ID = 0xB3C0E453
_ = Translator("Trivia", __file__)
YAMLSafeLoader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


class InvalidListError(Exception):
    """A Trivia list file is in invalid format."""

    pass


def _format_setting_value(key: str, value: Union[float, bool]) -> str:
    # handle bools
    if value is True:
        return _("Yes")
    if value is False:
        return _("No")
    # handle numbers
    value = humanize_number(value)
    if key in ("delay", "timeout"):
        return _("{seconds} seconds").format(seconds=value)
    return str(value)


def format_settings(settings: Dict[str, Union[float, bool]]) -> str:
    setting_names = {
        "bot_plays": _("Bot gains points"),
        "delay": _("Answer time limit"),
        "timeout": _("Lack of response timeout"),
        "max_score": _("Points to win"),
        "reveal_answer": _("Answers are revealed on timeout"),
        "payout_multiplier": _("Payout multiplier"),
        "allow_override": _("Lists are allowed to override settings"),
        "use_spoilers": _("Answers use spoilers"),
    }

    return "\n".join(
        f"{setting_name}: {_format_setting_value(key, settings[key])}"
        for key, setting_name in setting_names.items()
        if key in settings
    )


@cog_i18n(_)
class Trivia(commands.Cog):
    """Play trivia with friends!"""

    def __init__(self, bot: Red) -> None:
        super().__init__()
        self.bot = bot
        self.trivia_sessions = []
        self.config = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)

        self.config.register_guild(
            max_score=10,
            timeout=120.0,
            delay=15.0,
            bot_plays=False,
            reveal_answer=True,
            payout_multiplier=0.0,
            allow_override=True,
            use_spoilers=False,
        )

        self.config.register_member(wins=0, games=0, total_score=0)

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        if requester != "discord_deleted_user":
            return

        all_members = await self.config.all_members()

        async for guild_id, guild_data in AsyncIter(all_members.items(), steps=100):
            if user_id in guild_data:
                await self.config.member_from_ids(guild_id, user_id).clear()

    @commands.group()
    @commands.guild_only()
    @commands.mod_or_permissions(administrator=True)
    async def triviaset(self, ctx: commands.Context):
        """Manage Trivia settings."""

    @triviaset.command(name="showsettings")
    async def triviaset_showsettings(self, ctx: commands.Context):
        """Show the current trivia settings."""
        settings = await self.config.guild(ctx.guild).all()
        msg = box(_("Current settings:\n\n") + format_settings(settings))
        await ctx.send(msg)

    @triviaset.command(name="maxscore")
    async def triviaset_max_score(self, ctx: commands.Context, score: int):
        """Set the total points required to win."""
        if score <= 0:
            await ctx.send(_("Score must be greater than 0."))
            return
        settings = self.config.guild(ctx.guild)
        await settings.max_score.set(score)
        await ctx.send(_("Done. Points required to win set to {num}.").format(num=score))

    @triviaset.command(name="timelimit")
    async def triviaset_timelimit(self, ctx: commands.Context, seconds: finite_float):
        """Set the maximum seconds permitted to answer a question."""
        if seconds < 4.0:
            await ctx.send(_("Must be at least 4 seconds."))
            return
        settings = self.config.guild(ctx.guild)
        await settings.delay.set(seconds)
        await ctx.send(_("Done. Maximum seconds to answer set to {num}.").format(num=seconds))

    @triviaset.command(name="stopafter")
    async def triviaset_stopafter(self, ctx: commands.Context, seconds: finite_float):
        """Set how long until trivia stops due to no response."""
        settings = self.config.guild(ctx.guild)
        if seconds < await settings.delay():
            await ctx.send(_("Must be larger than the answer time limit."))
            return
        await settings.timeout.set(seconds)
        await ctx.send(
            _(
                "Done. Trivia sessions will now time out after {num} seconds of no responses."
            ).format(num=seconds)
        )

    @triviaset.command(name="override")
    async def triviaset_allowoverride(self, ctx: commands.Context, enabled: bool):
        """Allow/disallow trivia lists to override settings."""
        settings = self.config.guild(ctx.guild)
        await settings.allow_override.set(enabled)
        if enabled:
            await ctx.send(
                _("Done. Trivia lists can now override the trivia settings for this server.")
            )
        else:
            await ctx.send(
                _(
                    "Done. Trivia lists can no longer override the trivia settings for this "
                    "server."
                )
            )

    @triviaset.command(name="usespoilers", usage="<true_or_false>")
    async def triviaset_use_spoilers(self, ctx: commands.Context, enabled: bool):
        """Set if bot will display the answers in spoilers.

        If enabled, the bot will use spoilers to hide answers.
        """
        settings = self.config.guild(ctx.guild)
        await settings.use_spoilers.set(enabled)
        if enabled:
            await ctx.send(_("Done. I'll put the answers in spoilers next time."))
        else:
            await ctx.send(_("Alright, I won't use spoilers to hide answers anymore."))

    @triviaset.command(name="botplays", usage="<true_or_false>")
    async def triviaset_bot_plays(self, ctx: commands.Context, enabled: bool):
        """Set whether or not the bot gains points.

        If enabled, the bot will gain a point if no one guesses correctly.
        """
        settings = self.config.guild(ctx.guild)
        await settings.bot_plays.set(enabled)
        if enabled:
            await ctx.send(_("Done. I'll now gain a point if users don't answer in time."))
        else:
            await ctx.send(_("Alright, I won't embarrass you at trivia anymore."))

    @triviaset.command(name="revealanswer", usage="<true_or_false>")
    async def triviaset_reveal_answer(self, ctx: commands.Context, enabled: bool):
        """Set whether or not the answer is revealed.

        If enabled, the bot will reveal the answer if no one guesses correctly
        in time.
        """
        settings = self.config.guild(ctx.guild)
        await settings.reveal_answer.set(enabled)
        if enabled:
            await ctx.send(_("Done. I'll reveal the answer if no one knows it."))
        else:
            await ctx.send(_("Alright, I won't reveal the answer to the questions anymore."))

    @bank.is_owner_if_bank_global()
    @commands.admin_or_permissions(manage_guild=True)
    @triviaset.command(name="payout")
    async def triviaset_payout_multiplier(self, ctx: commands.Context, multiplier: finite_float):
        """Set the payout multiplier.

        This can be any positive decimal number. If a user wins trivia when at
        least 3 members are playing, they will receive credits. Set to 0 to
        disable.

        The number of credits is determined by multiplying their total score by
        this multiplier.
        """
        settings = self.config.guild(ctx.guild)
        if multiplier < 0:
            await ctx.send(_("Multiplier must be at least 0."))
            return
        await settings.payout_multiplier.set(multiplier)
        if multiplier:
            await ctx.send(_("Done. Payout multiplier set to {num}.").format(num=multiplier))
        else:
            await ctx.send(_("Done. I will no longer reward the winner with a payout."))

    @triviaset.group(name="custom")
    @commands.is_owner()
    async def triviaset_custom(self, ctx: commands.Context):
        """Manage Custom Trivia lists."""
        pass

    @triviaset_custom.command(name="list")
    async def custom_trivia_list(self, ctx: commands.Context):
        """List uploaded custom trivia."""
        personal_lists = sorted([p.resolve().stem for p in cog_data_path(self).glob("*.yaml")])
        no_lists_uploaded = _("No custom Trivia lists uploaded.")

        if not personal_lists:
            if await ctx.embed_requested():
                await ctx.send(
                    embed=discord.Embed(
                        colour=await ctx.embed_colour(), description=no_lists_uploaded
                    )
                )
            else:
                await ctx.send(no_lists_uploaded)
            return

        if await ctx.embed_requested():
            await ctx.send(
                embed=discord.Embed(
                    title=_("Uploaded trivia lists"),
                    colour=await ctx.embed_colour(),
                    description=", ".join(sorted(personal_lists)),
                )
            )
        else:
            msg = box(
                bold(_("Uploaded trivia lists")) + "\n\n" + ", ".join(sorted(personal_lists))
            )
            if len(msg) > 1000:
                await ctx.author.send(msg)
            else:
                await ctx.send(msg)

    @commands.is_owner()
    @triviaset_custom.command(name="upload", aliases=["add"])
    async def trivia_upload(self, ctx: commands.Context):
        """Upload a trivia file."""
        if not ctx.message.attachments:
            await ctx.send(_("Supply a file with next message or type anything to cancel."))
            try:
                message = await ctx.bot.wait_for(
                    "message", check=MessagePredicate.same_context(ctx), timeout=30
                )
            except asyncio.TimeoutError:
                await ctx.send(_("You took too long to upload a list."))
                return
            if not message.attachments:
                await ctx.send(_("You have cancelled the upload process."))
                return
            parsedfile = message.attachments[0]
        else:
            parsedfile = ctx.message.attachments[0]
        try:
            await self._save_trivia_list(ctx=ctx, attachment=parsedfile)
        except yaml.error.MarkedYAMLError as exc:
            await ctx.send(_("Invalid syntax:\n") + box(str(exc)))
        except yaml.error.YAMLError:
            await ctx.send(
                _("There was an error parsing the trivia list. See logs for more info.")
            )
            LOG.exception("Custom Trivia file %s failed to upload", parsedfile.filename)
        except schema.SchemaError as exc:
            await ctx.send(
                _(
                    "The custom trivia list was not saved."
                    " The file does not follow the proper data format.\n{schema_error}"
                ).format(schema_error=box(format_schema_error(exc)))
            )

    @commands.is_owner()
    @triviaset_custom.command(name="delete", aliases=["remove"])
    async def trivia_delete(self, ctx: commands.Context, name: str):
        """Delete a trivia file."""
        filepath = cog_data_path(self) / f"{name}.yaml"
        if filepath.exists():
            filepath.unlink()
            await ctx.send(_("Trivia {filename} was deleted.").format(filename=filepath.stem))
        else:
            await ctx.send(_("Trivia file was not found."))

    @commands.group(invoke_without_command=True, require_var_positional=True)
    @commands.guild_only()
    async def trivia(self, ctx: commands.Context, *categories: str):
        """Start trivia session on the specified category.

        You may list multiple categories, in which case the trivia will involve
        questions from all of them.
        """
        categories = [c.lower() for c in categories]
        session = self._get_trivia_session(ctx.channel)
        if session is not None:
            await ctx.send(_("There is already an ongoing trivia session in this channel."))
            return
        trivia_dict = {}
        authors = []
        for category in reversed(categories):
            # We reverse the categories so that the first list's config takes
            # priority over the others.
            try:
                dict_ = self.get_trivia_list(category)
            except FileNotFoundError:
                await ctx.send(
                    _(
                        "Invalid category `{name}`. See `{prefix}trivia list` for a list of "
                        "trivia categories."
                    ).format(name=category, prefix=ctx.clean_prefix)
                )
            except InvalidListError:
                await ctx.send(
                    _(
                        "There was an error parsing the trivia list for the `{name}` category. It "
                        "may be formatted incorrectly."
                    ).format(name=category)
                )
            else:
                trivia_dict.update(dict_)
                authors.append(trivia_dict.pop("AUTHOR", None))
                trivia_dict.pop("DESCRIPTION", None)
                continue
            return
        trivia_dict.pop("$schema", None)
        config = trivia_dict.pop("CONFIG", None)
        if not trivia_dict:
            await ctx.send(
                _("The trivia list was parsed successfully, however it appears to be empty!")
            )
            return
        settings = await self.config.guild(ctx.guild).all()
        if config and settings["allow_override"]:
            settings.update(config)
        settings["lists"] = dict(zip(categories, reversed(authors)))
        session = TriviaSession.start(ctx, trivia_dict, settings)
        self.trivia_sessions.append(session)
        LOG.debug("New trivia session; #%s in %d", ctx.channel, ctx.guild.id)

    @trivia_stop_check()
    @trivia.command(name="stop")
    async def trivia_stop(self, ctx: commands.Context):
        """Stop an ongoing trivia session."""
        session = self._get_trivia_session(ctx.channel)
        if session is None:
            await ctx.send(_("There is no ongoing trivia session in this channel."))
            return
        await session.end_game()
        session.force_stop()
        await ctx.send(_("Trivia stopped."))

    @trivia.command(name="list")
    async def trivia_list(self, ctx: commands.Context):
        """List available trivia categories."""
        lists = set(p.stem for p in self._all_lists())
        if await ctx.embed_requested():
            await ctx.send(
                embed=discord.Embed(
                    title=_("Available trivia lists"),
                    colour=await ctx.embed_colour(),
                    description=", ".join(sorted(lists)),
                )
            )
        else:
            msg = box(bold(_("Available trivia lists")) + "\n\n" + ", ".join(sorted(lists)))
            if len(msg) > 1000:
                await ctx.author.send(msg)
            else:
                await ctx.send(msg)

    @trivia.command(name="info")
    async def trivia_info(self, ctx: commands.Context, category: str.lower):
        """Get information about a trivia category."""
        try:
            data = self.get_trivia_list(category)
        except FileNotFoundError:
            return await ctx.send(
                _(
                    "Category {name} does not exist."
                    " See {command} for the list of available trivia categories."
                ).format(name=inline(category), command=inline(f"{ctx.clean_prefix}trivia list"))
            )
        except InvalidListError:
            return await ctx.send(
                _(
                    "There was an error parsing the trivia list for the {name} category."
                    " It may be formatted incorrectly."
                ).format(name=inline(category))
            )

        config_overrides = data.pop("CONFIG", None)

        embed = discord.Embed(
            title=_('"{category}" Category Details').format(category=category),
            color=await ctx.embed_colour(),
        )
        embed.add_field(
            name=_("Authors"), value=data.pop("AUTHOR", "").strip() or italics(_("Not provided."))
        )
        embed.add_field(name=_("Question count"), value=len(data))
        embed.add_field(
            name=_("Custom"),
            value=_format_setting_value(
                "", any(category == p.resolve().stem for p in cog_data_path(self).glob("*.yaml"))
            ),
        )
        embed.add_field(
            name=_("Description"),
            value=(
                data.pop("DESCRIPTION", "").strip()
                or italics(_("No description provided for this category."))
            ),
            inline=False,
        )

        if config_overrides:
            embed.add_field(
                name=_("Config"),
                value=box(format_settings(config_overrides)),
                inline=False,
            )
        await ctx.send(embed=embed)

    @trivia.group(
        name="leaderboard", aliases=["lboard"], autohelp=False, invoke_without_command=True
    )
    async def trivia_leaderboard(self, ctx: commands.Context):
        """Leaderboard for trivia.

        Defaults to the top 10 of this server, sorted by total wins. Use
        subcommands for a more customised leaderboard.
        """
        cmd = self.trivia_leaderboard_server
        if ctx.guild is None:
            cmd = self.trivia_leaderboard_global
        await ctx.invoke(cmd, "wins", 10)

    @trivia_leaderboard.command(name="server")
    @commands.guild_only()
    async def trivia_leaderboard_server(
        self, ctx: commands.Context, sort_by: str = "wins", top: int = 10
    ):
        """Leaderboard for this server.

        `<sort_by>` can be any of the following fields:
         - `wins`  : total wins
         - `avg`   : average score
         - `total` : total correct answers
         - `games` : total games played

        `<top>` is the number of ranks to show on the leaderboard.
        """
        key = self._get_sort_key(sort_by)
        if key is None:
            await ctx.send(
                _(
                    "Unknown field `{field_name}`, see `{prefix}help trivia leaderboard server` "
                    "for valid fields to sort by."
                ).format(field_name=sort_by, prefix=ctx.clean_prefix)
            )
            return
        guild = ctx.guild
        data = await self.config.all_members(guild)
        data = {guild.get_member(u): d for u, d in data.items()}
        data.pop(None, None)  # remove any members which aren't in the guild
        await self.send_leaderboard(ctx, data, key, top)

    @trivia_leaderboard.command(name="global")
    async def trivia_leaderboard_global(
        self, ctx: commands.Context, sort_by: str = "wins", top: int = 10
    ):
        """Global trivia leaderboard.

        `<sort_by>` can be any of the following fields:
         - `wins`  : total wins
         - `avg`   : average score
         - `total` : total correct answers from all sessions
         - `games` : total games played

        `<top>` is the number of ranks to show on the leaderboard.
        """
        key = self._get_sort_key(sort_by)
        if key is None:
            await ctx.send(
                _(
                    "Unknown field `{field_name}`, see `{prefix}help trivia leaderboard server` "
                    "for valid fields to sort by."
                ).format(field_name=sort_by, prefix=ctx.clean_prefix)
            )
            return
        data = await self.config.all_members()
        collated_data = {}
        for guild_id, guild_data in data.items():
            guild = ctx.bot.get_guild(guild_id)
            if guild is None:
                continue
            for member_id, member_data in guild_data.items():
                member = guild.get_member(member_id)
                if member is None:
                    continue
                collated_member_data = collated_data.get(member, Counter())
                for v_key, value in member_data.items():
                    collated_member_data[v_key] += value
                collated_data[member] = collated_member_data
        await self.send_leaderboard(ctx, collated_data, key, top)

    @staticmethod
    def _get_sort_key(key: str):
        key = key.lower()
        if key in ("wins", "average_score", "total_score", "games"):
            return key
        elif key in ("avg", "average"):
            return "average_score"
        elif key in ("total", "score", "answers", "correct"):
            return "total_score"

    async def send_leaderboard(self, ctx: commands.Context, data: dict, key: str, top: int):
        """Send the leaderboard from the given data.

        Parameters
        ----------
        ctx : commands.Context
            The context to send the leaderboard to.
        data : dict
            The data for the leaderboard. This must map `discord.Member` ->
            `dict`.
        key : str
            The field to sort the data by. Can be ``wins``, ``total_score``,
            ``games`` or ``average_score``.
        top : int
            The number of members to display on the leaderboard.

        Returns
        -------
        `list` of `discord.Message`
            The sent leaderboard messages.

        """
        if not data:
            await ctx.send(_("There are no scores on record!"))
            return
        leaderboard = self._get_leaderboard(data, key, top)
        ret = []
        for page in pagify(leaderboard, shorten_by=10):
            ret.append(await ctx.send(box(page, lang="py")))
        return ret

    @staticmethod
    def _get_leaderboard(data: dict, key: str, top: int):
        # Mix in average score
        for member, stats in data.items():
            if stats["games"] != 0:
                stats["average_score"] = stats["total_score"] / stats["games"]
            else:
                stats["average_score"] = 0.0
        # Sort by reverse order of priority
        priority = ["average_score", "total_score", "wins", "games"]
        try:
            priority.remove(key)
        except ValueError:
            raise ValueError(f"{key} is not a valid key.")
        # Put key last in reverse priority
        priority.append(key)
        items = data.items()
        for key in priority:
            items = sorted(items, key=lambda t: t[1][key], reverse=True)
        max_name_len = max(map(lambda m: len(str(m)), data.keys()))
        # Headers
        headers = (
            _("Rank"),
            _("Member") + " " * (max_name_len - 6),
            _("Wins"),
            _("Games Played"),
            _("Total Score"),
            _("Average Score"),
        )
        lines = [" | ".join(headers), " | ".join(("-" * len(h) for h in headers))]
        # Header underlines
        for rank, tup in enumerate(items, 1):
            member, m_data = tup
            # Align fields to header width
            fields = tuple(
                map(
                    str,
                    (
                        rank,
                        member,
                        m_data["wins"],
                        m_data["games"],
                        m_data["total_score"],
                        round(m_data["average_score"], 2),
                    ),
                )
            )
            padding = [" " * (len(h) - len(f)) for h, f in zip(headers, fields)]
            fields = tuple(f + padding[i] for i, f in enumerate(fields))
            lines.append(" | ".join(fields))
            if rank == top:
                break
        return "\n".join(lines)

    @commands.Cog.listener()
    async def on_trivia_end(self, session: TriviaSession):
        """Event for a trivia session ending.

        This method removes the session from this cog's sessions, and
        cancels any tasks which it was running.

        Parameters
        ----------
        session : TriviaSession
            The session which has just ended.

        """
        channel = session.ctx.channel
        LOG.debug("Ending trivia session; #%s in %s", channel, channel.guild.id)
        if session in self.trivia_sessions:
            self.trivia_sessions.remove(session)
        if session.scores:
            await self.update_leaderboard(session)

    async def update_leaderboard(self, session):
        """Update the leaderboard with the given scores.

        Parameters
        ----------
        session : TriviaSession
            The trivia session to update scores from.

        """
        max_score = session.settings["max_score"]
        for member, score in session.scores.items():
            if member.id == session.ctx.bot.user.id:
                continue
            stats = await self.config.member(member).all()
            if score == max_score:
                stats["wins"] += 1
            stats["total_score"] += score
            stats["games"] += 1
            await self.config.member(member).set(stats)

    def get_trivia_list(self, category: str) -> dict:
        """Get the trivia list corresponding to the given category.

        Parameters
        ----------
        category : str
            The desired category. Case sensitive.

        Returns
        -------
        `dict`
            A dict mapping questions (`str`) to answers (`list` of `str`).

        """
        try:
            path = next(p for p in self._all_lists() if p.stem == category)
        except StopIteration:
            raise FileNotFoundError("Could not find the `{}` category.".format(category))

        return get_list(path)

    async def _save_trivia_list(
        self, ctx: commands.Context, attachment: discord.Attachment
    ) -> None:
        """Checks and saves a trivia list to data folder.

        Parameters
        ----------
        file : discord.Attachment
            A discord message attachment.

        Returns
        -------
        None
        """
        filename = attachment.filename.rsplit(".", 1)[0].casefold()

        # Check if trivia filename exists in core files or if it is a command
        if filename in self.trivia.all_commands or any(
            filename == item.stem for item in get_core_lists()
        ):
            await ctx.send(
                _(
                    "{filename} is a reserved trivia name and cannot be replaced.\n"
                    "Choose another name."
                ).format(filename=filename)
            )
            return

        file = cog_data_path(self) / f"{filename}.yaml"
        if file.exists():
            overwrite_message = _("{filename} already exists. Do you wish to overwrite?").format(
                filename=filename
            )

            can_react = can_user_react_in(ctx.me, ctx.channel)
            if not can_react:
                overwrite_message += " (yes/no)"

            overwrite_message_object: discord.Message = await ctx.send(overwrite_message)
            if can_react:
                # noinspection PyAsyncCall
                start_adding_reactions(
                    overwrite_message_object, ReactionPredicate.YES_OR_NO_EMOJIS
                )
                pred = ReactionPredicate.yes_or_no(overwrite_message_object, ctx.author)
                event = "reaction_add"
            else:
                pred = MessagePredicate.yes_or_no(ctx=ctx)
                event = "message"
            try:
                await ctx.bot.wait_for(event, check=pred, timeout=30)
            except asyncio.TimeoutError:
                await ctx.send(_("You took too long answering."))
                return

            if pred.result is False:
                await ctx.send(_("I am not replacing the existing file."))
                return

        buffer = io.BytesIO(await attachment.read())
        trivia_dict = yaml.load(buffer, YAMLSafeLoader)
        TRIVIA_LIST_SCHEMA.validate(trivia_dict)

        buffer.seek(0)
        try:
            with file.open("wb") as fp:
                fp.write(buffer.read())
        except FileNotFoundError as e:
            await ctx.send(
                _(
                    "There was an error saving the file.\n"
                    "Please check the filename and try again, as it could be longer than your system supports."
                )
            )
            return

        await ctx.send(_("Saved Trivia list as {filename}.").format(filename=filename))

    def _get_trivia_session(
        self,
        channel: Union[
            discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread
        ],
    ) -> TriviaSession:
        return next(
            (session for session in self.trivia_sessions if session.ctx.channel == channel), None
        )

    def _all_lists(self) -> List[pathlib.Path]:
        personal_lists = [p.resolve() for p in cog_data_path(self).glob("*.yaml")]

        return personal_lists + get_core_lists()

    def cog_unload(self):
        for session in self.trivia_sessions:
            session.force_stop()


def get_core_lists() -> List[pathlib.Path]:
    """Return a list of paths for all trivia lists packaged with the bot."""
    core_lists_path = pathlib.Path(__file__).parent.resolve() / "data/lists"
    return list(core_lists_path.glob("*.yaml"))


def get_list(path: pathlib.Path, *, validate_schema: bool = True) -> Dict[str, Any]:
    """
    Returns a trivia list dictionary from the given path.

    Raises
    ------
    InvalidListError
        Parsing of list's YAML file failed.
    """
    with path.open(encoding="utf-8") as file:
        try:
            trivia_dict = yaml.load(file, YAMLSafeLoader)
        except yaml.error.YAMLError as exc:
            raise InvalidListError("YAML parsing failed.") from exc

    if validate_schema:
        try:
            TRIVIA_LIST_SCHEMA.validate(trivia_dict)
        except schema.SchemaError as exc:
            raise InvalidListError("The list does not adhere to the schema.") from exc

    return trivia_dict
