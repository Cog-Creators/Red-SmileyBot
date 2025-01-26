import pytest
from redbot.pytest.alias import *


def test_is_valid_alias_name(alias):
    assert alias.is_valid_alias_name("valid") is True
    assert alias.is_valid_alias_name("not valid name") is False


async def test_empty_guild_aliases(alias, empty_guild):
    assert list(await alias._aliases.get_guild_aliases(empty_guild)) == []


async def test_empty_global_aliases(alias):
    assert list(await alias._aliases.get_global_aliases()) == []


async def create_test_guild_alias(alias, ctx):
    await alias._aliases.add_alias(ctx, "test", "ping", global_=False)


async def create_test_global_alias(alias, ctx):
    await alias._aliases.add_alias(ctx, "test_global", "ping", global_=True)


async def test_add_guild_alias(alias, ctx):
    await create_test_guild_alias(alias, ctx)

    alias_obj = await alias._aliases.get_alias(ctx.guild, "test")
    assert alias_obj.name == "test"


async def test_translate_alias_message(alias, ctx, newline_message, prefix):
    await create_test_guild_alias(alias, ctx)
    alias_obj = await alias._aliases.get_alias(ctx.guild, "test")

    translated_message = alias.translate_alias_message(newline_message, prefix, alias_obj)

    original_content = newline_message.content.split(" ", 1)[1]
    original_content = original_content.replace(" ", "")
    new_content = translated_message.content.split(" ", 1)[1]
    new_content = new_content.replace(" ", "")

    assert new_content == original_content


async def test_delete_guild_alias(alias, ctx):
    await create_test_guild_alias(alias, ctx)
    alias_obj = await alias._aliases.get_alias(ctx.guild, "test")
    assert alias_obj.name == "test"

    did_delete = await alias._aliases.delete_alias(ctx, "test")
    assert did_delete is True

    alias_obj = await alias._aliases.get_alias(ctx.guild, "test")
    assert alias_obj is None


async def test_add_global_alias(alias, ctx):
    await create_test_global_alias(alias, ctx)
    alias_obj = await alias._aliases.get_alias(ctx.guild, "test_global")

    assert alias_obj.name == "test_global"


async def test_delete_global_alias(alias, ctx):
    await create_test_global_alias(alias, ctx)
    alias_obj = await alias._aliases.get_alias(ctx.guild, "test_global")
    assert alias_obj.name == "test_global"

    did_delete = await alias._aliases.delete_alias(ctx, alias_name="test_global", global_=True)
    assert did_delete is True

    alias_obj = await alias._aliases.get_alias(None, "test_global")
    assert alias_obj is None
