from abc import ABC, abstractmethod
from typing import Optional

import discord
from redbot.core import Config, commands
from redbot.core.bot import Red


class MixinMeta(ABC):
    """
    Base class for well behaved type hint detection with composite class.

    Basically, to keep developers sane when not all attributes are defined in each mixin.
    """

    def __init__(self, *_args):
        self.config: Config
        self.bot: Red
        self.cache: dict

    @staticmethod
    @abstractmethod
    async def _voice_perm_check(
        ctx: commands.Context, user_voice_state: Optional[discord.VoiceState], **perms: bool
    ) -> bool:
        raise NotImplementedError()
