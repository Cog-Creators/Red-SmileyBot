from typing import Optional, Dict

import discord

from dataclasses import dataclass


@dataclass
class MuteResponse:
    success: bool
    reason: Optional[str]
    user: discord.Member


@dataclass
class ChannelMuteResponse(MuteResponse):
    channel: discord.abc.GuildChannel
    old_overs: Optional[Dict[str, bool]]
    voice_mute: bool
