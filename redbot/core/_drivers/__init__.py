import enum
from typing import Optional, Type

from .. import data_manager
from .base import IdentifierData, BaseDriver, ConfigCategory
from .json import JsonDriver
from .postgres import PostgresDriver

__all__ = [
    "get_driver",
    "get_driver_class",
    "get_driver_class_include_old",
    "ConfigCategory",
    "IdentifierData",
    "BaseDriver",
    "JsonDriver",
    "PostgresDriver",
    "BackendType",
]


class BackendType(enum.Enum):
    """Represents storage backend type."""

    #: JSON storage backend.
    JSON = "JSON"
    #: Postgres storage backend.
    POSTGRES = "Postgres"
    # Dead drivers below retained for error handling.
    MONGOV1 = "MongoDB"
    MONGO = "MongoDBV2"


_DRIVER_CLASSES = {BackendType.JSON: JsonDriver, BackendType.POSTGRES: PostgresDriver}


def get_driver_class_include_old(storage_type: Optional[BackendType] = None) -> Type[BaseDriver]:
    """
    ONLY for use in CLI for moving data away from a no longer supported backend
    """
    if storage_type and storage_type == BackendType.MONGO:
        from ._mongo import MongoDriver

        return MongoDriver
    else:
        return get_driver_class(storage_type)


def get_driver_class(storage_type: Optional[BackendType] = None) -> Type[BaseDriver]:
    """Get the driver class for the given storage type.

    Parameters
    ----------
    storage_type : Optional[BackendType]
        The backend you want a driver class for. Omit to try to obtain
        the backend from data manager.

    Returns
    -------
    Type[BaseDriver]
        A subclass of `BaseDriver`.

    Raises
    ------
    ValueError
        If there is no driver for the given storage type.

    """
    if storage_type is None:
        storage_type = BackendType(data_manager.storage_type())
    try:
        return _DRIVER_CLASSES[storage_type]
    except KeyError:
        raise ValueError(f"No driver found for storage type {storage_type}") from None


def get_driver(
    cog_name: str,
    identifier: str,
    storage_type: Optional[BackendType] = None,
    *,
    allow_old: bool = False,
    **kwargs,
):
    """Get a driver instance.

    Parameters
    ----------
    cog_name : str
        The cog's name.
    identifier : str
        The cog's discriminator.
    storage_type : Optional[BackendType]
        The backend you want a driver for. Omit to try to obtain the
        backend from data manager.
    **kwargs
        Driver-specific keyword arguments.

    Returns
    -------
    BaseDriver
        A driver instance.

    Raises
    ------
    RuntimeError
        If the storage type is MongoV1, Mongo, or invalid.

    """
    if storage_type is None:
        try:
            storage_type = BackendType(data_manager.storage_type())
        except RuntimeError:
            storage_type = BackendType.JSON

    try:
        if not allow_old:
            driver_cls: Type[BaseDriver] = get_driver_class(storage_type)
        else:
            driver_cls: Type[BaseDriver] = get_driver_class_include_old(storage_type)
    except ValueError:
        if storage_type in (BackendType.MONGOV1, BackendType.MONGO):
            raise RuntimeError(
                "Please convert to JSON first to continue using the bot."
                "Mongo support was removed in 3.2."
            ) from None
        else:
            raise RuntimeError(f"Invalid driver type: '{storage_type}'") from None
    return driver_cls(cog_name, identifier, **kwargs)
