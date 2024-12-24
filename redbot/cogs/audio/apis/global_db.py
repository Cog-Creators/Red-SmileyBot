import asyncio
import contextlib
import json

from copy import copy
from pathlib import Path
from typing import TYPE_CHECKING, Mapping, Optional, Union

import aiohttp
from lavalink.rest_api import LoadResult
from red_commons.logging import getLogger

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import Cog
from redbot.core.i18n import Translator

from ..audio_dataclasses import Query

if TYPE_CHECKING:
    from .. import Audio

_API_URL = "https://api.redbot.app/"
_ = Translator("Audio", Path(__file__))
log = getLogger("red.cogs.Audio.api.GlobalDB")


class GlobalCacheWrapper:
    def __init__(
        self, bot: Red, config: Config, session: aiohttp.ClientSession, cog: Union["Audio", Cog]
    ):
        # Place Holder for the Global Cache PR
        self.bot = bot
        self.config = config
        self.session = session
        self.api_key = None
        self._handshake_token = ""
        self.has_api_key = None
        self._token: Mapping[str, str] = {}
        self.cog = cog

    async def update_token(self, new_token: Mapping[str, str]):
        self._token = new_token
        await self.get_perms()

    async def _get_api_key(
        self,
    ) -> Optional[str]:
        if not self._token:
            self._token = await self.bot.get_shared_api_tokens("audiodb")
        self.api_key = self._token.get("api_key", None)
        self.has_api_key = self.cog.global_api_user.get("can_post")
        id_list = list(self.bot.owner_ids)
        self._handshake_token = "||".join(map(str, id_list))
        return self.api_key

    async def get_call(self, query: Optional[Query] = None) -> dict:
        api_url = f"{_API_URL}api/v2/queries"
        if not self.cog.global_api_user.get("can_read"):
            return {}
        try:
            query = Query.process_input(query, self.cog.local_folder_current_path)
            if any([not query or not query.valid or query.is_spotify or query.is_local]):
                return {}
            await self._get_api_key()
            if self.api_key is None:
                return {}
            search_response = "error"
            query = query.lavalink_query
            with contextlib.suppress(aiohttp.ContentTypeError, asyncio.TimeoutError):
                async with self.session.get(
                    api_url,
                    timeout=aiohttp.ClientTimeout(total=await self.config.global_db_get_timeout()),
                    headers={"Authorization": self.api_key, "X-Token": self._handshake_token},
                    params={"query": query},
                ) as r:
                    search_response = await r.json(loads=json.loads)
                    log.trace(
                        "GET || Ping %s || Status code %s || %s",
                        r.headers.get("x-process-time"),
                        r.status,
                        query,
                    )
            if "tracks" not in search_response:
                return {}
            return search_response
        except Exception as exc:
            log.trace("Failed to Get query: %s/%s", api_url, query, exc_info=exc)
        return {}

    async def get_spotify(self, title: str, author: Optional[str]) -> dict:
        if not self.cog.global_api_user.get("can_read"):
            return {}
        api_url = f"{_API_URL}api/v2/queries/spotify"
        try:
            search_response = "error"
            params = {"title": title, "author": author}
            await self._get_api_key()
            if self.api_key is None:
                return {}
            with contextlib.suppress(aiohttp.ContentTypeError, asyncio.TimeoutError):
                async with self.session.get(
                    api_url,
                    timeout=aiohttp.ClientTimeout(total=await self.config.global_db_get_timeout()),
                    headers={"Authorization": self.api_key, "X-Token": self._handshake_token},
                    params=params,
                ) as r:
                    search_response = await r.json(loads=json.loads)
                    log.trace(
                        "GET/spotify || Ping %s || Status code %s || %s - %s",
                        r.headers.get("x-process-time"),
                        r.status,
                        title,
                        author,
                    )
            if "tracks" not in search_response:
                return {}
            return search_response
        except Exception as exc:
            log.trace("Failed to Get query: %s", api_url, exc_info=exc)
        return {}

    async def post_call(self, llresponse: LoadResult, query: Optional[Query]) -> None:
        try:
            if not self.cog.global_api_user.get("can_post"):
                return
            query = Query.process_input(query, self.cog.local_folder_current_path)
            if llresponse.has_error or llresponse.load_type.value in ["NO_MATCHES", "LOAD_FAILED"]:
                return
            if query and query.valid and query.is_youtube:
                query = query.lavalink_query
            else:
                return None
            await self._get_api_key()
            if self.api_key is None:
                return None
            api_url = f"{_API_URL}api/v2/queries"
            async with self.session.post(
                api_url,
                json=llresponse._raw,
                headers={"Authorization": self.api_key, "X-Token": self._handshake_token},
                params={"query": query},
            ) as r:
                await r.read()
                log.trace(
                    "GET || Ping %s || Status code %s || %s",
                    r.headers.get("x-process-time"),
                    r.status,
                    query,
                )
        except Exception as exc:
            log.trace("Failed to post query: %s", query, exc_info=exc)
        await asyncio.sleep(0)

    async def update_global(self, llresponse: LoadResult, query: Optional[Query] = None):
        await self.post_call(llresponse=llresponse, query=query)

    async def report_invalid(self, id: str) -> None:
        if not self.cog.global_api_user.get("can_delete"):
            return
        api_url = f"{_API_URL}api/v2/queries/es/id"
        with contextlib.suppress(Exception):
            async with self.session.delete(
                api_url,
                headers={"Authorization": self.api_key, "X-Token": self._handshake_token},
                params={"id": id},
            ) as r:
                await r.read()

    async def get_perms(self):
        global_api_user = copy(self.cog.global_api_user)
        await self._get_api_key()
        # global API is force-disabled right now
        is_enabled = False
        if (not is_enabled) or self.api_key is None:
            return global_api_user
        with contextlib.suppress(Exception):
            async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
                async with session.get(
                    f"{_API_URL}api/v2/users/me",
                    headers={"Authorization": self.api_key, "X-Token": self._handshake_token},
                ) as resp:
                    if resp.status == 200:
                        search_response = await resp.json(loads=json.loads)
                        global_api_user["fetched"] = True
                        global_api_user["can_read"] = search_response.get("can_read", False)
                        global_api_user["can_post"] = search_response.get("can_post", False)
                        global_api_user["can_delete"] = search_response.get("can_delete", False)
        return global_api_user
