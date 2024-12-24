import concurrent
import json
from pathlib import Path

from types import SimpleNamespace
from typing import List, MutableMapping, Optional

from red_commons.logging import getLogger

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter
from redbot.core.utils.dbtools import APSWConnectionWrapper

from ..sql_statements import (
    HANDLE_DISCORD_DATA_DELETION_QUERY,
    PLAYLIST_CREATE_INDEX,
    PLAYLIST_CREATE_TABLE,
    PLAYLIST_DELETE,
    PLAYLIST_DELETE_SCHEDULED,
    PLAYLIST_DELETE_SCOPE,
    PLAYLIST_FETCH,
    PLAYLIST_FETCH_ALL,
    PLAYLIST_FETCH_ALL_CONVERTER,
    PLAYLIST_FETCH_ALL_WITH_FILTER,
    PLAYLIST_UPSERT,
    PRAGMA_FETCH_user_version,
    PRAGMA_SET_journal_mode,
    PRAGMA_SET_read_uncommitted,
    PRAGMA_SET_temp_store,
    PRAGMA_SET_user_version,
)
from ..utils import PlaylistScope
from .api_utils import PlaylistFetchResult

log = getLogger("red.cogs.Audio.api.Playlists")
_ = Translator("Audio", Path(__file__))


class PlaylistWrapper:
    def __init__(self, bot: Red, config: Config, conn: APSWConnectionWrapper):
        self.bot = bot
        self.database = conn
        self.config = config
        self.statement = SimpleNamespace()
        self.statement.pragma_temp_store = PRAGMA_SET_temp_store
        self.statement.pragma_journal_mode = PRAGMA_SET_journal_mode
        self.statement.pragma_read_uncommitted = PRAGMA_SET_read_uncommitted
        self.statement.set_user_version = PRAGMA_SET_user_version
        self.statement.get_user_version = PRAGMA_FETCH_user_version
        self.statement.create_table = PLAYLIST_CREATE_TABLE
        self.statement.create_index = PLAYLIST_CREATE_INDEX

        self.statement.upsert = PLAYLIST_UPSERT
        self.statement.delete = PLAYLIST_DELETE
        self.statement.delete_scope = PLAYLIST_DELETE_SCOPE
        self.statement.delete_scheduled = PLAYLIST_DELETE_SCHEDULED

        self.statement.get_one = PLAYLIST_FETCH
        self.statement.get_all = PLAYLIST_FETCH_ALL
        self.statement.get_all_with_filter = PLAYLIST_FETCH_ALL_WITH_FILTER
        self.statement.get_all_converter = PLAYLIST_FETCH_ALL_CONVERTER

        self.statement.drop_user_playlists = HANDLE_DISCORD_DATA_DELETION_QUERY

    async def init(self) -> None:
        """Initialize the Playlist table."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(self.database.cursor().execute, self.statement.pragma_temp_store)
            executor.submit(self.database.cursor().execute, self.statement.pragma_journal_mode)
            executor.submit(self.database.cursor().execute, self.statement.pragma_read_uncommitted)
            executor.submit(self.database.cursor().execute, self.statement.create_table)
            executor.submit(self.database.cursor().execute, self.statement.create_index)

    @staticmethod
    def get_scope_type(scope: str) -> int:
        """Convert a scope to a numerical identifier."""
        if scope == PlaylistScope.GLOBAL.value:
            table = 1
        elif scope == PlaylistScope.USER.value:
            table = 3
        else:
            table = 2
        return table

    async def fetch(
        self, scope: str, playlist_id: int, scope_id: int
    ) -> Optional[PlaylistFetchResult]:
        """Fetch a single playlist."""
        scope_type = self.get_scope_type(scope)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for future in concurrent.futures.as_completed(
                [
                    executor.submit(
                        self.database.cursor().execute,
                        self.statement.get_one,
                        (
                            {
                                "playlist_id": playlist_id,
                                "scope_id": scope_id,
                                "scope_type": scope_type,
                            }
                        ),
                    )
                ]
            ):
                try:
                    row_result = future.result()
                except Exception as exc:
                    log.verbose("Failed to complete playlist fetch from database", exc_info=exc)
                    return None
            row = row_result.fetchone()
            if row:
                row = PlaylistFetchResult(*row)
        return row

    async def fetch_all(
        self, scope: str, scope_id: int, author_id=None
    ) -> List[PlaylistFetchResult]:
        """Fetch all playlists."""
        scope_type = self.get_scope_type(scope)
        output = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            if author_id is not None:
                for future in concurrent.futures.as_completed(
                    [
                        executor.submit(
                            self.database.cursor().execute,
                            self.statement.get_all_with_filter,
                            (
                                {
                                    "scope_type": scope_type,
                                    "scope_id": scope_id,
                                    "author_id": author_id,
                                }
                            ),
                        )
                    ]
                ):
                    try:
                        row_result = future.result()
                    except Exception as exc:
                        log.verbose(
                            "Failed to complete playlist fetch from database", exc_info=exc
                        )
                        return []
            else:
                for future in concurrent.futures.as_completed(
                    [
                        executor.submit(
                            self.database.cursor().execute,
                            self.statement.get_all,
                            ({"scope_type": scope_type, "scope_id": scope_id}),
                        )
                    ]
                ):
                    try:
                        row_result = future.result()
                    except Exception as exc:
                        log.verbose(
                            "Failed to complete playlist fetch from database", exc_info=exc
                        )
                        return []
        async for row in AsyncIter(row_result):
            output.append(PlaylistFetchResult(*row))
        return output

    async def fetch_all_converter(
        self, scope: str, playlist_name, playlist_id
    ) -> List[PlaylistFetchResult]:
        """Fetch all playlists with the specified filter."""
        scope_type = self.get_scope_type(scope)
        try:
            playlist_id = int(playlist_id)
        except Exception as exc:
            log.trace("Failed converting playlist_id to int", exc_info=exc)
            playlist_id = -1

        output = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for future in concurrent.futures.as_completed(
                [
                    executor.submit(
                        self.database.cursor().execute,
                        self.statement.get_all_converter,
                        (
                            {
                                "scope_type": scope_type,
                                "playlist_name": playlist_name,
                                "playlist_id": playlist_id,
                            }
                        ),
                    )
                ]
            ):
                try:
                    row_result = future.result()
                except Exception as exc:
                    log.verbose("Failed to complete fetch from database", exc_info=exc)
                    return []

            async for row in AsyncIter(row_result):
                output.append(PlaylistFetchResult(*row))
        return output

    async def delete(self, scope: str, playlist_id: int, scope_id: int):
        """Deletes a single playlists."""
        scope_type = self.get_scope_type(scope)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(
                self.database.cursor().execute,
                self.statement.delete,
                ({"playlist_id": playlist_id, "scope_id": scope_id, "scope_type": scope_type}),
            )

    async def delete_scheduled(self):
        """Clean up database from all deleted playlists."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(self.database.cursor().execute, self.statement.delete_scheduled)

    async def drop(self, scope: str):
        """Delete all playlists in a scope."""
        scope_type = self.get_scope_type(scope)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(
                self.database.cursor().execute,
                self.statement.delete_scope,
                ({"scope_type": scope_type}),
            )

    async def create_table(self):
        """Create the playlist table."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(self.database.cursor().execute, PLAYLIST_CREATE_TABLE)

    async def upsert(
        self,
        scope: str,
        playlist_id: int,
        playlist_name: str,
        scope_id: int,
        author_id: int,
        playlist_url: Optional[str],
        tracks: List[MutableMapping],
    ):
        """Insert or update a playlist into the database."""
        scope_type = self.get_scope_type(scope)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(
                self.database.cursor().execute,
                self.statement.upsert,
                {
                    "scope_type": str(scope_type),
                    "playlist_id": int(playlist_id),
                    "playlist_name": str(playlist_name),
                    "scope_id": int(scope_id),
                    "author_id": int(author_id),
                    "playlist_url": playlist_url,
                    "tracks": json.dumps(tracks),
                },
            )

    async def handle_playlist_user_id_deletion(self, user_id: int):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(
                self.database.cursor().execute,
                self.statement.drop_user_playlists,
                {"user_id": user_id},
            )
