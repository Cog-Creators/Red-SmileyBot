import inspect
from copy import deepcopy
from pathlib import Path
from typing import Dict

from . import _data_manager, commands

__all__ = (
    "cog_data_path",
    "core_data_path",
    "bundled_data_path",
    "data_path",
    "instance_name",
    "metadata_file",
    "storage_type",
    "storage_details",
)


def cog_data_path(cog_instance=None, raw_name: str = None) -> Path:
    """Gets the base cog data path. If you want to get the folder with
    which to store your own cog's data please pass in an instance
    of your cog class.

    Either ``cog_instance`` or ``raw_name`` will be used, not both.

    Parameters
    ----------
    cog_instance
        The instance of the cog you wish to get a data path for.
        If calling from a command or method of your cog, this should be ``self``.
    raw_name : str
        The name of the cog to get a data path for.

    Returns
    -------
    pathlib.Path
        If ``cog_instance`` is provided it will return a path to a folder
        dedicated to a given cog. Otherwise it will return a path to the
        folder that contains data for all cogs.
    """
    try:
        base_data_path = data_path()
    except RuntimeError as e:
        raise RuntimeError(
            "You must load the basic config before you can get the cog data path."
        ) from e
    cog_path = base_data_path / _data_manager.basic_config["COG_PATH_APPEND"]

    if raw_name is not None:
        cog_path = cog_path / raw_name
    elif cog_instance is not None:
        cog_path = cog_path / cog_instance.__class__.__name__
    cog_path.mkdir(exist_ok=True, parents=True)

    return cog_path.resolve()


def core_data_path() -> Path:
    try:
        base_data_path = data_path()
    except RuntimeError as e:
        raise RuntimeError(
            "You must load the basic config before you can get the core data path."
        ) from e
    core_path = base_data_path / _data_manager.basic_config["CORE_PATH_APPEND"]
    core_path.mkdir(exist_ok=True, parents=True)

    return core_path.resolve()


def bundled_data_path(cog_instance: commands.Cog) -> Path:
    """
    Get the path to the "data" directory bundled with this cog.

    The bundled data folder must be located alongside the ``.py`` file
    which contains the cog class.

    .. important::

        You should *NEVER* write to this directory.

    Parameters
    ----------
    cog_instance
        An instance of your cog. If calling from a command or method of
        your cog, this should be ``self``.

    Returns
    -------
    pathlib.Path
        Path object to the bundled data folder.

    Raises
    ------
    FileNotFoundError
        If no bundled data folder exists.

    """
    bundled_path = Path(inspect.getfile(cog_instance.__class__)).parent / "data"

    if not bundled_path.is_dir():
        raise FileNotFoundError("No such directory {}".format(bundled_path))

    return bundled_path


def data_path() -> Path:
    """Gets the base data path.

    Returns
    -------
    str
        Storage type.
    """
    basic_config = _data_manager.basic_config
    if basic_config is None:
        raise RuntimeError("You must load the basic config before you can get the base data path.")
    path = basic_config["DATA_PATH"]
    return Path(path).resolve()


def instance_name() -> str:
    """Gets instance's name.

    These are set on setup.

    Returns
    -------
    str
        Instance name.
    """
    return _data_manager.instance_name


def metadata_file() -> Path:
    """Gets the path of metadata file.

    Returns
    -------
    str
        Storage type.
    """
    return _data_manager.config_file


def storage_type() -> str:
    """Gets the storage type as a string.

    Returns
    -------
    str
        Storage type.
    """
    try:
        return _data_manager.basic_config["STORAGE_TYPE"]
    except KeyError as e:
        raise RuntimeError("Bot basic config has not been loaded yet.") from e


def storage_details() -> Dict[str, str]:
    """Gets any details necessary for config drivers to load.

    These are set on setup.

    Returns
    -------
    Dict[str, str]
        Storage details.
    """
    return deepcopy(_data_manager.basic_config.get("STORAGE_DETAILS", {}))
