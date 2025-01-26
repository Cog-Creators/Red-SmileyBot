import argparse
import asyncio
import logging
import sys
from enum import IntEnum
from typing import Optional

import discord
from discord import __version__ as discord_version

from redbot.core.utils._internal_utils import cli_level_to_log_level


# This needs to be an int enum to be used
# with sys.exit
class ExitCodes(IntEnum):
    #: Clean shutdown (through signals, keyboard interrupt, [p]shutdown, etc.).
    SHUTDOWN = 0
    #: An unrecoverable error occurred during application's runtime.
    CRITICAL = 1
    #: The CLI command was used incorrectly, such as when the wrong number of arguments are given.
    INVALID_CLI_USAGE = 2
    #: Restart was requested by the bot owner (probably through [p]restart command).
    RESTART = 26
    #: Some kind of configuration error occurred.
    CONFIGURATION_ERROR = 78  # Exit code borrowed from os.EX_CONFIG.


def confirm(text: str, default: Optional[bool] = None) -> bool:
    if default is None:
        options = "y/n"
    elif default is True:
        options = "Y/n"
    elif default is False:
        options = "y/N"
    else:
        raise TypeError(f"expected bool, not {type(default)}")

    while True:
        try:
            value = input(f"{text}: [{options}] ").lower().strip()
        except KeyboardInterrupt:
            print("\nAborted!")
            sys.exit(ExitCodes.SHUTDOWN)
        except EOFError:
            print("\nAborted!")
            sys.exit(ExitCodes.INVALID_CLI_USAGE)
        if value in ("y", "yes"):
            return True
        if value in ("n", "no"):
            return False
        if value == "":
            if default is not None:
                return default
        print("Error: invalid input")


async def interactive_config(red, token_set, prefix_set, *, print_header=True):
    token = None

    if print_header:
        print("Red - Discord Bot | Configuration process\n")

    if not token_set:
        print(
            "Please enter a valid token.\n"
            "You can find out how to obtain a token with this guide:\n"
            "https://docs.discord.red/en/stable/bot_application_guide.html#creating-a-bot-account"
        )
        while not token:
            token = input("> ")
            if not len(token) >= 50:
                print("That doesn't look like a valid token.")
                token = None
            if token:
                await red._config.token.set(token)

    if not prefix_set:
        prefix = ""
        print(
            "\nPick a prefix. A prefix is what you type before a "
            "command. Example:\n"
            "!help\n^ The exclamation mark (!) is the prefix in this case.\n"
            "The prefix can be multiple characters. You will be able to change it "
            "later and add more of them.\nChoose your prefix:\n"
        )
        while not prefix:
            prefix = input("Prefix> ")
            if len(prefix) > 10:
                if not confirm("Your prefix seems overly long. Are you sure that it's correct?"):
                    prefix = ""
            if prefix.startswith("/"):
                print(
                    "Prefixes cannot start with '/', as it conflicts with Discord's slash commands."
                )
                prefix = ""
            if prefix and not confirm(
                f'You chose "{prefix}" as your prefix. To run the help command,'
                f" you will have to send:\n{prefix}help\n\n"
                "Do you want to continue with this prefix?"
            ):
                prefix = ""
            if prefix:
                await red._config.prefix.set([prefix])

    return token


def non_negative_int(arg: str) -> int:
    try:
        x = int(arg)
    except ValueError:
        raise argparse.ArgumentTypeError("The argument has to be a number.")
    if x < 0:
        raise argparse.ArgumentTypeError("The argument has to be a non-negative integer.")
    if x > sys.maxsize:
        raise argparse.ArgumentTypeError(
            f"The argument has to be lower than or equal to {sys.maxsize}."
        )
    return x


def message_cache_size_int(arg: str) -> int:
    x = non_negative_int(arg)
    if x < 1000:
        raise argparse.ArgumentTypeError(
            "Message cache size has to be greater than or equal to 1000."
        )
    return x


def parse_cli_flags(args):
    parser = argparse.ArgumentParser(
        description="Red - Discord Bot", usage="redbot <instance_name> [arguments]"
    )
    parser.add_argument("--version", "-V", action="store_true", help="Show Red's current version")
    parser.add_argument("--debuginfo", action="store_true", help="Show debug information.")
    parser.add_argument(
        "--list-instances",
        action="store_true",
        help="List all instance names setup with 'redbot-setup'",
    )
    parser.add_argument(
        "--edit",
        action="store_true",
        help="Edit the instance. This can be done without console interaction "
        "by passing --no-prompt and arguments that you want to change (available arguments: "
        "--edit-instance-name, --edit-data-path, --copy-data, --owner, --token, --prefix).",
    )
    parser.add_argument(
        "--edit-instance-name",
        type=str,
        help="New name for the instance. This argument only works with --edit argument passed.",
    )
    parser.add_argument(
        "--overwrite-existing-instance",
        action="store_true",
        help="Confirm overwriting of existing instance when changing name."
        " This argument only works with --edit argument passed.",
    )
    parser.add_argument(
        "--edit-data-path",
        type=str,
        help=(
            "New data path for the instance. This argument only works with --edit argument passed."
        ),
    )
    parser.add_argument(
        "--copy-data",
        action="store_true",
        help="Copy data from old location. This argument only works "
        "with --edit and --edit-data-path arguments passed.",
    )
    parser.add_argument(
        "--owner",
        type=int,
        help="ID of the owner. Only who hosts "
        "Red should be owner, this has "
        "serious security implications if misused.",
    )
    parser.add_argument(
        "--co-owner",
        type=int,
        default=[],
        nargs="+",
        action="extend",
        help="ID of a co-owner. Only people who have access "
        "to the system that is hosting Red should be  "
        "co-owners, as this gives them complete access "
        "to the system's data. This has serious "
        "security implications if misused. Can be "
        "multiple.",
    )
    parser.add_argument(
        "--prefix", "-p", action="append", help="Global prefix. Can be multiple", default=[]
    )
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help="Disables console inputs. Features requiring "
        "console interaction could be disabled as a "
        "result",
    )
    parser.add_argument(
        "--no-cogs", action="store_true", help="Starts Red with no cogs loaded, only core"
    )
    parser.add_argument(
        "--load-cogs",
        type=str,
        nargs="+",
        action="extend",
        help="Force loading specified cogs from the installed packages. "
        "Can be used with the --no-cogs flag to load these cogs exclusively.",
    )
    parser.add_argument(
        "--unload-cogs",
        type=str,
        nargs="+",
        action="extend",
        help="Force unloading specified cogs.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Makes Red quit with code 0 just before the "
        "login. This is useful for testing the boot "
        "process.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        "--debug",
        action="count",
        default=0,
        dest="logging_level",
        help="Increase the verbosity of the logs, each usage of this flag increases the verbosity level by 1.",
    )
    parser.add_argument("--dev", action="store_true", help="Enables developer mode")
    parser.add_argument(
        "--mentionable",
        action="store_true",
        help="Allows mentioning the bot as an alternative to using the bot prefix",
    )
    parser.add_argument(
        "--rpc",
        action="store_true",
        help="Enables the built-in RPC server. Please read the docs prior to enabling this!",
    )
    parser.add_argument(
        "--rpc-port",
        type=int,
        default=6133,
        help="The port of the built-in RPC server to use. Default to 6133.",
    )
    parser.add_argument("--token", type=str, help="Run Red with the given token.")
    parser.add_argument(
        "--no-instance",
        action="store_true",
        help=(
            "Run Red without any existing instance. "
            "The data will be saved under a temporary folder "
            "and deleted on next system restart."
        ),
    )
    parser.add_argument(
        "instance_name", nargs="?", help="Name of the bot instance created during `redbot-setup`."
    )
    parser.add_argument(
        "--team-members-are-owners",
        "--team-developers-are-owners",
        action="store_true",
        dest="use_team_features",
        default=False,
        help=(
            "Treat application team members as owners, if their team role is Owner, "
            "Admin, or Developer. "
            "This is off by default. Owners can load and run arbitrary code. "
            "Do not enable if you would not trust all of your team members with "
            "all of the data on the host machine."
        ),
    )
    parser.add_argument(
        "--message-cache-size",
        type=message_cache_size_int,
        default=1000,
        help="Set the maximum number of messages to store in the internal message cache.",
    )
    parser.add_argument(
        "--no-message-cache", action="store_true", help="Disable the internal message cache."
    )
    parser.add_argument(
        "--disable-intent",
        action="append",
        choices=list(discord.Intents.VALID_FLAGS),  # DEP-WARN
        default=[],
        help="Unsupported flag that allows disabling the given intent."
        " Currently NOT SUPPORTED (and not covered by our version guarantees)"
        " as Red is not prepared to work without all intents.\n"
        f"Go to https://discordpy.readthedocs.io/en/v{discord_version}/api.html#discord.Intents"
        " to see what each intent does.\n"
        "This flag can be used multiple times to specify multiple intents.",
    )
    parser.add_argument(
        "--force-rich-logging",
        action="store_true",
        dest="rich_logging",
        default=None,
        help="Forcefully enables the Rich logging handlers. This is normally enabled for supported active terminals.",
    )
    parser.add_argument(
        "--force-disable-rich-logging",
        action="store_false",
        dest="rich_logging",
        default=None,
        help="Forcefully disables the Rich logging handlers.",
    )
    parser.add_argument(
        "--rich-traceback-extra-lines",
        type=non_negative_int,
        default=0,
        help="Set the number of additional lines of code before and after the executed line"
        " that should be shown in tracebacks generated by Rich.\n"
        "Useful for development.",
    )
    parser.add_argument(
        "--rich-traceback-show-locals",
        action="store_true",
        help="Enable showing local variables in tracebacks generated by Rich.\n"
        "Useful for development.",
    )

    args = parser.parse_args(args)

    if args.prefix:
        args.prefix = sorted(args.prefix, reverse=True)
    else:
        args.prefix = []
    args.logging_level = cli_level_to_log_level(args.logging_level)

    return args
