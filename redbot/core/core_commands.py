import asyncio
import contextlib
import datetime
import importlib
import itertools
import keyword
import logging
import io
import random
import markdown
import os
import re
import sys
import platform
import psutil
import getpass
import pip
import traceback
from pathlib import Path
from collections import defaultdict
from redbot.core import app_commands, data_manager
from redbot.core.utils.menus import menu
from redbot.core.utils.views import SetApiView
from redbot.core.commands import GuildConverter, RawUserIdConverter
from string import ascii_letters, digits
from typing import (
    TYPE_CHECKING,
    Union,
    Tuple,
    List,
    Optional,
    Iterable,
    Sequence,
    Dict,
    Set,
    Literal,
)

import aiohttp
import discord
from redbot.core.data_manager import storage_type

from . import (
    __version__,
    version_info as red_version_info,
    commands,
    errors,
    _i18n,
    i18n,
    bank,
    modlog,
)
from ._diagnoser import IssueDiagnoser
from .utils import AsyncIter, can_user_send_messages_in
from .utils._internal_utils import fetch_latest_red_version_info
from .utils.predicates import MessagePredicate
from .utils.chat_formatting import (
    box,
    escape,
    humanize_list,
    humanize_number,
    humanize_timedelta,
    inline,
    pagify,
    warning,
)
from .commands import CommandConverter, CogConverter
from .commands.requires import PrivilegeLevel
from .commands.help import HelpMenuSetting

_entities = {
    "*": "&midast;",
    "\\": "&bsol;",
    "`": "&grave;",
    "!": "&excl;",
    "{": "&lcub;",
    "[": "&lsqb;",
    "_": "&UnderBar;",
    "(": "&lpar;",
    "#": "&num;",
    ".": "&period;",
    "+": "&plus;",
    "}": "&rcub;",
    "]": "&rsqb;",
    ")": "&rpar;",
}

PRETTY_HTML_HEAD = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>3rd Party Data Statements</title>
<style type="text/css">
body{margin:2em auto;max-width:800px;line-height:1.4;font-size:16px;
background-color=#EEEEEE;color:#454545;padding:1em;text-align:justify}
h1,h2,h3{line-height:1.2}
</style></head><body>
"""  # This ends up being a small bit extra that really makes a difference.

HTML_CLOSING = "</body></html>"


def entity_transformer(statement: str) -> str:
    return "".join(_entities.get(c, c) for c in statement)


if TYPE_CHECKING:
    from redbot.core.bot import Red

__all__ = ["Core"]

log = logging.getLogger("red")

_ = i18n.Translator("Core", __file__)

TokenConverter = commands.get_dict_converter(delims=[" ", ",", ";"])

MAX_PREFIX_LENGTH = 25
MINIMUM_PREFIX_LENGTH = 1


class CoreLogic:
    def __init__(self, bot: "Red"):
        self.bot = bot
        self.bot.register_rpc_handler(self._load)
        self.bot.register_rpc_handler(self._unload)
        self.bot.register_rpc_handler(self._reload)
        self.bot.register_rpc_handler(self._name)
        self.bot.register_rpc_handler(self._prefixes)
        self.bot.register_rpc_handler(self._version_info)
        self.bot.register_rpc_handler(self._invite_url)

    async def _load(self, pkg_names: Iterable[str]) -> Dict[str, Union[List[str], Dict[str, str]]]:
        """
        Loads packages by name.

        Parameters
        ----------
        pkg_names : `list` of `str`
            List of names of packages to load.

        Returns
        -------
        dict
            Dictionary with keys:
              ``loaded_packages``: List of names of packages that loaded successfully
              ``failed_packages``: List of names of packages that failed to load without specified reason
              ``invalid_pkg_names``: List of names of packages that don't have a valid package name
              ``notfound_packages``: List of names of packages that weren't found in any cog path
              ``alreadyloaded_packages``: List of names of packages that are already loaded
              ``failed_with_reason_packages``: Dictionary of packages that failed to load with
              a specified reason with mapping of package names -> failure reason
              ``repos_with_shared_libs``: List of repo names that use deprecated shared libraries
        """
        failed_packages = []
        loaded_packages = []
        invalid_pkg_names = []
        notfound_packages = []
        alreadyloaded_packages = []
        failed_with_reason_packages = {}
        repos_with_shared_libs = set()

        bot = self.bot

        pkg_specs = []

        for name in pkg_names:
            if not name.isidentifier() or keyword.iskeyword(name):
                invalid_pkg_names.append(name)
                continue
            try:
                spec = await bot._cog_mgr.find_cog(name)
                if spec:
                    pkg_specs.append((spec, name))
                else:
                    notfound_packages.append(name)
            except Exception as e:
                log.exception("Package import failed", exc_info=e)

                exception_log = "Exception during import of package\n"
                exception_log += "".join(traceback.format_exception(type(e), e, e.__traceback__))
                bot._last_exception = exception_log
                failed_packages.append(name)

        async for spec, name in AsyncIter(pkg_specs, steps=10):
            try:
                self._cleanup_and_refresh_modules(spec.name)
                await bot.load_extension(spec)
            except errors.PackageAlreadyLoaded:
                alreadyloaded_packages.append(name)
            except errors.CogLoadError as e:
                failed_with_reason_packages[name] = str(e)
            except Exception as e:
                if isinstance(e, commands.CommandRegistrationError):
                    if e.alias_conflict:
                        error_message = _(
                            "Alias {alias_name} is already an existing command"
                            " or alias in one of the loaded cogs."
                        ).format(alias_name=inline(e.name))
                    else:
                        error_message = _(
                            "Command {command_name} is already an existing command"
                            " or alias in one of the loaded cogs."
                        ).format(command_name=inline(e.name))
                    failed_with_reason_packages[name] = error_message
                    continue

                log.exception("Package loading failed", exc_info=e)

                exception_log = "Exception during loading of package\n"
                exception_log += "".join(traceback.format_exception(type(e), e, e.__traceback__))
                bot._last_exception = exception_log
                failed_packages.append(name)
            else:
                await bot.add_loaded_package(name)
                loaded_packages.append(name)
                # remove in Red 3.4
                downloader = bot.get_cog("Downloader")
                if downloader is None:
                    continue
                try:
                    maybe_repo = await downloader._shared_lib_load_check(name)
                except Exception:
                    log.exception(
                        "Shared library check failed,"
                        " if you're not using modified Downloader, report this issue."
                    )
                    maybe_repo = None
                if maybe_repo is not None:
                    repos_with_shared_libs.add(maybe_repo.name)

        return {
            "loaded_packages": loaded_packages,
            "failed_packages": failed_packages,
            "invalid_pkg_names": invalid_pkg_names,
            "notfound_packages": notfound_packages,
            "alreadyloaded_packages": alreadyloaded_packages,
            "failed_with_reason_packages": failed_with_reason_packages,
            "repos_with_shared_libs": list(repos_with_shared_libs),
        }

    @staticmethod
    def _cleanup_and_refresh_modules(module_name: str) -> None:
        """Internally reloads modules so that changes are detected."""
        splitted = module_name.split(".")

        def maybe_reload(new_name):
            try:
                lib = sys.modules[new_name]
            except KeyError:
                pass
            else:
                importlib._bootstrap._exec(lib.__spec__, lib)

        # noinspection PyTypeChecker
        modules = itertools.accumulate(splitted, "{}.{}".format)
        for m in modules:
            maybe_reload(m)

        children = {
            name: lib
            for name, lib in sys.modules.items()
            if name == module_name or name.startswith(f"{module_name}.")
        }
        for child_name, lib in children.items():
            importlib._bootstrap._exec(lib.__spec__, lib)

    async def _unload(self, pkg_names: Iterable[str]) -> Dict[str, List[str]]:
        """
        Unloads packages with the given names.

        Parameters
        ----------
        pkg_names : `list` of `str`
            List of names of packages to unload.

        Returns
        -------
        dict
            Dictionary with keys:
              ``unloaded_packages``: List of names of packages that unloaded successfully.
              ``notloaded_packages``: List of names of packages that weren't unloaded
              because they weren't loaded.
        """
        notloaded_packages = []
        unloaded_packages = []

        bot = self.bot

        for name in pkg_names:
            if name in bot.extensions:
                await bot.unload_extension(name)
                await bot.remove_loaded_package(name)
                unloaded_packages.append(name)
            else:
                notloaded_packages.append(name)

        return {"unloaded_packages": unloaded_packages, "notloaded_packages": notloaded_packages}

    async def _reload(
        self, pkg_names: Sequence[str]
    ) -> Dict[str, Union[List[str], Dict[str, str]]]:
        """
        Reloads packages with the given names.

        Parameters
        ----------
        pkg_names : `list` of `str`
            List of names of packages to reload.

        Returns
        -------
        dict
            Dictionary with keys as returned by `CoreLogic._load()`
        """
        await self._unload(pkg_names)

        return await self._load(pkg_names)

    async def _name(self, name: Optional[str] = None) -> str:
        """
        Gets or sets the bot's username.

        Parameters
        ----------
        name : str
            If passed, the bot will change it's username.

        Returns
        -------
        str
            The current (or new) username of the bot.
        """
        if name is not None:
            return (await self.bot.user.edit(username=name)).name

        return self.bot.user.name

    async def _prefixes(self, prefixes: Optional[Sequence[str]] = None) -> List[str]:
        """
        Gets or sets the bot's global prefixes.

        Parameters
        ----------
        prefixes : list of str
            If passed, the bot will set it's global prefixes.

        Returns
        -------
        list of str
            The current (or new) list of prefixes.
        """
        if prefixes:
            await self.bot.set_prefixes(guild=None, prefixes=prefixes)
            return prefixes
        return await self.bot._prefix_cache.get_prefixes(guild=None)

    @classmethod
    async def _version_info(cls) -> Dict[str, str]:
        """
        Version information for Red and discord.py

        Returns
        -------
        dict
            `redbot` and `discordpy` keys containing version information for both.
        """
        return {"redbot": __version__, "discordpy": discord.__version__}

    async def _invite_url(self) -> str:
        """
        Generates the invite URL for the bot.

        Returns
        -------
        str
            Invite URL.
        """
        return await self.bot.get_invite_url()

    @staticmethod
    async def _can_get_invite_url(ctx):
        is_owner = await ctx.bot.is_owner(ctx.author)
        is_invite_public = await ctx.bot._config.invite_public()
        return is_owner or is_invite_public


@i18n.cog_i18n(_)
class Core(commands.commands._RuleDropper, commands.Cog, CoreLogic):
    """
    The Core cog has many commands related to core functions.

    These commands come loaded with every Red bot, and cover some of the most basic usage of the bot.
    """

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete (Core Config is handled in a bot method)"""
        return

    @commands.command(hidden=True)
    async def ping(self, ctx: commands.Context):
        """Pong."""
        await ctx.send("Pong.")

    @commands.command()
    async def info(self, ctx: commands.Context):
        """Shows info about [botname]."""
        embed_links = await ctx.embed_requested()
        author_repo = "https://github.com/Twentysix26"
        red_repo = "https://github.com/Cog-Creators/Red-DiscordBot"
        contributors_url = red_repo + "/graphs/contributors"
        red_pypi = "https://pypi.org/project/Red-DiscordBot"
        support_server_url = "https://discord.gg/red"
        dpy_repo = "https://github.com/Rapptz/discord.py"
        python_url = "https://www.python.org/"
        since = datetime.datetime(2016, 1, 2, 0, 0)
        days_since = (datetime.datetime.utcnow() - since).days

        app_info = await self.bot.application_info()
        if app_info.team:
            owner = app_info.team.name
        else:
            owner = app_info.owner
        custom_info = await self.bot._config.custom_info()

        pypi_version, py_version_req = await fetch_latest_red_version_info()
        outdated = pypi_version and pypi_version > red_version_info

        if embed_links:
            dpy_version = "[{}]({})".format(discord.__version__, dpy_repo)
            python_version = "[{}.{}.{}]({})".format(*sys.version_info[:3], python_url)
            red_version = "[{}]({})".format(__version__, red_pypi)

            about = _(
                "This bot is an instance of [Red, an open source Discord bot]({}) "
                "created by [Twentysix]({}) and [improved by many]({}).\n\n"
                "Red is backed by a passionate community who contributes and "
                "creates content for everyone to enjoy. [Join us today]({}) "
                "and help us improve!\n\n"
                "(c) Cog Creators"
            ).format(red_repo, author_repo, contributors_url, support_server_url)

            embed = discord.Embed(color=(await ctx.embed_colour()))
            embed.add_field(
                name=_("Instance owned by team") if app_info.team else _("Instance owned by"),
                value=str(owner),
            )
            embed.add_field(name="Python", value=python_version)
            embed.add_field(name="discord.py", value=dpy_version)
            embed.add_field(name=_("Red version"), value=red_version)
            if outdated in (True, None):
                if outdated is True:
                    outdated_value = _("Yes, {version} is available.").format(
                        version=str(pypi_version)
                    )
                else:
                    outdated_value = _("Checking for updates failed.")
                embed.add_field(name=_("Outdated"), value=outdated_value)
            if custom_info:
                embed.add_field(name=_("About this instance"), value=custom_info, inline=False)
            embed.add_field(name=_("About Red"), value=about, inline=False)

            embed.set_footer(
                text=_("Bringing joy since 02 Jan 2016 (over {} days ago!)").format(days_since)
            )
            await ctx.send(embed=embed)
        else:
            python_version = "{}.{}.{}".format(*sys.version_info[:3])
            dpy_version = "{}".format(discord.__version__)
            red_version = "{}".format(__version__)

            about = _(
                "This bot is an instance of Red, an open source Discord bot (1) "
                "created by Twentysix (2) and improved by many (3).\n\n"
                "Red is backed by a passionate community who contributes and "
                "creates content for everyone to enjoy. Join us today (4) "
                "and help us improve!\n\n"
                "(c) Cog Creators"
            )
            about = box(about)

            if app_info.team:
                extras = _(
                    "Instance owned by team: [{owner}]\n"
                    "Python:                 [{python_version}] (5)\n"
                    "discord.py:             [{dpy_version}] (6)\n"
                    "Red version:            [{red_version}] (7)\n"
                ).format(
                    owner=owner,
                    python_version=python_version,
                    dpy_version=dpy_version,
                    red_version=red_version,
                )
            else:
                extras = _(
                    "Instance owned by: [{owner}]\n"
                    "Python:            [{python_version}] (5)\n"
                    "discord.py:        [{dpy_version}] (6)\n"
                    "Red version:       [{red_version}] (7)\n"
                ).format(
                    owner=owner,
                    python_version=python_version,
                    dpy_version=dpy_version,
                    red_version=red_version,
                )

            if outdated in (True, None):
                if outdated is True:
                    outdated_value = _("Yes, {version} is available.").format(
                        version=str(pypi_version)
                    )
                else:
                    outdated_value = _("Checking for updates failed.")
                extras += _("Outdated:          [{state}]\n").format(state=outdated_value)

            red = (
                _("**About Red**\n")
                + about
                + "\n"
                + box(extras, lang="ini")
                + "\n"
                + _("Bringing joy since 02 Jan 2016 (over {} days ago!)").format(days_since)
                + "\n\n"
            )

            await ctx.send(red)
            if custom_info:
                custom_info = _("**About this instance**\n") + custom_info + "\n\n"
                await ctx.send(custom_info)
            refs = _(
                "**References**\n"
                "1. <{}>\n"
                "2. <{}>\n"
                "3. <{}>\n"
                "4. <{}>\n"
                "5. <{}>\n"
                "6. <{}>\n"
                "7. <{}>\n"
            ).format(
                red_repo,
                author_repo,
                contributors_url,
                support_server_url,
                python_url,
                dpy_repo,
                red_pypi,
            )
            await ctx.send(refs)

    @commands.command()
    async def uptime(self, ctx: commands.Context):
        """Shows [botname]'s uptime."""
        delta = datetime.datetime.utcnow() - self.bot.uptime
        uptime = self.bot.uptime.replace(tzinfo=datetime.timezone.utc)
        uptime_str = humanize_timedelta(timedelta=delta) or _("Less than one second.")
        await ctx.send(
            _("I have been up for: **{time_quantity}** (since {timestamp})").format(
                time_quantity=uptime_str, timestamp=discord.utils.format_dt(uptime, "f")
            )
        )

    @commands.group(cls=commands.commands._AlwaysAvailableGroup)
    async def mydata(self, ctx: commands.Context):
        """
        Commands which interact with the data [botname] has about you.

        More information can be found in the [End User Data Documentation.](https://docs.discord.red/en/stable/red_core_data_statement.html)
        """

    # 1/10 minutes. It's a static response, but the inability to lock
    # will annoy people if it's spammable
    @commands.cooldown(1, 600, commands.BucketType.user)
    @mydata.command(cls=commands.commands._AlwaysAvailableCommand, name="whatdata")
    async def mydata_whatdata(self, ctx: commands.Context):
        """
        Find out what type of data [botname] stores and why.

        **Example:**
        - `[p]mydata whatdata`
        """

        ver = "latest" if red_version_info.dev_release else "stable"
        link = f"https://docs.discord.red/en/{ver}/red_core_data_statement.html"
        await ctx.send(
            _(
                "This bot stores some data about users as necessary to function. "
                "This is mostly the ID your user is assigned by Discord, linked to "
                "a handful of things depending on what you interact with in the bot. "
                "There are a few commands which store it to keep track of who created "
                "something. (such as playlists) "
                "For full details about this as well as more in depth details of what "
                "is stored and why, see {link}.\n\n"
                "Additionally, 3rd party addons loaded by the bot's owner may or "
                "may not store additional things. "
                "You can use `{prefix}mydata 3rdparty` "
                "to view the statements provided by each 3rd-party addition."
            ).format(link=link, prefix=ctx.clean_prefix)
        )

    # 1/30 minutes. It's not likely to change much and uploads a standalone webpage.
    @commands.cooldown(1, 1800, commands.BucketType.user)
    @mydata.command(cls=commands.commands._AlwaysAvailableCommand, name="3rdparty")
    async def mydata_3rd_party(self, ctx: commands.Context):
        """View the End User Data statements of each 3rd-party module.

        This will send an attachment with the End User Data statements of all loaded 3rd party cogs.

        **Example:**
        - `[p]mydata 3rdparty`
        """

        # Can't check this as a command check, and want to prompt DMs as an option.
        if not ctx.bot_permissions.attach_files:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(_("I need to be able to attach files (try in DMs?)."))

        statements = {
            ext_name: getattr(ext, "__red_end_user_data_statement__", None)
            for ext_name, ext in ctx.bot.extensions.items()
            if not (ext.__package__ and ext.__package__.startswith("redbot."))
        }

        if not statements:
            return await ctx.send(
                _("This instance does not appear to have any 3rd-party extensions loaded.")
            )

        parts = []

        formatted_statements = []

        no_statements = []

        for ext_name, statement in sorted(statements.items()):
            if not statement:
                no_statements.append(ext_name)
            else:
                formatted_statements.append(
                    f"### {entity_transformer(ext_name)}\n\n{entity_transformer(statement)}"
                )

        if formatted_statements:
            parts.append(
                "## "
                + _("3rd party End User Data statements")
                + "\n\n"
                + _("The following are statements provided by 3rd-party extensions.")
            )
            parts.extend(formatted_statements)

        if no_statements:
            parts.append("## " + _("3rd-party extensions without statements\n"))
            for ext in no_statements:
                parts.append(f"\n - {entity_transformer(ext)}")

        generated = markdown.markdown("\n".join(parts), output_format="html")

        html = "\n".join((PRETTY_HTML_HEAD, generated, HTML_CLOSING))

        fp = io.BytesIO(html.encode())

        await ctx.send(
            _("Here's a generated page with the statements provided by 3rd-party extensions."),
            file=discord.File(fp, filename="3rd-party.html"),
        )

    async def get_serious_confirmation(self, ctx: commands.Context, prompt: str) -> bool:
        confirm_token = "".join(random.choices((*ascii_letters, *digits), k=8))

        await ctx.send(f"{prompt}\n\n{confirm_token}")
        try:
            message = await ctx.bot.wait_for(
                "message",
                check=lambda m: m.channel.id == ctx.channel.id and m.author.id == ctx.author.id,
                timeout=30,
            )
        except asyncio.TimeoutError:
            await ctx.send(_("Did not get confirmation, cancelling."))
        else:
            if message.content.strip() == confirm_token:
                return True
            else:
                await ctx.send(_("Did not get a matching confirmation, cancelling."))

        return False

    # 1 per day, not stored to config to avoid this being more stored data.
    # large bots shouldn't be restarting so often that this is an issue,
    # and small bots that do restart often don't have enough
    # users for this to be an issue.
    @commands.cooldown(1, 86400, commands.BucketType.user)
    @mydata.command(cls=commands.commands._ForgetMeSpecialCommand, name="forgetme")
    async def mydata_forgetme(self, ctx: commands.Context):
        """
        Have [botname] forget what it knows about you.

        This may not remove all data about you, data needed for operation,
        such as command cooldowns will be kept until no longer necessary.

        Further interactions with [botname] may cause it to learn about you again.

        **Example:**
        - `[p]mydata forgetme`
        """
        if ctx.assume_yes:
            # lol, no, we're not letting users schedule deletions every day to thrash the bot.
            ctx.command.reset_cooldown(ctx)  # We will however not let that lock them out either.
            return await ctx.send(
                _("This command ({command}) does not support non-interactive usage.").format(
                    command=ctx.command.qualified_name
                )
            )

        if not await self.get_serious_confirmation(
            ctx,
            _(
                "This will cause the bot to get rid of and/or disassociate "
                "data from you. It will not get rid of operational data such "
                "as modlog entries, warnings, or mutes. "
                "If you are sure this is what you want, "
                "please respond with the following:"
            ),
        ):
            ctx.command.reset_cooldown(ctx)
            return
        await ctx.send(_("This may take some time."))

        if await ctx.bot._config.datarequests.user_requests_are_strict():
            requester = "user_strict"
        else:
            requester = "user"

        results = await self.bot.handle_data_deletion_request(
            requester=requester, user_id=ctx.author.id
        )

        if results.failed_cogs and results.failed_modules:
            await ctx.send(
                _(
                    "I tried to delete all non-operational data about you "
                    "(that I know how to delete) "
                    "{mention}, however the following modules errored: {modules}. "
                    "Additionally, the following cogs errored: {cogs}.\n"
                    "Please contact the owner of this bot to address this.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(
                    mention=ctx.author.mention,
                    cogs=humanize_list(results.failed_cogs),
                    modules=humanize_list(results.failed_modules),
                )
            )
        elif results.failed_cogs:
            await ctx.send(
                _(
                    "I tried to delete all non-operational data about you "
                    "(that I know how to delete) "
                    "{mention}, however the following cogs errored: {cogs}.\n"
                    "Please contact the owner of this bot to address this.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(mention=ctx.author.mention, cogs=humanize_list(results.failed_cogs))
            )
        elif results.failed_modules:
            await ctx.send(
                _(
                    "I tried to delete all non-operational data about you "
                    "(that I know how to delete) "
                    "{mention}, however the following modules errored: {modules}.\n"
                    "Please contact the owner of this bot to address this.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(mention=ctx.author.mention, modules=humanize_list(results.failed_modules))
            )
        else:
            await ctx.send(
                _(
                    "I've deleted any non-operational data about you "
                    "(that I know how to delete) {mention}"
                ).format(mention=ctx.author.mention)
            )

        if results.unhandled:
            await ctx.send(
                _("{mention} The following cogs did not handle deletion:\n{cogs}.").format(
                    mention=ctx.author.mention, cogs=humanize_list(results.unhandled)
                )
            )

    # The cooldown of this should be longer once actually implemented
    # This is a couple hours, and lets people occasionally check status, I guess.
    @commands.cooldown(1, 7200, commands.BucketType.user)
    @mydata.command(cls=commands.commands._AlwaysAvailableCommand, name="getmydata")
    async def mydata_getdata(self, ctx: commands.Context):
        """[Coming Soon] Get what data [botname] has about you."""
        await ctx.send(
            _(
                "This command doesn't do anything yet, "
                "but we're working on adding support for this."
            )
        )

    @commands.is_owner()
    @mydata.group(name="ownermanagement")
    async def mydata_owner_management(self, ctx: commands.Context):
        """
        Commands for more complete data handling.
        """

    @mydata_owner_management.command(name="allowuserdeletions")
    async def mydata_owner_allow_user_deletions(self, ctx):
        """
        Set the bot to allow users to request a data deletion.

        This is on by default.
        Opposite of `[p]mydata ownermanagement disallowuserdeletions`

        **Example:**
        - `[p]mydata ownermanagement allowuserdeletions`
        """
        await ctx.bot._config.datarequests.allow_user_requests.set(True)
        await ctx.send(
            _(
                "User can delete their own data. "
                "This will not include operational data such as blocked users."
            )
        )

    @mydata_owner_management.command(name="disallowuserdeletions")
    async def mydata_owner_disallow_user_deletions(self, ctx):
        """
        Set the bot to not allow users to request a data deletion.

        Opposite of `[p]mydata ownermanagement allowuserdeletions`

        **Example:**
        - `[p]mydata ownermanagement disallowuserdeletions`
        """
        await ctx.bot._config.datarequests.allow_user_requests.set(False)
        await ctx.send(_("User can not delete their own data."))

    @mydata_owner_management.command(name="setuserdeletionlevel")
    async def mydata_owner_user_deletion_level(self, ctx, level: int):
        """
        Sets how user deletions are treated.

        **Example:**
        - `[p]mydata ownermanagement setuserdeletionlevel 1`

        **Arguments:**
        - `<level>` - The strictness level for user deletion. See Level guide below.

        Level:
        - `0`: What users can delete is left entirely up to each cog.
        - `1`: Cogs should delete anything the cog doesn't need about the user.
        """

        if level == 1:
            await ctx.bot._config.datarequests.user_requests_are_strict.set(True)
            await ctx.send(
                _(
                    "Cogs will be instructed to remove all non operational "
                    "data upon a user request."
                )
            )
        elif level == 0:
            await ctx.bot._config.datarequests.user_requests_are_strict.set(False)
            await ctx.send(
                _(
                    "Cogs will be informed a user has made a data deletion request, "
                    "and the details of what to delete will be left to the "
                    "discretion of the cog author."
                )
            )
        else:
            await ctx.send_help()

    @mydata_owner_management.command(name="processdiscordrequest")
    async def mydata_discord_deletion_request(self, ctx, user_id: int):
        """
        Handle a deletion request from Discord.

        This will cause the bot to get rid of or disassociate all data from the specified user ID.
        You should not use this unless Discord has specifically requested this with regard to a deleted user.
        This will remove the user from various anti-abuse measures.
        If you are processing a manual request from a user, you may want `[p]mydata ownermanagement deleteforuser` instead.

        **Arguments:**
        - `<user_id>` - The id of the user whose data would be deleted.
        """

        if not await self.get_serious_confirmation(
            ctx,
            _(
                "This will cause the bot to get rid of or disassociate all data "
                "from the specified user ID. You should not use this unless "
                "Discord has specifically requested this with regard to a deleted user. "
                "This will remove the user from various anti-abuse measures. "
                "If you are processing a manual request from a user, you may want "
                "`{prefix}{command_name}` instead."
                "\n\nIf you are sure this is what you intend to do "
                "please respond with the following:"
            ).format(prefix=ctx.clean_prefix, command_name="mydata ownermanagement deleteforuser"),
        ):
            return
        results = await self.bot.handle_data_deletion_request(
            requester="discord_deleted_user", user_id=user_id
        )

        if results.failed_cogs and results.failed_modules:
            await ctx.send(
                _(
                    "I tried to delete all data about that user, "
                    "(that I know how to delete) "
                    "however the following modules errored: {modules}. "
                    "Additionally, the following cogs errored: {cogs}\n"
                    "Please check your logs and contact the creators of "
                    "these cogs and modules.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(
                    cogs=humanize_list(results.failed_cogs),
                    modules=humanize_list(results.failed_modules),
                )
            )
        elif results.failed_cogs:
            await ctx.send(
                _(
                    "I tried to delete all data about that user, "
                    "(that I know how to delete) "
                    "however the following cogs errored: {cogs}.\n"
                    "Please check your logs and contact the creators of "
                    "these cogs and modules.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(cogs=humanize_list(results.failed_cogs))
            )
        elif results.failed_modules:
            await ctx.send(
                _(
                    "I tried to delete all data about that user, "
                    "(that I know how to delete) "
                    "however the following modules errored: {modules}.\n"
                    "Please check your logs and contact the creators of "
                    "these cogs and modules.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(modules=humanize_list(results.failed_modules))
            )
        else:
            await ctx.send(_("I've deleted all data about that user that I know how to delete."))

        if results.unhandled:
            await ctx.send(
                _("{mention} The following cogs did not handle deletion:\n{cogs}.").format(
                    mention=ctx.author.mention, cogs=humanize_list(results.unhandled)
                )
            )

    @mydata_owner_management.command(name="deleteforuser")
    async def mydata_user_deletion_request_by_owner(self, ctx, user_id: int):
        """Delete data [botname] has about a user for a user.

        This will cause the bot to get rid of or disassociate a lot of non-operational data from the specified user.
        Users have access to a different command for this unless they can't interact with the bot at all.
        This is a mostly safe operation, but you should not use it unless processing a request from this user as it may impact their usage of the bot.

        **Arguments:**
        - `<user_id>` - The id of the user whose data would be deleted.
        """
        if not await self.get_serious_confirmation(
            ctx,
            _(
                "This will cause the bot to get rid of or disassociate "
                "a lot of non-operational data from the "
                "specified user. Users have access to "
                "different command for this unless they can't interact with the bot at all. "
                "This is a mostly safe operation, but you should not use it "
                "unless processing a request from this "
                "user as it may impact their usage of the bot. "
                "\n\nIf you are sure this is what you intend to do "
                "please respond with the following:"
            ),
        ):
            return

        if await ctx.bot._config.datarequests.user_requests_are_strict():
            requester = "user_strict"
        else:
            requester = "user"

        results = await self.bot.handle_data_deletion_request(requester=requester, user_id=user_id)

        if results.failed_cogs and results.failed_modules:
            await ctx.send(
                _(
                    "I tried to delete all non-operational data about that user, "
                    "(that I know how to delete) "
                    "however the following modules errored: {modules}. "
                    "Additionally, the following cogs errored: {cogs}\n"
                    "Please check your logs and contact the creators of "
                    "these cogs and modules.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(
                    cogs=humanize_list(results.failed_cogs),
                    modules=humanize_list(results.failed_modules),
                )
            )
        elif results.failed_cogs:
            await ctx.send(
                _(
                    "I tried to delete all non-operational data about that user, "
                    "(that I know how to delete) "
                    "however the following cogs errored: {cogs}.\n"
                    "Please check your logs and contact the creators of "
                    "these cogs and modules.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(cogs=humanize_list(results.failed_cogs))
            )
        elif results.failed_modules:
            await ctx.send(
                _(
                    "I tried to delete all non-operational data about that user, "
                    "(that I know how to delete) "
                    "however the following modules errored: {modules}.\n"
                    "Please check your logs and contact the creators of "
                    "these cogs and modules.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(modules=humanize_list(results.failed_modules))
            )
        else:
            await ctx.send(
                _(
                    "I've deleted all non-operational data about that user "
                    "that I know how to delete."
                )
            )

        if results.unhandled:
            await ctx.send(
                _("{mention} The following cogs did not handle deletion:\n{cogs}.").format(
                    mention=ctx.author.mention, cogs=humanize_list(results.unhandled)
                )
            )

    @mydata_owner_management.command(name="deleteuserasowner")
    async def mydata_user_deletion_by_owner(self, ctx, user_id: int):
        """Delete data [botname] has about a user.

        This will cause the bot to get rid of or disassociate a lot of data about the specified user.
        This may include more than just end user data, including anti abuse records.

        **Arguments:**
        - `<user_id>` - The id of the user whose data would be deleted.
        """
        if not await self.get_serious_confirmation(
            ctx,
            _(
                "This will cause the bot to get rid of or disassociate "
                "a lot of data about the specified user. "
                "This may include more than just end user data, including "
                "anti abuse records."
                "\n\nIf you are sure this is what you intend to do "
                "please respond with the following:"
            ),
        ):
            return
        results = await self.bot.handle_data_deletion_request(requester="owner", user_id=user_id)

        if results.failed_cogs and results.failed_modules:
            await ctx.send(
                _(
                    "I tried to delete all data about that user, "
                    "(that I know how to delete) "
                    "however the following modules errored: {modules}. "
                    "Additionally, the following cogs errored: {cogs}\n"
                    "Please check your logs and contact the creators of "
                    "these cogs and modules.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(
                    cogs=humanize_list(results.failed_cogs),
                    modules=humanize_list(results.failed_modules),
                )
            )
        elif results.failed_cogs:
            await ctx.send(
                _(
                    "I tried to delete all data about that user, "
                    "(that I know how to delete) "
                    "however the following cogs errored: {cogs}.\n"
                    "Please check your logs and contact the creators of "
                    "these cogs and modules.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(cogs=humanize_list(results.failed_cogs))
            )
        elif results.failed_modules:
            await ctx.send(
                _(
                    "I tried to delete all data about that user, "
                    "(that I know how to delete) "
                    "however the following modules errored: {modules}.\n"
                    "Please check your logs and contact the creators of "
                    "these cogs and modules.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(modules=humanize_list(results.failed_modules))
            )
        else:
            await ctx.send(_("I've deleted all data about that user that I know how to delete."))

        if results.unhandled:
            await ctx.send(
                _("{mention} The following cogs did not handle deletion:\n{cogs}.").format(
                    mention=ctx.author.mention, cogs=humanize_list(results.unhandled)
                )
            )

    @commands.group()
    async def embedset(self, ctx: commands.Context):
        """
        Commands for toggling embeds on or off.

        This setting determines whether or not to use embeds as a response to a command (for commands that support it).
        The default is to use embeds.

        The embed settings are checked until the first True/False in this order:

        - In guild context:
          1. Channel override - `[p]embedset channel`
          2. Server command override - `[p]embedset command server`
          3. Server override - `[p]embedset server`
          4. Global command override - `[p]embedset command global`
          5. Global setting  -`[p]embedset global`

        - In DM context:
          1. User override - `[p]embedset user`
          2. Global command override - `[p]embedset command global`
          3. Global setting - `[p]embedset global`
        """

    @embedset.command(name="showsettings")
    async def embedset_showsettings(
        self, ctx: commands.Context, command: CommandConverter = None
    ) -> None:
        """
        Show the current embed settings.

        Provide a command name to check for command specific embed settings.

        **Examples:**
        - `[p]embedset showsettings` - Shows embed settings.
        - `[p]embedset showsettings info` - Also shows embed settings for the 'info' command.
        - `[p]embedset showsettings "ignore list"` - Checking subcommands requires quotes.

        **Arguments:**
        - `[command]` - Checks this command for command specific embed settings.
        """
        # qualified name might be different if alias was passed to this command
        command_name = command and command.qualified_name

        text = _("Embed settings:\n\n")
        global_default = await self.bot._config.embeds()
        text += _("Global default: {value}\n").format(value=global_default)

        if command_name is not None:
            scope = self.bot._config.custom("COMMAND", command_name, 0)
            global_command_setting = await scope.embeds()
            text += _("Global command setting for {command} command: {value}\n").format(
                command=inline(command_name), value=global_command_setting
            )

        if ctx.guild:
            guild_setting = await self.bot._config.guild(ctx.guild).embeds()
            text += _("Guild setting: {value}\n").format(value=guild_setting)

            if command_name is not None:
                scope = self.bot._config.custom("COMMAND", command_name, ctx.guild.id)
                command_setting = await scope.embeds()
                text += _("Server command setting for {command} command: {value}\n").format(
                    command=inline(command_name), value=command_setting
                )

        if ctx.channel:
            channel_setting = await self.bot._config.channel(ctx.channel).embeds()
            text += _("Channel setting: {value}\n").format(value=channel_setting)

        user_setting = await self.bot._config.user(ctx.author).embeds()
        text += _("User setting: {value}").format(value=user_setting)
        await ctx.send(box(text))

    @embedset.command(name="global")
    @commands.is_owner()
    async def embedset_global(self, ctx: commands.Context):
        """
        Toggle the global embed setting.

        This is used as a fallback if the user or guild hasn't set a preference.
        The default is to use embeds.

        To see full evaluation order of embed settings, run `[p]help embedset`.

        **Example:**
        - `[p]embedset global`
        """
        current = await self.bot._config.embeds()
        if current:
            await self.bot._config.embeds.set(False)
            await ctx.send(_("Embeds are now disabled by default."))
        else:
            await self.bot._config.embeds.clear()
            await ctx.send(_("Embeds are now enabled by default."))

    @embedset.command(name="server", aliases=["guild"])
    @commands.guildowner_or_permissions(administrator=True)
    @commands.guild_only()
    async def embedset_guild(self, ctx: commands.Context, enabled: bool = None):
        """
        Set the server's embed setting.

        If set, this is used instead of the global default to determine whether or not to use embeds.
        This is used for all commands done in a server.

        If enabled is left blank, the setting will be unset and the global default will be used instead.

        To see full evaluation order of embed settings, run `[p]help embedset`.

        **Examples:**
        - `[p]embedset server False` - Disables embeds on this server.
        - `[p]embedset server` - Resets value to use global default.

        **Arguments:**
        - `[enabled]` - Whether to use embeds on this server. Leave blank to reset to default.
        """
        if enabled is None:
            await self.bot._config.guild(ctx.guild).embeds.clear()
            await ctx.send(_("Embeds will now fall back to the global setting."))
            return

        await self.bot._config.guild(ctx.guild).embeds.set(enabled)
        await ctx.send(
            _("Embeds are now enabled for this guild.")
            if enabled
            else _("Embeds are now disabled for this guild.")
        )

    @commands.guildowner_or_permissions(administrator=True)
    @embedset.group(name="command", invoke_without_command=True)
    async def embedset_command(
        self, ctx: commands.Context, command: CommandConverter, enabled: bool = None
    ) -> None:
        """
        Sets a command's embed setting.

        If you're the bot owner, this will try to change the command's embed setting globally by default.
        Otherwise, this will try to change embed settings on the current server.

        If enabled is left blank, the setting will be unset.

        To see full evaluation order of embed settings, run `[p]help embedset`.

        **Examples:**
        - `[p]embedset command info` - Clears command specific embed settings for 'info'.
        - `[p]embedset command info False` - Disables embeds for 'info'.
        - `[p]embedset command "ignore list" True` - Quotes are needed for subcommands.

        **Arguments:**
        - `[enabled]` - Whether to use embeds for this command. Leave blank to reset to default.
        """
        # Select the scope based on the author's privileges
        if await ctx.bot.is_owner(ctx.author):
            await self.embedset_command_global(ctx, command, enabled)
        else:
            await self.embedset_command_guild(ctx, command, enabled)

    def _check_if_command_requires_embed_links(self, command_obj: commands.Command) -> None:
        for command in itertools.chain((command_obj,), command_obj.parents):
            if command.requires.bot_perms.embed_links:
                # a slight abuse of this exception to save myself two lines later...
                raise commands.UserFeedbackCheckFailure(
                    _(
                        "The passed command requires Embed Links permission"
                        " and therefore cannot be set to not use embeds."
                    )
                )

    @commands.is_owner()
    @embedset_command.command(name="global")
    async def embedset_command_global(
        self, ctx: commands.Context, command: CommandConverter, enabled: bool = None
    ):
        """
        Sets a command's embed setting globally.

        If set, this is used instead of the global default to determine whether or not to use embeds.

        If enabled is left blank, the setting will be unset.

        To see full evaluation order of embed settings, run `[p]help embedset`.

        **Examples:**
        - `[p]embedset command global info` - Clears command specific embed settings for 'info'.
        - `[p]embedset command global info False` - Disables embeds for 'info'.
        - `[p]embedset command global "ignore list" True` - Quotes are needed for subcommands.

        **Arguments:**
        - `[enabled]` - Whether to use embeds for this command. Leave blank to reset to default.
        """
        self._check_if_command_requires_embed_links(command)
        # qualified name might be different if alias was passed to this command
        command_name = command.qualified_name

        if enabled is None:
            await self.bot._config.custom("COMMAND", command_name, 0).embeds.clear()
            await ctx.send(_("Embeds will now fall back to the global setting."))
            return

        await self.bot._config.custom("COMMAND", command_name, 0).embeds.set(enabled)
        if enabled:
            await ctx.send(
                _("Embeds are now enabled for {command_name} command.").format(
                    command_name=inline(command_name)
                )
            )
        else:
            await ctx.send(
                _("Embeds are now disabled for {command_name} command.").format(
                    command_name=inline(command_name)
                )
            )

    @commands.guild_only()
    @embedset_command.command(name="server", aliases=["guild"])
    async def embedset_command_guild(
        self, ctx: commands.GuildContext, command: CommandConverter, enabled: bool = None
    ):
        """
        Sets a command's embed setting for the current server.

        If set, this is used instead of the server default to determine whether or not to use embeds.

        If enabled is left blank, the setting will be unset and the server default will be used instead.

        To see full evaluation order of embed settings, run `[p]help embedset`.

        **Examples:**
        - `[p]embedset command server info` - Clears command specific embed settings for 'info'.
        - `[p]embedset command server info False` - Disables embeds for 'info'.
        - `[p]embedset command server "ignore list" True` - Quotes are needed for subcommands.

        **Arguments:**
        - `[enabled]` - Whether to use embeds for this command. Leave blank to reset to default.
        """
        self._check_if_command_requires_embed_links(command)
        # qualified name might be different if alias was passed to this command
        command_name = command.qualified_name

        if enabled is None:
            await self.bot._config.custom("COMMAND", command_name, ctx.guild.id).embeds.clear()
            await ctx.send(_("Embeds will now fall back to the server setting."))
            return

        await self.bot._config.custom("COMMAND", command_name, ctx.guild.id).embeds.set(enabled)
        if enabled:
            await ctx.send(
                _("Embeds are now enabled for {command_name} command.").format(
                    command_name=inline(command_name)
                )
            )
        else:
            await ctx.send(
                _("Embeds are now disabled for {command_name} command.").format(
                    command_name=inline(command_name)
                )
            )

    @embedset.command(name="channel")
    @commands.guildowner_or_permissions(administrator=True)
    @commands.guild_only()
    async def embedset_channel(
        self,
        ctx: commands.Context,
        channel: Union[
            discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.ForumChannel
        ],
        enabled: bool = None,
    ):
        """
        Set's a channel's embed setting.

        If set, this is used instead of the guild and command defaults to determine whether or not to use embeds.
        This is used for all commands done in a channel.

        If enabled is left blank, the setting will be unset and the guild default will be used instead.

        To see full evaluation order of embed settings, run `[p]help embedset`.

        **Examples:**
        - `[p]embedset channel #text-channel False` - Disables embeds in the #text-channel.
        - `[p]embedset channel #forum-channel disable` - Disables embeds in the #forum-channel.
        - `[p]embedset channel #text-channel` - Resets value to use guild default in the #text-channel.

        **Arguments:**
            - `<channel>` - The text, voice, stage, or forum channel to set embed setting for.
            - `[enabled]` - Whether to use embeds in this channel. Leave blank to reset to default.
        """
        if enabled is None:
            await self.bot._config.channel(channel).embeds.clear()
            await ctx.send(_("Embeds will now fall back to the global setting."))
            return

        await self.bot._config.channel(channel).embeds.set(enabled)
        await ctx.send(
            _("Embeds are now {} for this channel.").format(
                _("enabled") if enabled else _("disabled")
            )
        )

    @embedset.command(name="user")
    async def embedset_user(self, ctx: commands.Context, enabled: bool = None):
        """
        Sets personal embed setting for DMs.

        If set, this is used instead of the global default to determine whether or not to use embeds.
        This is used for all commands executed in a DM with the bot.

        If enabled is left blank, the setting will be unset and the global default will be used instead.

        To see full evaluation order of embed settings, run `[p]help embedset`.

        **Examples:**
        - `[p]embedset user False` - Disables embeds in your DMs.
        - `[p]embedset user` - Resets value to use global default.

        **Arguments:**
        - `[enabled]` - Whether to use embeds in your DMs. Leave blank to reset to default.
        """
        if enabled is None:
            await self.bot._config.user(ctx.author).embeds.clear()
            await ctx.send(_("Embeds will now fall back to the global setting."))
            return

        await self.bot._config.user(ctx.author).embeds.set(enabled)
        await ctx.send(
            _("Embeds are now enabled for you in DMs.")
            if enabled
            else _("Embeds are now disabled for you in DMs.")
        )

    @commands.command()
    @commands.is_owner()
    async def traceback(self, ctx: commands.Context, public: bool = False):
        """Sends to the owner the last command exception that has occurred.

        If public (yes is specified), it will be sent to the chat instead.

        Warning: Sending the traceback publicly can accidentally reveal sensitive information about your computer or configuration.

        **Examples:**
        - `[p]traceback` - Sends the traceback to your DMs.
        - `[p]traceback True` - Sends the last traceback in the current context.

        **Arguments:**
        - `[public]` - Whether to send the traceback to the current context. Leave blank to send to your DMs.
        """
        channel = ctx.channel if public else ctx.author

        if self.bot._last_exception:
            try:
                await self.bot.send_interactive(
                    channel,
                    pagify(self.bot._last_exception, shorten_by=10),
                    user=ctx.author,
                    box_lang="py",
                )
            except discord.HTTPException:
                await ctx.channel.send(
                    "I couldn't send the traceback message to you in DM. "
                    "Either you blocked me or you disabled DMs in this server."
                )
                return
            if not public:
                await ctx.tick()
        else:
            await ctx.send(_("No exception has occurred yet."))

    @commands.command()
    @commands.check(CoreLogic._can_get_invite_url)
    async def invite(self, ctx):
        """Shows [botname]'s invite url.

        This will always send the invite to DMs to keep it private.

        This command is locked to the owner unless `[p]inviteset public` is set to True.

        **Example:**
        - `[p]invite`
        """
        message = await self.bot.get_invite_url()
        if (admin := self.bot.get_cog("Admin")) and await admin.config.serverlocked():
            message += "\n\n" + warning(
                _(
                    "This bot is currently **serverlocked**, meaning that it is locked "
                    "to its current servers and will leave any server it joins."
                )
            )
        try:
            await ctx.author.send(message)
            await ctx.tick()
        except discord.errors.Forbidden:
            await ctx.send(
                "I couldn't send the invite message to you in DM. "
                "Either you blocked me or you disabled DMs in this server."
            )

    @commands.group()
    @commands.is_owner()
    async def inviteset(self, ctx):
        """Commands to setup [botname]'s invite settings."""
        pass

    @inviteset.command()
    async def public(self, ctx, confirm: bool = False):
        """
        Toggles if `[p]invite` should be accessible for the average user.

        The bot must be made into a `Public bot` in the developer dashboard for public invites to work.

        **Example:**
        - `[p]inviteset public yes` - Toggles the public invite setting.

        **Arguments:**
        - `[confirm]` - Required to set to public. Not required to toggle back to private.
        """
        if await self.bot._config.invite_public():
            await self.bot._config.invite_public.set(False)
            await ctx.send("The invite is now private.")
            return
        app_info = await self.bot.application_info()
        if not app_info.bot_public:
            await ctx.send(
                "I am not a public bot. That means that nobody except "
                "you can invite me on new servers.\n\n"
                "You can change this by ticking `Public bot` in "
                "your token settings: "
                "https://discord.com/developers/applications/{0}/bot".format(self.bot.user.id)
            )
            return
        if not confirm:
            await ctx.send(
                "You're about to make the `{0}invite` command public. "
                "All users will be able to invite me on their server.\n\n"
                "If you agree, you can type `{0}inviteset public yes`.".format(ctx.clean_prefix)
            )
        else:
            await self.bot._config.invite_public.set(True)
            await ctx.send("The invite command is now public.")

    @inviteset.command()
    async def perms(self, ctx, level: int):
        """
        Make the bot create its own role with permissions on join.

        The bot will create its own role with the desired permissions when it joins a new server. This is a special role that can't be deleted or removed from the bot.

        For that, you need to provide a valid permissions level.
        You can generate one here: https://discordapi.com/permissions.html

        Please note that you might need two factor authentication for some permissions.

        **Example:**
        - `[p]inviteset perms 134217728` - Adds a "Manage Nicknames" permission requirement to the invite.

        **Arguments:**
        - `<level>` - The permission level to require for the bot in the generated invite.
        """
        await self.bot._config.invite_perm.set(level)
        await ctx.send("The new permissions level has been set.")

    @inviteset.command()
    async def commandscope(self, ctx: commands.Context):
        """
        Add the `applications.commands` scope to your invite URL.

        This allows the usage of slash commands on the servers that invited your bot with that scope.

        Note that previous servers that invited the bot without the scope cannot have slash commands, they will have to invite the bot a second time.
        """
        enabled = not await self.bot._config.invite_commands_scope()
        await self.bot._config.invite_commands_scope.set(enabled)
        if enabled is True:
            await ctx.send(
                _("The `applications.commands` scope has been added to the invite URL.")
            )
        else:
            await ctx.send(
                _("The `applications.commands` scope has been removed from the invite URL.")
            )

    @commands.command()
    @commands.is_owner()
    async def leave(self, ctx: commands.Context, *servers: GuildConverter):
        """
        Leaves servers.

        If no server IDs are passed the local server will be left instead.

        Note: This command is interactive.

        **Examples:**
        - `[p]leave` - Leave the current server.
        - `[p]leave "Red - Discord Bot"` - Quotes are necessary when there are spaces in the name.
        - `[p]leave 133049272517001216 240154543684321280` - Leaves multiple servers, using IDs.

        **Arguments:**
        - `[servers...]` - The servers to leave. When blank, attempts to leave the current server.
        """
        guilds = servers
        if ctx.guild is None and not guilds:
            return await ctx.send(_("You need to specify at least one server ID."))

        leaving_local_guild = not guilds
        number = len(guilds)

        if leaving_local_guild:
            guilds = (ctx.guild,)
            msg = (
                _("You haven't passed any server ID. Do you want me to leave this server?")
                + " (yes/no)"
            )
        else:
            if number > 1:
                msg = (
                    _("Are you sure you want me to leave these servers?")
                    + " (yes/no):\n"
                    + "\n".join(f"- {guild.name} (`{guild.id}`)" for guild in guilds)
                )
            else:
                msg = (
                    _("Are you sure you want me to leave this server?")
                    + " (yes/no):\n"
                    + f"- {guilds[0].name} (`{guilds[0].id}`)"
                )

        for guild in guilds:
            if guild.owner.id == ctx.me.id:
                return await ctx.send(
                    _("I cannot leave the server `{server_name}`: I am the owner of it.").format(
                        server_name=guild.name
                    )
                )

        for page in pagify(msg):
            await ctx.send(page)
        pred = MessagePredicate.yes_or_no(ctx)
        try:
            await self.bot.wait_for("message", check=pred, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send(_("Response timed out."))
            return
        else:
            if pred.result is True:
                if leaving_local_guild is True:
                    await ctx.send(_("Alright. Bye :wave:"))
                else:
                    if number > 1:
                        await ctx.send(
                            _("Alright. Leaving {number} servers...").format(number=number)
                        )
                    else:
                        await ctx.send(_("Alright. Leaving one server..."))
                for guild in guilds:
                    log.debug("Leaving guild '%s' (%s)", guild.name, guild.id)
                    await guild.leave()
            else:
                if leaving_local_guild is True:
                    await ctx.send(_("Alright, I'll stay then. :)"))
                else:
                    if number > 1:
                        await ctx.send(_("Alright, I'm not leaving those servers."))
                    else:
                        await ctx.send(_("Alright, I'm not leaving that server."))

    @commands.command()
    @commands.is_owner()
    async def servers(self, ctx: commands.Context):
        """
        Lists the servers [botname] is currently in.

        Note: This command is interactive.
        """
        guilds = sorted(self.bot.guilds, key=lambda s: s.name.lower())
        msg = "\n".join(
            f"{discord.utils.escape_markdown(guild.name)} (`{guild.id}`)\n" for guild in guilds
        )

        pages = list(pagify(msg, ["\n"], page_length=1000))

        if len(pages) == 1:
            await ctx.send(pages[0])
        else:
            await menu(ctx, pages)

    @commands.command(require_var_positional=True)
    @commands.is_owner()
    async def load(self, ctx: commands.Context, *cogs: str):
        """Loads cog packages from the local paths and installed cogs.

        See packages available to load with `[p]cogs`.

        Additional cogs can be added using Downloader, or from local paths using `[p]addpath`.

        **Examples:**
        - `[p]load general` - Loads the `general` cog.
        - `[p]load admin mod mutes` - Loads multiple cogs.

        **Arguments:**
        - `<cogs...>` - The cog packages to load.
        """
        cogs = tuple(map(lambda cog: cog.rstrip(","), cogs))
        async with ctx.typing():
            outcomes = await self._load(cogs)

        output = []

        if loaded := outcomes["loaded_packages"]:
            loaded_packages = humanize_list([inline(package) for package in loaded])
            formed = _("Loaded {packs}.").format(packs=loaded_packages)
            output.append(formed)

        if already_loaded := outcomes["alreadyloaded_packages"]:
            if len(already_loaded) == 1:
                formed = _("The following package is already loaded: {pack}").format(
                    pack=inline(already_loaded[0])
                )
            else:
                formed = _("The following packages are already loaded: {packs}").format(
                    packs=humanize_list([inline(package) for package in already_loaded])
                )
            output.append(formed)

        if failed := outcomes["failed_packages"]:
            if len(failed) == 1:
                formed = _(
                    "Failed to load the following package: {pack}."
                    "\nCheck your console or logs for details."
                ).format(pack=inline(failed[0]))
            else:
                formed = _(
                    "Failed to load the following packages: {packs}"
                    "\nCheck your console or logs for details."
                ).format(packs=humanize_list([inline(package) for package in failed]))
            output.append(formed)

        if invalid_pkg_names := outcomes["invalid_pkg_names"]:
            if len(invalid_pkg_names) == 1:
                formed = _(
                    "The following name is not a valid package name: {pack}\n"
                    "Package names cannot start with a number"
                    " and can only contain ascii numbers, letters, and underscores."
                ).format(pack=inline(invalid_pkg_names[0]))
            else:
                formed = _(
                    "The following names are not valid package names: {packs}\n"
                    "Package names cannot start with a number"
                    " and can only contain ascii numbers, letters, and underscores."
                ).format(packs=humanize_list([inline(package) for package in invalid_pkg_names]))
            output.append(formed)

        if not_found := outcomes["notfound_packages"]:
            if len(not_found) == 1:
                formed = _("The following package was not found in any cog path: {pack}.").format(
                    pack=inline(not_found[0])
                )
            else:
                formed = _(
                    "The following packages were not found in any cog path: {packs}"
                ).format(packs=humanize_list([inline(package) for package in not_found]))
            output.append(formed)

        if failed_with_reason := outcomes["failed_with_reason_packages"]:
            reasons = "\n".join([f"`{x}`: {y}" for x, y in failed_with_reason.items()])
            if len(failed_with_reason) == 1:
                formed = _(
                    "This package could not be loaded for the following reason:\n\n{reason}"
                ).format(reason=reasons)
            else:
                formed = _(
                    "These packages could not be loaded for the following reasons:\n\n{reasons}"
                ).format(reasons=reasons)
            output.append(formed)

        if repos_with_shared_libs := outcomes["repos_with_shared_libs"]:
            if len(repos_with_shared_libs) == 1:
                formed = _(
                    "**WARNING**: The following repo is using shared libs"
                    " which are marked for removal in the future: {repo}.\n"
                    "You should inform maintainer of the repo about this message."
                ).format(repo=inline(repos_with_shared_libs.pop()))
            else:
                formed = _(
                    "**WARNING**: The following repos are using shared libs"
                    " which are marked for removal in the future: {repos}.\n"
                    "You should inform maintainers of these repos about this message."
                ).format(repos=humanize_list([inline(repo) for repo in repos_with_shared_libs]))
            output.append(formed)

        if output:
            total_message = "\n\n".join(output)
            for page in pagify(
                total_message, delims=["\n", ", "], priority=True, page_length=1500
            ):
                if page.startswith(", "):
                    page = page[2:]
                await ctx.send(page)

    @commands.command(require_var_positional=True)
    @commands.is_owner()
    async def unload(self, ctx: commands.Context, *cogs: str):
        """Unloads previously loaded cog packages.

        See packages available to unload with `[p]cogs`.

        **Examples:**
        - `[p]unload general` - Unloads the `general` cog.
        - `[p]unload admin mod mutes` - Unloads multiple cogs.

        **Arguments:**
        - `<cogs...>` - The cog packages to unload.
        """
        cogs = tuple(map(lambda cog: cog.rstrip(","), cogs))
        outcomes = await self._unload(cogs)

        output = []

        if unloaded := outcomes["unloaded_packages"]:
            if len(unloaded) == 1:
                formed = _("The following package was unloaded: {pack}.").format(
                    pack=inline(unloaded[0])
                )
            else:
                formed = _("The following packages were unloaded: {packs}.").format(
                    packs=humanize_list([inline(package) for package in unloaded])
                )
            output.append(formed)

        if failed := outcomes["notloaded_packages"]:
            if len(failed) == 1:
                formed = _("The following package was not loaded: {pack}.").format(
                    pack=inline(failed[0])
                )
            else:
                formed = _("The following packages were not loaded: {packs}.").format(
                    packs=humanize_list([inline(package) for package in failed])
                )
            output.append(formed)

        if output:
            total_message = "\n\n".join(output)
            for page in pagify(total_message):
                await ctx.send(page)

    @commands.command(require_var_positional=True)
    @commands.is_owner()
    async def reload(self, ctx: commands.Context, *cogs: str):
        """Reloads cog packages.

        This will unload and then load the specified cogs.

        Cogs that were not loaded will only be loaded.

        **Examples:**
        - `[p]reload general` - Unloads then loads the `general` cog.
        - `[p]reload admin mod mutes` - Unloads then loads multiple cogs.

        **Arguments:**
        - `<cogs...>` - The cog packages to reload.
        """
        cogs = tuple(map(lambda cog: cog.rstrip(","), cogs))
        async with ctx.typing():
            outcomes = await self._reload(cogs)

        output = []

        if loaded := outcomes["loaded_packages"]:
            loaded_packages = humanize_list([inline(package) for package in loaded])
            formed = _("Reloaded {packs}.").format(packs=loaded_packages)
            output.append(formed)

        if failed := outcomes["failed_packages"]:
            if len(failed) == 1:
                formed = _(
                    "Failed to reload the following package: {pack}."
                    "\nCheck your console or logs for details."
                ).format(pack=inline(failed[0]))
            else:
                formed = _(
                    "Failed to reload the following packages: {packs}"
                    "\nCheck your console or logs for details."
                ).format(packs=humanize_list([inline(package) for package in failed]))
            output.append(formed)

        if invalid_pkg_names := outcomes["invalid_pkg_names"]:
            if len(invalid_pkg_names) == 1:
                formed = _(
                    "The following name is not a valid package name: {pack}\n"
                    "Package names cannot start with a number"
                    " and can only contain ascii numbers, letters, and underscores."
                ).format(pack=inline(invalid_pkg_names[0]))
            else:
                formed = _(
                    "The following names are not valid package names: {packs}\n"
                    "Package names cannot start with a number"
                    " and can only contain ascii numbers, letters, and underscores."
                ).format(packs=humanize_list([inline(package) for package in invalid_pkg_names]))
            output.append(formed)

        if not_found := outcomes["notfound_packages"]:
            if len(not_found) == 1:
                formed = _("The following package was not found in any cog path: {pack}.").format(
                    pack=inline(not_found[0])
                )
            else:
                formed = _(
                    "The following packages were not found in any cog path: {packs}"
                ).format(packs=humanize_list([inline(package) for package in not_found]))
            output.append(formed)

        if failed_with_reason := outcomes["failed_with_reason_packages"]:
            reasons = "\n".join([f"`{x}`: {y}" for x, y in failed_with_reason.items()])
            if len(failed_with_reason) == 1:
                formed = _(
                    "This package could not be reloaded for the following reason:\n\n{reason}"
                ).format(reason=reasons)
            else:
                formed = _(
                    "These packages could not be reloaded for the following reasons:\n\n{reasons}"
                ).format(reasons=reasons)
            output.append(formed)

        if repos_with_shared_libs := outcomes["repos_with_shared_libs"]:
            if len(repos_with_shared_libs) == 1:
                formed = _(
                    "**WARNING**: The following repo is using shared libs"
                    " which are marked for removal in the future: {repo}.\n"
                    "You should inform maintainers of these repos about this message."
                ).format(repo=inline(repos_with_shared_libs.pop()))
            else:
                formed = _(
                    "**WARNING**: The following repos are using shared libs"
                    " which are marked for removal in the future: {repos}.\n"
                    "You should inform maintainers of these repos about this message."
                ).format(repos=humanize_list([inline(repo) for repo in repos_with_shared_libs]))
            output.append(formed)

        if output:
            total_message = "\n\n".join(output)
            for page in pagify(total_message):
                await ctx.send(page)

    @staticmethod
    def _is_submodule(parent: str, child: str):
        return parent == child or child.startswith(parent + ".")

    # TODO: Guild owner permissions for guild scope slash commands and syncing?
    @commands.group()
    @commands.is_owner()
    async def slash(self, ctx: commands.Context):
        """Base command for managing what application commands are able to be used on [botname]."""

    @slash.command(name="enable")
    async def slash_enable(
        self,
        ctx: commands.Context,
        command_name: str,
        command_type: Literal["slash", "message", "user"] = "slash",
    ):
        """Marks an application command as being enabled, allowing it to be added to the bot.

        See commands available to enable with `[p]slash list`.

        This command does NOT sync the enabled commands with Discord, that must be done manually with `[p]slash sync` for commands to appear in users' clients.

        **Arguments:**
            - `<command_name>` - The command name to enable. Only the top level name of a group command should be used.
            - `[command_type]` - What type of application command to enable. Must be one of `slash`, `message`, or `user`. Defaults to `slash`.
        """
        command_type = command_type.lower().strip()

        if command_type == "slash":
            raw_type = discord.AppCommandType.chat_input
            command_list = self.bot.tree._disabled_global_commands
            key = command_name
        elif command_type == "message":
            raw_type = discord.AppCommandType.message
            command_list = self.bot.tree._disabled_context_menus
            key = (command_name, None, raw_type.value)
        elif command_type == "user":
            raw_type = discord.AppCommandType.user
            command_list = self.bot.tree._disabled_context_menus
            key = (command_name, None, raw_type.value)
        else:
            await ctx.send(_("Command type must be one of `slash`, `message`, or `user`."))
            return

        current_settings = await self.bot.list_enabled_app_commands()
        current_settings = current_settings[command_type]

        if command_name in current_settings:
            await ctx.send(_("That application command is already enabled."))
            return

        if key not in command_list:
            await ctx.send(
                _(
                    "That application command could not be found. "
                    "Use `{prefix}slash list` to see all application commands. "
                    "You may need to double check the command type."
                ).format(prefix=ctx.prefix)
            )
            return

        try:
            await self.bot.enable_app_command(command_name, raw_type)
        except app_commands.CommandLimitReached:
            await ctx.send(_("The command limit has been reached. Disable a command first."))
            return

        await self.bot.tree.red_check_enabled()
        await ctx.send(
            _("Enabled {command_type} application command `{command_name}`").format(
                command_type=command_type, command_name=command_name
            )
        )

    @slash.command(name="disable")
    async def slash_disable(
        self,
        ctx: commands.Context,
        command_name: str,
        command_type: Literal["slash", "message", "user"] = "slash",
    ):
        """Marks an application command as being disabled, preventing it from being added to the bot.

        See commands available to disable with `[p]slash list`.

        This command does NOT sync the enabled commands with Discord, that must be done manually with `[p]slash sync` for commands to appear in users' clients.

        **Arguments:**
            - `<command_name>` - The command name to disable. Only the top level name of a group command should be used.
            - `[command_type]` - What type of application command to disable. Must be one of `slash`, `message`, or `user`. Defaults to `slash`.
        """
        command_type = command_type.lower().strip()

        if command_type == "slash":
            raw_type = discord.AppCommandType.chat_input
        elif command_type == "message":
            raw_type = discord.AppCommandType.message
        elif command_type == "user":
            raw_type = discord.AppCommandType.user
        else:
            await ctx.send(_("Command type must be one of `slash`, `message`, or `user`."))
            return

        existing = self.bot.tree.get_command(command_name, type=raw_type)
        if existing is not None and existing.extras.get("red_force_enable", False):
            await ctx.send(
                _(
                    "That application command has been set as required for the cog to function "
                    "by the author, and cannot be disabled. "
                    "The cog must be unloaded to remove the command."
                )
            )
            return

        current_settings = await self.bot.list_enabled_app_commands()
        current_settings = current_settings[command_type]

        if command_name not in current_settings:
            await ctx.send(_("That application command is already disabled or does not exist."))
            return

        await self.bot.disable_app_command(command_name, raw_type)
        await self.bot.tree.red_check_enabled()
        await ctx.send(
            _("Disabled {command_type} application command `{command_name}`").format(
                command_type=command_type, command_name=command_name
            )
        )

    @slash.command(name="enablecog", require_var_positional=True)
    @commands.max_concurrency(1, wait=True)
    async def slash_enablecog(self, ctx: commands.Context, *cog_names: str):
        """Marks all application commands in a cog as being enabled, allowing them to be added to the bot.

        See a list of cogs with application commands with `[p]slash list`.

        This command does NOT sync the enabled commands with Discord, that must be done manually with `[p]slash sync` for commands to appear in users' clients.

        **Arguments:**
            - `<cog_names>` - The cogs to enable commands from. This argument is case sensitive.
        """
        enabled_commands = await self.bot.list_enabled_app_commands()
        to_add_slash = []
        to_add_message = []
        to_add_user = []

        successful_cogs = set()
        # Fetch a list of command names to enable
        for name, com in self.bot.tree._disabled_global_commands.items():
            for cog_name in cog_names:
                if self._is_submodule(cog_name, com.module):
                    to_add_slash.append(name)
                    successful_cogs.add(cog_name)
        for key, com in self.bot.tree._disabled_context_menus.items():
            for cog_name in cog_names:
                if self._is_submodule(cog_name, com.module):
                    name, guild_id, com_type = key
                    com_type = discord.AppCommandType(com_type)
                    if com_type is discord.AppCommandType.message:
                        to_add_message.append(name)
                        successful_cogs.add(cog_name)
                    elif com_type is discord.AppCommandType.user:
                        to_add_user.append(name)
                        successful_cogs.add(cog_name)
        failed_cogs = set(cog_names) - successful_cogs

        # Check that we are going to enable at least one command, for user feedback
        if not (to_add_slash or to_add_message or to_add_user):
            await ctx.send(
                _(
                    "Couldn't find any disabled commands from {cog_names}. Use `{prefix}slash list` to see all cogs with application commands"
                ).format(
                    cog_names=humanize_list([inline(name) for name in failed_cogs]),
                    prefix=ctx.clean_prefix,
                )
            )
            return

        SLASH_CAP = 100
        CONTEXT_CAP = 5
        total_slash = len(enabled_commands["slash"]) + len(to_add_slash)
        total_message = len(enabled_commands["message"]) + len(to_add_message)
        total_user = len(enabled_commands["user"]) + len(to_add_user)

        # If enabling would exceed any limit, exit early to not enable only a subset
        if total_slash > SLASH_CAP:
            await ctx.send(
                _(
                    "Enabling all application commands from these cogs would enable a total of {count} "
                    "commands, exceeding the {cap} command limit for slash commands. "
                    "Disable some commands first."
                ).format(count=total_slash, cap=SLASH_CAP)
            )
            return
        if total_message > CONTEXT_CAP:
            await ctx.send(
                _(
                    "Enabling all application commands from these cogs would enable a total of {count} "
                    "commands, exceeding the {cap} command limit for message commands. "
                    "Disable some commands first."
                ).format(count=total_message, cap=CONTEXT_CAP)
            )
            return
        if total_user > CONTEXT_CAP:
            await ctx.send(
                _(
                    "Enabling all application commands from these cogs would enable a total of {count} "
                    "commands, exceeding the {cap} command limit for user commands. "
                    "Disable some commands first."
                ).format(count=total_user, cap=CONTEXT_CAP)
            )
            return

        # Enable the cogs
        for name in to_add_slash:
            await self.bot.enable_app_command(name, discord.AppCommandType.chat_input)
        for name in to_add_message:
            await self.bot.enable_app_command(name, discord.AppCommandType.message)
        for name in to_add_user:
            await self.bot.enable_app_command(name, discord.AppCommandType.user)

        # Update the tree with the new list of enabled cogs
        await self.bot.tree.red_check_enabled()

        # Output processing
        count = len(to_add_slash) + len(to_add_message) + len(to_add_user)
        names = to_add_slash.copy()
        names.extend(to_add_message)
        names.extend(to_add_user)
        formatted_names = humanize_list([inline(name) for name in names])
        formatted_successful_cogs = humanize_list([inline(name) for name in successful_cogs])

        output = _("Enabled {count} commands from {cog_names}:\n{names}").format(
            count=count, cog_names=formatted_successful_cogs, names=formatted_names
        )
        if failed_cogs:
            output += "\n\n"
            output += _(
                "Couldn't find any disabled commands from {cog_names}. Use `{prefix}slash list` to see all cogs with application commands."
            ).format(
                cog_names=humanize_list([inline(name) for name in failed_cogs]),
                prefix=ctx.clean_prefix,
            )
        for page in pagify(output):
            await ctx.send(page)

    @slash.command(name="disablecog", require_var_positional=True)
    async def slash_disablecog(self, ctx: commands.Context, *cog_names: str):
        """Marks all application commands in a cog as being disabled, preventing them from being added to the bot.

        See a list of cogs with application commands with `[p]slash list`.

        This command does NOT sync the enabled commands with Discord, that must be done manually with `[p]slash sync` for commands to appear in users' clients.

        **Arguments:**
            - `<cog_names>` - The cogs to disable commands from. This argument is case sensitive.
        """
        removed = []
        removed_cogs = set()
        for name, com in self.bot.tree._global_commands.items():
            for cog_name in cog_names:
                if self._is_submodule(cog_name, com.module):
                    await self.bot.disable_app_command(name, discord.AppCommandType.chat_input)
                    removed.append(name)
                    removed_cogs.add(cog_name)
        for key, com in self.bot.tree._context_menus.items():
            for cog_name in cog_names:
                if self._is_submodule(cog_name, com.module):
                    name, guild_id, com_type = key
                    await self.bot.disable_app_command(name, discord.AppCommandType(com_type))
                    removed.append(name)
                    removed_cogs.add(cog_name)
        failed_cogs = set(cog_names) - removed_cogs

        if not removed:
            await ctx.send(
                _(
                    "Couldn't find any enabled commands from {cog_names}. Use `{prefix}slash list` to see all cogs with application commands."
                ).format(
                    cog_names=humanize_list([inline(name) for name in failed_cogs]),
                    prefix=ctx.clean_prefix,
                )
            )
            return

        await self.bot.tree.red_check_enabled()
        formatted_names = humanize_list([inline(name) for name in removed])
        formatted_removed_cogs = humanize_list([inline(name) for name in removed_cogs])

        output = _("Disabled {count} commands from {cog_names}:\n{names}").format(
            count=len(removed),
            cog_names=formatted_removed_cogs,
            names=formatted_names,
        )
        if failed_cogs:
            output += "\n\n"
            output += _(
                "Couldn't find any enabled commands from {cog_names}. Use `{prefix}slash list` to see all cogs with application commands."
            ).format(
                cog_names=humanize_list([inline(name) for name in failed_cogs]),
                prefix=ctx.clean_prefix,
            )
        for page in pagify(output):
            await ctx.send(page)

    @slash.command(name="list")
    async def slash_list(self, ctx: commands.Context):
        """List the slash commands the bot can see, and whether or not they are enabled.

        This command shows the state that will be changed to when `[p]slash sync` is run.
        Commands from the same cog are grouped, with the cog name as the header.

        The prefix denotes the state of the command:
        - Commands starting with `- ` have not yet been enabled.
        - Commands starting with `+ ` have been manually enabled.
        - Commands starting with `++` have been enabled by the cog author, and cannot be disabled.
        """
        cog_commands = defaultdict(list)
        slash_command_names = set()
        message_command_names = set()
        user_command_names = set()

        for command in self.bot.tree._global_commands.values():
            module = command.module
            if "." in module:
                module = module[: module.find(".")]
            cog_commands[module].append(
                (
                    command.name,
                    discord.AppCommandType.chat_input,
                    True,
                    command.extras.get("red_force_enable", False),
                )
            )
            slash_command_names.add(command.name)
        for command in self.bot.tree._disabled_global_commands.values():
            module = command.module
            if "." in module:
                module = module[: module.find(".")]
            cog_commands[module].append(
                (
                    command.name,
                    discord.AppCommandType.chat_input,
                    False,
                    command.extras.get("red_force_enable", False),
                )
            )
        for key, command in self.bot.tree._context_menus.items():
            # Filter out guild context menus
            if key[1] is not None:
                continue
            module = command.module
            if "." in module:
                module = module[: module.find(".")]
            cog_commands[module].append(
                (command.name, command.type, True, command.extras.get("red_force_enable", False))
            )
            if command.type is discord.AppCommandType.message:
                message_command_names.add(command.name)
            elif command.type is discord.AppCommandType.user:
                user_command_names.add(command.name)
        for command in self.bot.tree._disabled_context_menus.values():
            module = command.module
            if "." in module:
                module = module[: module.find(".")]
            cog_commands[module].append(
                (command.name, command.type, False, command.extras.get("red_force_enable", False))
            )

        # Commands added with evals will come from __main__, make them unknown instead
        if "__main__" in cog_commands:
            main_data = cog_commands["__main__"]
            del cog_commands["__main__"]
            cog_commands["(unknown)"] = main_data

        # Commands enabled but unloaded won't appear unless accounted for
        enabled_commands = await self.bot.list_enabled_app_commands()
        unknown_slash = set(enabled_commands["slash"]) - slash_command_names
        unknown_message = set(enabled_commands["message"]) - message_command_names
        unknown_user = set(enabled_commands["user"]) - user_command_names

        unknown_slash = [
            (n, discord.AppCommandType.chat_input, True, False) for n in unknown_slash
        ]
        unknown_message = [
            (n, discord.AppCommandType.message, True, False) for n in unknown_message
        ]
        unknown_user = [(n, discord.AppCommandType.user, True, False) for n in unknown_user]

        cog_commands["(unknown)"].extend(unknown_slash)
        cog_commands["(unknown)"].extend(unknown_message)
        cog_commands["(unknown)"].extend(unknown_user)
        # Hide it when empty
        if not cog_commands["(unknown)"]:
            del cog_commands["(unknown)"]

        if not cog_commands:
            await ctx.send(_("There are no application commands to list."))
            return

        msg = ""
        for cog in sorted(cog_commands.keys()):
            msg += cog + "\n"
            for name, raw_command_type, enabled, forced in sorted(
                cog_commands[cog], key=lambda v: v[0]
            ):
                diff = "-  "
                if forced:
                    diff = "++ "
                elif enabled:
                    diff = "+  "
                command_type = "unknown"
                if raw_command_type is discord.AppCommandType.chat_input:
                    command_type = "slash"
                elif raw_command_type is discord.AppCommandType.message:
                    command_type = "message"
                elif raw_command_type is discord.AppCommandType.user:
                    command_type = "user"
                msg += diff + command_type.ljust(7) + " | " + name + "\n"
            msg += "\n"

        pages = pagify(msg, delims=["\n\n", "\n"], shorten_by=12)
        pages = [box(page, lang="diff") for page in pages]
        await menu(ctx, pages)

    @slash.command(name="sync")
    @commands.cooldown(1, 60)
    async def slash_sync(self, ctx: commands.Context, guild: discord.Guild = None):
        """Syncs the slash settings to discord.

        Settings from `[p]slash list` will be synced with discord, changing what commands appear for users.
        This should be run sparingly, make all necessary changes before running this command.

        **Arguments:**
            - `[guild]` - If provided, syncs commands for that guild. Otherwise, syncs global commands.
        """
        # This command should not be automated due to the restrictive rate limits associated with it.
        if ctx.assume_yes:
            return
        commands = []
        async with ctx.typing():
            try:
                commands = await self.bot.tree.sync(guild=guild)
            except discord.Forbidden as e:
                # Should only be possible when syncing a guild, but just in case
                if not guild:
                    raise e
                await ctx.send(
                    _(
                        "I need the `applications.commands` scope in this server to be able to do that. "
                        "You can tell the bot to add that scope to invite links using `{prefix}inviteset commandscope`, "
                        "and can then run `{prefix}invite` to get an invite that will give the bot the scope. "
                        "You do not need to kick the bot to enable the scope, just use that invite to "
                        "re-auth the bot with the scope enabled."
                    ).format(prefix=ctx.prefix)
                )
                return
            except Exception as e:
                raise e
        await ctx.send(_("Synced {count} commands.").format(count=len(commands)))

    @slash_sync.error
    async def slash_sync_error(self, ctx: commands.Context, error: commands.CommandError):
        """Custom cooldown error message."""
        if not isinstance(error, commands.CommandOnCooldown):
            return await ctx.bot.on_command_error(ctx, error, unhandled_by_cog=True)
        if ctx.bot._bypass_cooldowns and ctx.author.id in ctx.bot.owner_ids:
            ctx.command.reset_cooldown(ctx)
            new_ctx = await ctx.bot.get_context(ctx.message)
            await ctx.bot.invoke(new_ctx)
            return
        await ctx.send(
            _(
                "You seem to be attempting to sync after recently syncing. Discord does not like it "
                "when bots sync more often than necessary, so this command has a cooldown. You "
                "should enable/disable all commands you want to change first, and run this command "
                "one time only after all changes have been made. "
            )
        )

    @commands.command(name="shutdown")
    @commands.is_owner()
    async def _shutdown(self, ctx: commands.Context, silently: bool = False):
        """Shuts down the bot.

        Allows [botname] to shut down gracefully.

        This is the recommended method for shutting down the bot.

        **Examples:**
        - `[p]shutdown`
        - `[p]shutdown True` - Shutdowns silently.

        **Arguments:**
        - `[silently]` - Whether to skip sending the shutdown message. Defaults to False.
        """
        wave = "\N{WAVING HAND SIGN}"
        skin = "\N{EMOJI MODIFIER FITZPATRICK TYPE-3}"
        with contextlib.suppress(discord.HTTPException):
            if not silently:
                await ctx.send(_("Shutting down... ") + wave + skin)
        await ctx.bot.shutdown()

    @commands.command(name="restart")
    @commands.is_owner()
    async def _restart(self, ctx: commands.Context, silently: bool = False):
        """Attempts to restart [botname].

        Makes [botname] quit with exit code 26.
        The restart is not guaranteed: it must be dealt with by the process manager in use.

        **Examples:**
        - `[p]restart`
        - `[p]restart True` - Restarts silently.

        **Arguments:**
        - `[silently]` - Whether to skip sending the restart message. Defaults to False.
        """
        with contextlib.suppress(discord.HTTPException):
            if not silently:
                await ctx.send(_("Restarting..."))
        await ctx.bot.shutdown(restart=True)

    @bank.is_owner_if_bank_global()
    @commands.guildowner_or_permissions(administrator=True)
    @commands.group()
    async def bankset(self, ctx: commands.Context):
        """Base command for bank settings."""

    @bankset.command(name="showsettings")
    async def bankset_showsettings(self, ctx: commands.Context):
        """Show the current bank settings."""
        cur_setting = await bank.is_global()
        if cur_setting:
            group = bank._config
        else:
            if not ctx.guild:
                return
            group = bank._config.guild(ctx.guild)
        group_data = await group.all()
        bank_name = group_data["bank_name"]
        bank_scope = _("Global") if cur_setting else _("Server")
        currency_name = group_data["currency"]
        default_balance = group_data["default_balance"]
        max_balance = group_data["max_balance"]

        settings = _(
            "Bank settings:\n\nBank name: {bank_name}\nBank scope: {bank_scope}\n"
            "Currency: {currency_name}\nDefault balance: {default_balance}\n"
            "Maximum allowed balance: {maximum_bal}\n"
        ).format(
            bank_name=bank_name,
            bank_scope=bank_scope,
            currency_name=currency_name,
            default_balance=humanize_number(default_balance),
            maximum_bal=humanize_number(max_balance),
        )
        await ctx.send(box(settings))

    @bankset.command(name="toggleglobal")
    @commands.is_owner()
    async def bankset_toggleglobal(self, ctx: commands.Context, confirm: bool = False):
        """Toggle whether the bank is global or not.

        If the bank is global, it will become per-server.
        If the bank is per-server, it will become global.
        """
        cur_setting = await bank.is_global()

        word = _("per-server") if cur_setting else _("global")
        if confirm is False:
            await ctx.send(
                _(
                    "This will toggle the bank to be {banktype}, deleting all accounts "
                    "in the process! If you're sure, type `{command}`"
                ).format(banktype=word, command=f"{ctx.clean_prefix}bankset toggleglobal yes")
            )
        else:
            await bank.set_global(not cur_setting)
            await ctx.send(_("The bank is now {banktype}.").format(banktype=word))

    @bank.is_owner_if_bank_global()
    @commands.guildowner_or_permissions(administrator=True)
    @bankset.command(name="bankname")
    async def bankset_bankname(self, ctx: commands.Context, *, name: str):
        """Set the bank's name."""
        await bank.set_bank_name(name, ctx.guild)
        await ctx.send(_("Bank name has been set to: {name}").format(name=name))

    @bank.is_owner_if_bank_global()
    @commands.guildowner_or_permissions(administrator=True)
    @bankset.command(name="creditsname")
    async def bankset_creditsname(self, ctx: commands.Context, *, name: str):
        """Set the name for the bank's currency."""
        await bank.set_currency_name(name, ctx.guild)
        await ctx.send(_("Currency name has been set to: {name}").format(name=name))

    @bank.is_owner_if_bank_global()
    @commands.guildowner_or_permissions(administrator=True)
    @bankset.command(name="maxbal")
    async def bankset_maxbal(self, ctx: commands.Context, *, amount: int):
        """Set the maximum balance a user can get."""
        try:
            await bank.set_max_balance(amount, ctx.guild)
        except ValueError:
            # noinspection PyProtectedMember
            return await ctx.send(
                _("Amount must be greater than zero and less than {max}.").format(
                    max=humanize_number(bank._MAX_BALANCE)
                )
            )
        await ctx.send(
            _("Maximum balance has been set to: {amount}").format(amount=humanize_number(amount))
        )

    @bank.is_owner_if_bank_global()
    @commands.guildowner_or_permissions(administrator=True)
    @bankset.command(name="registeramount")
    async def bankset_registeramount(self, ctx: commands.Context, creds: int):
        """Set the initial balance for new bank accounts.

        Example:
        - `[p]bankset registeramount 5000`

        **Arguments**

        - `<creds>` The new initial balance amount. Default is 0.
        """
        guild = ctx.guild
        max_balance = await bank.get_max_balance(ctx.guild)
        credits_name = await bank.get_currency_name(guild)
        try:
            await bank.set_default_balance(creds, guild)
        except ValueError:
            return await ctx.send(
                _("Amount must be greater than or equal to zero and less than {maxbal}.").format(
                    maxbal=humanize_number(max_balance)
                )
            )
        await ctx.send(
            _("Registering an account will now give {num} {currency}.").format(
                num=humanize_number(creds), currency=credits_name
            )
        )

    @bank.is_owner_if_bank_global()
    @commands.guildowner_or_permissions(administrator=True)
    @bankset.command(name="reset")
    async def bankset_reset(self, ctx, confirmation: bool = False):
        """Delete all bank accounts.

        Examples:
        - `[p]bankset reset` - Did not confirm. Shows the help message.
        - `[p]bankset reset yes`

        **Arguments**

        - `<confirmation>` This will default to false unless specified.
        """
        if confirmation is False:
            await ctx.send(
                _(
                    "This will delete all bank accounts for {scope}.\nIf you're sure, type "
                    "`{prefix}bankset reset yes`"
                ).format(
                    scope=self.bot.user.display_name
                    if await bank.is_global()
                    else _("this server"),
                    prefix=ctx.clean_prefix,
                )
            )
        else:
            await bank.wipe_bank(guild=ctx.guild)
            await ctx.send(
                _("All bank accounts for {scope} have been deleted.").format(
                    scope=self.bot.user.display_name
                    if await bank.is_global()
                    else _("this server")
                )
            )

    @bank.is_owner_if_bank_global()
    @commands.admin_or_permissions(manage_guild=True)
    @bankset.group(name="prune")
    async def bankset_prune(self, ctx):
        """Base command for pruning bank accounts."""
        pass

    @bankset_prune.command(name="server", aliases=["guild", "local"])
    @commands.guild_only()
    @commands.guildowner()
    async def bankset_prune_local(self, ctx, confirmation: bool = False):
        """Prune bank accounts for users no longer in the server.

        Cannot be used with a global bank. See `[p]bankset prune global`.

        Examples:
        - `[p]bankset prune server` - Did not confirm. Shows the help message.
        - `[p]bankset prune server yes`

        **Arguments**

        - `<confirmation>` This will default to false unless specified.
        """
        global_bank = await bank.is_global()
        if global_bank is True:
            return await ctx.send(_("This command cannot be used with a global bank."))

        if confirmation is False:
            await ctx.send(
                _(
                    "This will delete all bank accounts for users no longer in this server."
                    "\nIf you're sure, type "
                    "`{prefix}bankset prune local yes`"
                ).format(prefix=ctx.clean_prefix)
            )
        else:
            await bank.bank_prune(self.bot, guild=ctx.guild)
            await ctx.send(
                _("Bank accounts for users no longer in this server have been deleted.")
            )

    @bankset_prune.command(name="global")
    @commands.is_owner()
    async def bankset_prune_global(self, ctx, confirmation: bool = False):
        """Prune bank accounts for users who no longer share a server with the bot.

        Cannot be used without a global bank. See `[p]bankset prune server`.

        Examples:
        - `[p]bankset prune global` - Did not confirm. Shows the help message.
        - `[p]bankset prune global yes`

        **Arguments**

        - `<confirmation>` This will default to false unless specified.
        """
        global_bank = await bank.is_global()
        if global_bank is False:
            return await ctx.send(_("This command cannot be used with a local bank."))

        if confirmation is False:
            await ctx.send(
                _(
                    "This will delete all bank accounts for users "
                    "who no longer share a server with the bot."
                    "\nIf you're sure, type `{prefix}bankset prune global yes`"
                ).format(prefix=ctx.clean_prefix)
            )
        else:
            await bank.bank_prune(self.bot)
            await ctx.send(
                _(
                    "Bank accounts for users who "
                    "no longer share a server with the bot have been pruned."
                )
            )

    @bankset_prune.command(name="user", usage="<user> [confirmation=False]")
    async def bankset_prune_user(
        self,
        ctx,
        member_or_id: Union[discord.Member, RawUserIdConverter],
        confirmation: bool = False,
    ):
        """Delete the bank account of a specified user.

        Examples:
        - `[p]bankset prune user @Twentysix` - Did not confirm. Shows the help message.
        - `[p]bankset prune user @Twentysix yes`

        **Arguments**

        - `<user>` The user to delete the bank of. Takes mentions, names, and user ids.
        - `<confirmation>` This will default to false unless specified.
        """
        try:
            name = member_or_id.display_name
            uid = member_or_id.id
        except AttributeError:
            name = member_or_id
            uid = member_or_id

        if confirmation is False:
            await ctx.send(
                _(
                    "This will delete {name}'s bank account."
                    "\nIf you're sure, type "
                    "`{prefix}bankset prune user {id} yes`"
                ).format(prefix=ctx.clean_prefix, id=uid, name=name)
            )
        else:
            await bank.bank_prune(self.bot, guild=ctx.guild, user_id=uid)
            await ctx.send(_("The bank account for {name} has been pruned.").format(name=name))

    @commands.group()
    @commands.guildowner_or_permissions(administrator=True)
    async def modlogset(self, ctx: commands.Context):
        """Manage modlog settings."""
        pass

    @commands.is_owner()
    @modlogset.command(hidden=True, name="fixcasetypes")
    async def modlogset_fixcasetypes(self, ctx: commands.Context):
        """Command to fix misbehaving casetypes."""
        await modlog._handle_audit_type_key()
        await ctx.tick()

    @modlogset.command(aliases=["channel"], name="modlog")
    @commands.guild_only()
    async def modlogset_modlog(
        self,
        ctx: commands.Context,
        channel: Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel] = None,
    ):
        """Set a channel as the modlog.

        Omit `[channel]` to disable the modlog.
        """
        guild = ctx.guild
        if channel:
            if channel.permissions_for(guild.me).send_messages:
                await modlog.set_modlog_channel(guild, channel)
                await ctx.send(
                    _("Mod events will be sent to {channel}.").format(channel=channel.mention)
                )
            else:
                await ctx.send(
                    _("I do not have permissions to send messages in {channel}!").format(
                        channel=channel.mention
                    )
                )
        else:
            try:
                await modlog.get_modlog_channel(guild)
            except RuntimeError:
                await ctx.send(_("Mod log is already disabled."))
            else:
                await modlog.set_modlog_channel(guild, None)
                await ctx.send(_("Mod log deactivated."))

    @modlogset.command(name="cases")
    @commands.guild_only()
    async def modlogset_cases(self, ctx: commands.Context, action: str = None):
        """
        Enable or disable case creation for a mod action.

        An action can be enabling or disabling specific cases. (Ban, kick, mute, etc.)

        Example: `[p]modlogset cases kick enabled`
        """
        guild = ctx.guild

        if action is None:  # No args given
            casetypes = await modlog.get_all_casetypes(guild)
            await ctx.send_help()
            lines = []
            for ct in casetypes:
                enabled = _("enabled") if await ct.is_enabled() else _("disabled")
                lines.append(f"{ct.name} : {enabled}")

            await ctx.send(_("Current settings:\n") + box("\n".join(lines)))
            return

        casetype = await modlog.get_casetype(action, guild)
        if not casetype:
            await ctx.send(_("That action is not registered."))
        else:
            enabled = await casetype.is_enabled()
            await casetype.set_enabled(not enabled)
            await ctx.send(
                _("Case creation for {action_name} actions is now {enabled}.").format(
                    action_name=action, enabled=_("enabled") if not enabled else _("disabled")
                )
            )

    @modlogset.command(name="resetcases")
    @commands.guild_only()
    async def modlogset_resetcases(self, ctx: commands.Context):
        """Reset all modlog cases in this server."""
        guild = ctx.guild
        await ctx.send(
            _("Are you sure you would like to reset all modlog cases in this server?")
            + " (yes/no)"
        )
        try:
            pred = MessagePredicate.yes_or_no(ctx, user=ctx.author)
            msg = await ctx.bot.wait_for("message", check=pred, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send(_("You took too long to respond."))
            return
        if pred.result:
            await modlog.reset_cases(guild)
            await ctx.send(_("Cases have been reset."))
        else:
            await ctx.send(_("No changes have been made."))

    @commands.group(name="set")
    async def _set(self, ctx: commands.Context):
        """Commands for changing [botname]'s settings."""

    # -- Bot Metadata Commands -- ###

    @_set.group(name="bot", aliases=["metadata"])
    @commands.admin_or_permissions(manage_nicknames=True)
    async def _set_bot(self, ctx: commands.Context):
        """Commands for changing [botname]'s metadata."""

    @commands.is_owner()
    @_set_bot.command(name="description")
    async def _set_bot_description(self, ctx: commands.Context, *, description: str = ""):
        """
        Sets the bot's description.

        Use without a description to reset.
        This is shown in a few locations, including the help menu.

        The maximum description length is 250 characters to ensure it displays properly.

        The default is "Red V3".

        **Examples:**
        - `[p]set bot description` - Resets the description to the default setting.
        - `[p]set bot description MyBot: A Red V3 Bot`

        **Arguments:**
        - `[description]` - The description to use for this bot. Leave blank to reset to the default.
        """
        if not description:
            await ctx.bot._config.description.clear()
            ctx.bot.description = "Red V3"
            await ctx.send(_("Description reset."))
        elif len(description) > 250:  # While the limit is 256, we bold it adding characters.
            await ctx.send(
                _(
                    "This description is too long to properly display. "
                    "Please try again with below 250 characters."
                )
            )
        else:
            await ctx.bot._config.description.set(description)
            ctx.bot.description = description
            await ctx.tick()

    async def _set_bot_image(
        self,
        image_type: Literal["avatar", "banner"],
        ctx: commands.Context,
        url: Optional[str] = None,
    ):
        if len(ctx.message.attachments) > 0:  # Attachments take priority
            data = await ctx.message.attachments[0].read()
        elif url is not None:
            if url.startswith("<") and url.endswith(">"):
                url = url[1:-1]

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url) as r:
                        data = await r.read()
                except aiohttp.InvalidURL:
                    return await ctx.send(_("That URL is invalid."))
                except aiohttp.ClientError:
                    return await ctx.send(_("Something went wrong while trying to get the image."))
        else:
            await ctx.send_help()
            return

        try:
            async with ctx.typing():
                if image_type == "avatar":
                    await ctx.bot.user.edit(avatar=data)
                else:
                    await ctx.bot.user.edit(banner=data)
        except discord.HTTPException:
            if image_type == "avatar":
                await ctx.send(
                    _(
                        "Failed. Remember that you can edit my avatar "
                        "up to two times a hour. The URL or attachment "
                        "must be a valid image in either JPG, PNG, GIF, or WEBP format."
                    )
                )
            else:
                await ctx.send(
                    _(
                        "Failed. Remember that you can edit my banner "
                        "up to two times a hour. The URL or attachment "
                        "must be a valid image in either JPG, PNG, GIF, or WEBP format."
                    )
                )
        except ValueError:
            await ctx.send(_("JPG / PNG / GIF / WEBP format only."))
        else:
            await ctx.send(_("Done."))

    @_set_bot.group(name="avatar", invoke_without_command=True)
    @commands.is_owner()
    async def _set_bot_avatar(self, ctx: commands.Context, url: str = None):
        """Sets [botname]'s avatar

        Supports either an attachment or an image URL.

        **Examples:**
        - `[p]set bot avatar` - With an image attachment, this will set the avatar.
        - `[p]set bot avatar` - Without an attachment, this will show the command help.
        - `[p]set bot avatar https://avatars.githubusercontent.com/u/23690422` - Sets the avatar to the provided url.

        **Arguments:**
        - `[url]` - An image url to be used as an avatar. Leave blank when uploading an attachment.
        """
        await self._set_bot_image("avatar", ctx, url)

    @_set_bot_avatar.command(name="remove", aliases=["clear"])
    @commands.is_owner()
    async def _set_bot_avatar_remove(self, ctx: commands.Context):
        """
        Removes [botname]'s avatar.

        **Example:**
        - `[p]set bot avatar remove`
        """
        async with ctx.typing():
            await ctx.bot.user.edit(avatar=None)
        await ctx.send(_("Avatar removed."))

    @_set_bot.group(name="banner", invoke_without_command=True)
    @commands.is_owner()
    async def _set_bot_banner(self, ctx: commands.Context, url: str = None):
        """Sets [botname]'s banner

        Supports either an attachment or an image URL.

        **Examples:**
        - `[p]set bot banner` - With an image attachment, this will set the banner.
        - `[p]set bot banner` - Without an attachment, this will show the command help.
        - `[p]set bot banner https://opengraph.githubassets.com` - Sets the banner to the provided url.

        **Arguments:**
        - `[url]` - An image url to be used as an banner. Leave blank when uploading an attachment.
        """
        await self._set_bot_image("banner", ctx, url)

    @_set_bot_banner.command(name="remove", aliases=["clear"])
    @commands.is_owner()
    async def _set_bot_banner_remove(self, ctx: commands.Context):
        """
        Removes [botname]'s banner.

        **Example:**
        - `[p]set bot banner remove`
        """
        async with ctx.typing():
            await ctx.bot.user.edit(banner=None)
        await ctx.send(_("Banner removed."))

    @_set_bot.command(name="username", aliases=["name"])
    @commands.is_owner()
    async def _set_bot_username(self, ctx: commands.Context, *, username: str):
        """Sets [botname]'s username.

        Maximum length for a username is 32 characters.

        Note: The username of a verified bot cannot be manually changed.
            Please contact Discord support to change it.

        **Example:**
        - `[p]set bot username BaguetteBot`

        **Arguments:**
        - `<username>` - The username to give the bot.
        """
        try:
            if self.bot.user.public_flags.verified_bot:
                await ctx.send(
                    _(
                        "The username of a verified bot cannot be manually changed."
                        " Please contact Discord support to change it."
                    )
                )
                return
            if len(username) > 32:
                await ctx.send(_("Failed to change name. Must be 32 characters or fewer."))
                return
            async with ctx.typing():
                await asyncio.wait_for(self._name(name=username), timeout=30)
        except asyncio.TimeoutError:
            await ctx.send(
                _(
                    "Changing the username timed out. "
                    "Remember that you can only do it up to 2 times an hour."
                    " Use nicknames if you need frequent changes: {command}"
                ).format(command=inline(f"{ctx.clean_prefix}set bot nickname"))
            )
        except discord.HTTPException as e:
            if e.code == 50035:
                error_string = e.text.split("\n")[1]  # Remove the "Invalid Form body"
                await ctx.send(
                    _(
                        "Failed to change the username. "
                        "Discord returned the following error:\n"
                        "{error_message}"
                    ).format(error_message=inline(error_string))
                )
            else:
                log.error(
                    "Unexpected error occurred when trying to change the username.", exc_info=e
                )
                await ctx.send(_("Unexpected error occurred when trying to change the username."))
        else:
            await ctx.send(_("Done."))

    @_set_bot.command(name="nickname")
    @commands.admin_or_permissions(manage_nicknames=True)
    @commands.guild_only()
    async def _set_bot_nickname(self, ctx: commands.Context, *, nickname: str = None):
        """Sets [botname]'s nickname for the current server.

        Maximum length for a nickname is 32 characters.

        **Example:**
        - `[p]set bot nickname 🎃 SpookyBot 🎃`

        **Arguments:**
        - `[nickname]` - The nickname to give the bot. Leave blank to clear the current nickname.
        """
        try:
            if nickname and len(nickname) > 32:
                await ctx.send(_("Failed to change nickname. Must be 32 characters or fewer."))
                return
            await ctx.guild.me.edit(nick=nickname)
        except discord.Forbidden:
            await ctx.send(_("I lack the permissions to change my own nickname."))
        else:
            await ctx.send(_("Done."))

    @_set_bot.command(name="custominfo")
    @commands.is_owner()
    async def _set_bot_custominfo(self, ctx: commands.Context, *, text: str = None):
        """Customizes a section of `[p]info`.

        The maximum amount of allowed characters is 1024.
        Supports markdown, links and "mentions".

        Link example: `[My link](https://example.com)`

        **Examples:**
        - `[p]set bot custominfo >>> I can use **markdown** such as quotes, ||spoilers|| and multiple lines.`
        - `[p]set bot custominfo Join my [support server](discord.gg/discord)!`
        - `[p]set bot custominfo` - Removes custom info text.

        **Arguments:**
        - `[text]` - The custom info text.
        """
        if not text:
            await ctx.bot._config.custom_info.clear()
            await ctx.send(_("The custom text has been cleared."))
            return
        if len(text) <= 1024:
            await ctx.bot._config.custom_info.set(text)
            await ctx.send(_("The custom text has been set."))
            await ctx.invoke(self.info)
        else:
            await ctx.send(_("Text must be fewer than 1024 characters long."))

    # -- End Bot Metadata Commands -- ###
    # -- Bot Status Commands -- ###

    @_set.group(name="status")
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status(self, ctx: commands.Context):
        """Commands for setting [botname]'s status."""

    @_set_status.command(
        name="streaming", aliases=["stream", "twitch"], usage="[(<streamer> <stream_title>)]"
    )
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status_stream(
        self,
        ctx: commands.Context,
        streamer: commands.Range[str, 1, 489] = None,
        *,
        stream_title: commands.Range[str, 1, 128] = None,
    ):
        """Sets [botname]'s streaming status to a twitch stream.

        This will appear as `Streaming <stream_title>` or `LIVE ON TWITCH` depending on the context.
        It will also include a `Watch` button with a twitch.tv url for the provided streamer.

        Maximum length for a stream title is 128 characters.

        Leaving both streamer and stream_title empty will clear it.

        **Examples:**
        - `[p]set status stream` - Clears the activity status.
        - `[p]set status stream 26 Twentysix is streaming` - Sets the stream to `https://www.twitch.tv/26`.
        - `[p]set status stream https://twitch.tv/26 Twentysix is streaming` - Sets the URL manually.

        **Arguments:**
        - `<streamer>` - The twitch streamer to provide a link to. This can be their twitch name or the entire URL.
        - `<stream_title>` - The text to follow `Streaming` in the status."""
        status = ctx.bot.guilds[0].me.status if len(ctx.bot.guilds) > 0 else None

        if stream_title:
            stream_title = stream_title.strip()
            if "twitch.tv/" not in streamer:
                streamer = "https://www.twitch.tv/" + streamer
            activity = discord.Streaming(url=streamer, name=stream_title)
            await ctx.bot.change_presence(status=status, activity=activity)
        elif streamer is not None:
            await ctx.send_help()
            return
        else:
            await ctx.bot.change_presence(activity=None, status=status)
        await ctx.send(_("Done."))

    @_set_status.command(name="playing", aliases=["game"])
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status_game(
        self, ctx: commands.Context, *, game: commands.Range[str, 1, 128] = None
    ):
        """Sets [botname]'s playing status.

        This will appear as `Playing <game>` or `PLAYING A GAME: <game>` depending on the context.

        Maximum length for a playing status is 128 characters.

        **Examples:**
        - `[p]set status playing` - Clears the activity status.
        - `[p]set status playing the keyboard`

        **Arguments:**
        - `[game]` - The text to follow `Playing`. Leave blank to clear the current activity status.
        """

        if game:
            game = discord.Game(name=game)
        else:
            game = None
        status = ctx.bot.guilds[0].me.status if len(ctx.bot.guilds) > 0 else discord.Status.online
        await ctx.bot.change_presence(status=status, activity=game)
        if game:
            await ctx.send(_("Status set to `Playing {game.name}`.").format(game=game))
        else:
            await ctx.send(_("Game cleared."))

    @_set_status.command(name="listening")
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status_listening(
        self, ctx: commands.Context, *, listening: commands.Range[str, 1, 128] = None
    ):
        """Sets [botname]'s listening status.

        This will appear as `Listening to <listening>`.

        Maximum length for a listening status is 128 characters.

        **Examples:**
        - `[p]set status listening` - Clears the activity status.
        - `[p]set status listening jams`

        **Arguments:**
        - `[listening]` - The text to follow `Listening to`. Leave blank to clear the current activity status.
        """

        status = ctx.bot.guilds[0].me.status if len(ctx.bot.guilds) > 0 else discord.Status.online
        if listening:
            activity = discord.Activity(name=listening, type=discord.ActivityType.listening)
        else:
            activity = None
        await ctx.bot.change_presence(status=status, activity=activity)
        if activity:
            await ctx.send(
                _("Status set to `Listening to {listening}`.").format(listening=listening)
            )
        else:
            await ctx.send(_("Listening cleared."))

    @_set_status.command(name="watching")
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status_watching(
        self, ctx: commands.Context, *, watching: commands.Range[str, 1, 128] = None
    ):
        """Sets [botname]'s watching status.

        This will appear as `Watching <watching>`.

        Maximum length for a watching status is 128 characters.

        **Examples:**
        - `[p]set status watching` - Clears the activity status.
        - `[p]set status watching [p]help`

        **Arguments:**
        - `[watching]` - The text to follow `Watching`. Leave blank to clear the current activity status.
        """

        status = ctx.bot.guilds[0].me.status if len(ctx.bot.guilds) > 0 else discord.Status.online
        if watching:
            activity = discord.Activity(name=watching, type=discord.ActivityType.watching)
        else:
            activity = None
        await ctx.bot.change_presence(status=status, activity=activity)
        if activity:
            await ctx.send(_("Status set to `Watching {watching}`.").format(watching=watching))
        else:
            await ctx.send(_("Watching cleared."))

    @_set_status.command(name="competing")
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status_competing(
        self, ctx: commands.Context, *, competing: commands.Range[str, 1, 128] = None
    ):
        """Sets [botname]'s competing status.

        This will appear as `Competing in <competing>`.

        Maximum length for a competing status is 128 characters.

        **Examples:**
        - `[p]set status competing` - Clears the activity status.
        - `[p]set status competing London 2012 Olympic Games`

        **Arguments:**
        - `[competing]` - The text to follow `Competing in`. Leave blank to clear the current activity status.
        """

        status = ctx.bot.guilds[0].me.status if len(ctx.bot.guilds) > 0 else discord.Status.online
        if competing:
            activity = discord.Activity(name=competing, type=discord.ActivityType.competing)
        else:
            activity = None
        await ctx.bot.change_presence(status=status, activity=activity)
        if activity:
            await ctx.send(
                _("Status set to `Competing in {competing}`.").format(competing=competing)
            )
        else:
            await ctx.send(_("Competing cleared."))

    @_set_status.command(name="custom")
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status_custom(
        self, ctx: commands.Context, *, text: commands.Range[str, 1, 128] = None
    ):
        """Sets [botname]'s custom status.

        This will appear as `<text>`.

        Maximum length for a custom status is 128 characters.

        **Examples:**
        - `[p]set status custom` - Clears the activity status.
        - `[p]set status custom Running cogs...`

        **Arguments:**
        - `[text]` - The custom status text. Leave blank to clear the current activity status.
        """

        status = ctx.bot.guilds[0].me.status if len(ctx.bot.guilds) > 0 else discord.Status.online
        if text:
            activity = discord.CustomActivity(name=text)
        else:
            activity = None
        await ctx.bot.change_presence(status=status, activity=activity)
        if activity:
            await ctx.send(_("Custom status set to `{text}`.").format(text=text))
        else:
            await ctx.send(_("Custom status cleared."))

    async def _set_my_status(self, ctx: commands.Context, status: discord.Status):
        game = ctx.bot.guilds[0].me.activity if len(ctx.bot.guilds) > 0 else None
        await ctx.bot.change_presence(status=status, activity=game)
        return await ctx.send(_("Status changed to {}.").format(status))

    @_set_status.command(name="online")
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status_online(self, ctx: commands.Context):
        """Set [botname]'s status to online."""
        await self._set_my_status(ctx, discord.Status.online)

    @_set_status.command(name="dnd", aliases=["donotdisturb", "busy"])
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status_dnd(self, ctx: commands.Context):
        """Set [botname]'s status to do not disturb."""
        await self._set_my_status(ctx, discord.Status.do_not_disturb)

    @_set_status.command(name="idle", aliases=["away", "afk"])
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status_idle(self, ctx: commands.Context):
        """Set [botname]'s status to idle."""
        await self._set_my_status(ctx, discord.Status.idle)

    @_set_status.command(name="invisible", aliases=["offline"])
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status_invisible(self, ctx: commands.Context):
        """Set [botname]'s status to invisible."""
        await self._set_my_status(ctx, discord.Status.invisible)

    # -- End Bot Status Commands -- ###
    # -- Bot Roles Commands -- ###

    @_set.group(name="roles")
    @commands.guildowner()
    @commands.guild_only()
    async def _set_roles(self, ctx: commands.Context):
        """Set server's admin and mod roles for [botname]."""

    @_set_roles.command(name="addadminrole")
    @commands.guildowner()
    @commands.guild_only()
    async def _set_roles_addadminrole(self, ctx: commands.Context, *, role: discord.Role):
        """
        Adds an admin role for this server.

        Admins have the same access as Mods, plus additional admin level commands like:
         - `[p]set serverprefix`
         - `[p]addrole`
         - `[p]ban`
         - `[p]ignore guild`

         And more.

        **Examples:**
        - `[p]set roles addadminrole @Admins`
        - `[p]set roles addadminrole Super Admins`

        **Arguments:**
        - `<role>` - The role to add as an admin.
        """
        async with ctx.bot._config.guild(ctx.guild).admin_role() as roles:
            if role.id in roles:
                return await ctx.send(_("This role is already an admin role."))
            roles.append(role.id)
        await ctx.send(_("That role is now considered an admin role."))

    @_set_roles.command(name="addmodrole")
    @commands.guildowner()
    @commands.guild_only()
    async def _set_roles_addmodrole(self, ctx: commands.Context, *, role: discord.Role):
        """
        Adds a moderator role for this server.

        This grants access to moderator level commands like:
         - `[p]mute`
         - `[p]cleanup`
         - `[p]customcommand create`

         And more.

        **Examples:**
        - `[p]set roles addmodrole @Mods`
        - `[p]set roles addmodrole Loyal Helpers`

        **Arguments:**
        - `<role>` - The role to add as a moderator.
        """
        async with ctx.bot._config.guild(ctx.guild).mod_role() as roles:
            if role.id in roles:
                return await ctx.send(_("This role is already a mod role."))
            roles.append(role.id)
        await ctx.send(_("That role is now considered a mod role."))

    @_set_roles.command(
        name="removeadminrole", aliases=["remadmindrole", "deladminrole", "deleteadminrole"]
    )
    @commands.guildowner()
    @commands.guild_only()
    async def _set_roles_removeadminrole(self, ctx: commands.Context, *, role: discord.Role):
        """
        Removes an admin role for this server.

        **Examples:**
        - `[p]set roles removeadminrole @Admins`
        - `[p]set roles removeadminrole Super Admins`

        **Arguments:**
        - `<role>` - The role to remove from being an admin.
        """
        async with ctx.bot._config.guild(ctx.guild).admin_role() as roles:
            if role.id not in roles:
                return await ctx.send(_("That role was not an admin role to begin with."))
            roles.remove(role.id)
        await ctx.send(_("That role is no longer considered an admin role."))

    @_set_roles.command(
        name="removemodrole", aliases=["remmodrole", "delmodrole", "deletemodrole"]
    )
    @commands.guildowner()
    @commands.guild_only()
    async def _set_roles_removemodrole(self, ctx: commands.Context, *, role: discord.Role):
        """
        Removes a mod role for this server.

        **Examples:**
        - `[p]set roles removemodrole @Mods`
        - `[p]set roles removemodrole Loyal Helpers`

        **Arguments:**
        - `<role>` - The role to remove from being a moderator.
        """
        async with ctx.bot._config.guild(ctx.guild).mod_role() as roles:
            if role.id not in roles:
                return await ctx.send(_("That role was not a mod role to begin with."))
            roles.remove(role.id)
        await ctx.send(_("That role is no longer considered a mod role."))

    # -- End Set Roles Commands -- ###
    # -- Set Locale Commands -- ###

    @_set.group(name="locale", invoke_without_command=True)
    @commands.guildowner_or_permissions(manage_guild=True)
    async def _set_locale(self, ctx: commands.Context, language_code: str):
        """
        Changes [botname]'s locale in this server.

        Go to [Red's Crowdin page](https://translate.discord.red) to see locales that are available with translations.

        Use "default" to return to the bot's default set language.

        If you want to change bot's global locale, see `[p]set locale global` command.

        **Examples:**
        - `[p]set locale en-US`
        - `[p]set locale de-DE`
        - `[p]set locale fr-FR`
        - `[p]set locale pl-PL`
        - `[p]set locale default` - Resets to the global default locale.

        **Arguments:**
        - `<language_code>` - The default locale to use for the bot. This can be any language code with country code included.
        """
        if ctx.guild is None:
            await ctx.send_help()
            return
        await ctx.invoke(self._set_locale_local, language_code)

    @_set_locale.command(name="global")
    @commands.is_owner()
    async def _set_locale_global(self, ctx: commands.Context, language_code: str):
        """
        Changes [botname]'s default locale.

        This will be used when a server has not set a locale, or in DMs.

        Go to [Red's Crowdin page](https://translate.discord.red) to see locales that are available with translations.

        To reset to English, use "en-US".

        **Examples:**
        - `[p]set locale global en-US`
        - `[p]set locale global de-DE`
        - `[p]set locale global fr-FR`
        - `[p]set locale global pl-PL`

        **Arguments:**
        - `<language_code>` - The default locale to use for the bot. This can be any language code with country code included.
        """
        try:
            standardized_locale_name = _i18n.set_global_locale(language_code)
        except ValueError:
            await ctx.send(_("Invalid language code. Use format: `en-US`"))
            return
        await self.bot._i18n_cache.set_locale(None, standardized_locale_name)
        await i18n.set_contextual_locales_from_guild(self.bot, ctx.guild)
        await ctx.send(_("Global locale has been set."))

    @_set_locale.command(name="server", aliases=["local", "guild"])
    @commands.guild_only()
    @commands.guildowner_or_permissions(manage_guild=True)
    async def _set_locale_local(self, ctx: commands.Context, language_code: str):
        """
        Changes [botname]'s locale in this server.

        Go to [Red's Crowdin page](https://translate.discord.red) to see locales that are available with translations.

        Use "default" to return to the bot's default set language.

        **Examples:**
        - `[p]set locale server en-US`
        - `[p]set locale server de-DE`
        - `[p]set locale server fr-FR`
        - `[p]set locale server pl-PL`
        - `[p]set locale server default` - Resets to the global default locale.

        **Arguments:**
        - `<language_code>` - The default locale to use for the bot. This can be any language code with country code included.
        """
        if language_code.lower() == "default":
            global_locale = await self.bot._config.locale()
            i18n.set_contextual_locale(global_locale)
            await self.bot._i18n_cache.set_locale(ctx.guild, None)
            await ctx.send(_("Locale has been set to the default."))
            return
        try:
            standardized_locale_name = i18n.set_contextual_locale(language_code)
        except ValueError:
            await ctx.send(_("Invalid language code. Use format: `en-US`"))
            return
        await self.bot._i18n_cache.set_locale(ctx.guild, standardized_locale_name)
        await ctx.send(_("Locale has been set."))

    @_set.group(name="regionalformat", aliases=["region"], invoke_without_command=True)
    @commands.guildowner_or_permissions(manage_guild=True)
    async def _set_regional_format(self, ctx: commands.Context, language_code: str):
        """
        Changes the bot's regional format in this server. This is used for formatting date, time and numbers.

        `language_code` can be any language code with country code included, e.g. `en-US`, `de-DE`, `fr-FR`, `pl-PL`, etc.
        Pass "reset" to `language_code` to base regional formatting on bot's locale in this server.

        If you want to change bot's global regional format, see `[p]set regionalformat global` command.

        **Examples:**
        - `[p]set regionalformat en-US`
        - `[p]set region de-DE`
        - `[p]set regionalformat reset` - Resets to the locale.

        **Arguments:**
        - `[language_code]` - The region format to use for the bot in this server.
        """
        if ctx.guild is None:
            await ctx.send_help()
            return
        await ctx.invoke(self._set_regional_format_local, language_code)

    @_set_regional_format.command(name="global")
    @commands.is_owner()
    async def _set_regional_format_global(self, ctx: commands.Context, language_code: str):
        """
        Changes the bot's regional format. This is used for formatting date, time and numbers.

        `language_code` can be any language code with country code included, e.g. `en-US`, `de-DE`, `fr-FR`, `pl-PL`, etc.
        Pass "reset" to `language_code` to base regional formatting on bot's locale.

        **Examples:**
        - `[p]set regionalformat global en-US`
        - `[p]set region global de-DE`
        - `[p]set regionalformat global reset` - Resets to the locale.

        **Arguments:**
        - `[language_code]` - The default region format to use for the bot.
        """
        if language_code.lower() == "reset":
            _i18n.set_global_regional_format(None)
            await self.bot._i18n_cache.set_regional_format(None, None)
            await ctx.send(_("Global regional formatting will now be based on bot's locale."))
            return

        try:
            standardized_locale_name = _i18n.set_global_regional_format(language_code)
        except ValueError:
            await ctx.send(_("Invalid language code. Use format: `en-US`"))
            return
        await self.bot._i18n_cache.set_regional_format(None, standardized_locale_name)
        await ctx.send(
            _("Global regional formatting will now be based on `{language_code}` locale.").format(
                language_code=standardized_locale_name
            )
        )

    @_set_regional_format.command(name="server", aliases=["local", "guild"])
    @commands.guild_only()
    @commands.guildowner_or_permissions(manage_guild=True)
    async def _set_regional_format_local(self, ctx: commands.Context, language_code: str):
        """
        Changes the bot's regional format in this server. This is used for formatting date, time and numbers.

        `language_code` can be any language code with country code included, e.g. `en-US`, `de-DE`, `fr-FR`, `pl-PL`, etc.
        Pass "reset" to `language_code` to base regional formatting on bot's locale in this server.

        **Examples:**
        - `[p]set regionalformat server en-US`
        - `[p]set region local de-DE`
        - `[p]set regionalformat server reset` - Resets to the locale.

        **Arguments:**
        - `[language_code]` - The region format to use for the bot in this server.
        """
        if language_code.lower() == "reset":
            i18n.set_contextual_regional_format(None)
            await self.bot._i18n_cache.set_regional_format(ctx.guild, None)
            await ctx.send(
                _("Regional formatting will now be based on bot's locale in this server.")
            )
            return

        try:
            standardized_locale_name = i18n.set_contextual_regional_format(language_code)
        except ValueError:
            await ctx.send(_("Invalid language code. Use format: `en-US`"))
            return
        await self.bot._i18n_cache.set_regional_format(ctx.guild, standardized_locale_name)
        await ctx.send(
            _("Regional formatting will now be based on `{language_code}` locale.").format(
                language_code=standardized_locale_name
            )
        )

    # -- End Set Locale Commands -- ###
    # -- Set Api Commands -- ###

    @_set.group(name="api", invoke_without_command=True)
    @commands.is_owner()
    async def _set_api(
        self,
        ctx: commands.Context,
        service: Optional[str] = None,
        *,
        tokens: Optional[TokenConverter] = None,
    ):
        """
        Commands to set, list or remove various external API tokens.

        This setting will be asked for by some 3rd party cogs and some core cogs.

        If passed without the `<service>` or `<tokens>` arguments it will allow you to open a modal to set your API keys securely.

        To add the keys provide the service name and the tokens as a comma separated
        list of key,values as described by the cog requesting this command.

        Note: API tokens are sensitive, so this command should only be used in a private channel or in DM with the bot.

        **Examples:**
        - `[p]set api`
        - `[p]set api spotify`
        - `[p]set api spotify redirect_uri localhost`
        - `[p]set api github client_id,whoops client_secret,whoops`

        **Arguments:**
        - `<service>` - The service you're adding tokens to.
        - `<tokens>` - Pairs of token keys and values. The key and value should be separated by one of ` `, `,`, or `;`.
        """
        if service is None or tokens is None:
            view = SetApiView(default_service=service)
            msg = await ctx.send(_("Click the button below to set your keys."), view=view)
            await view.wait()
            await msg.edit(content=_("This API keys setup message has expired."), view=None)
        else:
            if ctx.bot_permissions.manage_messages:
                await ctx.message.delete()
            await ctx.bot.set_shared_api_tokens(service, **tokens)
            await ctx.send(_("`{service}` API tokens have been set.").format(service=service))

    @_set_api.command(name="list")
    async def _set_api_list(self, ctx: commands.Context):
        """
        Show all external API services along with their keys that have been set.

        Secrets are not shown.

        **Example:**
        - `[p]set api list`
        """

        services: dict = await ctx.bot.get_shared_api_tokens()
        if not services:
            await ctx.send(_("No API services have been set yet."))
            return

        sorted_services = sorted(services.keys(), key=str.lower)

        joined = _("Set API services:\n") if len(services) > 1 else _("Set API service:\n")
        for service_name in sorted_services:
            joined += "+ {}\n".format(service_name)
            for key_name in services[service_name].keys():
                joined += "  - {}\n".format(key_name)
        for page in pagify(joined, ["\n"], shorten_by=16):
            await ctx.send(box(page.lstrip(" "), lang="diff"))

    @_set_api.command(name="remove", require_var_positional=True)
    async def _set_api_remove(self, ctx: commands.Context, *services: str):
        """
        Remove the given services with all their keys and tokens.

        **Examples:**
        - `[p]set api remove spotify`
        - `[p]set api remove github youtube`

        **Arguments:**
        - `<services...>` - The services to remove."""
        bot_services = (await ctx.bot.get_shared_api_tokens()).keys()
        services = [s for s in services if s in bot_services]

        if services:
            await self.bot.remove_shared_api_services(*services)
            if len(services) > 1:
                msg = _("Services deleted successfully:\n{services_list}").format(
                    services_list=humanize_list(services)
                )
            else:
                msg = _("Service deleted successfully: {service_name}").format(
                    service_name=services[0]
                )
            await ctx.send(msg)
        else:
            await ctx.send(_("None of the services you provided had any keys set."))

    # -- End Set Api Commands -- ###
    # -- Set Ownernotifications Commands -- ###

    @commands.is_owner()
    @_set.group(name="ownernotifications")
    async def _set_ownernotifications(self, ctx: commands.Context):
        """
        Commands for configuring owner notifications.

        Owner notifications include usage of `[p]contact` and available Red updates.
        """
        pass

    @_set_ownernotifications.command(name="optin")
    async def _set_ownernotifications_optin(self, ctx: commands.Context):
        """
        Opt-in on receiving owner notifications.

        This is the default state.

        Note: This will only resume sending owner notifications to your DMs.
            Additional owners and destinations will not be affected.

        **Example:**
        - `[p]set ownernotifications optin`
        """
        async with ctx.bot._config.owner_opt_out_list() as opt_outs:
            if ctx.author.id in opt_outs:
                opt_outs.remove(ctx.author.id)

        await ctx.tick()

    @_set_ownernotifications.command(name="optout")
    async def _set_ownernotifications_optout(self, ctx: commands.Context):
        """
        Opt-out of receiving owner notifications.

        Note: This will only stop sending owner notifications to your DMs.
            Additional owners and destinations will still receive notifications.

        **Example:**
        - `[p]set ownernotifications optout`
        """
        async with ctx.bot._config.owner_opt_out_list() as opt_outs:
            if ctx.author.id not in opt_outs:
                opt_outs.append(ctx.author.id)

        await ctx.tick()

    @_set_ownernotifications.command(name="adddestination")
    async def _set_ownernotifications_adddestination(
        self,
        ctx: commands.Context,
        *,
        channel: Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel],
    ):
        """
        Adds a destination text channel to receive owner notifications.

        **Examples:**
        - `[p]set ownernotifications adddestination #owner-notifications`
        - `[p]set ownernotifications adddestination 168091848718417920` - Accepts channel IDs.

        **Arguments:**
        - `<channel>` - The channel to send owner notifications to.
        """
        async with ctx.bot._config.extra_owner_destinations() as extras:
            if channel.id not in extras:
                extras.append(channel.id)

        await ctx.tick()

    @_set_ownernotifications.command(
        name="removedestination", aliases=["remdestination", "deletedestination", "deldestination"]
    )
    async def _set_ownernotifications_removedestination(
        self,
        ctx: commands.Context,
        *,
        channel: Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel, int],
    ):
        """
        Removes a destination text channel from receiving owner notifications.

        **Examples:**
        - `[p]set ownernotifications removedestination #owner-notifications`
        - `[p]set ownernotifications deletedestination 168091848718417920` - Accepts channel IDs.

        **Arguments:**
        - `<channel>` - The channel to stop sending owner notifications to.
        """

        try:
            channel_id = channel.id
        except AttributeError:
            channel_id = channel

        async with ctx.bot._config.extra_owner_destinations() as extras:
            if channel_id in extras:
                extras.remove(channel_id)

        await ctx.tick()

    @_set_ownernotifications.command(name="listdestinations")
    async def _set_ownernotifications_listdestinations(self, ctx: commands.Context):
        """
        Lists the configured extra destinations for owner notifications.

        **Example:**
        - `[p]set ownernotifications listdestinations`
        """

        channel_ids = await ctx.bot._config.extra_owner_destinations()

        if not channel_ids:
            await ctx.send(_("There are no extra channels being sent to."))
            return

        data = []

        for channel_id in channel_ids:
            channel = ctx.bot.get_channel(channel_id)
            if channel:
                # This includes the channel name in case the user can't see the channel.
                data.append(f"{channel.mention} {channel} ({channel.id})")
            else:
                data.append(_("Unknown channel with id: {id}").format(id=channel_id))

        output = "\n".join(data)
        for page in pagify(output):
            await ctx.send(page)

    # -- End Set Ownernotifications Commands -- ###

    @_set.command(name="showsettings")
    async def _set_showsettings(self, ctx: commands.Context, server: discord.Guild = None):
        """
        Show the current settings for [botname].

        Accepts optional server parameter to allow prefix recovery.
        """
        if server is None:
            server = ctx.guild

        if server:
            guild_data = await ctx.bot._config.guild(server).all()
            guild = server
            admin_role_ids = guild_data["admin_role"]
            admin_role_names = [r.name for r in guild.roles if r.id in admin_role_ids]
            admin_roles_str = (
                humanize_list(admin_role_names) if admin_role_names else _("Not Set.")
            )
            mod_role_ids = guild_data["mod_role"]
            mod_role_names = [r.name for r in guild.roles if r.id in mod_role_ids]
            mod_roles_str = humanize_list(mod_role_names) if mod_role_names else _("Not Set.")

            guild_locale = await i18n.get_locale_from_guild(self.bot, server)
            guild_regional_format = (
                await i18n.get_regional_format_from_guild(self.bot, server) or guild_locale
            )

            guild_settings = _(
                "Admin roles: {admin}\n"
                "Mod roles: {mod}\n"
                "Locale: {guild_locale}\n"
                "Regional format: {guild_regional_format}\n"
            ).format(
                admin=admin_roles_str,
                mod=mod_roles_str,
                guild_locale=guild_locale,
                guild_regional_format=guild_regional_format,
            )
        else:
            guild_settings = ""

        prefixes = await ctx.bot._prefix_cache.get_prefixes(server)
        global_data = await ctx.bot._config.all()
        locale = global_data["locale"]
        regional_format = global_data["regional_format"] or locale
        colour = discord.Colour(global_data["color"])

        prefix_string = " ".join(prefixes)
        settings = _(
            "{bot_name} Settings:\n\n"
            "Prefixes: {prefixes}\n"
            "{guild_settings}"
            "Global locale: {locale}\n"
            "Global regional format: {regional_format}\n"
            "Default embed colour: {colour}"
        ).format(
            bot_name=ctx.bot.user.display_name,
            prefixes=prefix_string,
            guild_settings=guild_settings,
            locale=locale,
            regional_format=regional_format,
            colour=colour,
        )
        for page in pagify(settings):
            await ctx.send(box(page))

    @commands.guildowner_or_permissions(administrator=True)
    @_set.command(name="deletedelay")
    @commands.guild_only()
    async def _set_deletedelay(self, ctx: commands.Context, time: int = None):
        """Set the delay until the bot removes the command message.

        Must be between -1 and 60.

        Set to -1 to disable this feature.

        This is only applied to the current server and not globally.

        **Examples:**
        - `[p]set deletedelay` - Shows the current delete delay setting.
        - `[p]set deletedelay 60` - Sets the delete delay to the max of 60 seconds.
        - `[p]set deletedelay -1` - Disables deleting command messages.

        **Arguments:**
        - `[time]` - The seconds to wait before deleting the command message. Use -1 to disable.
        """
        guild = ctx.guild
        if time is not None:
            time = min(max(time, -1), 60)  # Enforces the time limits
            await ctx.bot._config.guild(guild).delete_delay.set(time)
            if time == -1:
                await ctx.send(_("Command deleting disabled."))
            else:
                await ctx.send(_("Delete delay set to {num} seconds.").format(num=time))
        else:
            delay = await ctx.bot._config.guild(guild).delete_delay()
            if delay != -1:
                await ctx.send(
                    _(
                        "Bot will delete command messages after"
                        " {num} seconds. Set this value to -1 to"
                        " stop deleting messages"
                    ).format(num=delay)
                )
            else:
                await ctx.send(_("I will not delete command messages."))

    @_set.command(name="usebotcolour", aliases=["usebotcolor"])
    @commands.guildowner()
    @commands.guild_only()
    async def _set_usebotcolour(self, ctx: commands.Context):
        """
        Toggle whether to use the bot owner-configured colour for embeds.

        Default is to use the bot's configured colour.
        Otherwise, the colour used will be the colour of the bot's top role.

        **Example:**
        - `[p]set usebotcolour`
        """
        current_setting = await ctx.bot._config.guild(ctx.guild).use_bot_color()
        await ctx.bot._config.guild(ctx.guild).use_bot_color.set(not current_setting)
        await ctx.send(
            _("The bot {} use its configured color for embeds.").format(
                _("will not") if not current_setting else _("will")
            )
        )

    @_set.command(name="serverfuzzy")
    @commands.guildowner()
    @commands.guild_only()
    async def _set_serverfuzzy(self, ctx: commands.Context):
        """
        Toggle whether to enable fuzzy command search for the server.

        This allows the bot to identify potential misspelled commands and offer corrections.

        Note: This can be processor intensive and may be unsuitable for larger servers.

        Default is for fuzzy command search to be disabled.

        **Example:**
        - `[p]set serverfuzzy`
        """
        current_setting = await ctx.bot._config.guild(ctx.guild).fuzzy()
        await ctx.bot._config.guild(ctx.guild).fuzzy.set(not current_setting)
        await ctx.send(
            _("Fuzzy command search has been {} for this server.").format(
                _("disabled") if current_setting else _("enabled")
            )
        )

    @_set.command(name="fuzzy")
    @commands.is_owner()
    async def _set_fuzzy(self, ctx: commands.Context):
        """
        Toggle whether to enable fuzzy command search in DMs.

        This allows the bot to identify potential misspelled commands and offer corrections.

        Default is for fuzzy command search to be disabled.

        **Example:**
        - `[p]set fuzzy`
        """
        current_setting = await ctx.bot._config.fuzzy()
        await ctx.bot._config.fuzzy.set(not current_setting)
        await ctx.send(
            _("Fuzzy command search has been {} in DMs.").format(
                _("disabled") if current_setting else _("enabled")
            )
        )

    @_set.command(name="colour", aliases=["color"])
    @commands.is_owner()
    async def _set_colour(self, ctx: commands.Context, *, colour: discord.Colour = None):
        """
        Sets a default colour to be used for the bot's embeds.

        Acceptable values for the colour parameter can be found at:

        https://discordpy.readthedocs.io/en/stable/ext/commands/api.html#discord.ext.commands.ColourConverter

        **Examples:**
        - `[p]set colour dark red`
        - `[p]set colour blurple`
        - `[p]set colour 0x5DADE2`
        - `[p]set color 0x#FDFEFE`
        - `[p]set color #7F8C8D`

        **Arguments:**
        - `[colour]` - The colour to use for embeds. Leave blank to set to the default value (red).
        """
        if colour is None:
            ctx.bot._color = discord.Color.red()
            await ctx.bot._config.color.set(discord.Color.red().value)
            return await ctx.send(_("The color has been reset."))
        ctx.bot._color = colour
        await ctx.bot._config.color.set(colour.value)
        await ctx.send(_("The color has been set."))

    @_set.command(
        name="prefix",
        aliases=["prefixes", "globalprefix", "globalprefixes"],
        require_var_positional=True,
    )
    @commands.is_owner()
    async def _set_prefix(self, ctx: commands.Context, *prefixes: str):
        """Sets [botname]'s global prefix(es).

        Warning: This is not additive. It will replace all current prefixes.

        See also the `--mentionable` flag to enable mentioning the bot as the prefix.

        **Examples:**
        - `[p]set prefix !`
        - `[p]set prefix "! "` - Quotes are needed to use spaces in prefixes.
        - `[p]set prefix "@[botname] "` - This uses a mention as the prefix. See also the `--mentionable` flag.
        - `[p]set prefix ! ? .` - Sets multiple prefixes.

        **Arguments:**
        - `<prefixes...>` - The prefixes the bot will respond to globally.
        """
        if any(prefix.startswith("/") for prefix in prefixes):
            await ctx.send(
                _("Prefixes cannot start with '/', as it conflicts with Discord's slash commands.")
            )
            return
        if any(len(x) < MINIMUM_PREFIX_LENGTH for x in prefixes):
            await ctx.send(
                _(
                    "Warning: A prefix is below the recommended length (1 character).\n"
                    "Do you want to continue?"
                )
                + " (yes/no)"
            )
            pred = MessagePredicate.yes_or_no(ctx)
            try:
                await self.bot.wait_for("message", check=pred, timeout=30)
            except asyncio.TimeoutError:
                await ctx.send(_("Response timed out."))
                return
            else:
                if pred.result is False:
                    await ctx.send(_("Cancelled."))
                    return
        if any(len(x) > MAX_PREFIX_LENGTH for x in prefixes):
            await ctx.send(
                _(
                    "Warning: A prefix is above the recommended length (25 characters).\n"
                    "Do you want to continue?"
                )
                + " (yes/no)"
            )
            pred = MessagePredicate.yes_or_no(ctx)
            try:
                await self.bot.wait_for("message", check=pred, timeout=30)
            except asyncio.TimeoutError:
                await ctx.send(_("Response timed out."))
                return
            else:
                if pred.result is False:
                    await ctx.send(_("Cancelled."))
                    return
        await ctx.bot.set_prefixes(guild=None, prefixes=prefixes)
        if len(prefixes) == 1:
            await ctx.send(_("Prefix set."))
        else:
            await ctx.send(_("Prefixes set."))

    @_set.command(name="serverprefix", aliases=["serverprefixes"])
    @commands.admin_or_permissions(manage_guild=True)
    async def _set_serverprefix(
        self, ctx: commands.Context, server: Optional[discord.Guild], *prefixes: str
    ):
        """
        Sets [botname]'s server prefix(es).

        Warning: This will override global prefixes, the bot will not respond to any global prefixes in this server.
            This is not additive. It will replace all current server prefixes.
            A prefix cannot have more than 25 characters.

        **Examples:**
        - `[p]set serverprefix !`
        - `[p]set serverprefix "! "` - Quotes are needed to use spaces in prefixes.
        - `[p]set serverprefix "@[botname] "` - This uses a mention as the prefix.
        - `[p]set serverprefix ! ? .` - Sets multiple prefixes.
        - `[p]set serverprefix "Red - Discord Bot" ?` - Sets the prefix for a specific server. Quotes are needed to use spaces in the server name.

        **Arguments:**
        - `[server]` - The server to set the prefix for. Defaults to current server.
        - `[prefixes...]` - The prefixes the bot will respond to on this server. Leave blank to clear server prefixes.
        """
        if server is None:
            server = ctx.guild

        if not prefixes:
            await ctx.bot.set_prefixes(guild=server, prefixes=[])
            await ctx.send(_("Server prefixes have been reset."))
            return
        if any(prefix.startswith("/") for prefix in prefixes):
            await ctx.send(
                _("Prefixes cannot start with '/', as it conflicts with Discord's slash commands.")
            )
            return
        if any(len(x) < MINIMUM_PREFIX_LENGTH for x in prefixes):
            await ctx.send(_("You cannot have a prefix shorter than 1 character."))
            return
        if any(len(x) > MAX_PREFIX_LENGTH for x in prefixes):
            await ctx.send(_("You cannot have a prefix longer than 25 characters."))
            return
        prefixes = sorted(prefixes, reverse=True)
        await ctx.bot.set_prefixes(guild=server, prefixes=prefixes)
        if len(prefixes) == 1:
            await ctx.send(_("Server prefix set."))
        else:
            await ctx.send(_("Server prefixes set."))

    @_set.command(name="usebuttons")
    @commands.is_owner()
    async def _set_usebuttons(self, ctx: commands.Context, use_buttons: bool = None):
        """
        Set a global bot variable for using buttons in menus.

        When enabled, all usage of cores menus API will use buttons instead of reactions.

        This defaults to False.
        Using this without a setting will toggle.

        **Examples:**
            - `[p]set usebuttons True` - Enables using buttons.
            - `[p]helpset usebuttons` - Toggles the value.

        **Arguments:**
            - `[use_buttons]` - Whether to use buttons. Leave blank to toggle.
        """
        if use_buttons is None:
            use_buttons = not await ctx.bot._config.use_buttons()
        await ctx.bot._config.use_buttons.set(use_buttons)
        if use_buttons:
            await ctx.send(_("I will use buttons on basic menus."))
        else:
            await ctx.send(_("I will not use buttons on basic menus."))

    @_set.command(name="errormsg")
    @commands.is_owner()
    async def _set_errormsg(self, ctx: commands.Context, *, msg: str = None):
        """
        Set the message that will be sent on uncaught bot errors.

        To include the command name in the message, use the `{command}` placeholder.

        If you omit the `msg` argument, the message will be reset to the default one.

        **Examples:**
            - `[p]set errormsg` - Resets the error message back to the default: "Error in command '{command}'.". If the command invoker is one of the bot owners, the message will also include "Check your console or logs for details.".
            - `[p]set errormsg Oops, the command {command} has failed! Please try again later.` - Sets the error message to a custom one.

        **Arguments:**
            - `[msg]` - The custom error message. Must be less than 1000 characters. Omit to reset to the default one.
        """
        if msg is not None and len(msg) >= 1000:
            return await ctx.send(_("The message must be less than 1000 characters."))

        if msg is not None:
            await self.bot._config.invoke_error_msg.set(msg)
            content = _("Successfully updated the error message.")
        else:
            await self.bot._config.invoke_error_msg.clear()
            content = _("Successfully reset the error message back to the default one.")

        await ctx.send(content)

    @commands.group()
    @commands.is_owner()
    async def helpset(self, ctx: commands.Context):
        """
        Commands to manage settings for the help command.

        All help settings are applied globally.
        """
        pass

    @helpset.command(name="showsettings")
    async def helpset_showsettings(self, ctx: commands.Context):
        """
        Show the current help settings.

        Warning: These settings may not be accurate if the default formatter is not in use.

        **Example:**
        - `[p]helpset showsettings`
        """

        help_settings = await commands.help.HelpSettings.from_context(ctx)

        if type(ctx.bot._help_formatter) is commands.help.RedHelpFormatter:
            message = help_settings.pretty
        else:
            message = _(
                "Warning: The default formatter is not in use, these settings may not apply."
            )
            message += f"\n\n{help_settings.pretty}"

        for page in pagify(message):
            await ctx.send(page)

    @helpset.command(name="resetformatter")
    async def helpset_resetformatter(self, ctx: commands.Context):
        """
        This resets [botname]'s help formatter to the default formatter.

        **Example:**
        - `[p]helpset resetformatter`
        """

        ctx.bot.reset_help_formatter()
        await ctx.send(
            _(
                "The help formatter has been reset. "
                "This will not prevent cogs from modifying help, "
                "you may need to remove a cog if this has been an issue."
            )
        )

    @helpset.command(name="resetsettings")
    async def helpset_resetsettings(self, ctx: commands.Context):
        """
        This resets [botname]'s help settings to their defaults.

        This may not have an impact when using custom formatters from 3rd party cogs

        **Example:**
        - `[p]helpset resetsettings`
        """
        await ctx.bot._config.help.clear()
        await ctx.send(
            _(
                "The help settings have been reset to their defaults. "
                "This may not have an impact when using 3rd party help formatters."
            )
        )

    @helpset.command(name="usemenus")
    async def helpset_usemenus(
        self,
        ctx: commands.Context,
        use_menus: Literal["buttons", "reactions", "select", "selectonly", "disable"],
    ):
        """
        Allows the help command to be sent as a paginated menu instead of separate
        messages.

        When "reactions", "buttons", "select", or "selectonly" is passed,
         `[p]help` will only show one page at a time
        and will use the associated control scheme to navigate between pages.

         **Examples:**
        - `[p]helpset usemenus reactions` - Enables using reaction menus.
        - `[p]helpset usemenus buttons` - Enables using button menus.
        - `[p]helpset usemenus select` - Enables buttons with a select menu.
        - `[p]helpset usemenus selectonly` - Enables a select menu only on help.
        - `[p]helpset usemenus disable` - Disables help menus.

        **Arguments:**
            - `<"buttons"|"reactions"|"select"|"selectonly"|"disable">` - Whether to use `buttons`,
            `reactions`, `select`, `selectonly`, or no menus.
        """
        if use_menus == "selectonly":
            msg = _("Help will use the select menu only.")
            await ctx.bot._config.help.use_menus.set(4)
        if use_menus == "select":
            msg = _("Help will use button menus and add a select menu.")
            await ctx.bot._config.help.use_menus.set(3)
        if use_menus == "buttons":
            msg = _("Help will use button menus.")
            await ctx.bot._config.help.use_menus.set(2)
        if use_menus == "reactions":
            msg = _("Help will use reaction menus.")
            await ctx.bot._config.help.use_menus.set(1)
        if use_menus == "disable":
            msg = _("Help will not use menus.")
            await ctx.bot._config.help.use_menus.set(0)

        await ctx.send(msg)

    @helpset.command(name="showhidden")
    async def helpset_showhidden(self, ctx: commands.Context, show_hidden: bool = None):
        """
        This allows the help command to show hidden commands.

        This defaults to False.
        Using this without a setting will toggle.

        **Examples:**
        - `[p]helpset showhidden True` - Enables showing hidden commands.
        - `[p]helpset showhidden` - Toggles the value.

        **Arguments:**
        - `[show_hidden]` - Whether to use show hidden commands in help. Leave blank to toggle.
        """
        if show_hidden is None:
            show_hidden = not await ctx.bot._config.help.show_hidden()
        await ctx.bot._config.help.show_hidden.set(show_hidden)
        if show_hidden:
            await ctx.send(_("Help will not filter hidden commands."))
        else:
            await ctx.send(_("Help will filter hidden commands."))

    @helpset.command(name="showaliases")
    async def helpset_showaliases(self, ctx: commands.Context, show_aliases: bool = None):
        """
        This allows the help command to show existing commands aliases if there is any.

        This defaults to True.
        Using this without a setting will toggle.

        **Examples:**
        - `[p]helpset showaliases False` - Disables showing aliases on this server.
        - `[p]helpset showaliases` - Toggles the value.

        **Arguments:**
        - `[show_aliases]` - Whether to include aliases in help. Leave blank to toggle.
        """
        if show_aliases is None:
            show_aliases = not await ctx.bot._config.help.show_aliases()
        await ctx.bot._config.help.show_aliases.set(show_aliases)
        if show_aliases:
            await ctx.send(_("Help will now show command aliases."))
        else:
            await ctx.send(_("Help will no longer show command aliases."))

    @helpset.command(name="usetick")
    async def helpset_usetick(self, ctx: commands.Context, use_tick: bool = None):
        """
        This allows the help command message to be ticked if help is sent to a DM.

        Ticking is reacting to the help message with a ✅.

        Defaults to False.
        Using this without a setting will toggle.

        Note: This is only used when the bot is not using menus.

        **Examples:**
        - `[p]helpset usetick False` - Disables ticking when help is sent to DMs.
        - `[p]helpset usetick` - Toggles the value.

        **Arguments:**
        - `[use_tick]` - Whether to tick the help command when help is sent to DMs. Leave blank to toggle.
        """
        if use_tick is None:
            use_tick = not await ctx.bot._config.help.use_tick()
        await ctx.bot._config.help.use_tick.set(use_tick)
        if use_tick:
            await ctx.send(_("Help will now tick the command when sent in a DM."))
        else:
            await ctx.send(_("Help will not tick the command when sent in a DM."))

    @helpset.command(name="verifychecks")
    async def helpset_permfilter(self, ctx: commands.Context, verify: bool = None):
        """
        Sets if commands which can't be run in the current context should be filtered from help.

        Defaults to True.
        Using this without a setting will toggle.

        **Examples:**
        - `[p]helpset verifychecks False` - Enables showing unusable commands in help.
        - `[p]helpset verifychecks` - Toggles the value.

        **Arguments:**
        - `[verify]` - Whether to hide unusable commands in help. Leave blank to toggle.
        """
        if verify is None:
            verify = not await ctx.bot._config.help.verify_checks()
        await ctx.bot._config.help.verify_checks.set(verify)
        if verify:
            await ctx.send(_("Help will only show for commands which can be run."))
        else:
            await ctx.send(_("Help will show up without checking if the commands can be run."))

    @helpset.command(name="verifyexists")
    async def helpset_verifyexists(self, ctx: commands.Context, verify: bool = None):
        """
        Sets whether the bot should respond to help commands for nonexistent topics.

        When enabled, this will indicate the existence of help topics, even if the user can't use it.

        Note: This setting on its own does not fully prevent command enumeration.

        Defaults to False.
        Using this without a setting will toggle.

        **Examples:**
        - `[p]helpset verifyexists True` - Enables sending help for nonexistent topics.
        - `[p]helpset verifyexists` - Toggles the value.

        **Arguments:**
        - `[verify]` - Whether to respond to help for nonexistent topics. Leave blank to toggle.
        """
        if verify is None:
            verify = not await ctx.bot._config.help.verify_exists()
        await ctx.bot._config.help.verify_exists.set(verify)
        if verify:
            await ctx.send(_("Help will verify the existence of help topics."))
        else:
            await ctx.send(
                _(
                    "Help will only verify the existence of "
                    "help topics via fuzzy help (if enabled)."
                )
            )

    @helpset.command(name="pagecharlimit")
    async def helpset_pagecharlimt(self, ctx: commands.Context, limit: int):
        """Set the character limit for each page in the help message.

        Note: This setting only applies to embedded help.

        The default value is 1000 characters. The minimum value is 500.
        The maximum is based on the lower of what you provide and what discord allows.

        Please note that setting a relatively small character limit may
        mean some pages will exceed this limit.

        **Example:**
        - `[p]helpset pagecharlimit 1500`

        **Arguments:**
        - `<limit>` - The max amount of characters to show per page in the help message.
        """
        if limit < 500:
            await ctx.send(_("You must give a value of at least 500 characters."))
            return

        await ctx.bot._config.help.page_char_limit.set(limit)
        await ctx.send(_("Done. The character limit per page has been set to {}.").format(limit))

    @helpset.command(name="maxpages")
    async def helpset_maxpages(self, ctx: commands.Context, pages: int):
        """Set the maximum number of help pages sent in a server channel.

        If a help message contains more pages than this value, the help message will
        be sent to the command author via DM. This is to help reduce spam in server
        text channels.

        The default value is 2 pages.

        **Examples:**
        - `[p]helpset maxpages 50` - Basically never send help to DMs.
        - `[p]helpset maxpages 0` - Always send help to DMs.

        **Arguments:**
        - `<limit>` - The max pages allowed to send per help in a server.
        """
        if pages < 0:
            await ctx.send(_("You must give a value of zero or greater!"))
            return

        await ctx.bot._config.help.max_pages_in_guild.set(pages)
        await ctx.send(_("Done. The page limit has been set to {}.").format(pages))

    @helpset.command(name="deletedelay")
    @commands.bot_has_permissions(manage_messages=True)
    async def helpset_deletedelay(self, ctx: commands.Context, seconds: int):
        """Set the delay after which help pages will be deleted.

        The setting is disabled by default, and only applies to non-menu help,
        sent in server text channels.
        Setting the delay to 0 disables this feature.

        The bot has to have MANAGE_MESSAGES permission for this to work.

        **Examples:**
        - `[p]helpset deletedelay 60` - Delete the help pages after a minute.
        - `[p]helpset deletedelay 1` - Delete the help pages as quickly as possible.
        - `[p]helpset deletedelay 1209600` - Max time to wait before deleting (14 days).
        - `[p]helpset deletedelay 0` - Disable deleting help pages.

        **Arguments:**
        - `<seconds>` - The seconds to wait before deleting help pages.
        """
        if seconds < 0:
            await ctx.send(_("You must give a value of zero or greater!"))
            return
        if seconds > 60 * 60 * 24 * 14:  # 14 days
            await ctx.send(_("The delay cannot be longer than 14 days!"))
            return

        await ctx.bot._config.help.delete_delay.set(seconds)
        if seconds == 0:
            await ctx.send(_("Done. Help messages will not be deleted now."))
        else:
            await ctx.send(_("Done. The delete delay has been set to {} seconds.").format(seconds))

    @helpset.command(name="reacttimeout")
    async def helpset_reacttimeout(self, ctx: commands.Context, seconds: int):
        """Set the timeout for reactions, if menus are enabled.

        The default is 30 seconds.
        The timeout has to be between 15 and 300 seconds.

        **Examples:**
        - `[p]helpset reacttimeout 30` - The default timeout.
        - `[p]helpset reacttimeout 60` - Timeout of 1 minute.
        - `[p]helpset reacttimeout 15` - Minimum allowed timeout.
        - `[p]helpset reacttimeout 300` - Max allowed timeout (5 mins).

        **Arguments:**
        - `<seconds>` - The timeout, in seconds, of the reactions.
        """
        if seconds < 15:
            await ctx.send(_("You must give a value of at least 15 seconds!"))
            return
        if seconds > 300:
            await ctx.send(_("The timeout cannot be greater than 5 minutes!"))
            return

        await ctx.bot._config.help.react_timeout.set(seconds)
        await ctx.send(_("Done. The reaction timeout has been set to {} seconds.").format(seconds))

    @helpset.command(name="tagline")
    async def helpset_tagline(self, ctx: commands.Context, *, tagline: str = None):
        """
        Set the tagline to be used.

        The maximum tagline length is 2048 characters.
        This setting only applies to embedded help. If no tagline is specified, the default will be used instead.

        You can use `[\u200bp]` in your tagline, which will be replaced by the bot's prefix.

        **Examples:**
        - `[p]helpset tagline Thanks for using the bot!`
        - `[p]helpset tagline Use [\u200bp]invite to add me to your server.`
        - `[p]helpset tagline` - Resets the tagline to the default.

        **Arguments:**
        - `[tagline]` - The tagline to appear at the bottom of help embeds. Leave blank to reset.
        """
        if tagline is None:
            await ctx.bot._config.help.tagline.set("")
            return await ctx.send(_("The tagline has been reset."))

        if len(tagline) > 2048:
            await ctx.send(
                _(
                    "Your tagline is too long! Please shorten it to be "
                    "no more than 2048 characters long."
                )
            )
            return

        await ctx.bot._config.help.tagline.set(tagline)
        await ctx.send(_("The tagline has been set."))

    @commands.command(cooldown_after_parsing=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def contact(self, ctx: commands.Context, *, message: str):
        """Sends a message to the owner.

        This is limited to one message every 60 seconds per person.

        **Example:**
        - `[p]contact Help! The bot has become sentient!`

        **Arguments:**
        - `[message]` - The message to send to the owner.
        """
        guild = ctx.message.guild
        author = ctx.message.author
        footer = _("User ID: {}").format(author.id)

        if ctx.guild is None:
            source = _("through DM")
        else:
            source = _("from {}").format(guild)
            footer += _(" | Server ID: {}").format(guild.id)

        prefixes = await ctx.bot.get_valid_prefixes()
        prefix = re.sub(rf"<@!?{ctx.me.id}>", f"@{ctx.me.name}".replace("\\", r"\\"), prefixes[0])

        content = _("Use `{}dm {} <text>` to reply to this user").format(prefix, author.id)

        description = _("Sent by {} {}").format(author, source)

        destinations = await ctx.bot.get_owner_notification_destinations()

        if not destinations:
            await ctx.send(_("I've been configured not to send this anywhere."))
            return

        successful = False

        for destination in destinations:
            is_dm = isinstance(destination, discord.User)
            if not is_dm and not destination.permissions_for(destination.guild.me).send_messages:
                continue

            if await ctx.bot.embed_requested(destination, command=ctx.command):
                color = await ctx.bot.get_embed_color(destination)

                e = discord.Embed(colour=color, description=message)
                e.set_author(name=description, icon_url=author.display_avatar)
                e.set_footer(text=f"{footer}\n{content}")

                try:
                    await destination.send(embed=e)
                except discord.Forbidden:
                    log.exception(f"Contact failed to {destination}({destination.id})")
                    # Should this automatically opt them out?
                except discord.HTTPException:
                    log.exception(
                        f"An unexpected error happened while attempting to"
                        f" send contact to {destination}({destination.id})"
                    )
                else:
                    successful = True
            else:
                msg_text = "{}\nMessage:\n\n{}\n{}".format(description, message, footer)

                try:
                    await destination.send("{}\n{}".format(content, box(msg_text)))
                except discord.Forbidden:
                    log.exception(f"Contact failed to {destination}({destination.id})")
                    # Should this automatically opt them out?
                except discord.HTTPException:
                    log.exception(
                        f"An unexpected error happened while attempting to"
                        f" send contact to {destination}({destination.id})"
                    )
                else:
                    successful = True

        if successful:
            await ctx.send(_("Your message has been sent."))
        else:
            await ctx.send(_("I'm unable to deliver your message. Sorry."))

    @commands.command()
    @commands.is_owner()
    async def dm(self, ctx: commands.Context, user_id: int, *, message: str):
        """Sends a DM to a user.

        This command needs a user ID to work.

        To get a user ID, go to Discord's settings and open the 'Appearance' tab.
        Enable 'Developer Mode', then right click a user and click on 'Copy ID'.

        **Example:**
        - `[p]dm 262626262626262626 Do you like me? Yes / No`

        **Arguments:**
        - `[message]` - The message to dm to the user.
        """
        destination = self.bot.get_user(user_id)
        if destination is None or destination.bot:
            await ctx.send(
                _(
                    "Invalid ID, user not found, or user is a bot. "
                    "You can only send messages to people I share "
                    "a server with."
                )
            )
            return

        prefixes = await ctx.bot.get_valid_prefixes()
        prefix = re.sub(rf"<@!?{ctx.me.id}>", f"@{ctx.me.name}".replace("\\", r"\\"), prefixes[0])
        description = _("Owner of {}").format(ctx.bot.user)
        content = _("You can reply to this message with {}contact").format(prefix)
        if await ctx.embed_requested():
            e = discord.Embed(colour=await ctx.embed_colour(), description=message)

            e.set_footer(text=content)
            e.set_author(name=description, icon_url=ctx.bot.user.display_avatar)

            try:
                await destination.send(embed=e)
            except discord.HTTPException:
                await ctx.send(
                    _("Sorry, I couldn't deliver your message to {}").format(destination)
                )
            else:
                await ctx.send(_("Message delivered to {}").format(destination))
        else:
            response = "{}\nMessage:\n\n{}".format(description, message)
            try:
                await destination.send("{}\n{}".format(box(response), content))
            except discord.HTTPException:
                await ctx.send(
                    _("Sorry, I couldn't deliver your message to {}").format(destination)
                )
            else:
                await ctx.send(_("Message delivered to {}").format(destination))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def datapath(self, ctx: commands.Context):
        """Prints the bot's data path."""
        from redbot.core.data_manager import basic_config

        data_dir = Path(basic_config["DATA_PATH"])
        msg = _("Data path: {path}").format(path=data_dir)
        await ctx.send(box(msg))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def debuginfo(self, ctx: commands.Context):
        """Shows debug information useful for debugging."""
        from redbot.core._debuginfo import DebugInfo

        await ctx.send(await DebugInfo(self.bot).get_command_text())

    # You may ask why this command is owner-only,
    # cause after all it could be quite useful to guild owners!
    # Truth to be told, that would require us to make some part of this
    # more end-user friendly rather than just bot owner friendly - terms like
    # 'global call once checks' are not of any use to someone who isn't bot owner.
    @commands.is_owner()
    @commands.command()
    async def diagnoseissues(
        self,
        ctx: commands.Context,
        channel: Optional[
            Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread]
        ] = commands.CurrentChannel,
        # avoid non-default argument following default argument by using empty param()
        member: Union[discord.Member, discord.User] = commands.param(),
        *,
        command_name: str,
    ) -> None:
        """
        Diagnose issues with the command checks with ease!

        If you want to diagnose the command from a text channel in a different server,
        you can do so by using the command in DMs.

        **Example:**
        - `[p]diagnoseissues #general @Slime ban` - Diagnose why @Slime can't use `[p]ban` in #general channel.

        **Arguments:**
        - `[channel]` - The text channel that the command should be tested for. Defaults to the current channel.
        - `<member>` - The member that should be considered as the command caller.
        - `<command_name>` - The name of the command to test.
        """
        if ctx.guild is None:
            await ctx.send(
                _(
                    "A text channel, voice channel, stage channel, or thread needs to be passed"
                    " when using this command in DMs."
                )
            )
            return

        command = self.bot.get_command(command_name)
        if command is None:
            await ctx.send("Command not found!")
            return

        # This is done to allow the bot owner to diagnose a command
        # while not being a part of the server.
        if isinstance(member, discord.User):
            maybe_member = channel.guild.get_member(member.id)
            if maybe_member is None:
                await ctx.send(_("The given user is not a member of the diagnosed server."))
                return
            member = maybe_member

        if not can_user_send_messages_in(member, channel):
            # Let's make Flame happy here
            await ctx.send(
                _(
                    "Don't try to fool me, the given member can't access the {channel} channel!"
                ).format(channel=channel.mention)
            )
            return
        issue_diagnoser = IssueDiagnoser(self.bot, ctx, channel, member, command)
        await ctx.send(await issue_diagnoser.diagnose())

    @commands.group(aliases=["whitelist"])
    @commands.is_owner()
    async def allowlist(self, ctx: commands.Context):
        """
        Commands to manage the allowlist.

        Warning: When the allowlist is in use, the bot will ignore commands from everyone not on the list.

        Use `[p]allowlist clear` to disable the allowlist
        """
        pass

    @allowlist.command(name="add", require_var_positional=True)
    async def allowlist_add(self, ctx: commands.Context, *users: Union[discord.Member, int]):
        """
        Adds users to the allowlist.

        **Examples:**
        - `[p]allowlist add @26 @Will` - Adds two users to the allowlist.
        - `[p]allowlist add 262626262626262626` - Adds a user by ID.

        **Arguments:**
        - `<users...>` - The user or users to add to the allowlist.
        """
        await self.bot.add_to_whitelist(users)
        if len(users) > 1:
            await ctx.send(_("Users have been added to the allowlist."))
        else:
            await ctx.send(_("User has been added to the allowlist."))

    @allowlist.command(name="list")
    async def allowlist_list(self, ctx: commands.Context):
        """
        Lists users on the allowlist.

        **Example:**
        - `[p]allowlist list`
        """
        curr_list = await ctx.bot._config.whitelist()

        if not curr_list:
            await ctx.send("Allowlist is empty.")
            return
        if len(curr_list) > 1:
            msg = _("Users on the allowlist:")
        else:
            msg = _("User on the allowlist:")
        for user_id in curr_list:
            user = self.bot.get_user(user_id)
            if not user:
                user = _("Unknown or Deleted User")
            msg += f"\n\t- {user_id} ({user})"

        for page in pagify(msg):
            await ctx.send(box(page))

    @allowlist.command(name="remove", require_var_positional=True)
    async def allowlist_remove(self, ctx: commands.Context, *users: Union[discord.Member, int]):
        """
        Removes users from the allowlist.

        The allowlist will be disabled if all users are removed.

        **Examples:**
        - `[p]allowlist remove @26 @Will` - Removes two users from the allowlist.
        - `[p]allowlist remove 262626262626262626` - Removes a user by ID.

        **Arguments:**
        - `<users...>` - The user or users to remove from the allowlist.
        """
        await self.bot.remove_from_whitelist(users)
        if len(users) > 1:
            await ctx.send(_("Users have been removed from the allowlist."))
        else:
            await ctx.send(_("User has been removed from the allowlist."))

    @allowlist.command(name="clear")
    async def allowlist_clear(self, ctx: commands.Context):
        """
        Clears the allowlist.

        This disables the allowlist.

        **Example:**
        - `[p]allowlist clear`
        """
        await self.bot.clear_whitelist()
        await ctx.send(_("Allowlist has been cleared."))

    @commands.group(aliases=["blacklist", "denylist"])
    @commands.is_owner()
    async def blocklist(self, ctx: commands.Context):
        """
        Commands to manage the blocklist.

        Use `[p]blocklist clear` to disable the blocklist
        """
        pass

    @blocklist.command(name="add", require_var_positional=True)
    async def blocklist_add(self, ctx: commands.Context, *users: Union[discord.Member, int]):
        """
        Adds users to the blocklist.

        **Examples:**
        - `[p]blocklist add @26 @Will` - Adds two users to the blocklist.
        - `[p]blocklist add 262626262626262626` - Blocks a user by ID.

        **Arguments:**
        - `<users...>` - The user or users to add to the blocklist.
        """
        for user in users:
            if isinstance(user, int):
                user_obj = discord.Object(id=user)
            else:
                user_obj = user
            if await ctx.bot.is_owner(user_obj):
                await ctx.send(_("You cannot add an owner to the blocklist!"))
                return

        await self.bot.add_to_blacklist(users)
        if len(users) > 1:
            await ctx.send(_("Users have been added to the blocklist."))
        else:
            await ctx.send(_("User has been added to the blocklist."))

    @blocklist.command(name="list")
    async def blocklist_list(self, ctx: commands.Context):
        """
        Lists users on the blocklist.

        **Example:**
        - `[p]blocklist list`
        """
        curr_list = await self.bot.get_blacklist()

        if not curr_list:
            await ctx.send("Blocklist is empty.")
            return
        if len(curr_list) > 1:
            msg = _("Users on the blocklist:")
        else:
            msg = _("User on the blocklist:")
        for user_id in curr_list:
            user = self.bot.get_user(user_id)
            if not user:
                user = _("Unknown or Deleted User")
            msg += f"\n\t- {user_id} ({user})"

        for page in pagify(msg):
            await ctx.send(box(page))

    @blocklist.command(name="remove", require_var_positional=True)
    async def blocklist_remove(self, ctx: commands.Context, *users: Union[discord.Member, int]):
        """
        Removes users from the blocklist.

        **Examples:**
        - `[p]blocklist remove @26 @Will` - Removes two users from the blocklist.
        - `[p]blocklist remove 262626262626262626` - Removes a user by ID.

        **Arguments:**
        - `<users...>` - The user or users to remove from the blocklist.
        """
        await self.bot.remove_from_blacklist(users)
        if len(users) > 1:
            await ctx.send(_("Users have been removed from the blocklist."))
        else:
            await ctx.send(_("User has been removed from the blocklist."))

    @blocklist.command(name="clear")
    async def blocklist_clear(self, ctx: commands.Context):
        """
        Clears the blocklist.

        **Example:**
        - `[p]blocklist clear`
        """
        await self.bot.clear_blacklist()
        await ctx.send(_("Blocklist has been cleared."))

    @commands.group(aliases=["localwhitelist"])
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    async def localallowlist(self, ctx: commands.Context):
        """
        Commands to manage the server specific allowlist.

        Warning: When the allowlist is in use, the bot will ignore commands from everyone not on the list in the server.

        Use `[p]localallowlist clear` to disable the allowlist
        """
        pass

    @localallowlist.command(name="add", require_var_positional=True)
    async def localallowlist_add(
        self, ctx: commands.Context, *users_or_roles: Union[discord.Member, discord.Role, int]
    ):
        """
        Adds a user or role to the server allowlist.

        **Examples:**
        - `[p]localallowlist add @26 @Will` - Adds two users to the local allowlist.
        - `[p]localallowlist add 262626262626262626` - Allows a user by ID.
        - `[p]localallowlist add "Super Admins"` - Allows a role with a space in the name without mentioning.

        **Arguments:**
        - `<users_or_roles...>` - The users or roles to remove from the local allowlist.
        """
        names = [getattr(u_or_r, "name", u_or_r) for u_or_r in users_or_roles]
        uids = {getattr(u_or_r, "id", u_or_r) for u_or_r in users_or_roles}
        if not (ctx.guild.owner == ctx.author or await self.bot.is_owner(ctx.author)):
            current_whitelist = await self.bot.get_whitelist(ctx.guild)
            theoretical_whitelist = current_whitelist.union(uids)
            ids = {i for i in (ctx.author.id, *(getattr(ctx.author, "_roles", [])))}
            if ids.isdisjoint(theoretical_whitelist):
                return await ctx.send(
                    _(
                        "I cannot allow you to do this, as it would "
                        "remove your ability to run commands, "
                        "please ensure to add yourself to the allowlist first."
                    )
                )
        await self.bot.add_to_whitelist(uids, guild=ctx.guild)

        if len(uids) > 1:
            await ctx.send(_("Users and/or roles have been added to the allowlist."))
        else:
            await ctx.send(_("User or role has been added to the allowlist."))

    @localallowlist.command(name="list")
    async def localallowlist_list(self, ctx: commands.Context):
        """
        Lists users and roles on the server allowlist.

        **Example:**
        - `[p]localallowlist list`
        """
        curr_list = await self.bot.get_whitelist(ctx.guild)

        if not curr_list:
            await ctx.send("Server allowlist is empty.")
            return
        if len(curr_list) > 1:
            msg = _("Allowed users and/or roles:")
        else:
            msg = _("Allowed user or role:")
        for obj_id in curr_list:
            user_or_role = self.bot.get_user(obj_id) or ctx.guild.get_role(obj_id)
            if not user_or_role:
                user_or_role = _("Unknown or Deleted User/Role")
            msg += f"\n\t- {obj_id} ({user_or_role})"

        for page in pagify(msg):
            await ctx.send(box(page))

    @localallowlist.command(name="remove", require_var_positional=True)
    async def localallowlist_remove(
        self, ctx: commands.Context, *users_or_roles: Union[discord.Member, discord.Role, int]
    ):
        """
        Removes user or role from the allowlist.

        The local allowlist will be disabled if all users are removed.

        **Examples:**
        - `[p]localallowlist remove @26 @Will` - Removes two users from the local allowlist.
        - `[p]localallowlist remove 262626262626262626` - Removes a user by ID.
        - `[p]localallowlist remove "Super Admins"` - Removes a role with a space in the name without mentioning.

        **Arguments:**
        - `<users_or_roles...>` - The users or roles to remove from the local allowlist.
        """
        names = [getattr(u_or_r, "name", u_or_r) for u_or_r in users_or_roles]
        uids = {getattr(u_or_r, "id", u_or_r) for u_or_r in users_or_roles}
        if not (ctx.guild.owner == ctx.author or await self.bot.is_owner(ctx.author)):
            current_whitelist = await self.bot.get_whitelist(ctx.guild)
            theoretical_whitelist = current_whitelist - uids
            ids = {i for i in (ctx.author.id, *(getattr(ctx.author, "_roles", [])))}
            if theoretical_whitelist and ids.isdisjoint(theoretical_whitelist):
                return await ctx.send(
                    _(
                        "I cannot allow you to do this, as it would "
                        "remove your ability to run commands."
                    )
                )
        await self.bot.remove_from_whitelist(uids, guild=ctx.guild)

        if len(uids) > 1:
            await ctx.send(_("Users and/or roles have been removed from the server allowlist."))
        else:
            await ctx.send(_("User or role has been removed from the server allowlist."))

    @localallowlist.command(name="clear")
    async def localallowlist_clear(self, ctx: commands.Context):
        """
        Clears the allowlist.

        This disables the local allowlist and clears all entries.

        **Example:**
        - `[p]localallowlist clear`
        """
        await self.bot.clear_whitelist(ctx.guild)
        await ctx.send(_("Server allowlist has been cleared."))

    @commands.group(aliases=["localblacklist"])
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    async def localblocklist(self, ctx: commands.Context):
        """
        Commands to manage the server specific blocklist.

        Use `[p]localblocklist clear` to disable the blocklist
        """
        pass

    @localblocklist.command(name="add", require_var_positional=True)
    async def localblocklist_add(
        self, ctx: commands.Context, *users_or_roles: Union[discord.Member, discord.Role, int]
    ):
        """
        Adds a user or role to the local blocklist.

        **Examples:**
        - `[p]localblocklist add @26 @Will` - Adds two users to the local blocklist.
        - `[p]localblocklist add 262626262626262626` - Blocks a user by ID.
        - `[p]localblocklist add "Bad Apples"` - Blocks a role with a space in the name without mentioning.

        **Arguments:**
        - `<users_or_roles...>` - The users or roles to add to the local blocklist.
        """
        for user_or_role in users_or_roles:
            uid = discord.Object(id=getattr(user_or_role, "id", user_or_role))
            if uid.id == ctx.author.id:
                await ctx.send(_("You cannot add yourself to the blocklist!"))
                return
            if uid.id == ctx.guild.owner_id and not await ctx.bot.is_owner(ctx.author):
                await ctx.send(_("You cannot add the guild owner to the blocklist!"))
                return
            if await ctx.bot.is_owner(uid):
                await ctx.send(_("You cannot add a bot owner to the blocklist!"))
                return
        await self.bot.add_to_blacklist(users_or_roles, guild=ctx.guild)

        if len(users_or_roles) > 1:
            await ctx.send(_("Users and/or roles have been added from the server blocklist."))
        else:
            await ctx.send(_("User or role has been added from the server blocklist."))

    @localblocklist.command(name="list")
    async def localblocklist_list(self, ctx: commands.Context):
        """
        Lists users and roles on the server blocklist.

        **Example:**
        - `[p]localblocklist list`
        """
        curr_list = await self.bot.get_blacklist(ctx.guild)

        if not curr_list:
            await ctx.send("Server blocklist is empty.")
            return
        if len(curr_list) > 1:
            msg = _("Blocked users and/or roles:")
        else:
            msg = _("Blocked user or role:")
        for obj_id in curr_list:
            user_or_role = self.bot.get_user(obj_id) or ctx.guild.get_role(obj_id)
            if not user_or_role:
                user_or_role = _("Unknown or Deleted User/Role")
            msg += f"\n\t- {obj_id} ({user_or_role})"

        for page in pagify(msg):
            await ctx.send(box(page))

    @localblocklist.command(name="remove", require_var_positional=True)
    async def localblocklist_remove(
        self, ctx: commands.Context, *users_or_roles: Union[discord.Member, discord.Role, int]
    ):
        """
        Removes user or role from local blocklist.

        **Examples:**
        - `[p]localblocklist remove @26 @Will` - Removes two users from the local blocklist.
        - `[p]localblocklist remove 262626262626262626` - Unblocks a user by ID.
        - `[p]localblocklist remove "Bad Apples"` - Unblocks a role with a space in the name without mentioning.

        **Arguments:**
        - `<users_or_roles...>` - The users or roles to remove from the local blocklist.
        """
        await self.bot.remove_from_blacklist(users_or_roles, guild=ctx.guild)

        if len(users_or_roles) > 1:
            await ctx.send(_("Users and/or roles have been removed from the server blocklist."))
        else:
            await ctx.send(_("User or role has been removed from the server blocklist."))

    @localblocklist.command(name="clear")
    async def localblocklist_clear(self, ctx: commands.Context):
        """
        Clears the server blocklist.

        This disables the server blocklist and clears all entries.

        **Example:**
        - `[p]blocklist clear`
        """
        await self.bot.clear_blacklist(ctx.guild)
        await ctx.send(_("Server blocklist has been cleared."))

    @commands.guildowner_or_permissions(administrator=True)
    @commands.group(name="command")
    async def command_manager(self, ctx: commands.Context):
        """Commands to enable and disable commands and cogs."""
        pass

    @commands.is_owner()
    @command_manager.command(name="defaultdisablecog")
    async def command_default_disable_cog(self, ctx: commands.Context, *, cog: CogConverter):
        """Set the default state for a cog as disabled.

        This will disable the cog for all servers by default.
        To override it, use `[p]command enablecog` on the servers you want to allow usage.

        Note: This will only work on loaded cogs, and must reference the title-case cog name.

        **Examples:**
        - `[p]command defaultdisablecog Economy`
        - `[p]command defaultdisablecog ModLog`

        **Arguments:**
        - `<cog>` - The name of the cog to make disabled by default. Must be title-case.
        """
        cogname = cog.qualified_name
        if isinstance(cog, commands.commands._RuleDropper):
            return await ctx.send(_("You can't disable this cog by default."))
        await self.bot._disabled_cog_cache.default_disable(cogname)
        await ctx.send(_("{cogname} has been set as disabled by default.").format(cogname=cogname))

    @commands.is_owner()
    @command_manager.command(name="defaultenablecog")
    async def command_default_enable_cog(self, ctx: commands.Context, *, cog: CogConverter):
        """Set the default state for a cog as enabled.

        This will re-enable the cog for all servers by default.
        To override it, use `[p]command disablecog` on the servers you want to disallow usage.

        Note: This will only work on loaded cogs, and must reference the title-case cog name.

        **Examples:**
        - `[p]command defaultenablecog Economy`
        - `[p]command defaultenablecog ModLog`

        **Arguments:**
        - `<cog>` - The name of the cog to make enabled by default. Must be title-case.
        """
        cogname = cog.qualified_name
        await self.bot._disabled_cog_cache.default_enable(cogname)
        await ctx.send(_("{cogname} has been set as enabled by default.").format(cogname=cogname))

    @commands.guild_only()
    @command_manager.command(name="disablecog")
    async def command_disable_cog(self, ctx: commands.Context, *, cog: CogConverter):
        """Disable a cog in this server.

        Note: This will only work on loaded cogs, and must reference the title-case cog name.

        **Examples:**
        - `[p]command disablecog Economy`
        - `[p]command disablecog ModLog`

        **Arguments:**
        - `<cog>` - The name of the cog to disable on this server. Must be title-case.
        """
        cogname = cog.qualified_name
        if isinstance(cog, commands.commands._RuleDropper):
            return await ctx.send(_("You can't disable this cog as you would lock yourself out."))
        if await self.bot._disabled_cog_cache.disable_cog_in_guild(cogname, ctx.guild.id):
            await ctx.send(_("{cogname} has been disabled in this guild.").format(cogname=cogname))
        else:
            await ctx.send(
                _("{cogname} was already disabled (nothing to do).").format(cogname=cogname)
            )

    @commands.guild_only()
    @command_manager.command(name="enablecog", usage="<cog>")
    async def command_enable_cog(self, ctx: commands.Context, *, cogname: str):
        """Enable a cog in this server.

        Note: This will only work on loaded cogs, and must reference the title-case cog name.

        **Examples:**
        - `[p]command enablecog Economy`
        - `[p]command enablecog ModLog`

        **Arguments:**
        - `<cog>` - The name of the cog to enable on this server. Must be title-case.
        """
        if await self.bot._disabled_cog_cache.enable_cog_in_guild(cogname, ctx.guild.id):
            await ctx.send(_("{cogname} has been enabled in this guild.").format(cogname=cogname))
        else:
            # putting this here allows enabling a cog that isn't loaded but was disabled.
            cog = self.bot.get_cog(cogname)
            if not cog:
                return await ctx.send(_('Cog "{arg}" not found.').format(arg=cogname))

            await ctx.send(
                _("{cogname} was not disabled (nothing to do).").format(cogname=cogname)
            )

    @commands.guild_only()
    @command_manager.command(name="listdisabledcogs")
    async def command_list_disabled_cogs(self, ctx: commands.Context):
        """List the cogs which are disabled in this server.

        **Example:**
        - `[p]command listdisabledcogs`
        """
        disabled = [
            cog.qualified_name
            for cog in self.bot.cogs.values()
            if await self.bot._disabled_cog_cache.cog_disabled_in_guild(
                cog.qualified_name, ctx.guild.id
            )
        ]
        if disabled:
            output = _("The following cogs are disabled in this guild:\n")
            output += humanize_list(disabled)

            for page in pagify(output):
                await ctx.send(page)
        else:
            await ctx.send(_("There are no disabled cogs in this guild."))

    @command_manager.group(name="listdisabled", invoke_without_command=True)
    async def list_disabled(self, ctx: commands.Context):
        """
        List disabled commands.

        If you're the bot owner, this will show global disabled commands by default.
        Otherwise, this will show disabled commands on the current server.

        **Example:**
        - `[p]command listdisabled`
        """
        # Select the scope based on the author's privileges
        if await ctx.bot.is_owner(ctx.author):
            await ctx.invoke(self.list_disabled_global)
        else:
            await ctx.invoke(self.list_disabled_guild)

    @list_disabled.command(name="global")
    async def list_disabled_global(self, ctx: commands.Context):
        """List disabled commands globally.

        **Example:**
        - `[p]command listdisabled global`
        """
        disabled_list = await self.bot._config.disabled_commands()
        if not disabled_list:
            return await ctx.send(_("There aren't any globally disabled commands."))

        if len(disabled_list) > 1:
            header = _("{} commands are disabled globally.\n").format(
                humanize_number(len(disabled_list))
            )
        else:
            header = _("1 command is disabled globally.\n")
        paged = [box(x) for x in pagify(humanize_list(disabled_list), page_length=1000)]
        paged[0] = header + paged[0]
        await ctx.send_interactive(paged)

    @commands.guild_only()
    @list_disabled.command(name="guild")
    async def list_disabled_guild(self, ctx: commands.Context):
        """List disabled commands in this server.

        **Example:**
        - `[p]command listdisabled guild`
        """
        disabled_list = await self.bot._config.guild(ctx.guild).disabled_commands()
        if not disabled_list:
            return await ctx.send(_("There aren't any disabled commands in {}.").format(ctx.guild))

        if len(disabled_list) > 1:
            header = _("{} commands are disabled in {}.\n").format(
                humanize_number(len(disabled_list)), ctx.guild
            )
        else:
            header = _("1 command is disabled in {}.\n").format(ctx.guild)
        paged = [box(x) for x in pagify(humanize_list(disabled_list), page_length=1000)]
        paged[0] = header + paged[0]
        await ctx.send_interactive(paged)

    @command_manager.group(name="disable", invoke_without_command=True)
    async def command_disable(self, ctx: commands.Context, *, command: CommandConverter):
        """
        Disable a command.

        If you're the bot owner, this will disable commands globally by default.
        Otherwise, this will disable commands on the current server.

        **Examples:**
        - `[p]command disable userinfo` - Disables the `userinfo` command in the Mod cog.
        - `[p]command disable urban` - Disables the `urban` command in the General cog.

        **Arguments:**
        - `<command>` - The command to disable.
        """
        # Select the scope based on the author's privileges
        if await ctx.bot.is_owner(ctx.author):
            await ctx.invoke(self.command_disable_global, command=command)
        else:
            await ctx.invoke(self.command_disable_guild, command=command)

    @commands.is_owner()
    @command_disable.command(name="global")
    async def command_disable_global(self, ctx: commands.Context, *, command: CommandConverter):
        """
        Disable a command globally.

        **Examples:**
        - `[p]command disable global userinfo` - Disables the `userinfo` command in the Mod cog.
        - `[p]command disable global urban` - Disables the `urban` command in the General cog.

        **Arguments:**
        - `<command>` - The command to disable globally.
        """
        if self.command_manager in command.parents or self.command_manager == command:
            await ctx.send(
                _("The command to disable cannot be `command` or any of its subcommands.")
            )
            return

        if isinstance(command, commands.commands._RuleDropper):
            await ctx.send(
                _("This command is designated as being always available and cannot be disabled.")
            )
            return

        async with ctx.bot._config.disabled_commands() as disabled_commands:
            if command.qualified_name not in disabled_commands:
                disabled_commands.append(command.qualified_name)

        if not command.enabled:
            await ctx.send(_("That command is already disabled globally."))
            return
        command.enabled = False

        await ctx.tick()

    @commands.guild_only()
    @command_disable.command(name="server", aliases=["guild"])
    async def command_disable_guild(self, ctx: commands.Context, *, command: CommandConverter):
        """
        Disable a command in this server only.

        **Examples:**
        - `[p]command disable server userinfo` - Disables the `userinfo` command in the Mod cog.
        - `[p]command disable server urban` - Disables the `urban` command in the General cog.

        **Arguments:**
        - `<command>` - The command to disable for the current server.
        """
        if self.command_manager in command.parents or self.command_manager == command:
            await ctx.send(
                _("The command to disable cannot be `command` or any of its subcommands.")
            )
            return

        if isinstance(command, commands.commands._RuleDropper):
            await ctx.send(
                _("This command is designated as being always available and cannot be disabled.")
            )
            return

        if command.requires.privilege_level is not None:
            if command.requires.privilege_level > await PrivilegeLevel.from_ctx(ctx):
                await ctx.send(_("You are not allowed to disable that command."))
                return

        async with ctx.bot._config.guild(ctx.guild).disabled_commands() as disabled_commands:
            if command.qualified_name not in disabled_commands:
                disabled_commands.append(command.qualified_name)

        done = command.disable_in(ctx.guild)

        if not done:
            await ctx.send(_("That command is already disabled in this server."))
        else:
            await ctx.tick()

    @command_manager.group(name="enable", invoke_without_command=True)
    async def command_enable(self, ctx: commands.Context, *, command: CommandConverter):
        """Enable a command.

        If you're the bot owner, this will try to enable a globally disabled command by default.
        Otherwise, this will try to enable a command disabled on the current server.

        **Examples:**
        - `[p]command enable userinfo` - Enables the `userinfo` command in the Mod cog.
        - `[p]command enable urban` - Enables the `urban` command in the General cog.

        **Arguments:**
        - `<command>` - The command to enable.
        """
        if await ctx.bot.is_owner(ctx.author):
            await ctx.invoke(self.command_enable_global, command=command)
        else:
            await ctx.invoke(self.command_enable_guild, command=command)

    @commands.is_owner()
    @command_enable.command(name="global")
    async def command_enable_global(self, ctx: commands.Context, *, command: CommandConverter):
        """
        Enable a command globally.

        **Examples:**
        - `[p]command enable global userinfo` - Enables the `userinfo` command in the Mod cog.
        - `[p]command enable global urban` - Enables the `urban` command in the General cog.

        **Arguments:**
        - `<command>` - The command to enable globally.
        """
        async with ctx.bot._config.disabled_commands() as disabled_commands:
            with contextlib.suppress(ValueError):
                disabled_commands.remove(command.qualified_name)

        if command.enabled:
            await ctx.send(_("That command is already enabled globally."))
            return

        command.enabled = True
        await ctx.tick()

    @commands.guild_only()
    @command_enable.command(name="server", aliases=["guild"])
    async def command_enable_guild(self, ctx: commands.Context, *, command: CommandConverter):
        """
            Enable a command in this server.

        **Examples:**
        - `[p]command enable server userinfo` - Enables the `userinfo` command in the Mod cog.
        - `[p]command enable server urban` - Enables the `urban` command in the General cog.

        **Arguments:**
        - `<command>` - The command to enable for the current server.
        """
        if command.requires.privilege_level is not None:
            if command.requires.privilege_level > await PrivilegeLevel.from_ctx(ctx):
                await ctx.send(_("You are not allowed to enable that command."))
                return

        async with ctx.bot._config.guild(ctx.guild).disabled_commands() as disabled_commands:
            with contextlib.suppress(ValueError):
                disabled_commands.remove(command.qualified_name)

        done = command.enable_in(ctx.guild)

        if not done:
            await ctx.send(_("That command is already enabled in this server."))
        else:
            await ctx.tick()

    @commands.is_owner()
    @command_manager.command(name="disabledmsg")
    async def command_disabledmsg(self, ctx: commands.Context, *, message: str = ""):
        """Set the bot's response to disabled commands.

        Leave blank to send nothing.

        To include the command name in the message, include the `{command}` placeholder.

        **Examples:**
        - `[p]command disabledmsg This command is disabled`
        - `[p]command disabledmsg {command} is disabled`
        - `[p]command disabledmsg` - Sends nothing when a disabled command is attempted.

        **Arguments:**
        - `[message]` - The message to send when a disabled command is attempted.
        """
        await ctx.bot._config.disabled_command_msg.set(message)
        await ctx.tick()

    @commands.guild_only()
    @commands.guildowner_or_permissions(manage_guild=True)
    @commands.group(name="autoimmune")
    async def autoimmune_group(self, ctx: commands.Context):
        """
        Commands to manage server settings for immunity from automated actions.

        This includes duplicate message deletion and mention spam from the Mod cog, and filters from the Filter cog.
        """
        pass

    @autoimmune_group.command(name="list")
    async def autoimmune_list(self, ctx: commands.Context):
        """
        Gets the current members and roles configured for automatic moderation action immunity.

        **Example:**
        - `[p]autoimmune list`
        """
        ai_ids = await ctx.bot._config.guild(ctx.guild).autoimmune_ids()

        roles = {r.name for r in ctx.guild.roles if r.id in ai_ids}
        members = {str(m) for m in ctx.guild.members if m.id in ai_ids}

        output = ""
        if roles:
            output += _("Roles immune from automated moderation actions:\n")
            output += ", ".join(roles)
        if members:
            if roles:
                output += "\n"
            output += _("Members immune from automated moderation actions:\n")
            output += ", ".join(members)

        if not output:
            output = _("No immunity settings here.")

        for page in pagify(output):
            await ctx.send(page)

    @autoimmune_group.command(name="add")
    async def autoimmune_add(
        self, ctx: commands.Context, *, user_or_role: Union[discord.Member, discord.Role]
    ):
        """
        Makes a user or role immune from automated moderation actions.

        **Examples:**
        - `[p]autoimmune add @Twentysix` - Adds a user.
        - `[p]autoimmune add @Mods` - Adds a role.

        **Arguments:**
        - `<user_or_role>` - The user or role to add immunity to.
        """
        async with ctx.bot._config.guild(ctx.guild).autoimmune_ids() as ai_ids:
            if user_or_role.id in ai_ids:
                return await ctx.send(_("Already added."))
            ai_ids.append(user_or_role.id)
        await ctx.tick()

    @autoimmune_group.command(name="remove")
    async def autoimmune_remove(
        self, ctx: commands.Context, *, user_or_role: Union[discord.Member, discord.Role]
    ):
        """
        Remove a user or role from being immune to automated moderation actions.

        **Examples:**
        - `[p]autoimmune remove @Twentysix` - Removes a user.
        - `[p]autoimmune remove @Mods` - Removes a role.

        **Arguments:**
        - `<user_or_role>` - The user or role to remove immunity from.
        """
        async with ctx.bot._config.guild(ctx.guild).autoimmune_ids() as ai_ids:
            if user_or_role.id not in ai_ids:
                return await ctx.send(_("Not in list."))
            ai_ids.remove(user_or_role.id)
        await ctx.tick()

    @autoimmune_group.command(name="isimmune")
    async def autoimmune_checkimmune(
        self, ctx: commands.Context, *, user_or_role: Union[discord.Member, discord.Role]
    ):
        """
        Checks if a user or role would be considered immune from automated actions.

        **Examples:**
        - `[p]autoimmune isimmune @Twentysix`
        - `[p]autoimmune isimmune @Mods`

        **Arguments:**
        - `<user_or_role>` - The user or role to check the immunity of.
        """

        if await ctx.bot.is_automod_immune(user_or_role):
            await ctx.send(_("They are immune."))
        else:
            await ctx.send(_("They are not immune."))

    # RPC handlers
    async def rpc_load(self, request):
        cog_name = request.params[0]

        spec = await self.bot._cog_mgr.find_cog(cog_name)
        if spec is None:
            raise LookupError("No such cog found.")

        self._cleanup_and_refresh_modules(spec.name)

        await self.bot.load_extension(spec)

    async def rpc_unload(self, request):
        cog_name = request.params[0]

        await self.bot.unload_extension(cog_name)

    async def rpc_reload(self, request):
        await self.rpc_unload(request)
        await self.rpc_load(request)

    @commands.group()
    @commands.guild_only()
    @commands.admin_or_can_manage_channel()
    async def ignore(self, ctx: commands.Context):
        """
        Commands to add servers or channels to the ignore list.

        The ignore list will prevent the bot from responding to commands in the configured locations.

        Note: Owners and Admins override the ignore list.
        """

    @ignore.command(name="list")
    async def ignore_list(self, ctx: commands.Context):
        """
        List the currently ignored servers and channels.

        **Example:**
        - `[p]ignore list`
        """
        for page in pagify(await self.count_ignored(ctx)):
            await ctx.maybe_send_embed(page)

    @ignore.command(name="channel")
    async def ignore_channel(
        self,
        ctx: commands.Context,
        channel: Union[
            discord.TextChannel,
            discord.VoiceChannel,
            discord.StageChannel,
            discord.ForumChannel,
            discord.CategoryChannel,
            discord.Thread,
        ] = commands.CurrentChannel,
    ):
        """
        Ignore commands in the channel, thread, or category.

        Defaults to the current thread or channel.

        Note: Owners, Admins, and those with Manage Channel permissions override ignored channels.

        **Examples:**
        - `[p]ignore channel #general` - Ignores commands in the #general channel.
        - `[p]ignore channel` - Ignores commands in the current channel.
        - `[p]ignore channel "General Channels"` - Use quotes for categories with spaces.
        - `[p]ignore channel 356236713347252226` - Also accepts IDs.

        **Arguments:**
        - `<channel>` - The channel to ignore. This can also be a thread or category channel.
        """
        if not await self.bot._ignored_cache.get_ignored_channel(channel):
            await self.bot._ignored_cache.set_ignored_channel(channel, True)
            await ctx.send(_("Channel added to ignore list."))
        else:
            await ctx.send(_("Channel already in ignore list."))

    @ignore.command(name="server", aliases=["guild"])
    @commands.admin_or_permissions(manage_guild=True)
    async def ignore_guild(self, ctx: commands.Context):
        """
        Ignore commands in this server.

        Note: Owners, Admins, and those with Manage Server permissions override ignored servers.

        **Example:**
        - `[p]ignore server` - Ignores the current server
        """
        guild = ctx.guild
        if not await self.bot._ignored_cache.get_ignored_guild(guild):
            await self.bot._ignored_cache.set_ignored_guild(guild, True)
            await ctx.send(_("This server has been added to the ignore list."))
        else:
            await ctx.send(_("This server is already being ignored."))

    @commands.group()
    @commands.guild_only()
    @commands.admin_or_can_manage_channel()
    async def unignore(self, ctx: commands.Context):
        """Commands to remove servers or channels from the ignore list."""

    @unignore.command(name="channel")
    async def unignore_channel(
        self,
        ctx: commands.Context,
        channel: Union[
            discord.TextChannel,
            discord.VoiceChannel,
            discord.StageChannel,
            discord.ForumChannel,
            discord.CategoryChannel,
            discord.Thread,
        ] = commands.CurrentChannel,
    ):
        """
        Remove a channel, thread, or category from the ignore list.

        Defaults to the current thread or channel.

        **Examples:**
        - `[p]unignore channel #general` - Unignores commands in the #general channel.
        - `[p]unignore channel` - Unignores commands in the current channel.
        - `[p]unignore channel "General Channels"` - Use quotes for categories with spaces.
        - `[p]unignore channel 356236713347252226` - Also accepts IDs. Use this method to unignore categories.

        **Arguments:**
        - `<channel>` - The channel to unignore. This can also be a thread or category channel.
        """
        if await self.bot._ignored_cache.get_ignored_channel(channel):
            await self.bot._ignored_cache.set_ignored_channel(channel, False)
            await ctx.send(_("Channel removed from ignore list."))
        else:
            await ctx.send(_("That channel is not in the ignore list."))

    @unignore.command(name="server", aliases=["guild"])
    @commands.admin_or_permissions(manage_guild=True)
    async def unignore_guild(self, ctx: commands.Context):
        """
        Remove this server from the ignore list.

        **Example:**
        - `[p]unignore server` - Stops ignoring the current server
        """
        guild = ctx.message.guild
        if await self.bot._ignored_cache.get_ignored_guild(guild):
            await self.bot._ignored_cache.set_ignored_guild(guild, False)
            await ctx.send(_("This server has been removed from the ignore list."))
        else:
            await ctx.send(_("This server is not in the ignore list."))

    async def count_ignored(self, ctx: commands.Context):
        category_channels: List[discord.CategoryChannel] = []
        channels: List[
            Union[
                discord.TextChannel,
                discord.VoiceChannel,
                discord.StageChannel,
                discord.ForumChannel,
            ]
        ] = []
        threads: List[discord.Thread] = []
        if await self.bot._ignored_cache.get_ignored_guild(ctx.guild):
            return _("This server is currently being ignored.")
        for channel in itertools.chain(
            ctx.guild.text_channels,
            ctx.guild.voice_channels,
            ctx.guild.stage_channels,
            ctx.guild.forums,
        ):
            if channel.category and channel.category not in category_channels:
                if await self.bot._ignored_cache.get_ignored_channel(channel.category):
                    category_channels.append(channel.category)
            if await self.bot._ignored_cache.get_ignored_channel(channel, check_category=False):
                channels.append(channel)
        for thread in ctx.guild.threads:
            if await self.bot._ignored_cache.get_ignored_channel(thread, check_category=False):
                threads.append(thread)

        cat_str = (
            humanize_list([c.name for c in category_channels]) if category_channels else _("None")
        )
        chan_str = humanize_list([c.mention for c in channels]) if channels else _("None")
        thread_str = humanize_list([c.mention for c in threads]) if threads else _("None")
        msg = _(
            "Currently ignored categories: {categories}\n"
            "Channels: {channels}\n"
            "Threads (excluding archived):{threads}"
        ).format(categories=cat_str, channels=chan_str, threads=thread_str)
        return msg

    # Removing this command from forks is a violation of the GPLv3 under which it is licensed.
    # Otherwise interfering with the ability for this command to be accessible is also a violation.
    @commands.cooldown(1, 180, lambda ctx: (ctx.message.channel.id, ctx.message.author.id))
    @commands.command(
        cls=commands.commands._AlwaysAvailableCommand,
        name="licenseinfo",
        aliases=["licenceinfo"],
        i18n=_,
    )
    async def license_info_command(self, ctx):
        """
        Get info about Red's licenses.
        """

        message = (
            "This bot is an instance of Red-DiscordBot (hereinafter referred to as Red).\n"
            "Red is a free and open source application made available to the public and "
            "licensed under the GNU GPLv3. The full text of this license is available to you at "
            "<https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/LICENSE>."
        )
        await ctx.send(message)
        # We need a link which contains a thank you to other projects which we use at some point.
