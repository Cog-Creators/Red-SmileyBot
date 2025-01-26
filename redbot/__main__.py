from redbot import _early_init

# this needs to be called as early as possible
_early_init()

import asyncio
import functools
import getpass
import json
import logging
import os
import pip
import platform
import shutil
import signal
import sys
from argparse import Namespace
from copy import deepcopy
from pathlib import Path
from typing import Any, Awaitable, Callable, NoReturn, Optional, Union

import discord
import rich

import redbot.logging
from redbot import __version__
from redbot.core.bot import Red, ExitCodes, _NoOwnerSet
from redbot.core._cli import interactive_config, confirm, parse_cli_flags
from redbot.setup import get_data_dir, get_name, save_config
from redbot.core import data_manager, _drivers
from redbot.core._debuginfo import DebugInfo
from redbot.core._sharedlibdeprecation import SharedLibImportWarner


log = logging.getLogger("red.main")

#
#               Red - Discord Bot v3
#
#         Made by Twentysix, improved by many
#


def _get_instance_names():
    with data_manager.config_file.open(encoding="utf-8") as fs:
        data = json.load(fs)
    return sorted(data.keys())


def list_instances():
    if not data_manager.config_file.exists():
        print(
            "No instances have been configured! Configure one "
            "using `redbot-setup` before trying to run the bot!"
        )
        sys.exit(ExitCodes.CONFIGURATION_ERROR)
    else:
        text = "Configured Instances:\n\n"
        for instance_name in _get_instance_names():
            text += "{}\n".format(instance_name)
        print(text)
        sys.exit(ExitCodes.SHUTDOWN)


async def debug_info(red: Optional[Red] = None, *args: Any) -> None:
    """Shows debug information useful for debugging."""
    print(await DebugInfo(red).get_cli_text())


async def edit_instance(red, cli_flags):
    no_prompt = cli_flags.no_prompt
    token = cli_flags.token
    owner = cli_flags.owner
    prefix = cli_flags.prefix
    old_name = cli_flags.instance_name
    new_name = cli_flags.edit_instance_name
    data_path = cli_flags.edit_data_path
    copy_data = cli_flags.copy_data
    confirm_overwrite = cli_flags.overwrite_existing_instance

    if data_path is None and copy_data:
        print("--copy-data can't be used without --edit-data-path argument")
        sys.exit(ExitCodes.INVALID_CLI_USAGE)
    if new_name is None and confirm_overwrite:
        print("--overwrite-existing-instance can't be used without --edit-instance-name argument")
        sys.exit(ExitCodes.INVALID_CLI_USAGE)
    if (
        no_prompt
        and all(to_change is None for to_change in (token, owner, new_name, data_path))
        and not prefix
    ):
        print(
            "No arguments to edit were provided."
            " Available arguments (check help for more information):"
            " --edit-instance-name, --edit-data-path, --copy-data, --owner, --token, --prefix"
        )
        sys.exit(ExitCodes.INVALID_CLI_USAGE)

    await _edit_token(red, token, no_prompt)
    await _edit_prefix(red, prefix, no_prompt)
    await _edit_owner(red, owner, no_prompt)

    data = deepcopy(data_manager.basic_config)
    name = _edit_instance_name(old_name, new_name, confirm_overwrite, no_prompt)
    _edit_data_path(data, name, data_path, copy_data, no_prompt)

    save_config(name, data)
    if old_name != name:
        save_config(old_name, {}, remove=True)


async def _edit_token(red, token, no_prompt):
    if token:
        if not len(token) >= 50:
            print(
                "The provided token doesn't look a valid Discord bot token."
                " Instance's token will remain unchanged.\n"
            )
            return
        await red._config.token.set(token)
    elif not no_prompt and confirm("Would you like to change instance's token?", default=False):
        await interactive_config(red, False, True, print_header=False)
        print("Token updated.\n")


async def _edit_prefix(red, prefix, no_prompt):
    if prefix:
        prefixes = sorted(prefix, reverse=True)
        await red._config.prefix.set(prefixes)
    elif not no_prompt and confirm("Would you like to change instance's prefixes?", default=False):
        print(
            "Enter the prefixes, separated by a space (please note "
            "that prefixes containing a space will need to be added with [p]set prefix)"
        )
        while True:
            prefixes = input("> ").strip().split()
            if not prefixes:
                print("You need to pass at least one prefix!")
                continue
            if any(prefix.startswith("/") for prefix in prefixes):
                print(
                    "Prefixes cannot start with '/', as it conflicts with Discord's slash commands."
                )
                continue
            prefixes = sorted(prefixes, reverse=True)
            await red._config.prefix.set(prefixes)
            print("Prefixes updated.\n")
            break


async def _edit_owner(red, owner, no_prompt):
    if owner:
        if not (15 <= len(str(owner)) <= 20):
            print(
                "The provided owner id doesn't look like a valid Discord user id."
                " Instance's owner will remain unchanged."
            )
            return
        await red._config.owner.set(owner)
    elif not no_prompt and confirm("Would you like to change instance's owner?", default=False):
        print(
            "Remember:\n"
            "ONLY the person who is hosting Red should be owner."
            " This has SERIOUS security implications."
            " The owner can access any data that is present on the host system.\n"
        )
        if confirm("Are you sure you want to change instance's owner?", default=False):
            print("Please enter a Discord user id for new owner:")
            while True:
                owner_id = input("> ").strip()
                if not (15 <= len(owner_id) <= 20 and owner_id.isdecimal()):
                    print("That doesn't look like a valid Discord user id.")
                    continue
                owner_id = int(owner_id)
                await red._config.owner.set(owner_id)
                print("Owner updated.")
                break
        else:
            print("Instance's owner will remain unchanged.")
        print()


def _edit_instance_name(old_name, new_name, confirm_overwrite, no_prompt):
    if new_name:
        name = new_name
        if name in _get_instance_names() and not confirm_overwrite:
            name = old_name
            print(
                "An instance with this name already exists.\n"
                "If you want to remove the existing instance and replace it with this one,"
                " run this command with --overwrite-existing-instance flag."
            )
    elif not no_prompt and confirm("Would you like to change the instance name?", default=False):
        name = get_name("")
        if name in _get_instance_names():
            print(
                "WARNING: An instance already exists with this name. "
                "Continuing will overwrite the existing instance config."
            )
            if not confirm(
                "Are you absolutely certain you want to continue with this instance name?",
                default=False,
            ):
                print("Instance name will remain unchanged.")
                name = old_name
            else:
                print("Instance name updated.")
        else:
            print("Instance name updated.")
        print()
    else:
        name = old_name
    return name


def _edit_data_path(data, instance_name, data_path, copy_data, no_prompt):
    # This modifies the passed dict.
    if data_path:
        new_path = Path(data_path)
        try:
            exists = new_path.exists()
        except OSError:
            print(
                "We were unable to check your chosen directory."
                " Provided path may contain an invalid character."
                " Data location will remain unchanged."
            )

        if not exists:
            try:
                new_path.mkdir(parents=True, exist_ok=True)
            except OSError:
                print(
                    "We were unable to create your chosen directory."
                    " Data location will remain unchanged."
                )
        data["DATA_PATH"] = data_path
        if copy_data and not _copy_data(data):
            print("Can't copy data to non-empty location. Data location will remain unchanged.")
            data["DATA_PATH"] = data_manager.basic_config["DATA_PATH"]
    elif not no_prompt and confirm("Would you like to change the data location?", default=False):
        data["DATA_PATH"] = get_data_dir(
            instance_name=instance_name, data_path=None, interactive=True
        )
        if confirm("Do you want to copy the data from old location?", default=True):
            if not _copy_data(data):
                print("Can't copy the data to non-empty location.")
                if not confirm("Do you still want to use the new data location?"):
                    data["DATA_PATH"] = data_manager.basic_config["DATA_PATH"]
                    print("Data location will remain unchanged.")
                    return
            print("Old data has been copied over to the new location.")
        print("Data location updated.")


def _copy_data(data):
    if Path(data["DATA_PATH"]).exists():
        if any(os.scandir(data["DATA_PATH"])):
            return False
        else:
            # this is needed because copytree doesn't work when destination folder exists
            # Python 3.8 has `dirs_exist_ok` option for that
            os.rmdir(data["DATA_PATH"])
    shutil.copytree(data_manager.basic_config["DATA_PATH"], data["DATA_PATH"])
    return True


def early_exit_runner(
    cli_flags: Namespace,
    func: Union[Callable[[], Awaitable[Any]], Callable[[Red, Namespace], Awaitable[Any]]],
) -> NoReturn:
    """
    This one exists to not log all the things like it's a full run of the bot.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        if not cli_flags.instance_name:
            loop.run_until_complete(func())
            sys.exit(ExitCodes.SHUTDOWN)
            return

        data_manager.load_basic_configuration(cli_flags.instance_name)
        red = Red(cli_flags=cli_flags, description="Red V3", dm_help=None)
        driver_cls = _drivers.get_driver_class()
        loop.run_until_complete(driver_cls.initialize(**data_manager.storage_details()))
        loop.run_until_complete(func(red, cli_flags))
        loop.run_until_complete(driver_cls.teardown())
    except (KeyboardInterrupt, EOFError):
        print("Aborted!")
    finally:
        # note: sleep is unnecessary since we're not making any network connections
        asyncio.set_event_loop(None)
        loop.stop()
        loop.close()

    sys.exit(ExitCodes.SHUTDOWN)


async def run_bot(red: Red, cli_flags: Namespace) -> None:
    """
    This runs the bot.

    Any shutdown which is a result of not being able to log in needs to raise
    a SystemExit exception.

    If the bot starts normally, the bot should be left to handle the exit case.
    It will raise SystemExit in a task, which will reach the event loop and
    interrupt running forever, then trigger our cleanup process, and does not
    need additional handling in this function.
    """

    driver_cls = _drivers.get_driver_class()

    await driver_cls.initialize(**data_manager.storage_details())

    redbot.logging.init_logging(
        level=cli_flags.logging_level,
        location=data_manager.core_data_path() / "logs",
        cli_flags=cli_flags,
    )

    log.debug("====Basic Config====")
    log.debug("Data Path: %s", data_manager._base_data_path())
    log.debug("Storage Type: %s", data_manager.storage_type())

    # lib folder has to be in sys.path before trying to load any 3rd-party cog (GH-3061)
    # We might want to change handling of requirements in Downloader at later date
    LIB_PATH = data_manager.cog_data_path(raw_name="Downloader") / "lib"
    LIB_PATH.mkdir(parents=True, exist_ok=True)
    if str(LIB_PATH) not in sys.path:
        sys.path.append(str(LIB_PATH))

        # "It's important to note that the global `working_set` object is initialized from
        # `sys.path` when `pkg_resources` is first imported, but is only updated if you do
        # all future `sys.path` manipulation via `pkg_resources` APIs. If you manually modify
        # `sys.path`, you must invoke the appropriate methods on the `working_set` instance
        # to keep it in sync."
        # Source: https://setuptools.readthedocs.io/en/latest/pkg_resources.html#workingset-objects
        pkg_resources = sys.modules.get("pkg_resources")
        if pkg_resources is not None:
            pkg_resources.working_set.add_entry(str(LIB_PATH))
    sys.meta_path.insert(0, SharedLibImportWarner())

    if cli_flags.token:
        token = cli_flags.token
    else:
        token = os.environ.get("RED_TOKEN", None)
        if not token:
            token = await red._config.token()

    prefix = cli_flags.prefix or await red._config.prefix()

    if not (token and prefix):
        if cli_flags.no_prompt is False:
            new_token = await interactive_config(
                red, token_set=bool(token), prefix_set=bool(prefix)
            )
            if new_token:
                token = new_token
        else:
            log.critical("Token and prefix must be set in order to login.")
            sys.exit(ExitCodes.CONFIGURATION_ERROR)

    if cli_flags.dry_run:
        sys.exit(ExitCodes.SHUTDOWN)
    try:
        # `async with red:` is unnecessary here because we call red.close() in shutdown handler
        await red.start(token)
    except discord.LoginFailure:
        log.critical("This token doesn't seem to be valid.")
        db_token = await red._config.token()
        if db_token and not cli_flags.no_prompt:
            if confirm("\nDo you want to reset the token?"):
                await red._config.token.set("")
                print("Token has been reset.")
                sys.exit(ExitCodes.SHUTDOWN)
        sys.exit(ExitCodes.CONFIGURATION_ERROR)
    except discord.PrivilegedIntentsRequired:
        console = rich.get_console()
        console.print(
            "Red requires all Privileged Intents to be enabled.\n"
            "You can find out how to enable Privileged Intents with this guide:\n"
            "https://docs.discord.red/en/stable/bot_application_guide.html#enabling-privileged-intents",
            style="red",
        )
        sys.exit(ExitCodes.CONFIGURATION_ERROR)
    except _NoOwnerSet:
        print(
            "Bot doesn't have any owner set!\n"
            "This can happen when your bot's application is owned by team"
            " as team members are NOT owners by default.\n\n"
            "Remember:\n"
            "ONLY the person who is hosting Red should be owner."
            " This has SERIOUS security implications."
            " The owner can access any data that is present on the host system.\n"
            "With that out of the way, depending on who you want to be considered as owner,"
            " you can:\n"
            "a) pass --team-members-are-owners when launching Red"
            " - in this case Red will treat members of the bot application's team as owners,"
            " if their team role is Owner, Admin, or Developer\n"
            f"b) set owner manually with `redbot --edit {cli_flags.instance_name}`\n"
            "c) pass owner ID(s) when launching Red with --owner"
            " (and --co-owner if you need more than one) flag\n"
        )
        sys.exit(ExitCodes.CONFIGURATION_ERROR)

    return None


def handle_early_exit_flags(cli_flags: Namespace):
    if cli_flags.list_instances:
        list_instances()
    elif cli_flags.version:
        print("Red V3")
        print("Current Version: {}".format(__version__))
        sys.exit(ExitCodes.SHUTDOWN)
    elif cli_flags.debuginfo:
        early_exit_runner(cli_flags, debug_info)
    elif not cli_flags.instance_name and (not cli_flags.no_instance or cli_flags.edit):
        print("Error: No instance name was provided!")
        sys.exit(ExitCodes.INVALID_CLI_USAGE)


async def shutdown_handler(red, signal_type=None, exit_code=None):
    if signal_type:
        log.info("%s received. Quitting...", signal_type.name)
        # Do not collapse the below line into other logic
        # We need to renter this function
        # after it interrupts the event loop.
        sys.exit(ExitCodes.SHUTDOWN)
    elif exit_code is None:
        log.info("Shutting down from unhandled exception")
        red._shutdown_mode = ExitCodes.CRITICAL

    if exit_code is not None:
        red._shutdown_mode = exit_code

    try:
        if not red.is_closed():
            await red.close()
    finally:
        # Then cancels all outstanding tasks other than ourselves
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in pending]
        await asyncio.gather(*pending, return_exceptions=True)


def global_exception_handler(red, loop, context):
    """
    Logs unhandled exceptions in other tasks
    """
    exc = context.get("exception")
    # These will get handled later when it *also* kills loop.run_forever
    if exc is not None and isinstance(exc, (KeyboardInterrupt, SystemExit)):
        return
    loop.default_exception_handler(context)


def red_exception_handler(red, red_task: asyncio.Future):
    """
    This is set as a done callback for Red

    must be used with functools.partial

    If the main bot.run dies for some reason,
    we don't want to swallow the exception and hang.
    """
    try:
        red_task.result()
    except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
        pass  # Handled by the global_exception_handler, or cancellation
    except Exception as exc:
        log.critical("The main bot task didn't handle an exception and has crashed", exc_info=exc)
        log.warning("Attempting to die as gracefully as possible...")
        asyncio.create_task(shutdown_handler(red))


def main():
    red = None  # Error handling for users misusing the bot
    cli_flags = parse_cli_flags(sys.argv[1:])
    handle_early_exit_flags(cli_flags)
    if cli_flags.edit:
        early_exit_runner(cli_flags, edit_instance)
        return
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        if cli_flags.no_instance:
            print(
                "\033[1m"
                "Warning: The data will be placed in a temporary folder and removed on next system "
                "reboot."
                "\033[0m"
            )
            cli_flags.instance_name = "temporary_red"
            data_manager.create_temp_config()

        data_manager.load_basic_configuration(cli_flags.instance_name)

        red = Red(cli_flags=cli_flags, description="Red V3", dm_help=None)

        if os.name != "nt":
            # None of this works on windows.
            # At least it's not a redundant handler...
            signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
            for s in signals:
                loop.add_signal_handler(
                    s, lambda s=s: asyncio.create_task(shutdown_handler(red, s))
                )

        exc_handler = functools.partial(global_exception_handler, red)
        loop.set_exception_handler(exc_handler)
        # We actually can't (just) use asyncio.run here
        # We probably could if we didn't support windows, but we might run into
        # a scenario where this isn't true if anyone works on RPC more in the future
        fut = loop.create_task(run_bot(red, cli_flags))
        r_exc_handler = functools.partial(red_exception_handler, red)
        fut.add_done_callback(r_exc_handler)
        loop.run_forever()
    except KeyboardInterrupt:
        # We still have to catch this here too. (*joy*)
        log.warning("Please do not use Ctrl+C to Shutdown Red! (attempting to die gracefully...)")
        log.error("Received KeyboardInterrupt, treating as interrupt")
        if red is not None:
            loop.run_until_complete(shutdown_handler(red, signal.SIGINT))
    except SystemExit as exc:
        # We also have to catch this one here. Basically any exception which normally
        # Kills the python interpreter (Base Exceptions minus asyncio.cancelled)
        # We need to do something with prior to having the loop close
        exit_code = int(exc.code)
        try:
            exit_code_name = ExitCodes(exit_code).name
        except ValueError:
            exit_code_name = "UNKNOWN"
        log.info("Shutting down with exit code: %s (%s)", exit_code, exit_code_name)
        if red is not None:
            loop.run_until_complete(shutdown_handler(red, None, exc.code))
    except Exception as exc:  # Non standard case.
        log.exception("Unexpected exception (%s): ", type(exc), exc_info=exc)
        if red is not None:
            loop.run_until_complete(shutdown_handler(red, None, ExitCodes.CRITICAL))
    finally:
        # Allows transports to close properly, and prevent new ones from being opened.
        # Transports may still not be closed correctly on windows, see below
        loop.run_until_complete(loop.shutdown_asyncgens())
        # *we* aren't cleaning up more here, but it prevents
        # a runtime error at the event loop on windows
        # with resources which require longer to clean up.
        # With other event loops, a failure to cleanup prior to here
        # results in a resource warning instead
        log.info("Please wait, cleaning up a bit more")
        loop.run_until_complete(asyncio.sleep(2))
        asyncio.set_event_loop(None)
        loop.stop()
        loop.close()
    exit_code = red._shutdown_mode if red is not None else ExitCodes.CRITICAL
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
