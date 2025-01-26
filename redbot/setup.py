from redbot import _early_init

# this needs to be called as early as possible
_early_init()

import asyncio
import json
import logging
import sys
import re
from copy import deepcopy
from pathlib import Path
from typing import Dict, Any, Optional, Union

import click

from redbot.core._cli import confirm
from redbot.core.utils._internal_utils import (
    safe_delete,
    create_backup as red_create_backup,
    cli_level_to_log_level,
)
from redbot.core import config, data_manager
from redbot.core._config import migrate
from redbot.core._cli import ExitCodes
from redbot.core.data_manager import appdir, config_dir, config_file
from redbot.core._drivers import (
    BackendType,
    IdentifierData,
    get_driver_class,
    get_driver_class_include_old,
)

conversion_log = logging.getLogger("red.converter")

try:
    config_dir.mkdir(parents=True, exist_ok=True)
except PermissionError:
    print("You don't have permission to write to '{}'\nExiting...".format(config_dir))
    sys.exit(ExitCodes.CONFIGURATION_ERROR)

instance_data = data_manager.load_existing_config()
if instance_data is None:
    instance_list = []
else:
    instance_list = list(instance_data.keys())


def save_config(name, data, remove=False):
    _config = data_manager.load_existing_config()
    if remove and name in _config:
        _config.pop(name)
    else:
        _config[name] = data

    with config_file.open("w", encoding="utf-8") as fs:
        json.dump(_config, fs, indent=4)


def get_data_dir(*, instance_name: str, data_path: Optional[Path], interactive: bool) -> str:
    if data_path is not None:
        return str(data_path.resolve())
    data_path = Path(appdir.user_data_dir) / "data" / instance_name
    if not interactive:
        return str(data_path.resolve())

    print(
        "We've attempted to figure out a sane default data location which is printed below."
        " If you don't want to change this default please press [ENTER],"
        " otherwise input your desired data location."
    )
    print()
    print("Default: {}".format(data_path))

    data_path_input = input("> ")

    if data_path_input != "":
        data_path = Path(data_path_input)

    try:
        exists = data_path.exists()
    except OSError:
        print(
            "We were unable to check your chosen directory."
            " Provided path may contain an invalid character."
        )
        sys.exit(ExitCodes.INVALID_CLI_USAGE)

    if not exists:
        try:
            data_path.mkdir(parents=True, exist_ok=True)
        except OSError:
            print(
                "We were unable to create your chosen directory."
                " You may need to create the directory and set proper permissions"
                " for it manually before it can be used as the data directory."
            )
            sys.exit(ExitCodes.INVALID_CLI_USAGE)

    print("You have chosen {} to be your data directory.".format(data_path))
    if not click.confirm("Please confirm", default=True):
        print("Please start the process over.")
        sys.exit(ExitCodes.CRITICAL)
    return str(data_path.resolve())


def get_storage_type(backend: Optional[str], *, interactive: bool):
    if backend:
        return get_target_backend(backend)
    if not interactive:
        return BackendType.JSON
    storage_dict = {1: BackendType.JSON, 2: BackendType.POSTGRES}
    storage = None
    while storage is None:
        print()
        print("Please choose your storage backend.")
        print("1. JSON (file storage, requires no database).")
        print("2. PostgreSQL (Requires a database server)")
        print("If you're unsure, press [ENTER] to use the recommended default - JSON.")

        storage = input("> ")
        if not storage:
            return BackendType.JSON
        try:
            storage = int(storage)
        except ValueError:
            storage = None
        else:
            if storage not in storage_dict:
                storage = None
    return storage_dict[storage]


def get_name(name: str) -> str:
    INSTANCE_NAME_RE = re.compile(
        r"""
        [a-z0-9]              # starts with letter or digit
        (?:
            (?!.*[_\.\-]{2})  # ensure no consecutive dots, hyphens, or underscores
            [a-z0-9_\.\-]*    # match allowed characters
            [a-z0-9]          # ensure string ends with letter or digit
        )?                    # optional to allow strings of length 1
        """,
        re.VERBOSE | re.IGNORECASE,
    )
    if name:
        if INSTANCE_NAME_RE.fullmatch(name) is None:
            print(
                "ERROR: Instance names need to start and end with a letter or a number"
                " and can only include characters A-z, numbers,"
                " and non-consecutive underscores (_) and periods (.)."
            )
            sys.exit(ExitCodes.INVALID_CLI_USAGE)
        return name

    while len(name) == 0:
        print(
            "Please enter a name for your instance,"
            " it will be used to run your bot from here on out.\n"
            "This name is case-sensitive, needs to start and end with a letter or a number"
            " and should only include characters A-z, numbers,"
            " and non-consecutive underscores (_) and periods (.)."
        )
        name = input("> ")
        if not name:
            pass
        elif INSTANCE_NAME_RE.fullmatch(name) is None:
            print(
                "ERROR: Instance names need to start and end with a letter or a number"
                " and can only include characters A-z, numbers,"
                " and non-consecutive underscores (_) and periods (.)."
            )
            name = ""
        elif "-" in name and not confirm(
            "Hyphens (-) in instance names may cause issues. Are you sure you want to continue with this instance name?",
            default=False,
        ):
            name = ""

        print()  # new line for aesthetics
    return name


def basic_setup(
    *,
    name: str,
    data_path: Optional[Path],
    backend: Optional[str],
    interactive: bool,
    overwrite_existing_instance: bool,
):
    """
    Creates the data storage folder.
    :return:
    """
    if not interactive and not name:
        print(
            "Providing instance name through --instance-name is required"
            " when using non-interactive mode."
        )
        sys.exit(ExitCodes.INVALID_CLI_USAGE)

    if interactive:
        print(
            "Hello! Before we begin, we need to gather some initial information"
            " for the new instance."
        )
    name = get_name(name)

    default_data_dir = get_data_dir(
        instance_name=name, data_path=data_path, interactive=interactive
    )

    default_dirs = deepcopy(data_manager.basic_config_default)
    default_dirs["DATA_PATH"] = default_data_dir

    storage_type = get_storage_type(backend, interactive=interactive)

    default_dirs["STORAGE_TYPE"] = storage_type.value
    driver_cls = get_driver_class(storage_type)
    default_dirs["STORAGE_DETAILS"] = driver_cls.get_config_details()

    if name in instance_data:
        if overwrite_existing_instance:
            pass
        elif interactive:
            print(
                "WARNING: An instance already exists with this name. "
                "Continuing will overwrite the existing instance config."
            )
            if not click.confirm(
                "Are you absolutely certain you want to continue?", default=False
            ):
                print("Not continuing")
                sys.exit(ExitCodes.SHUTDOWN)
        else:
            print(
                "An instance with this name already exists.\n"
                "If you want to remove the existing instance and replace it with this one,"
                " run this command with --overwrite-existing-instance flag."
            )
            sys.exit(ExitCodes.INVALID_CLI_USAGE)
    save_config(name, default_dirs)

    if interactive:
        print()
        print(
            f"Your basic configuration has been saved. Please run `redbot {name}` to"
            " continue your setup process and to run the bot.\n\n"
            "First time? Read the quickstart guide:\n"
            "https://docs.discord.red/en/stable/getting_started.html"
        )
    else:
        print("Your basic configuration has been saved.")


def get_current_backend(instance: str) -> BackendType:
    return BackendType(instance_data[instance]["STORAGE_TYPE"])


def get_target_backend(backend: str) -> BackendType:
    if backend == "json":
        return BackendType.JSON
    elif backend == "postgres":
        return BackendType.POSTGRES


async def do_migration(
    current_backend: BackendType, target_backend: BackendType
) -> Dict[str, Any]:
    cur_driver_cls = get_driver_class_include_old(current_backend)
    new_driver_cls = get_driver_class(target_backend)
    cur_storage_details = data_manager.storage_details()
    new_storage_details = new_driver_cls.get_config_details()

    await cur_driver_cls.initialize(**cur_storage_details)
    await new_driver_cls.initialize(**new_storage_details)

    await migrate(cur_driver_cls, new_driver_cls)

    await cur_driver_cls.teardown()
    await new_driver_cls.teardown()

    return new_storage_details


async def create_backup(instance: str, destination_folder: Path = Path.home()) -> None:
    data_manager.load_basic_configuration(instance)
    backend_type = get_current_backend(instance)
    if backend_type != BackendType.JSON:
        await do_migration(backend_type, BackendType.JSON)
    print("Backing up the instance's data...")
    driver_cls = get_driver_class()
    await driver_cls.initialize(**data_manager.storage_details())
    backup_fpath = await red_create_backup(destination_folder)
    await driver_cls.teardown()
    if backup_fpath is not None:
        print(f"A backup of {instance} has been made. It is at {backup_fpath}")
    else:
        print("Creating the backup failed.")


async def remove_instance(
    instance: str,
    interactive: bool = False,
    delete_data: Optional[bool] = None,
    _create_backup: Optional[bool] = None,
    drop_db: Optional[bool] = None,
    remove_datapath: Optional[bool] = None,
) -> None:
    data_manager.load_basic_configuration(instance)
    backend = get_current_backend(instance)

    if interactive is True and delete_data is None:
        msg = "Would you like to delete this instance's data?"
        if backend != BackendType.JSON:
            msg += " The database server must be running for this to work."
        delete_data = click.confirm(msg, default=False)

    if interactive is True and _create_backup is None:
        msg = "Would you like to make a backup of the data for this instance?"
        if backend != BackendType.JSON:
            msg += " The database server must be running for this to work."
        _create_backup = click.confirm(msg, default=False)

    if _create_backup is True:
        await create_backup(instance)

    driver_cls = get_driver_class(backend)
    if delete_data is True:
        await driver_cls.initialize(**data_manager.storage_details())
        try:
            await driver_cls.delete_all_data(interactive=interactive, drop_db=drop_db)
        finally:
            await driver_cls.teardown()

    if interactive is True and remove_datapath is None:
        remove_datapath = click.confirm(
            "Would you like to delete the instance's entire datapath?", default=False
        )

    if remove_datapath is True:
        data_path = data_manager.core_data_path().parent
        safe_delete(data_path)

    save_config(instance, {}, remove=True)
    print("The instance {} has been removed.".format(instance))


async def remove_instance_interaction() -> None:
    if not instance_list:
        print("No instances have been set up!")
        return

    print(
        "You have chosen to remove an instance. The following "
        "is a list of instances that currently exist:\n"
    )
    for instance in instance_data.keys():
        print("{}\n".format(instance))
    print("Please select one of the above by entering its name")
    selected = input("> ")

    if selected not in instance_data.keys():
        print("That isn't a valid instance!")
        return

    await remove_instance(selected, interactive=True)


@click.group(invoke_without_command=True)
@click.option(
    "--debug",
    "--verbose",
    "-v",
    count=True,
    help=(
        "Increase the verbosity of the logs, each usage of this flag increases the verbosity"
        " level by 1."
    ),
)
@click.option(
    "--no-prompt",
    "interactive",
    type=bool,
    is_flag=True,
    default=True,
    help=(
        "Don't ask for user input during the process (non-interactive mode)."
        " This makes `--instance-name` required."
    ),
)
@click.option(
    "--instance-name",
    type=str,
    default="",
    help="Name of the new instance. Required if --no-prompt is passed.",
)
@click.option(
    "--data-path",
    type=click.Path(exists=False, dir_okay=True, file_okay=False, writable=True, path_type=Path),
    default=None,
    help=(
        "Data path of the new instance. If this option and --no-prompt are omitted,"
        " you will be asked for this."
    ),
)
@click.option(
    "--backend",
    type=click.Choice(["json", "postgres"]),
    default=None,
    help=(
        "Choose a backend type for the new instance."
        " If this option is omitted, you will be asked for this."
        " Defaults to JSON in non-interactive mode.\n"
        "Note: Choosing PostgreSQL will prevent the setup from being completely non-interactive."
    ),
)
@click.option(
    "--overwrite-existing-instance",
    type=bool,
    is_flag=True,
    help=(
        "Confirm overwriting of existing instance.\n"
        "Note: This removes *metadata* about the existing instance with that name."
    ),
)
@click.pass_context
def cli(
    ctx: click.Context,
    debug: bool,
    interactive: bool,
    instance_name: str,
    data_path: Optional[Path],
    backend: Optional[str],
    overwrite_existing_instance: bool,
) -> None:
    """Create a new instance."""
    level = cli_level_to_log_level(debug)
    base_logger = logging.getLogger("red")
    base_logger.setLevel(level)
    formatter = logging.Formatter(
        "[{asctime}] [{levelname}] {name}: {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{"
    )
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    base_logger.addHandler(stdout_handler)

    if ctx.invoked_subcommand is None:
        basic_setup(
            name=instance_name,
            data_path=data_path,
            backend=backend,
            overwrite_existing_instance=overwrite_existing_instance,
            interactive=interactive,
        )


@cli.command()
@click.argument("instance", type=click.Choice(instance_list), metavar="<INSTANCE_NAME>")
@click.option(
    "--no-prompt",
    "interactive",
    is_flag=True,
    default=True,
    help="Don't ask for user input during the process.",
)
@click.option(
    "--delete-data/--no-delete-data",
    "delete_data",
    is_flag=True,
    default=None,
    help=(
        "Delete this instance's data. "
        "If these options and --no-prompt are omitted, you will be asked about this."
    ),
)
@click.option(
    "--backup/--no-backup",
    "_create_backup",
    is_flag=True,
    default=None,
    help=(
        "Create backup of this instance's data. "
        "If these options and --no-prompt are omitted, you will be asked about this."
    ),
)
@click.option(
    "--drop-db/--no-drop-db",
    is_flag=True,
    default=None,
    help=(
        "Drop the entire database containing this instance's data. Has no effect on JSON "
        "instances, or if --no-delete-data is set. If these options and --no-prompt are omitted,"
        "you will be asked about this."
    ),
)
@click.option(
    "--remove-datapath/--no-remove-datapath",
    is_flag=True,
    default=None,
    help=(
        "Remove this entire instance's datapath. If these options and --no-prompt are omitted, "
        "you will be asked about this. NOTE: --remove-datapath will override --no-delete-data "
        "for JSON instances."
    ),
)
def delete(
    instance: str,
    interactive: bool,
    delete_data: Optional[bool],
    _create_backup: Optional[bool],
    drop_db: Optional[bool],
    remove_datapath: Optional[bool],
) -> None:
    """Removes an instance."""
    asyncio.run(
        remove_instance(
            instance, interactive, delete_data, _create_backup, drop_db, remove_datapath
        )
    )


@cli.command()
@click.argument("instance", type=click.Choice(instance_list), metavar="<INSTANCE_NAME>")
@click.argument("backend", type=click.Choice(["json", "postgres"]))
def convert(instance: str, backend: str) -> None:
    """Convert data backend of an instance."""
    current_backend = get_current_backend(instance)
    target = get_target_backend(backend)
    data_manager.load_basic_configuration(instance)

    default_dirs = deepcopy(data_manager.basic_config_default)
    default_dirs["DATA_PATH"] = str(Path(instance_data[instance]["DATA_PATH"]))

    if current_backend == BackendType.MONGOV1:
        raise RuntimeError("Please see the 3.2 release notes for upgrading a bot using mongo.")
    else:
        new_storage_details = asyncio.run(do_migration(current_backend, target))

    if new_storage_details is not None:
        default_dirs["STORAGE_TYPE"] = target.value
        default_dirs["STORAGE_DETAILS"] = new_storage_details
        save_config(instance, default_dirs)
        conversion_log.info(f"Conversion to {target} complete.")
    else:
        conversion_log.info(
            f"Cannot convert {current_backend.value} to {target.value} at this time."
        )


@cli.command()
@click.argument("instance", type=click.Choice(instance_list), metavar="<INSTANCE_NAME>")
@click.argument(
    "destination_folder",
    type=click.Path(
        dir_okay=True, file_okay=False, resolve_path=True, writable=True, path_type=Path
    ),
    default=Path.home(),
)
def backup(instance: str, destination_folder: Path) -> None:
    """Backup instance's data."""
    asyncio.run(create_backup(instance, destination_folder))


def run_cli():
    # Setuptools entry point script stuff...
    try:
        cli()  # pylint: disable=no-value-for-parameter  # click
    except KeyboardInterrupt:
        print("Exiting...")
    else:
        print("Exiting...")


if __name__ == "__main__":
    run_cli()
