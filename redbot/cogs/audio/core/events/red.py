import asyncio
from pathlib import Path
from typing import Literal, Mapping

from red_commons.logging import getLogger

from redbot.core import commands
from redbot.core.i18n import Translator
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = getLogger("red.cogs.Audio.cog.Events.red")
_ = Translator("Audio", Path(__file__))


class RedEvents(MixinMeta, metaclass=CompositeMetaClass):
    @commands.Cog.listener()
    async def on_red_api_tokens_update(
        self, service_name: str, api_tokens: Mapping[str, str]
    ) -> None:
        if service_name == "youtube":
            await self.api_interface.youtube_api.update_token(api_tokens)
        elif service_name == "spotify":
            await self.api_interface.spotify_api.update_token(api_tokens)
        elif service_name == "audiodb":
            await self.api_interface.global_cache_api.update_token(api_tokens)

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        await self.cog_ready_event.wait()

        if requester in ("discord_deleted_user", "owner"):
            await self.playlist_api.handle_playlist_user_id_deletion(user_id)

            all_equalizers = await self.config.custom("EQUALIZER").all()

            collected_for_removal = []

            c = 0
            for guild_id, guild_equalizers in all_equalizers.items():
                c += 1
                if not c % 100:
                    await asyncio.sleep(0)

                for preset_name, preset in guild_equalizers.get("eq_presets", {}).items():
                    c += 1
                    if not c % 100:
                        await asyncio.sleep(0)

                    if preset.get("author", 0) == user_id:
                        collected_for_removal.append((guild_id, preset_name))

            async with self.config.custom("EQUALIZER").all() as all_eqs:
                for guild_id, preset_name in collected_for_removal:
                    all_eqs[str(guild_id)]["eq_presets"][preset_name]["author"] = 0xDE1
