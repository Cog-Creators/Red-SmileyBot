import random
from collections import namedtuple
from pathlib import Path
import weakref

import pytest
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core import config as config_module, _drivers

__all__ = [
    "override_data_path",
    "coroutine",
    "driver",
    "config",
    "config_fr",
    "red",
    "guild_factory",
    "empty_guild",
    "empty_channel",
    "empty_member",
    "empty_message",
    "empty_role",
    "empty_user",
    "member_factory",
    "newline_message",
    "user_factory",
    "prefix",
    "ctx",
]


@pytest.fixture(autouse=True)
def override_data_path(tmpdir):
    from redbot.core import data_manager

    data_manager.basic_config = data_manager.basic_config_default
    data_manager.basic_config["DATA_PATH"] = str(tmpdir)


@pytest.fixture()
def coroutine():
    async def some_coro(*args, **kwargs):
        return args, kwargs

    return some_coro


@pytest.fixture()
def driver(tmpdir_factory):
    import uuid

    rand = str(uuid.uuid4())
    path = Path(str(tmpdir_factory.mktemp(rand)))
    return _drivers.get_driver("PyTest", str(random.randint(1, 999999)), data_path_override=path)


@pytest.fixture()
def config(driver):
    config_module._config_cache = weakref.WeakValueDictionary()
    conf = Config(cog_name="PyTest", unique_identifier=driver.unique_cog_identifier, driver=driver)
    yield conf


@pytest.fixture()
def config_fr(driver):
    """
    Mocked config object with force_register enabled.
    """
    config_module._config_cache = weakref.WeakValueDictionary()
    conf = Config(
        cog_name="PyTest",
        unique_identifier=driver.unique_cog_identifier,
        driver=driver,
        force_registration=True,
    )
    yield conf


# region Dpy Mocks
@pytest.fixture()
def guild_factory():
    mock_guild = namedtuple("Guild", "id members")

    class GuildFactory:
        def get(self):
            return mock_guild(random.randint(1, 999999999), [])

    return GuildFactory()


@pytest.fixture()
def empty_guild(guild_factory):
    return guild_factory.get()


@pytest.fixture(scope="module")
def empty_channel():
    mock_channel = namedtuple("Channel", "id")
    return mock_channel(random.randint(1, 999999999))


@pytest.fixture(scope="module")
def empty_role():
    mock_role = namedtuple("Role", "id")
    return mock_role(random.randint(1, 999999999))


@pytest.fixture()
def member_factory(guild_factory):
    mock_member = namedtuple("Member", "id guild display_name")

    class MemberFactory:
        def get(self):
            return mock_member(random.randint(1, 999999999), guild_factory.get(), "Testing_Name")

    return MemberFactory()


@pytest.fixture()
def empty_member(member_factory):
    return member_factory.get()


@pytest.fixture()
def user_factory():
    mock_user = namedtuple("User", "id")

    class UserFactory:
        def get(self):
            return mock_user(random.randint(1, 999999999))

    return UserFactory()


@pytest.fixture()
def empty_user(user_factory):
    return user_factory.get()


@pytest.fixture(scope="module")
def empty_message():
    mock_msg = namedtuple("Message", "content")
    return mock_msg("No content.")


@pytest.fixture(scope="module")
def newline_message():
    mock_msg = type("", (), {})()
    mock_msg.content = "!test a\nb\nc"
    return mock_msg


@pytest.fixture(scope="module")
def prefix():
    return "!"


@pytest.fixture()
def ctx(empty_member, empty_channel, red):
    mock_ctx = namedtuple("Context", "author guild channel message bot")
    return mock_ctx(empty_member, empty_member.guild, empty_channel, empty_message, red)


# endregion


# region Red Mock
@pytest.fixture()
def red(config_fr):
    from redbot.core._cli import parse_cli_flags

    cli_flags = parse_cli_flags(["ignore_me"])

    description = "Red v3 - Alpha"

    Config.get_core_conf = lambda *args, **kwargs: config_fr

    red = Red(cli_flags=cli_flags, description=description, dm_help=None, owner_ids=set())

    yield red


# endregion
