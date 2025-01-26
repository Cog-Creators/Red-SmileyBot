import asyncio
import contextlib
import platform
import sys
import logging
import traceback
from datetime import datetime, timedelta, timezone
from typing import Tuple

import aiohttp
import discord
import importlib.metadata
from packaging.requirements import Requirement
from redbot.core import data_manager

from redbot.core.bot import ExitCodes
from redbot.core.commands import RedHelpFormatter, HelpSettings
from redbot.core.i18n import (
    Translator,
    set_contextual_locales_from_guild,
)
from .. import __version__ as red_version, version_info as red_version_info
from . import commands
from ._config import get_latest_confs
from .utils._internal_utils import (
    fuzzy_command_search,
    format_fuzzy_results,
    expected_version,
    fetch_latest_red_version_info,
    send_to_owners_with_prefix_replaced,
)
from .utils.chat_formatting import inline, format_perms_list

import rich
from rich import box
from rich.table import Table
from rich.columns import Columns
from rich.panel import Panel
from rich.text import Text

log = logging.getLogger("red")

INTRO = r"""
______         _           ______ _                       _  ______       _
| ___ \       | |          |  _  (_)                     | | | ___ \     | |
| |_/ /___  __| |  ______  | | | |_ ___  ___ ___  _ __ __| | | |_/ / ___ | |_
|    // _ \/ _` | |______| | | | | / __|/ __/ _ \| '__/ _` | | ___ \/ _ \| __|
| |\ \  __/ (_| |          | |/ /| \__ \ (_| (_) | | | (_| | | |_/ / (_) | |_
\_| \_\___|\__,_|          |___/ |_|___/\___\___/|_|  \__,_| \____/ \___/ \__|
"""

_ = Translator(__name__, __file__)


def get_outdated_red_messages(pypi_version: str, py_version_req: str) -> Tuple[str, str]:
    outdated_red_message = _(
        "Your Red instance is out of date! {} is the current version, however you are using {}!"
    ).format(pypi_version, red_version)
    rich_outdated_message = (
        f"[red]Outdated version![/red]\n"
        f"[red]!!![/red]Version [cyan]{pypi_version}[/] is available, "
        f"but you're using [cyan]{red_version}[/][red]!!![/red]"
    )
    current_python = platform.python_version()
    extra_update = _(
        "\n\nWhile the following command should work in most scenarios as it is "
        "based on your current OS, environment, and Python version, "
        "**we highly recommend you to read the update docs at <{docs}> and "
        "make sure there is nothing else that "
        "needs to be done during the update.**"
    ).format(docs="https://docs.discord.red/en/stable/update_red.html")

    if not expected_version(current_python, py_version_req):
        extra_update += _(
            "\n\nYou have Python `{py_version}` and this update "
            "requires `{req_py}`; you cannot simply run the update command.\n\n"
            "You will need to follow the update instructions in our docs above, "
            "if you still need help updating after following the docs go to our "
            "#support channel in <https://discord.gg/red>"
        ).format(py_version=current_python, req_py=py_version_req)
        outdated_red_message += extra_update
        return outdated_red_message, rich_outdated_message

    red_dist = importlib.metadata.distribution("Red-DiscordBot")
    installed_extras = red_dist.metadata.get_all("Provides-Extra")
    installed_extras.remove("dev")
    installed_extras.remove("all")
    distributions = {}
    for req_str in red_dist.requires:
        req = Requirement(req_str)
        if req.marker is None or req.marker.evaluate():
            continue
        for extra in reversed(installed_extras):
            if not req.marker.evaluate({"extra": extra}):
                continue

            # Check that the requirement is met.
            # This is a bit simplified for our purposes and does not check
            # whether the requirements of our requirements are met as well.
            # This could potentially be an issue if we'll ever depend on
            # a dependency's extra in our extra when we already depend on that
            # in our base dependencies. However, considering that right now, all
            # our dependencies are also fully pinned, this should not ever matter.
            if req.name in distributions:
                dist = distributions[req.name]
            else:
                try:
                    dist = importlib.metadata.distribution(req.name)
                except importlib.metadata.PackageNotFoundError:
                    dist = None
                distributions[req.name] = dist
            if dist is None or not req.specifier.contains(dist.version, prereleases=True):
                installed_extras.remove(extra)

    if installed_extras:
        package_extras = f"[{','.join(installed_extras)}]"
    else:
        package_extras = ""

    extra_update += _(
        "\n\nTo update your bot, first shutdown your bot"
        " then open a window of {console} (Not as admin) and run the following:"
        "{command_1}\n"
        "Once you've started up your bot again, we recommend that"
        " you update any installed 3rd-party cogs with this command in Discord:"
        "{command_2}"
    ).format(
        console=_("Command Prompt") if platform.system() == "Windows" else _("Terminal"),
        command_1=f'```"{sys.executable}" -m pip install -U "Red-DiscordBot{package_extras}"```',
        command_2=f"```[p]cog update```",
    )
    outdated_red_message += extra_update
    return outdated_red_message, rich_outdated_message


def init_events(bot, cli_flags):
    @bot.event
    async def on_connect():
        if bot._uptime is None:
            log.info("Connected to Discord. Getting ready...")

    @bot.event
    async def on_ready():
        try:
            await _on_ready()
        except Exception as exc:
            log.critical("The bot failed to get ready!", exc_info=exc)
            sys.exit(ExitCodes.CRITICAL)

    async def _on_ready():
        if bot._uptime is not None:
            return

        bot._uptime = datetime.utcnow()

        guilds = len(bot.guilds)
        users = len(set([m for m in bot.get_all_members()]))

        invite_url = discord.utils.oauth_url(bot.application_id, scopes=("bot",))

        prefixes = cli_flags.prefix or (await bot._config.prefix())
        lang = await bot._config.locale()
        dpy_version = discord.__version__

        table_general_info = Table(show_edge=False, show_header=False, box=box.MINIMAL)
        table_general_info.add_row("Prefixes", ", ".join(prefixes))
        table_general_info.add_row("Language", lang)
        table_general_info.add_row("Red version", red_version)
        table_general_info.add_row("Discord.py version", dpy_version)
        table_general_info.add_row("Storage type", data_manager.storage_type())

        table_counts = Table(show_edge=False, show_header=False, box=box.MINIMAL)
        # String conversion is needed as Rich doesn't deal with ints
        table_counts.add_row("Shards", str(bot.shard_count))
        table_counts.add_row("Servers", str(guilds))
        if bot.intents.members:  # Lets avoid 0 Unique Users
            table_counts.add_row("Unique Users", str(users))

        outdated_red_message = ""
        rich_outdated_message = ""
        pypi_version, py_version_req = await fetch_latest_red_version_info()
        outdated = pypi_version and pypi_version > red_version_info
        if outdated:
            outdated_red_message, rich_outdated_message = get_outdated_red_messages(
                pypi_version, py_version_req
            )

        rich_console = rich.get_console()
        rich_console.print(INTRO, style="red", markup=False, highlight=False)
        if guilds:
            rich_console.print(
                Columns(
                    [Panel(table_general_info, title=bot.user.display_name), Panel(table_counts)],
                    equal=True,
                    align="center",
                )
            )
        else:
            rich_console.print(Columns([Panel(table_general_info, title=bot.user.display_name)]))

        rich_console.print(
            "Loaded {} cogs with {} commands".format(len(bot.cogs), len(bot.commands))
        )

        if invite_url:
            rich_console.print(f"\nInvite URL: {Text(invite_url, style=f'link {invite_url}')}")
            # We generally shouldn't care if the client supports it or not as Rich deals with it.
        if not guilds:
            rich_console.print(
                f"Looking for a quick guide on setting up Red? Checkout {Text('https://start.discord.red', style='link https://start.discord.red}')}"
            )
        if rich_outdated_message:
            rich_console.print(rich_outdated_message)

        bot._red_ready.set()
        if outdated_red_message:
            await send_to_owners_with_prefix_replaced(bot, outdated_red_message)

    @bot.event
    async def on_command_completion(ctx: commands.Context):
        await bot._delete_delay(ctx)

    @bot.event
    async def on_command_error(ctx, error, unhandled_by_cog=False):
        if not unhandled_by_cog:
            if hasattr(ctx.command, "on_error"):
                return

            if ctx.cog:
                if ctx.cog.has_error_handler():
                    return
        if not isinstance(error, commands.CommandNotFound):
            asyncio.create_task(bot._delete_delay(ctx))
        converter = getattr(ctx.current_parameter, "converter", None)
        argument = ctx.current_argument

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send_help()
        elif isinstance(error, commands.ArgParserFailure):
            msg = _("`{user_input}` is not a valid value for `{command}`").format(
                user_input=error.user_input, command=error.cmd
            )
            if error.custom_help_msg:
                msg += f"\n{error.custom_help_msg}"
            await ctx.send(msg)
            if error.send_cmd_help:
                await ctx.send_help()
        elif isinstance(error, commands.RangeError):
            if isinstance(error.value, int):
                if error.minimum == 0 and error.maximum is None:
                    message = _("Argument `{parameter_name}` must be a positive integer.")
                elif error.minimum is None and error.maximum is not None:
                    message = _(
                        "Argument `{parameter_name}` must be an integer no more than {maximum}."
                    )
                elif error.minimum is not None and error.maximum is None:
                    message = _(
                        "Argument `{parameter_name}` must be an integer no less than {minimum}."
                    )
                elif error.maximum is not None and error.minimum is not None:
                    message = _(
                        "Argument `{parameter_name}` must be an integer between {minimum} and {maximum}."
                    )
            elif isinstance(error.value, float):
                if error.minimum == 0 and error.maximum is None:
                    message = _("Argument `{parameter_name}` must be a positive number.")
                elif error.minimum is None and error.maximum is not None:
                    message = _(
                        "Argument `{parameter_name}` must be a number no more than {maximum}."
                    )
                elif error.minimum is not None and error.maximum is None:
                    message = _(
                        "Argument `{parameter_name}` must be a number no less than {maximum}."
                    )
                elif error.maximum is not None and error.minimum is not None:
                    message = _(
                        "Argument `{parameter_name}` must be a number between {minimum} and {maximum}."
                    )
            elif isinstance(error.value, str):
                if error.minimum is None and error.maximum is not None:
                    message = _(
                        "Argument `{parameter_name}` must be a string with a length of no more than {maximum}."
                    )
                elif error.minimum is not None and error.maximum is None:
                    message = _(
                        "Argument `{parameter_name}` must be a string with a length of no less than {minimum}."
                    )
                elif error.maximum is not None and error.minimum is not None:
                    message = _(
                        "Argument `{parameter_name}` must be a string with a length of between {minimum} and {maximum}."
                    )
            await ctx.send(
                message.format(
                    maximum=error.maximum,
                    minimum=error.minimum,
                    parameter_name=ctx.current_parameter.name,
                )
            )
            return
        elif isinstance(error, commands.BadArgument):
            if isinstance(converter, commands.Range):
                if converter.annotation is int:
                    if converter.min == 0 and converter.max is None:
                        message = _("Argument `{parameter_name}` must be a positive integer.")
                    elif converter.min is None and converter.max is not None:
                        message = _(
                            "Argument `{parameter_name}` must be an integer no more than {maximum}."
                        )
                    elif converter.min is not None and converter.max is None:
                        message = _(
                            "Argument `{parameter_name}` must be an integer no less than {minimum}."
                        )
                    elif converter.max is not None and converter.min is not None:
                        message = _(
                            "Argument `{parameter_name}` must be an integer between {minimum} and {maximum}."
                        )
                elif converter.annotation is float:
                    if converter.min == 0 and converter.max is None:
                        message = _("Argument `{parameter_name}` must be a positive number.")
                    elif converter.min is None and converter.max is not None:
                        message = _(
                            "Argument `{parameter_name}` must be a number no more than {maximum}."
                        )
                    elif converter.min is not None and converter.max is None:
                        message = _(
                            "Argument `{parameter_name}` must be a number no less than {minimum}."
                        )
                    elif converter.max is not None and converter.min is not None:
                        message = _(
                            "Argument `{parameter_name}` must be a number between {minimum} and {maximum}."
                        )
                elif converter.annotation is str:
                    if error.minimum is None and error.maximum is not None:
                        message = _(
                            "Argument `{parameter_name}` must be a string with a length of no more than {maximum}."
                        )
                    elif error.minimum is not None and error.maximum is None:
                        message = _(
                            "Argument `{parameter_name}` must be a string with a length of no less than {minimum}."
                        )
                    elif error.maximum is not None and error.minimum is not None:
                        message = _(
                            "Argument `{parameter_name}` must be a string with a length of between {minimum} and {maximum}."
                        )
                await ctx.send(
                    message.format(
                        maximum=converter.max,
                        minimum=converter.min,
                        parameter_name=ctx.current_parameter.name,
                    )
                )
                return
            if isinstance(error.__cause__, ValueError):
                if converter is int:
                    await ctx.send(_('"{argument}" is not an integer.').format(argument=argument))
                    return
                if converter is float:
                    await ctx.send(_('"{argument}" is not a number.').format(argument=argument))
                    return
            if error.args:
                await ctx.send(error.args[0])
            else:
                await ctx.send_help()
        elif isinstance(error, commands.UserInputError):
            await ctx.send_help()
        elif isinstance(error, commands.DisabledCommand):
            disabled_message = await bot._config.disabled_command_msg()
            if disabled_message:
                await ctx.send(disabled_message.replace("{command}", ctx.invoked_with))
        elif isinstance(error, commands.CommandInvokeError):
            log.exception(
                "Exception in command '{}'".format(ctx.command.qualified_name),
                exc_info=error.original,
            )
            exception_log = "Exception in command '{}'\n" "".format(ctx.command.qualified_name)
            exception_log += "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            bot._last_exception = exception_log

            message = await bot._config.invoke_error_msg()
            if not message:
                if ctx.author.id in bot.owner_ids:
                    message = inline(
                        _("Error in command '{command}'. Check your console or logs for details.")
                    )
                else:
                    message = inline(_("Error in command '{command}'."))
            await ctx.send(message.replace("{command}", ctx.command.qualified_name))
        elif isinstance(error, commands.CommandNotFound):
            help_settings = await HelpSettings.from_context(ctx)
            fuzzy_commands = await fuzzy_command_search(
                ctx,
                commands=RedHelpFormatter.help_filter_func(
                    ctx, bot.walk_commands(), help_settings=help_settings
                ),
            )
            if not fuzzy_commands:
                pass
            elif await ctx.embed_requested():
                await ctx.send(embed=await format_fuzzy_results(ctx, fuzzy_commands, embed=True))
            else:
                await ctx.send(await format_fuzzy_results(ctx, fuzzy_commands, embed=False))
        elif isinstance(error, commands.BotMissingPermissions):
            if bin(error.missing.value).count("1") == 1:  # Only one perm missing
                msg = _("I require the {permission} permission to execute that command.").format(
                    permission=format_perms_list(error.missing)
                )
            else:
                msg = _("I require {permission_list} permissions to execute that command.").format(
                    permission_list=format_perms_list(error.missing)
                )
            await ctx.send(msg)
        elif isinstance(error, commands.UserFeedbackCheckFailure):
            if error.message:
                await ctx.send(error.message)
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send(_("That command is not available in DMs."))
        elif isinstance(error, commands.PrivateMessageOnly):
            await ctx.send(_("That command is only available in DMs."))
        elif isinstance(error, commands.NSFWChannelRequired):
            await ctx.send(_("That command is only available in NSFW channels."))
        elif isinstance(error, commands.CheckFailure):
            pass
        elif isinstance(error, commands.CommandOnCooldown):
            if bot._bypass_cooldowns and ctx.author.id in bot.owner_ids:
                ctx.command.reset_cooldown(ctx)
                new_ctx = await bot.get_context(ctx.message)
                await bot.invoke(new_ctx)
                return
            relative_time = discord.utils.format_dt(
                datetime.now(timezone.utc) + timedelta(seconds=error.retry_after), "R"
            )
            msg = _("This command is on cooldown. Try again {relative_time}.").format(
                relative_time=relative_time
            )
            await ctx.send(msg, delete_after=error.retry_after)
        elif isinstance(error, commands.MaxConcurrencyReached):
            if error.per is commands.BucketType.default:
                if error.number > 1:
                    msg = _(
                        "Too many people using this command."
                        " It can only be used {number} times concurrently."
                    ).format(number=error.number)
                else:
                    msg = _(
                        "Too many people using this command."
                        " It can only be used once concurrently."
                    )
            elif error.per in (commands.BucketType.user, commands.BucketType.member):
                if error.number > 1:
                    msg = _(
                        "That command is still completing,"
                        " it can only be used {number} times per {type} concurrently."
                    ).format(number=error.number, type=error.per.name)
                else:
                    msg = _(
                        "That command is still completing,"
                        " it can only be used once per {type} concurrently."
                    ).format(type=error.per.name)
            else:
                if error.number > 1:
                    msg = _(
                        "Too many people using this command."
                        " It can only be used {number} times per {type} concurrently."
                    ).format(number=error.number, type=error.per.name)
                else:
                    msg = _(
                        "Too many people using this command."
                        " It can only be used once per {type} concurrently."
                    ).format(type=error.per.name)
            await ctx.send(msg)
        else:
            log.exception(type(error).__name__, exc_info=error)

    @bot.event
    async def on_message(message, /):
        await set_contextual_locales_from_guild(bot, message.guild)

        await bot.process_commands(message)
        discord_now = message.created_at
        if (
            not bot._checked_time_accuracy
            or (discord_now - timedelta(minutes=60)) > bot._checked_time_accuracy
        ):
            system_now = datetime.now(timezone.utc)
            diff = abs((discord_now - system_now).total_seconds())
            if diff > 60:
                log.warning(
                    "Detected significant difference (%d seconds) in system clock to discord's "
                    "clock. Any time sensitive code may fail.",
                    diff,
                )
            bot._checked_time_accuracy = discord_now

    @bot.event
    async def on_command_add(command: commands.Command):
        if command.cog is not None:
            return

        await _disable_command_no_cog(command)

    async def _guild_added(guild: discord.Guild):
        disabled_commands = await bot._config.guild(guild).disabled_commands()
        for command_name in disabled_commands:
            command_obj = bot.get_command(command_name)
            if command_obj is not None:
                command_obj.disable_in(guild)

    @bot.event
    async def on_guild_join(guild: discord.Guild):
        await _guild_added(guild)

    @bot.event
    async def on_guild_available(guild: discord.Guild):
        # We need to check guild-disabled commands here since some cogs
        # are loaded prior to `on_ready`.
        await _guild_added(guild)

    @bot.event
    async def on_guild_remove(guild: discord.Guild):
        # Clean up any unneeded checks
        disabled_commands = await bot._config.guild(guild).disabled_commands()
        for command_name in disabled_commands:
            command_obj = bot.get_command(command_name)
            if command_obj is not None:
                command_obj.enable_in(guild)

    @bot.event
    async def on_cog_add(cog: commands.Cog):
        confs = get_latest_confs()
        for c in confs:
            uuid = c.unique_identifier
            group_data = c.custom_groups
            await bot._config.custom("CUSTOM_GROUPS", c.cog_name, uuid).set(group_data)

        await _disable_commands_cog(cog)

    async def _disable_command(
        command: commands.Command, global_disabled: list, guilds_data: dict
    ):
        if command.qualified_name in global_disabled:
            command.enabled = False
        for guild_id, data in guilds_data.items():
            guild_disabled_cmds = data.get("disabled_commands", [])
            if command.qualified_name in guild_disabled_cmds:
                command.disable_in(discord.Object(id=guild_id))

    async def _disable_commands_cog(cog: commands.Cog):
        global_disabled = await bot._config.disabled_commands()
        guilds_data = await bot._config.all_guilds()
        for command in cog.walk_commands():
            await _disable_command(command, global_disabled, guilds_data)

    async def _disable_command_no_cog(command: commands.Command):
        global_disabled = await bot._config.disabled_commands()
        guilds_data = await bot._config.all_guilds()
        await _disable_command(command, global_disabled, guilds_data)
