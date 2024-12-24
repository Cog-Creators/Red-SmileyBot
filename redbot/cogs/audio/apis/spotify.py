import base64
import contextlib
import json
import time
from pathlib import Path

from typing import TYPE_CHECKING, List, Mapping, MutableMapping, Optional, Tuple, Union

import aiohttp
from red_commons.logging import getLogger

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import Cog, Context
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter

from ..errors import SpotifyFetchError

if TYPE_CHECKING:
    from .. import Audio

_ = Translator("Audio", Path(__file__))

log = getLogger("red.cogs.Audio.api.Spotify")


CATEGORY_ENDPOINT = "https://api.spotify.com/v1/browse/categories"
TOKEN_ENDPOINT = "https://accounts.spotify.com/api/token"
ALBUMS_ENDPOINT = "https://api.spotify.com/v1/albums"
TRACKS_ENDPOINT = "https://api.spotify.com/v1/tracks"
PLAYLISTS_ENDPOINT = "https://api.spotify.com/v1/playlists"


class SpotifyWrapper:
    """Wrapper for the Spotify API."""

    def __init__(
        self, bot: Red, config: Config, session: aiohttp.ClientSession, cog: Union["Audio", Cog]
    ):
        self.bot = bot
        self.config = config
        self.session = session
        self.spotify_token: Optional[MutableMapping] = None
        self.client_id: Optional[str] = None
        self.client_secret: Optional[str] = None
        self._token: Mapping[str, str] = {}
        self.cog = cog

    @staticmethod
    def spotify_format_call(query_type: str, key: str) -> Tuple[str, MutableMapping]:
        """Format the spotify endpoint."""
        params: MutableMapping = {}
        if query_type == "album":
            query = f"{ALBUMS_ENDPOINT}/{key}/tracks"
        elif query_type == "track":
            query = f"{TRACKS_ENDPOINT}/{key}"
        else:
            query = f"{PLAYLISTS_ENDPOINT}/{key}/tracks"
        return query, params

    async def get_spotify_track_info(
        self, track_data: MutableMapping, ctx: Context
    ) -> Tuple[str, ...]:
        """Extract track info from spotify response."""
        prefer_lyrics = await self.cog.get_lyrics_status(ctx)
        track_name = track_data["name"]
        if prefer_lyrics:
            track_name = f"{track_name} - lyrics"
        artist_name = track_data["artists"][0]["name"]
        track_info = f"{track_name} {artist_name}"
        song_url = track_data.get("external_urls", {}).get("spotify")
        uri = track_data["uri"]
        _id = track_data["id"]
        _type = track_data["type"]

        return song_url, track_info, uri, artist_name, track_name, _id, _type

    @staticmethod
    async def is_access_token_valid(token: MutableMapping) -> bool:
        """Check if current token is not too old."""
        return (token["expires_at"] - int(time.time())) < 60

    @staticmethod
    def make_auth_header(
        client_id: Optional[str], client_secret: Optional[str]
    ) -> MutableMapping[str, Union[str, int]]:
        """Make Authorization header for spotify token."""
        if client_id is None:
            client_id = ""
        if client_secret is None:
            client_secret = ""
        auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode("ascii"))
        return {"Authorization": f"Basic {auth_header.decode('ascii')}"}

    async def get(
        self, url: str, headers: MutableMapping = None, params: MutableMapping = None
    ) -> MutableMapping[str, str]:
        """Make a GET request to the spotify API."""
        if params is None:
            params = {}
        async with self.session.request("GET", url, params=params, headers=headers) as r:
            data = await r.json(loads=json.loads)
            if r.status != 200:
                log.verbose("Issue making GET request to %r: [%s] %r", url, r.status, data)
            return data

    async def update_token(self, new_token: Mapping[str, str]):
        self._token = new_token

    async def get_token(self) -> None:
        """Get the stored spotify tokens."""
        if not self._token:
            self._token = await self.bot.get_shared_api_tokens("spotify")

        self.client_id = self._token.get("client_id", "")
        self.client_secret = self._token.get("client_secret", "")

    async def get_country_code(self, ctx: Context = None) -> str:
        return (
            (
                await self.config.user(ctx.author).country_code()
                or await self.config.guild(ctx.guild).country_code()
            )
            if ctx
            else "US"
        )

    async def request_access_token(self) -> MutableMapping:
        """Make a spotify call to get the auth token."""
        await self.get_token()
        payload = {"grant_type": "client_credentials"}
        headers = self.make_auth_header(self.client_id, self.client_secret)
        r = await self.post(TOKEN_ENDPOINT, payload=payload, headers=headers)
        return r

    async def get_access_token(self) -> Optional[str]:
        """Get the access_token."""
        if self.spotify_token and not await self.is_access_token_valid(self.spotify_token):
            return self.spotify_token["access_token"]
        token = await self.request_access_token()
        if token is None:
            log.debug("Requested a token from Spotify, did not end up getting one.")
        try:
            token["expires_at"] = int(time.time()) + int(token["expires_in"])
        except KeyError:
            return None
        self.spotify_token = token
        log.debug("Created a new access token for Spotify: %s", token)
        return self.spotify_token["access_token"]

    async def post(
        self, url: str, payload: MutableMapping, headers: MutableMapping = None
    ) -> MutableMapping:
        """Make a POST call to spotify."""
        async with self.session.post(url, data=payload, headers=headers) as r:
            data = await r.json(loads=json.loads)
            if r.status != 200:
                log.verbose("Issue making POST request to %r: [%s] %r", url, r.status, data)
            return data

    async def make_get_call(self, url: str, params: MutableMapping) -> MutableMapping:
        """Make a Get call to spotify."""
        token = await self.get_access_token()
        return await self.get(url, params=params, headers={"Authorization": f"Bearer {token}"})

    async def get_categories(self, ctx: Context = None) -> List[MutableMapping]:
        """Get the spotify categories."""
        country_code = await self.get_country_code(ctx=ctx)
        params: MutableMapping = {"country": country_code} if country_code else {}
        result = await self.make_get_call(CATEGORY_ENDPOINT, params=params)
        with contextlib.suppress(KeyError):
            if result["error"]["status"] == 401:
                raise SpotifyFetchError(
                    message=_(
                        "The Spotify API key or client secret has not been set properly. "
                        "\nUse `{prefix}audioset spotifyapi` for instructions."
                    )
                )
        categories = result.get("categories", {}).get("items", [])
        return [{c["name"]: c["id"]} for c in categories if c]

    async def get_playlist_from_category(self, category: str, ctx: Context = None):
        """Get spotify playlists for the specified category."""
        url = f"{CATEGORY_ENDPOINT}/{category}/playlists"
        country_code = await self.get_country_code(ctx=ctx)
        params: MutableMapping = {"country": country_code} if country_code else {}
        result = await self.make_get_call(url, params=params)
        playlists = result.get("playlists", {}).get("items", [])
        return [
            {
                "name": c["name"],
                "uri": c["uri"],
                "url": c.get("external_urls", {}).get("spotify"),
                "tracks": c.get("tracks", {}).get("total", "Unknown"),
            }
            async for c in AsyncIter(playlists)
            if c
        ]
