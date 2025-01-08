from pathlib import Path
from typing import Any, Dict, Tuple

from redbot.core import _json

from .info_schemas import REPO_SCHEMA, update_mixin
from .log import log


class RepoJSONMixin:
    INFO_FILE_NAME = "info.json"

    def __init__(self, repo_folder: Path):
        self._repo_folder = repo_folder

        self.author: Tuple[str, ...]
        self.install_msg: str
        self.short: str
        self.description: str

        self._info_file = repo_folder / self.INFO_FILE_NAME
        self._info: Dict[str, Any]

        self._read_info_file()

    def _read_info_file(self) -> None:
        if self._info_file.exists():
            try:
                with self._info_file.open(encoding="utf-8") as f:
                    info = _json.load(f)
            except _json.JSONDecodeError as e:
                log.error(
                    "Invalid JSON information file at path: %s\nError: %s", self._info_file, str(e)
                )
                info = {}
        else:
            info = {}
        if not isinstance(info, dict):
            log.warning(
                "Invalid top-level structure (expected dict, got %s)"
                " in JSON information file at path: %s",
                type(info).__name__,
                self._info_file,
            )
            info = {}
        self._info = info

        update_mixin(self, REPO_SCHEMA)
