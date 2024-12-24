import asyncio
from unittest.mock import patch
import pytest
from collections import Counter


# region Register Tests
async def test_config_register_global(config):
    config.register_global(enabled=False)
    assert config.defaults["GLOBAL"]["enabled"] is False
    assert await config.enabled() is False


def test_config_register_global_badvalues(config):
    with pytest.raises(RuntimeError):
        config.register_global(**{"invalid var name": True})


async def test_config_register_guild(config, empty_guild):
    config.register_guild(enabled=False, some_list=[], some_dict={})
    assert config.defaults[config.GUILD]["enabled"] is False
    assert config.defaults[config.GUILD]["some_list"] == []
    assert config.defaults[config.GUILD]["some_dict"] == {}

    assert await config.guild(empty_guild).enabled() is False
    assert await config.guild(empty_guild).some_list() == []
    assert await config.guild(empty_guild).some_dict() == {}


async def test_config_register_channel(config, empty_channel):
    config.register_channel(enabled=False)
    assert config.defaults[config.CHANNEL]["enabled"] is False
    assert await config.channel(empty_channel).enabled() is False


async def test_config_register_role(config, empty_role):
    config.register_role(enabled=False)
    assert config.defaults[config.ROLE]["enabled"] is False
    assert await config.role(empty_role).enabled() is False


async def test_config_register_member(config, empty_member):
    config.register_member(some_number=-1)
    assert config.defaults[config.MEMBER]["some_number"] == -1
    assert await config.member(empty_member).some_number() == -1


async def test_config_register_user(config, empty_user):
    config.register_user(some_value=None)
    assert config.defaults[config.USER]["some_value"] is None
    assert await config.user(empty_user).some_value() is None


async def test_config_force_register_global(config_fr):
    with pytest.raises(AttributeError):
        await config_fr.enabled()

    config_fr.register_global(enabled=True)
    assert await config_fr.enabled() is True


# endregion


# Test nested registration
async def test_nested_registration(config):
    config.register_global(foo__bar__baz=False)
    assert await config.foo.bar.baz() is False


async def test_nested_registration_asdict(config):
    defaults = {"bar": {"baz": False}}
    config.register_global(foo=defaults)

    assert await config.foo.bar.baz() is False


async def test_nested_registration_and_changing(config):
    defaults = {"bar": {"baz": False}}
    config.register_global(foo=defaults)

    assert await config.foo.bar.baz() is False

    with pytest.raises(ValueError):
        await config.foo.set(True)


async def test_doubleset_default(config):
    config.register_global(foo=True)
    config.register_global(foo=False)

    assert await config.foo() is False


async def test_nested_registration_multidict(config):
    defaults = {"foo": {"bar": {"baz": True}}, "blah": True}
    config.register_global(**defaults)

    assert await config.foo.bar.baz() is True
    assert await config.blah() is True


def test_nested_group_value_badreg(config):
    config.register_global(foo=True)
    with pytest.raises(KeyError):
        config.register_global(foo__bar=False)


async def test_nested_toplevel_reg(config):
    defaults = {"bar": True, "baz": False}
    config.register_global(foo=defaults)

    assert await config.foo.bar() is True
    assert await config.foo.baz() is False


async def test_nested_overlapping(config):
    config.register_global(foo__bar=True)
    config.register_global(foo__baz=False)

    assert await config.foo.bar() is True
    assert await config.foo.baz() is False


async def test_nesting_nofr(config):
    config.register_global(foo={})
    assert await config.foo.bar() is None
    assert await config.foo() == {}


# region Default Value Overrides
async def test_global_default_override(config):
    assert await config.enabled(True) is True


async def test_global_default_nofr(config):
    assert await config.nofr() is None
    assert await config.nofr(True) is True


async def test_guild_default_override(config, empty_guild):
    assert await config.guild(empty_guild).enabled(True) is True


async def test_channel_default_override(config, empty_channel):
    assert await config.channel(empty_channel).enabled(True) is True


async def test_role_default_override(config, empty_role):
    assert await config.role(empty_role).enabled(True) is True


async def test_member_default_override(config, empty_member):
    assert await config.member(empty_member).enabled(True) is True


async def test_user_default_override(config, empty_user):
    assert await config.user(empty_user).some_value(True) is True


# endregion


# region Setting Values
async def test_set_global(config):
    await config.enabled.set(True)
    assert await config.enabled() is True


async def test_set_guild(config, empty_guild):
    await config.guild(empty_guild).enabled.set(True)
    assert await config.guild(empty_guild).enabled() is True

    curr_list = await config.guild(empty_guild).some_list([1, 2, 3])
    assert curr_list == [1, 2, 3]
    curr_list.append(4)

    await config.guild(empty_guild).some_list.set(curr_list)
    assert await config.guild(empty_guild).some_list() == curr_list


async def test_set_channel(config, empty_channel):
    await config.channel(empty_channel).enabled.set(True)
    assert await config.channel(empty_channel).enabled() is True


async def test_set_channel_no_register(config, empty_channel):
    await config.channel(empty_channel).no_register.set(True)
    assert await config.channel(empty_channel).no_register() is True


# endregion


# Dynamic attribute testing
async def test_set_dynamic_attr(config):
    await config.set_raw("foobar", value=True)

    assert await config.foobar() is True


async def test_clear_dynamic_attr(config):
    await config.foo.set(True)
    await config.clear_raw("foo")

    with pytest.raises(KeyError):
        await config.get_raw("foo")


async def test_get_dynamic_attr(config):
    assert await config.get_raw("foobaz", default=True) is True


# Member Group testing
async def test_membergroup_allguilds(config, empty_member):
    await config.member(empty_member).foo.set(False)

    all_servers = await config.all_members()
    assert empty_member.guild.id in all_servers


async def test_membergroup_allmembers(config, empty_member):
    await config.member(empty_member).foo.set(False)

    all_members = await config.all_members(empty_member.guild)
    assert empty_member.id in all_members


# Clearing testing
async def test_global_clear(config):
    config.register_global(foo=True, bar=False)

    await config.foo.set(False)
    await config.bar.set(True)

    assert await config.foo() is False
    assert await config.bar() is True

    await config.clear()

    assert await config.foo() is True
    assert await config.bar() is False


async def test_member_clear(config, member_factory):
    config.register_member(foo=True)

    m1 = member_factory.get()
    await config.member(m1).foo.set(False)
    assert await config.member(m1).foo() is False

    m2 = member_factory.get()
    await config.member(m2).foo.set(False)
    assert await config.member(m2).foo() is False

    assert m1.guild.id != m2.guild.id

    await config.member(m1).clear()
    assert await config.member(m1).foo() is True
    assert await config.member(m2).foo() is False


async def test_member_clear_all(config, member_factory):
    server_ids = []
    for _ in range(5):
        member = member_factory.get()
        await config.member(member).foo.set(True)
        server_ids.append(member.guild.id)

    member = member_factory.get()
    assert len(await config.all_members()) == len(server_ids)

    await config.clear_all_members()

    assert len(await config.all_members()) == 0


async def test_clear_all(config):
    await config.foo.set(True)
    assert await config.foo() is True

    await config.clear_all()
    with pytest.raises(KeyError):
        await config.get_raw("foo")


async def test_clear_value(config):
    await config.foo.set(True)
    await config.foo.clear()

    with pytest.raises(KeyError):
        await config.get_raw("foo")


# Get All testing
async def test_user_get_all_from_kind(config, user_factory):
    config.register_user(foo=False, bar=True)
    for _ in range(5):
        user = user_factory.get()
        await config.user(user).foo.set(True)

    all_data = await config.all_users()

    assert len(all_data) == 5

    for _, v in all_data.items():
        assert v["foo"] is True
        assert v["bar"] is True


async def test_user_getalldata(config, user_factory):
    user = user_factory.get()
    config.register_user(foo=True, bar=False)
    await config.user(user).foo.set(False)

    all_data = await config.user(user).all()

    assert "foo" in all_data
    assert "bar" in all_data

    assert config.user(user).defaults["foo"] is True


async def test_value_ctxmgr(config):
    config.register_global(foo_list=[])

    async with config.foo_list() as foo_list:
        foo_list.append("foo")

    foo_list = await config.foo_list()

    assert "foo" in foo_list


async def test_value_ctxmgr_saves(config):
    config.register_global(bar_list=[])

    try:
        async with config.bar_list() as bar_list:
            bar_list.append("bar")
            raise RuntimeError()
    except RuntimeError:
        pass

    bar_list = await config.bar_list()

    assert "bar" in bar_list


async def test_value_ctxmgr_immutable(config):
    config.register_global(foo=True)

    with pytest.raises(TypeError):
        async with config.foo() as foo:
            foo = False

    foo = await config.foo()
    assert foo is True


async def test_ctxmgr_no_shared_default(config, member_factory):
    config.register_member(foo=[])
    m1 = member_factory.get()
    m2 = member_factory.get()

    async with config.member(m1).foo() as foo:
        foo.append(1)

    assert 1 not in await config.member(m2).foo()


async def test_ctxmgr_no_unnecessary_write(config):
    config.register_global(foo=[])
    foo_value_obj = config.foo
    with patch.object(foo_value_obj, "set") as set_method:
        async with foo_value_obj() as foo:
            pass
        set_method.assert_not_called()


async def test_get_then_mutate(config):
    """Tests that mutating an object after getting it as a value doesn't mutate the data store."""
    config.register_global(list1=[])
    await config.list1.set([])
    list1 = await config.list1()
    list1.append("foo")
    list1 = await config.list1()
    assert "foo" not in list1


async def test_set_then_mutate(config):
    """Tests that mutating an object after setting it as a value doesn't mutate the data store."""
    config.register_global(list1=[])
    list1 = []
    await config.list1.set(list1)
    list1.append("foo")
    list1 = await config.list1()
    assert "foo" not in list1


async def test_call_group_fills_defaults(config):
    config.register_global(subgroup={"foo": True})
    subgroup = await config.subgroup()
    assert "foo" in subgroup


async def test_group_call_ctxmgr_writes(config):
    config.register_global(subgroup={"foo": True})
    async with config.subgroup() as subgroup:
        subgroup["bar"] = False

    subgroup = await config.subgroup()
    assert subgroup == {"foo": True, "bar": False}


async def test_all_works_as_ctxmgr(config):
    config.register_global(subgroup={"foo": True})
    async with config.subgroup.all() as subgroup:
        subgroup["bar"] = False

    subgroup = await config.subgroup()
    assert subgroup == {"foo": True, "bar": False}


async def test_get_raw_mixes_defaults(config):
    config.register_global(subgroup={"foo": True})
    await config.subgroup.set_raw("bar", value=False)

    subgroup = await config.get_raw("subgroup")
    assert subgroup == {"foo": True, "bar": False}


async def test_cast_str_raw(config):
    await config.set_raw(123, 456, value=True)
    assert await config.get_raw(123, 456) is True
    assert await config.get_raw("123", "456") is True
    await config.clear_raw("123", 456)


async def test_cast_str_nested(config):
    config.register_global(foo={})
    await config.foo.set({123: True, 456: {789: False}})
    assert await config.foo() == {"123": True, "456": {"789": False}}


def test_config_custom_noinit(config):
    with pytest.raises(ValueError):
        config.custom("TEST", 1, 2, 3)


def test_config_custom_init(config):
    config.init_custom("TEST", 3)
    config.custom("TEST", 1, 2, 3)


def test_config_custom_doubleinit(config):
    config.init_custom("TEST", 3)
    with pytest.raises(ValueError):
        config.init_custom("TEST", 2)


async def test_config_locks_cache(config, empty_guild):
    lock1 = config.foo.get_lock()
    assert lock1 is config.foo.get_lock()
    lock2 = config.guild(empty_guild).foo.get_lock()
    assert lock2 is config.guild(empty_guild).foo.get_lock()
    assert lock1 is not lock2


async def test_config_value_atomicity(config):
    config.register_global(foo=[])
    tasks = []
    for _ in range(15):

        async def func():
            async with config.foo.get_lock():
                foo = await config.foo()
                foo.append(0)
                await asyncio.sleep(0.1)
                await config.foo.set(foo)

        tasks.append(asyncio.create_task(func()))

    await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)

    assert len(await config.foo()) == 15


async def test_config_ctxmgr_atomicity(config):
    config.register_global(foo=[])
    tasks = []
    for _ in range(15):

        async def func():
            async with config.foo() as foo:
                foo.append(0)
                await asyncio.sleep(0.1)

        tasks.append(asyncio.create_task(func()))

    await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)

    assert len(await config.foo()) == 15


async def test_set_with_partial_primary_keys(config):
    config.init_custom("CUSTOM", 3)
    await config.custom("CUSTOM", "1").set({"11": {"111": {"foo": "bar"}}})
    assert await config.custom("CUSTOM", "1", "11", "111").foo() == "bar"

    await config.custom("CUSTOM", "2").set(
        {
            "11": {"111": {"foo": "bad"}},
            "22": {"111": {"foo": "baz"}},
            "33": {"111": {"foo": "boo"}, "222": {"foo": "boz"}},
        }
    )
    assert await config.custom("CUSTOM", "2", "11", "111").foo() == "bad"
    assert await config.custom("CUSTOM", "2", "22", "111").foo() == "baz"
    assert await config.custom("CUSTOM", "2", "33", "111").foo() == "boo"
    assert await config.custom("CUSTOM", "2", "33", "222").foo() == "boz"

    await config.custom("CUSTOM", "2").set({"22": {}, "33": {"111": {}, "222": {"foo": "biz"}}})
    with pytest.raises(KeyError):
        await config.custom("CUSTOM").get_raw("2", "11")
    with pytest.raises(KeyError):
        await config.custom("CUSTOM").get_raw("2", "22", "111")
    with pytest.raises(KeyError):
        await config.custom("CUSTOM").get_raw("2", "33", "111", "foo")
    assert await config.custom("CUSTOM", "2", "33", "222").foo() == "biz"


async def test_raw_with_partial_primary_keys(config):
    config.init_custom("CUSTOM", 1)
    await config.custom("CUSTOM").set_raw("primary_key", "identifier", value=True)
    assert await config.custom("CUSTOM", "primary_key").identifier() is True
    await config.custom("CUSTOM").set_raw(value={"primary_key": {"identifier": False}})
    assert await config.custom("CUSTOM", "primary_key").identifier() is False


@pytest.mark.asyncio
async def test_cast_subclass_default(config):
    # regression test for GH-5557/GH-5585
    config.register_global(foo=Counter({}))
    assert type(config.defaults["GLOBAL"]["foo"]) is dict
    assert config.defaults["GLOBAL"]["foo"] == {}
    stored_value = await config.foo()
    assert type(stored_value) is dict
    assert stored_value == {}
    await config.foo.set(Counter({"bar": 1}))
    stored_value = await config.foo()
    assert type(stored_value) is dict
    assert stored_value == {"bar": 1}


"""
Following PARAMS can be generated with:
from functools import reduce
from pprint import pprint
def generate_test_args(print_args=True):
    pkeys = ("1", "2", "3")
    identifiers = ("foo",)
    full_dict = {"1": {"2": {"3": {"foo": "bar"}}}}
    argvalues = [
        (
            pkeys[:x],
            (pkeys[x:] + identifiers)[:y],
            reduce(lambda d, k: d[k], (pkeys + identifiers)[:x+y], full_dict),
        )
        for x in range(len(pkeys) + 1)
        for y in range(len(pkeys) + len(identifiers) - x + 1)
    ]
    if print_args:
        print("[")
        for args in argvalues:
            print(f"    {args!r},")
        print("]")
    else:
        return argvalues
generate_test_args()
"""
PARAMS = [
    ((), (), {"1": {"2": {"3": {"foo": "bar"}}}}),
    ((), (1,), {"2": {"3": {"foo": "bar"}}}),
    ((), (1, 2), {"3": {"foo": "bar"}}),
    ((), (1, 2, 3), {"foo": "bar"}),
    ((), (1, 2, 3, "foo"), "bar"),
    ((1,), (), {"2": {"3": {"foo": "bar"}}}),
    ((1,), (2,), {"3": {"foo": "bar"}}),
    ((1,), (2, 3), {"foo": "bar"}),
    ((1,), (2, 3, "foo"), "bar"),
    ((1, 2), (), {"3": {"foo": "bar"}}),
    ((1, 2), (3,), {"foo": "bar"}),
    ((1, 2), (3, "foo"), "bar"),
    ((1, 2, 3), (), {"foo": "bar"}),
    ((1, 2, 3), ("foo",), "bar"),
]


@pytest.mark.parametrize("pkeys, raw_args, result", PARAMS)
async def test_config_custom_partial_pkeys_get(config, pkeys, raw_args, result):
    # setup
    config.init_custom("TEST", 3)
    config.register_custom("TEST")
    await config.custom("TEST", 1, 2, 3).set({"foo": "bar"})

    group = config.custom("TEST", *pkeys)
    assert await group.get_raw(*raw_args) == result


@pytest.mark.parametrize("pkeys, raw_args, result", PARAMS)
async def test_config_custom_partial_pkeys_set(config, pkeys, raw_args, result):
    # setup
    config.init_custom("TEST", 3)
    config.register_custom("TEST")
    await config.custom("TEST", 1, 2, 3).set({"foo": "blah"})

    group = config.custom("TEST", *pkeys)
    await group.set_raw(*raw_args, value=result)
    assert await group.get_raw(*raw_args) == result


@pytest.mark.asyncio
async def test_config_custom_get_raw_with_default_on_whole_scope(config):
    config.init_custom("TEST", 3)
    config.register_custom("TEST")

    group = config.custom("TEST")
    assert await group.get_raw(default=True) is True


@pytest.mark.parametrize(
    "pkeys,raw_args,to_set",
    (
        # no config data for (cog_name, cog_id) is present
        ((), (), None),
        ((1,), (), None),
        ((1, 2), (), None),
        ((1, 2, 3), (), None),
        ((1, 2, 3), ("key1",), None),
        ((1, 2, 3), ("key1", "key2"), None),
        # config data for (cog_name, cog_id) is present but scope does not exist
        ((), (), ()),
        ((1,), (), ()),
        ((1, 2), (), ()),
        ((1, 2, 3), (), ()),
        ((1, 2, 3), ("key1",), ()),
        ((1, 2, 3), ("key1", "key2"), ()),
        # the scope exists with no records
        ((1,), (), ("1",)),
        ((1, 2), (), ("1",)),
        ((1, 2, 3), (), ("1",)),
        ((1, 2, 3), ("key1",), ("1",)),
        ((1, 2, 3), ("key1", "key2"), ("1",)),
        # scope with partial primary key (1,) exists
        ((1, 2), (), ("1", "2")),
        ((1, 2, 3), (), ("1", "2")),
        ((1, 2, 3), ("key1",), ("1", "2")),
        ((1, 2, 3), ("key1", "key2"), ("1", "2")),
        # scope with partial primary key (1, 2) exists
        ((1, 2, 3), (), ("1", "2", "3")),
        ((1, 2, 3), ("key1",), ("1", "2", "3")),
        ((1, 2, 3), ("key1", "key2"), ("1", "2", "3")),
        # scope with full primary key (1, 2, 3)
        ((1, 2, 3), ("key1",), ("1", "2", "3", "key1")),
        ((1, 2, 3), ("key1", "key2"), ("1", "2", "3", "key1")),
        # scope with full primary key (1, 2, 3) and a group named "key1" exists
        ((1, 2, 3), ("key1", "key2"), ("1", "2", "3", "key1", "key2")),
    ),
)
@pytest.mark.asyncio
async def test_config_custom_clear_identifiers_that_do_not_exist(config, pkeys, raw_args, to_set):
    config.init_custom("TEST", 3)
    config.register_custom("TEST")

    group = config.custom("TEST", *pkeys)
    if to_set is not None:
        data = {}
        partial = data
        for key in to_set:
            partial[key] = {}
            partial = partial[key]
        scope = config.custom("TEST")
        await scope.set(data)
        # Clear needed to be able to differ between missing config data and missing scope data
        await scope.clear_raw(*to_set)
    await group.clear_raw(*raw_args)
