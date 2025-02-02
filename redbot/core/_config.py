import weakref
from typing import Tuple, Type

from redbot.core.config import Config, _config_cache
from redbot.core._drivers import BaseDriver

__all__ = ("get_latest_confs", "migrate")

_retrieved = weakref.WeakSet()


def get_latest_confs() -> Tuple[Config, ...]:
    global _retrieved
    ret = set(_config_cache.values()) - set(_retrieved)
    _retrieved |= ret
    return tuple(ret)


async def migrate(cur_driver_cls: Type[BaseDriver], new_driver_cls: Type[BaseDriver]) -> None:
    """Migrate from one driver type to another."""
    # Get custom group data
    core_conf = Config.get_core_conf(allow_old=True)
    core_conf.init_custom("CUSTOM_GROUPS", 2)
    all_custom_group_data = await core_conf.custom("CUSTOM_GROUPS").all()

    await cur_driver_cls.migrate_to(new_driver_cls, all_custom_group_data)
