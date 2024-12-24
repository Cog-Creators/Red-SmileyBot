import pytest
from redbot.pytest.economy import *


async def test_bank_register(bank, ctx):
    default_bal = await bank.get_default_balance(ctx.guild)
    assert default_bal == (await bank.get_account(ctx.author)).balance


async def has_account(member, bank):
    balance = await bank.get_balance(member)
    if balance == 0:
        balance = 1
    await bank.set_balance(member, balance)


async def test_bank_transfer(bank, member_factory):
    mbr1 = member_factory.get()
    mbr2 = member_factory.get()
    bal1 = (await bank.get_account(mbr1)).balance
    bal2 = (await bank.get_account(mbr2)).balance
    await bank.transfer_credits(mbr1, mbr2, 50)
    newbal1 = (await bank.get_account(mbr1)).balance
    newbal2 = (await bank.get_account(mbr2)).balance
    assert bal1 - 50 == newbal1
    assert bal2 + 50 == newbal2


async def test_bank_set(bank, member_factory):
    mbr = member_factory.get()
    await bank.set_balance(mbr, 250)
    acc = await bank.get_account(mbr)
    assert acc.balance == 250


async def test_bank_can_spend(bank, member_factory):
    mbr = member_factory.get()
    canspend = await bank.can_spend(mbr, 50)
    assert canspend == (50 < await bank.get_default_balance(mbr.guild))
    await bank.set_balance(mbr, 200)
    acc = await bank.get_account(mbr)
    canspendnow = await bank.can_spend(mbr, 100)
    assert canspendnow


async def test_set_bank_name(bank, guild_factory):
    guild = guild_factory.get()
    await bank.set_bank_name("Test Bank", guild)
    name = await bank.get_bank_name(guild)
    assert name == "Test Bank"


async def test_set_currency_name(bank, guild_factory):
    guild = guild_factory.get()
    await bank.set_currency_name("Coins", guild)
    name = await bank.get_currency_name(guild)
    assert name == "Coins"


async def test_set_default_balance(bank, guild_factory):
    guild = guild_factory.get()
    await bank.set_default_balance(500, guild)
    default_bal = await bank.get_default_balance(guild)
    assert default_bal == 500


async def test_nonint_transaction_amount(bank, member_factory):
    mbr1 = member_factory.get()
    mbr2 = member_factory.get()
    with pytest.raises(TypeError):
        await bank.deposit_credits(mbr1, 1.0)
    with pytest.raises(TypeError):
        await bank.withdraw_credits(mbr1, 1.0)
    with pytest.raises(TypeError):
        await bank.transfer_credits(mbr1, mbr2, 1.0)
