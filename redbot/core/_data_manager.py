import json
import os
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

import platformdirs

from ._cli import ExitCodes

__all__ = (
    "basic_config",
    "instance_name",
    "load_existing_config",
    "create_temp_config",
    "load_basic_configuration",
)

basic_config: Optional[Dict[str, Any]] = None

instance_name = None

basic_config_default: Dict[str, Any] = {
    "DATA_PATH": None,
    "COG_PATH_APPEND": "cogs",
    "CORE_PATH_APPEND": "core",
}

appdir = platformdirs.PlatformDirs("Red-DiscordBot")
config_dir = appdir.user_config_path
_system_user = sys.platform == "linux" and 0 < os.getuid() < 1000
if _system_user:
    if Path.home().exists():
        # We don't want to break someone just because they created home dir
        # but were already using the site_data_path.
        #
        # But otherwise, we do want Red to use user_config_path if home dir exists.
        _maybe_config_file = appdir.site_data_path / "config.json"
        if _maybe_config_file.exists():
            config_dir = _maybe_config_file.parent
    else:
        config_dir = appdir.site_data_path

config_file = config_dir / "config.json"


def load_existing_config():
    """Get the contents of the config file, or an empty dictionary if it does not exist.

    Returns
    -------
    dict
        The config data.
    """
    if not config_file.exists():
        return {}

    with config_file.open(encoding="utf-8") as fs:
        return json.load(fs)


def create_temp_config():
    """
    Creates a default instance for Red, so it can be ran
    without creating an instance.

    .. warning:: The data of this instance will be removed
        on next system restart.
    """
    name = "temporary_red"

    default_dirs = deepcopy(basic_config_default)
    default_dirs["DATA_PATH"] = tempfile.mkdtemp()
    default_dirs["STORAGE_TYPE"] = "JSON"
    default_dirs["STORAGE_DETAILS"] = {}

    config = load_existing_config()

    config[name] = default_dirs

    with config_file.open("w", encoding="utf-8") as fs:
        json.dump(config, fs, indent=4)


def load_basic_configuration(instance_name_: str):
    """Loads the basic bootstrap configuration necessary for `Config`
    to know where to store or look for data.

    .. important::
        It is necessary to call this function BEFORE getting any `Config`
        objects!

    Parameters
    ----------
    instance_name_ : str
        The instance name given by CLI argument and created during
        redbot setup.
    """
    global basic_config
    global instance_name
    instance_name = instance_name_

    try:
        with config_file.open(encoding="utf-8") as fs:
            config = json.load(fs)
    except FileNotFoundError:
        print(
            "You need to configure the bot instance using `redbot-setup`"
            " prior to running the bot."
        )
        sys.exit(ExitCodes.CONFIGURATION_ERROR)
    try:
        basic_config = config[instance_name]
    except KeyError:
        print(
            f"Instance with name '{instance_name}' doesn't exist."
            " You can create new instance using `redbot-setup` prior to running the bot."
        )
        sys.exit(ExitCodes.INVALID_CLI_USAGE)
