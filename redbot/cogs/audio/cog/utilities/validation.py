import logging
import re
from typing import List, Set
from urllib.parse import urlparse

import discord

from redbot.core import Config
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass
from ...audio_dataclasses import Query

log = logging.getLogger("red.cogs.Audio.cog.Utilities.validation")

_RE_YT_LIST_PLAYLIST = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com|youtu\.?be)(/playlist\?).*(list=)(.*)(&|$)"
)


class ValidationUtilities(MixinMeta, metaclass=CompositeMetaClass):
    def match_url(self, url) -> bool:
        try:
            query_url = urlparse(url)
            return all([query_url.scheme, query_url.netloc, query_url.path])
        except Exception:
            return False

    def match_yt_playlist(self, url) -> bool:
        if _RE_YT_LIST_PLAYLIST.match(url):
            return True
        return False

    def url_check(self, url) -> bool:
        valid_tld = [
            "youtube.com",
            "youtu.be",
            "soundcloud.com",
            "bandcamp.com",
            "vimeo.com",
            "beam.pro",
            "mixer.com",
            "twitch.tv",
            "spotify.com",
            "localtracks",
        ]
        query_url = urlparse(url)
        url_domain = ".".join(query_url.netloc.split(".")[-2:])
        if not query_url.netloc:
            url_domain = ".".join(query_url.path.split("/")[0].split(".")[-2:])
        return True if url_domain in valid_tld else False

    def userlimit(self, channel) -> bool:
        if channel.user_limit == 0 or channel.user_limit > len(channel.members) + 1:
            return False
        return True

    async def is_allowed(
        self, config: Config, guild: discord.Guild, query: str, query_obj: Query = None
    ) -> bool:
        """Checks if the query is allowed in this server or globally"""

        query = query.lower().strip()
        if query_obj is not None:
            query = query_obj.lavalink_query.replace("ytsearch:", "youtubesearch").replace(
                "scsearch:", "soundcloudsearch"
            )
        global_whitelist = set(await config.url_keyword_whitelist())
        global_whitelist = [i.lower() for i in global_whitelist]
        if global_whitelist:
            return any(i in query for i in global_whitelist)
        global_blacklist = set(await config.url_keyword_blacklist())
        global_blacklist = [i.lower() for i in global_blacklist]
        if any(i in query for i in global_blacklist):
            return False
        if guild is not None:
            whitelist_unique: Set[str] = set(await config.guild(guild).url_keyword_whitelist())
            whitelist: List[str] = [i.lower() for i in whitelist_unique]
            if whitelist:
                return any(i in query for i in whitelist)
            blacklist = set(await config.guild(guild).url_keyword_blacklist())
            blacklist = [i.lower() for i in blacklist]
            return not any(i in query for i in blacklist)
        return True
