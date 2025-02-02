import abc
import enum
from typing import Tuple, Dict, Any, Union, List, AsyncIterator, Type

import rich.progress

from redbot.core.utils._internal_utils import RichIndefiniteBarColumn

__all__ = ("BaseDriver", "IdentifierData", "ConfigCategory", "MissingExtraRequirements")


class MissingExtraRequirements(Exception):
    """Raised when an extra requirement is missing but required."""


class ConfigCategory(str, enum.Enum):
    """Represents config category."""

    #: Global category.
    GLOBAL = "GLOBAL"
    #: Guild category.
    GUILD = "GUILD"
    #: Channel category.
    CHANNEL = "TEXTCHANNEL"
    #: Role category.
    ROLE = "ROLE"
    #: User category.
    USER = "USER"
    #: Member category.
    MEMBER = "MEMBER"

    @classmethod
    def get_pkey_info(
        cls, category: Union[str, "ConfigCategory"], custom_group_data: Dict[str, int]
    ) -> Tuple[int, bool]:
        """Get the full primary key length for the given category,
        and whether or not the category is a custom category.
        """
        try:
            # noinspection PyArgumentList
            category_obj = cls(category)
        except ValueError:
            return custom_group_data[category], True
        else:
            return _CATEGORY_PKEY_COUNTS[category_obj], False


_CATEGORY_PKEY_COUNTS = {
    ConfigCategory.GLOBAL: 0,
    ConfigCategory.GUILD: 1,
    ConfigCategory.CHANNEL: 1,
    ConfigCategory.ROLE: 1,
    ConfigCategory.USER: 1,
    ConfigCategory.MEMBER: 2,
}


class IdentifierData:
    def __init__(
        self,
        cog_name: str,
        uuid: str,
        category: str,
        primary_key: Tuple[str, ...],
        identifiers: Tuple[str, ...],
        primary_key_len: int,
        is_custom: bool = False,
    ):
        self._cog_name = cog_name
        self._uuid = uuid
        self._category = category
        self._primary_key = primary_key
        self._identifiers = identifiers
        self.primary_key_len = primary_key_len
        self._is_custom = is_custom

    @property
    def cog_name(self) -> str:
        return self._cog_name

    @property
    def uuid(self) -> str:
        return self._uuid

    @property
    def category(self) -> str:
        return self._category

    @property
    def primary_key(self) -> Tuple[str, ...]:
        return self._primary_key

    @property
    def identifiers(self) -> Tuple[str, ...]:
        return self._identifiers

    @property
    def is_custom(self) -> bool:
        return self._is_custom

    def __repr__(self) -> str:
        return (
            f"<IdentifierData cog_name={self.cog_name} uuid={self.uuid} category={self.category} "
            f"primary_key={self.primary_key} identifiers={self.identifiers}>"
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, IdentifierData):
            return False
        return (
            self.uuid == other.uuid
            and self.category == other.category
            and self.primary_key == other.primary_key
            and self.identifiers == other.identifiers
        )

    def __hash__(self) -> int:
        return hash((self.uuid, self.category, self.primary_key, self.identifiers))

    def get_child(self, *keys: str) -> "IdentifierData":
        if not all(isinstance(i, str) for i in keys):
            raise ValueError("Identifiers must be strings.")

        primary_keys = self.primary_key
        identifiers = self.identifiers
        num_missing_pkeys = self.primary_key_len - len(self.primary_key)
        if num_missing_pkeys > 0:
            primary_keys += keys[:num_missing_pkeys]
        if len(keys) > num_missing_pkeys:
            identifiers += keys[num_missing_pkeys:]

        return IdentifierData(
            self.cog_name,
            self.uuid,
            self.category,
            primary_keys,
            identifiers,
            self.primary_key_len,
            self.is_custom,
        )

    def add_identifier(self, *identifier: str) -> "IdentifierData":
        if not all(isinstance(i, str) for i in identifier):
            raise ValueError("Identifiers must be strings.")

        return IdentifierData(
            self.cog_name,
            self.uuid,
            self.category,
            self.primary_key,
            self.identifiers + identifier,
            self.primary_key_len,
            is_custom=self.is_custom,
        )

    def to_tuple(self) -> Tuple[str, ...]:
        return tuple(
            filter(
                None,
                (self.cog_name, self.uuid, self.category, *self.primary_key, *self.identifiers),
            )
        )


class BaseDriver(abc.ABC):
    def __init__(self, cog_name: str, identifier: str, **kwargs):
        self.cog_name = cog_name
        self.unique_cog_identifier = identifier

    @classmethod
    @abc.abstractmethod
    async def initialize(cls, **storage_details) -> None:
        """
        Initialize this driver.

        Parameters
        ----------
        **storage_details
            The storage details required to initialize this driver.
            Should be the same as :func:`data_manager.storage_details`

        Raises
        ------
        MissingExtraRequirements
            If initializing the driver requires an extra which isn't
            installed.

        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    async def teardown(cls) -> None:
        """
        Tear down this driver.
        """
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def get_config_details() -> Dict[str, Any]:
        """
        Asks users for additional configuration information necessary
        to use this config driver.

        Returns
        -------
        Dict[str, Any]
            Dictionary of configuration details.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get(self, identifier_data: IdentifierData) -> Any:
        """
        Finds the value indicate by the given identifiers.

        Parameters
        ----------
        identifier_data

        Returns
        -------
        Any
            Stored value.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def set(self, identifier_data: IdentifierData, value=None) -> None:
        """
        Sets the value of the key indicated by the given identifiers.

        Parameters
        ----------
        identifier_data
        value
            Any JSON serializable python object.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def clear(self, identifier_data: IdentifierData) -> None:
        """
        Clears out the value specified by the given identifiers.

        Equivalent to using ``del`` on a dict.

        Parameters
        ----------
        identifier_data
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def aiter_cogs(cls) -> AsyncIterator[Tuple[str, str]]:
        """Get info for cogs which have data stored on this backend.

        Yields
        ------
        Tuple[str, str]
            Asynchronously yields (cog_name, cog_identifier) tuples.

        """
        raise NotImplementedError

    @classmethod
    async def migrate_to(
        cls,
        new_driver_cls: Type["BaseDriver"],
        all_custom_group_data: Dict[str, Dict[str, Dict[str, int]]],
    ) -> None:
        """Migrate data from this backend to another.

        Both drivers must be initialized beforehand.

        This will only move the data - no instance metadata is modified
        as a result of this operation.

        Parameters
        ----------
        new_driver_cls
            Subclass of `BaseDriver`.
        all_custom_group_data : Dict[str, Dict[str, Dict[str, int]]]
            Dict mapping cog names, to cog IDs, to custom groups, to
            primary key lengths.

        """
        # Backend-agnostic method of migrating from one driver to another.
        with rich.progress.Progress(
            rich.progress.SpinnerColumn(),
            rich.progress.TextColumn("[progress.description]{task.description}"),
            RichIndefiniteBarColumn(),
            rich.progress.TextColumn("{task.completed} cogs processed"),
            rich.progress.TimeElapsedColumn(),
        ) as progress:
            cog_count = 0
            tid = progress.add_task("[yellow]Migrating", completed=cog_count, total=cog_count + 1)
            async for cog_name, cog_id in cls.aiter_cogs():
                progress.console.print(f"Working on {cog_name}...")

                this_driver = cls(cog_name, cog_id)
                other_driver = new_driver_cls(cog_name, cog_id)
                custom_group_data = all_custom_group_data.get(cog_name, {}).get(cog_id, {})
                exported_data = await this_driver.export_data(custom_group_data)
                await other_driver.import_data(exported_data, custom_group_data)

                cog_count += 1
                progress.update(tid, completed=cog_count, total=cog_count + 1)
            progress.update(tid, total=cog_count)
        print()

    @classmethod
    async def delete_all_data(cls, **kwargs) -> None:
        """Delete all data being stored by this driver.

        The driver must be initialized before this operation.

        The BaseDriver provides a generic method which may be overridden
        by subclasses.

        Parameters
        ----------
        **kwargs
            Driver-specific kwargs to change the way this method
            operates.

        """
        async for cog_name, cog_id in cls.aiter_cogs():
            driver = cls(cog_name, cog_id)
            await driver.clear(IdentifierData(cog_name, cog_id, "", (), (), 0))

    @staticmethod
    def _split_primary_key(
        category: Union[ConfigCategory, str],
        custom_group_data: Dict[str, int],
        data: Dict[str, Any],
    ) -> List[Tuple[Tuple[str, ...], Dict[str, Any]]]:
        pkey_len = ConfigCategory.get_pkey_info(category, custom_group_data)[0]
        if pkey_len == 0:
            return [((), data)]

        def flatten(levels_remaining, currdata, parent_key=()):
            items = []
            for _k, _v in currdata.items():
                new_key = parent_key + (_k,)
                if levels_remaining > 1:
                    items.extend(flatten(levels_remaining - 1, _v, new_key).items())
                else:
                    items.append((new_key, _v))
            return dict(items)

        ret = []
        for k, v in flatten(pkey_len, data).items():
            ret.append((k, v))
        return ret

    async def export_data(
        self, custom_group_data: Dict[str, int]
    ) -> List[Tuple[str, Dict[str, Any]]]:
        categories = [c.value for c in ConfigCategory]
        categories.extend(custom_group_data.keys())

        ret = []
        for c in categories:
            ident_data = IdentifierData(
                self.cog_name,
                self.unique_cog_identifier,
                c,
                (),
                (),
                *ConfigCategory.get_pkey_info(c, custom_group_data),
            )
            try:
                data = await self.get(ident_data)
            except KeyError:
                continue
            ret.append((c, data))
        return ret

    async def import_data(
        self, cog_data: List[Tuple[str, Dict[str, Any]]], custom_group_data: Dict[str, int]
    ) -> None:
        for category, all_data in cog_data:
            splitted_pkey = self._split_primary_key(category, custom_group_data, all_data)
            for pkey, data in splitted_pkey:
                ident_data = IdentifierData(
                    self.cog_name,
                    self.unique_cog_identifier,
                    category,
                    pkey,
                    (),
                    *ConfigCategory.get_pkey_info(category, custom_group_data),
                )
                await self.set(ident_data, data)
