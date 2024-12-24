import concurrent
import contextlib
import datetime
import random
import time
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Callable, List, MutableMapping, Optional, Tuple, Union

from red_commons.logging import getLogger

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import Cog
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter
from redbot.core.utils.dbtools import APSWConnectionWrapper

from ..sql_statements import (
    LAVALINK_CREATE_INDEX,
    LAVALINK_CREATE_TABLE,
    LAVALINK_DELETE_OLD_ENTRIES,
    LAVALINK_FETCH_ALL_ENTRIES_GLOBAL,
    LAVALINK_QUERY,
    LAVALINK_QUERY_ALL,
    LAVALINK_QUERY_LAST_FETCHED_RANDOM,
    LAVALINK_UPDATE,
    LAVALINK_UPSERT,
    SPOTIFY_CREATE_INDEX,
    SPOTIFY_CREATE_TABLE,
    SPOTIFY_DELETE_OLD_ENTRIES,
    SPOTIFY_QUERY,
    SPOTIFY_QUERY_ALL,
    SPOTIFY_QUERY_LAST_FETCHED_RANDOM,
    SPOTIFY_UPDATE,
    SPOTIFY_UPSERT,
    YOUTUBE_CREATE_INDEX,
    YOUTUBE_CREATE_TABLE,
    YOUTUBE_DELETE_OLD_ENTRIES,
    YOUTUBE_QUERY,
    YOUTUBE_QUERY_ALL,
    YOUTUBE_QUERY_LAST_FETCHED_RANDOM,
    YOUTUBE_UPDATE,
    YOUTUBE_UPSERT,
    PRAGMA_FETCH_user_version,
    PRAGMA_SET_journal_mode,
    PRAGMA_SET_read_uncommitted,
    PRAGMA_SET_temp_store,
    PRAGMA_SET_user_version,
)
from .api_utils import (
    LavalinkCacheFetchForGlobalResult,
    LavalinkCacheFetchResult,
    SpotifyCacheFetchResult,
    YouTubeCacheFetchResult,
)

if TYPE_CHECKING:
    from .. import Audio


log = getLogger("red.cogs.Audio.api.LocalDB")
_ = Translator("Audio", Path(__file__))
_SCHEMA_VERSION = 3


class BaseWrapper:
    def __init__(
        self, bot: Red, config: Config, conn: APSWConnectionWrapper, cog: Union["Audio", Cog]
    ):
        self.bot = bot
        self.config = config
        self.database = conn
        self.statement = SimpleNamespace()
        self.statement.pragma_temp_store = PRAGMA_SET_temp_store
        self.statement.pragma_journal_mode = PRAGMA_SET_journal_mode
        self.statement.pragma_read_uncommitted = PRAGMA_SET_read_uncommitted
        self.statement.set_user_version = PRAGMA_SET_user_version
        self.statement.get_user_version = PRAGMA_FETCH_user_version
        self.fetch_result: Optional[Callable] = None
        self.cog = cog

    async def init(self) -> None:
        """Initialize the local cache"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(self.database.cursor().execute, self.statement.pragma_temp_store)
            executor.submit(self.database.cursor().execute, self.statement.pragma_journal_mode)
            executor.submit(self.database.cursor().execute, self.statement.pragma_read_uncommitted)
            executor.submit(self.maybe_migrate)
            executor.submit(self.database.cursor().execute, LAVALINK_CREATE_TABLE)
            executor.submit(self.database.cursor().execute, LAVALINK_CREATE_INDEX)
            executor.submit(self.database.cursor().execute, YOUTUBE_CREATE_TABLE)
            executor.submit(self.database.cursor().execute, YOUTUBE_CREATE_INDEX)
            executor.submit(self.database.cursor().execute, SPOTIFY_CREATE_TABLE)
            executor.submit(self.database.cursor().execute, SPOTIFY_CREATE_INDEX)
            await self.clean_up_old_entries()

    def close(self) -> None:
        """Close the connection with the local cache"""
        with contextlib.suppress(Exception):
            self.database.close()

    async def clean_up_old_entries(self) -> None:
        """Delete entries older than x in the local cache tables"""
        max_age = await self.config.cache_age()
        maxage = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=max_age)
        maxage_int = int(time.mktime(maxage.timetuple()))
        values = {"maxage": maxage_int}
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(self.database.cursor().execute, LAVALINK_DELETE_OLD_ENTRIES, values)
            executor.submit(self.database.cursor().execute, YOUTUBE_DELETE_OLD_ENTRIES, values)
            executor.submit(self.database.cursor().execute, SPOTIFY_DELETE_OLD_ENTRIES, values)

    def maybe_migrate(self) -> None:
        """Maybe migrate Database schema for the local cache"""
        current_version = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for future in concurrent.futures.as_completed(
                [executor.submit(self.database.cursor().execute, self.statement.get_user_version)]
            ):
                try:
                    row_result = future.result()
                    current_version = row_result.fetchone()
                    break
                except Exception as exc:
                    log.verbose("Failed to completed fetch from database", exc_info=exc)
            if isinstance(current_version, tuple):
                current_version = current_version[0]
            if current_version == _SCHEMA_VERSION:
                return
            executor.submit(
                self.database.cursor().execute,
                self.statement.set_user_version,
                {"version": _SCHEMA_VERSION},
            )

    async def insert(self, values: List[MutableMapping]) -> None:
        """Insert an entry into the local cache"""
        try:
            with self.database.transaction() as transaction:
                transaction.executemany(self.statement.upsert, values)
        except Exception as exc:
            log.trace("Error during table insert", exc_info=exc)

    async def update(self, values: MutableMapping) -> None:
        """Update an entry of the local cache"""

        try:
            time_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
            values["last_fetched"] = time_now
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(self.database.cursor().execute, self.statement.update, values)
        except Exception as exc:
            log.verbose("Error during table update", exc_info=exc)

    async def _fetch_one(
        self, values: MutableMapping
    ) -> Optional[
        Union[LavalinkCacheFetchResult, SpotifyCacheFetchResult, YouTubeCacheFetchResult]
    ]:
        """Get an entry from the local cache"""
        max_age = await self.config.cache_age()
        maxage = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=max_age)
        maxage_int = int(time.mktime(maxage.timetuple()))
        values.update({"maxage": maxage_int})
        row = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for future in concurrent.futures.as_completed(
                [executor.submit(self.database.cursor().execute, self.statement.get_one, values)]
            ):
                try:
                    row_result = future.result()
                    row = row_result.fetchone()
                except Exception as exc:
                    log.verbose("Failed to completed fetch from database", exc_info=exc)
        if not row:
            return None
        if self.fetch_result is None:
            return None
        return self.fetch_result(*row)

    async def _fetch_all(
        self, values: MutableMapping
    ) -> List[Union[LavalinkCacheFetchResult, SpotifyCacheFetchResult, YouTubeCacheFetchResult]]:
        """Get all entries from the local cache"""
        output = []
        row_result = []
        if self.fetch_result is None:
            return []
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for future in concurrent.futures.as_completed(
                [executor.submit(self.database.cursor().execute, self.statement.get_all, values)]
            ):
                try:
                    row_result = future.result()
                except Exception as exc:
                    log.verbose("Failed to completed fetch from database", exc_info=exc)
        async for row in AsyncIter(row_result):
            output.append(self.fetch_result(*row))
        return output

    async def _fetch_random(
        self, values: MutableMapping
    ) -> Optional[
        Union[LavalinkCacheFetchResult, SpotifyCacheFetchResult, YouTubeCacheFetchResult]
    ]:
        """Get a random entry from the local cache"""
        row = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for future in concurrent.futures.as_completed(
                [
                    executor.submit(
                        self.database.cursor().execute, self.statement.get_random, values
                    )
                ]
            ):
                try:
                    row_result = future.result()
                    rows = row_result.fetchall()
                    if rows:
                        row = random.choice(rows)
                    else:
                        row = None
                except Exception as exc:
                    log.verbose("Failed to completed random fetch from database", exc_info=exc)
        if not row:
            return None
        if self.fetch_result is None:
            return None
        return self.fetch_result(*row)


class YouTubeTableWrapper(BaseWrapper):
    def __init__(
        self, bot: Red, config: Config, conn: APSWConnectionWrapper, cog: Union["Audio", Cog]
    ):
        super().__init__(bot, config, conn, cog)
        self.statement.upsert = YOUTUBE_UPSERT
        self.statement.update = YOUTUBE_UPDATE
        self.statement.get_one = YOUTUBE_QUERY
        self.statement.get_all = YOUTUBE_QUERY_ALL
        self.statement.get_random = YOUTUBE_QUERY_LAST_FETCHED_RANDOM
        self.fetch_result = YouTubeCacheFetchResult

    async def fetch_one(
        self, values: MutableMapping
    ) -> Tuple[Optional[str], Optional[datetime.datetime]]:
        """Get an entry from the Youtube table"""
        result = await self._fetch_one(values)
        if not result or not isinstance(result.query, str):
            return None, None
        return result.query, result.updated_on

    async def fetch_all(self, values: MutableMapping) -> List[YouTubeCacheFetchResult]:
        """Get all entries from the Youtube table"""
        result = await self._fetch_all(values)
        if result and isinstance(result[0], YouTubeCacheFetchResult):
            return result
        return []

    async def fetch_random(self, values: MutableMapping) -> Optional[str]:
        """Get a random entry from the Youtube table"""
        result = await self._fetch_random(values)
        if not result or not isinstance(result.query, str):
            return None
        return result.query


class SpotifyTableWrapper(BaseWrapper):
    def __init__(
        self, bot: Red, config: Config, conn: APSWConnectionWrapper, cog: Union["Audio", Cog]
    ):
        super().__init__(bot, config, conn, cog)
        self.statement.upsert = SPOTIFY_UPSERT
        self.statement.update = SPOTIFY_UPDATE
        self.statement.get_one = SPOTIFY_QUERY
        self.statement.get_all = SPOTIFY_QUERY_ALL
        self.statement.get_random = SPOTIFY_QUERY_LAST_FETCHED_RANDOM
        self.fetch_result = SpotifyCacheFetchResult

    async def fetch_one(
        self, values: MutableMapping
    ) -> Tuple[Optional[str], Optional[datetime.datetime]]:
        """Get an entry from the Spotify table"""
        result = await self._fetch_one(values)
        if not result or not isinstance(result.query, str):
            return None, None
        return result.query, result.updated_on

    async def fetch_all(self, values: MutableMapping) -> List[SpotifyCacheFetchResult]:
        """Get all entries from the Spotify table"""
        result = await self._fetch_all(values)
        if result and isinstance(result[0], SpotifyCacheFetchResult):
            return result
        return []

    async def fetch_random(self, values: MutableMapping) -> Optional[str]:
        """Get a random entry from the Spotify table"""
        result = await self._fetch_random(values)
        if not result or not isinstance(result.query, str):
            return None
        return result.query


class LavalinkTableWrapper(BaseWrapper):
    def __init__(
        self, bot: Red, config: Config, conn: APSWConnectionWrapper, cog: Union["Audio", Cog]
    ):
        super().__init__(bot, config, conn, cog)
        self.statement.upsert = LAVALINK_UPSERT
        self.statement.update = LAVALINK_UPDATE
        self.statement.get_one = LAVALINK_QUERY
        self.statement.get_all = LAVALINK_QUERY_ALL
        self.statement.get_random = LAVALINK_QUERY_LAST_FETCHED_RANDOM
        self.statement.get_all_global = LAVALINK_FETCH_ALL_ENTRIES_GLOBAL
        self.fetch_result = LavalinkCacheFetchResult
        self.fetch_for_global: Optional[Callable] = LavalinkCacheFetchForGlobalResult

    async def fetch_one(
        self, values: MutableMapping
    ) -> Tuple[Optional[MutableMapping], Optional[datetime.datetime]]:
        """Get an entry from the Lavalink table"""
        result = await self._fetch_one(values)
        if not result or not isinstance(result.query, dict):
            return None, None
        return result.query, result.updated_on

    async def fetch_all(self, values: MutableMapping) -> List[LavalinkCacheFetchResult]:
        """Get all entries from the Lavalink table"""
        result = await self._fetch_all(values)
        if result and isinstance(result[0], LavalinkCacheFetchResult):
            return result
        return []

    async def fetch_random(self, values: MutableMapping) -> Optional[MutableMapping]:
        """Get a random entry from the Lavalink table"""
        result = await self._fetch_random(values)
        if not result or not isinstance(result.query, dict):
            return None
        return result.query

    async def fetch_all_for_global(self) -> List[LavalinkCacheFetchForGlobalResult]:
        """Get all entries from the Lavalink table"""
        output: List[LavalinkCacheFetchForGlobalResult] = []
        row_result = []
        if self.fetch_for_global is None:
            return []
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for future in concurrent.futures.as_completed(
                [executor.submit(self.database.cursor().execute, self.statement.get_all_global)]
            ):
                try:
                    row_result = future.result()
                except Exception as exc:
                    log.verbose("Failed to completed fetch from database", exc_info=exc)
        async for row in AsyncIter(row_result):
            output.append(self.fetch_for_global(*row))
        return output


class LocalCacheWrapper:
    """Wraps all table apis into 1 object representing the local cache"""

    def __init__(
        self, bot: Red, config: Config, conn: APSWConnectionWrapper, cog: Union["Audio", Cog]
    ):
        self.bot = bot
        self.config = config
        self.database = conn
        self.cog = cog
        self.lavalink: LavalinkTableWrapper = LavalinkTableWrapper(bot, config, conn, self.cog)
        self.spotify: SpotifyTableWrapper = SpotifyTableWrapper(bot, config, conn, self.cog)
        self.youtube: YouTubeTableWrapper = YouTubeTableWrapper(bot, config, conn, self.cog)
