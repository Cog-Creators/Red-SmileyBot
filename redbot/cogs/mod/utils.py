import discord

from collections import defaultdict, deque

from redbot.core.bot import Red
from redbot.core.config import Config


async def is_allowed_by_hierarchy(
    bot: Red, config: Config, guild: discord.Guild, mod: discord.Member, user: discord.Member
):
    if not await config.guild(guild).respect_hierarchy():
        return True
    is_special = mod == guild.owner or await bot.is_owner(mod)
    return mod.top_role > user.top_role or is_special


def lambda_cache(repeats_channel):
    return lambda: deque(maxlen=repeats_channel if repeats_channel != -1 else 0)


async def create_new_cache(config: Config, guild: discord.Guild):
    repeats = await config.guild(guild).delete_repeats()
    channel_data = await config.all_channels()
    guild_cache = defaultdict(
        lambda: defaultdict(lambda: deque(maxlen=repeats if repeats != -1 else 0))
    )
    # Create already keys for custom amount of repeated messages per channel
    for channel in guild.channels:
        data = channel_data.get(channel.id, None)
        if data is not None and data["delete_repeats"]:
            guild_cache[channel.id] = defaultdict(lambda_cache(data["delete_repeats"]))
    return guild_cache
