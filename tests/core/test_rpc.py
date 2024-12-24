import pytest

from redbot.pytest.rpc import *
from redbot.core._rpc import get_name


def test_get_name(cog):
    assert get_name(cog.cofunc) == "COG__COFUNC"
    assert get_name(cog.cofunc2) == "COG__COFUNC2"
    assert get_name(cog.func) == "COG__FUNC"


def test_internal_methods_exist(rpc):
    assert "GET_METHODS" in rpc._rpc.methods


def test_add_method(rpc, cog):
    rpc.add_method(cog.cofunc)

    assert get_name(cog.cofunc) in rpc._rpc.methods


def test_double_add(rpc, cog):
    rpc.add_method(cog.cofunc)
    count = len(rpc._rpc.methods)

    rpc.add_method(cog.cofunc)

    assert count == len(rpc._rpc.methods)


def test_add_notcoro_method(rpc, cog):
    with pytest.raises(TypeError):
        rpc.add_method(cog.func)


def test_add_multi(rpc, cog):
    funcs = [cog.cofunc, cog.cofunc2, cog.cofunc3]
    rpc.add_multi_method(*funcs)

    names = [get_name(f) for f in funcs]

    assert all(n in rpc._rpc.methods for n in names)


def test_add_multi_bad(rpc, cog):
    funcs = [cog.cofunc, cog.cofunc2, cog.cofunc3, cog.func]

    with pytest.raises(TypeError):
        rpc.add_multi_method(*funcs)

    names = [get_name(f) for f in funcs]

    assert not any(n in rpc._rpc.methods for n in names)


def test_remove_method(rpc, existing_func):
    before_count = len(rpc._rpc.methods)
    rpc.remove_method(existing_func)

    assert get_name(existing_func) not in rpc._rpc.methods
    assert before_count - 1 == len(rpc._rpc.methods)


def test_remove_multi_method(rpc, existing_multi_func):
    before_count = len(rpc._rpc.methods)
    name = get_name(existing_multi_func[0])
    prefix = name.split("__")[0]

    rpc.remove_methods(prefix)

    assert before_count - len(existing_multi_func) == len(rpc._rpc.methods)

    names = [get_name(f) for f in existing_multi_func]

    assert not any(n in rpc._rpc.methods for n in names)


def test_rpcmixin_register(rpcmixin, cog):
    rpcmixin.register_rpc_handler(cog.cofunc)

    assert rpcmixin.rpc.add_method.called_once_with(cog.cofunc)

    name = get_name(cog.cofunc)
    cogname = name.split("__")[0]

    assert cogname in rpcmixin.rpc_handlers


def test_rpcmixin_unregister(rpcmixin, cog):
    rpcmixin.register_rpc_handler(cog.cofunc)
    rpcmixin.unregister_rpc_handler(cog.cofunc)

    assert rpcmixin.rpc.remove_method.called_once_with(cog.cofunc)

    name = get_name(cog.cofunc)
    cogname = name.split("__")[0]

    if cogname in rpcmixin.rpc_handlers:
        assert cog.cofunc not in rpcmixin.rpc_handlers[cogname]
