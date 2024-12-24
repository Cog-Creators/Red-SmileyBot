import asyncio
import os

import pytest

from redbot import _update_event_loop_policy
from redbot.core import _drivers, data_manager

_update_event_loop_policy()


@pytest.fixture(scope="session")
def event_loop(request):
    """Create an instance of the default event loop for entire session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    asyncio.set_event_loop(None)
    loop.close()


def _get_backend_type():
    if os.getenv("RED_STORAGE_TYPE") == "postgres":
        return _drivers.BackendType.POSTGRES
    else:
        return _drivers.BackendType.JSON


@pytest.fixture(scope="session", autouse=True)
async def _setup_driver():
    backend_type = _get_backend_type()
    storage_details = {}
    data_manager.storage_type = lambda: backend_type.value
    data_manager.storage_details = lambda: storage_details
    driver_cls = _drivers.get_driver_class(backend_type)
    await driver_cls.initialize(**storage_details)
    yield
    await driver_cls.teardown()
