import discord

import random

__all__ = ("randomize_colour", "randomize_color")


def randomize_colour(embed: discord.Embed) -> discord.Embed:
    """
    Gives the provided embed a random color.
    There is an alias for this called randomize_color

    Parameters
    ----------
    embed : discord.Embed
        The embed to add a color to

    Returns
    -------
    discord.Embed
        The embed with the color set to a random color

    """
    embed.colour = discord.Color(value=random.randint(0x000000, 0xFFFFFF))
    return embed


randomize_color = randomize_colour
