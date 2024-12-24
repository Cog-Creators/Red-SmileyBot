from collections import namedtuple
import pytest

from redbot.pytest.mod import *


async def test_modlog_register_casetype(mod):
    ct = {"name": "ban", "default_setting": True, "image": ":hammer:", "case_str": "Ban"}
    casetype = await mod.register_casetype(**ct)
    assert casetype is not None


async def test_modlog_case_create(mod, ctx, monkeypatch, member_factory, empty_user):
    from datetime import datetime, timezone

    # Run casetype register test to register casetype in this test too
    await test_modlog_register_casetype(mod)

    usr = member_factory.get()
    guild = ctx.guild
    bot = ctx.bot
    case_type = "ban"
    moderator = ctx.author
    reason = "Test 12345"
    created_at = datetime.now(timezone.utc)
    # mod.create_case needs bot to have a user object. Without a connection to discord it would be none by default.
    # due to the implementation of bot.user we need to set the user as part of bot._connection
    mock_connection = namedtuple("Connection", "user")
    monkeypatch.setattr(bot, "_connection", mock_connection(empty_user))
    case = await mod.create_case(bot, guild, created_at, case_type, usr, moderator, reason)
    assert case is not None
    assert case.user == usr
    assert case.action_type == case_type
    assert case.moderator == moderator
    assert case.reason == reason
    assert case.created_at == int(created_at.timestamp())


async def test_modlog_set_modlog_channel(mod, ctx):
    await mod.set_modlog_channel(ctx.guild, ctx.channel)
    assert await mod.get_modlog_channel(ctx.guild) == ctx.channel.id
