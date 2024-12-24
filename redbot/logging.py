import argparse
import logging.handlers
import pathlib
import re
import sys

from typing import List, Tuple, Optional
from logging import LogRecord
from datetime import datetime  # This clearly never leads to confusion...
from os import isatty

import rich
from pygments.styles.monokai import MonokaiStyle  # DEP-WARN
from pygments.token import (
    Comment,
    Error,
    Keyword,
    Name,
    Number,
    Operator,
    String,
    Token,
)
from rich._log_render import LogRender  # DEP-WARN
from rich.console import group
from rich.highlighter import NullHighlighter
from rich.logging import RichHandler
from rich.style import Style
from rich.syntax import ANSISyntaxTheme, PygmentsSyntaxTheme  # DEP-WARN
from rich.text import Text
from rich.theme import Theme
from rich.traceback import PathHighlighter, Traceback  # DEP-WARN


MAX_OLD_LOGS = 8


class RotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Custom rotating file handler.

    This file handler rotates a bit differently to the one in stdlib.

    For a start, this works off of a "stem" and a "directory". The stem
    is the base name of the log file, without the extension. The
    directory is where all log files (including backups) will be placed.

    Secondly, this logger rotates files downwards, and new logs are
    *started* with the backup number incremented. The stdlib handler
    rotates files upwards, and this leaves the logs in reverse order.

    Thirdly, naming conventions are not customisable with this class.
    Logs will initially be named in the format "{stem}.log", and after
    rotating, the first log file will be renamed "{stem}-part1.log",
    and a new file "{stem}-part2.log" will be created for logging to
    continue.

    A few things can't be modified in this handler: it must use append
    mode, it doesn't support use of the `delay` arg, and it will ignore
    custom namers and rotators.

    When this handler is instantiated, it will search through the
    directory for logs from previous runtimes, and will open the file
    with the highest backup number to append to.
    """

    def __init__(
        self,
        stem: str,
        directory: pathlib.Path,
        maxBytes: int = 0,
        backupCount: int = 0,
        encoding: Optional[str] = None,
    ) -> None:
        self.baseStem = stem
        self.directory = directory.resolve()
        # Scan for existing files in directory, append to last part of existing log
        log_part_re = re.compile(rf"{stem}-part(?P<partnum>\d)\.log")
        highest_part = 0
        for path in directory.iterdir():
            match = log_part_re.match(path.name)
            if match and int(match["partnum"]) > highest_part:
                highest_part = int(match["partnum"])
        if highest_part:
            filename = directory / f"{stem}-part{highest_part}.log"
        else:
            filename = directory / f"{stem}.log"
        super().__init__(
            filename,
            mode="a",
            maxBytes=maxBytes,
            backupCount=backupCount,
            encoding=encoding,
            delay=False,
        )

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None
        initial_path = self.directory / f"{self.baseStem}.log"
        if self.backupCount > 0 and initial_path.exists():
            initial_path.replace(self.directory / f"{self.baseStem}-part1.log")

        match = re.match(
            rf"{self.baseStem}(?:-part(?P<part>\d))?\.log", pathlib.Path(self.baseFilename).name
        )
        latest_part_num = int(match.groupdict(default="1").get("part", "1"))
        if self.backupCount < 1:
            # No backups, just delete the existing log and start again
            pathlib.Path(self.baseFilename).unlink()
        elif latest_part_num > self.backupCount:
            # Rotate files down one
            # red-part2.log becomes red-part1.log etc, a new log is added at the end.
            for i in range(1, self.backupCount + 1):
                next_log = self.directory / f"{self.baseStem}-part{i + 1}.log"
                if next_log.exists():
                    prev_log = self.directory / f"{self.baseStem}-part{i}.log"
                    next_log.replace(prev_log)
        else:
            # Simply start a new file
            self.baseFilename = str(
                self.directory / f"{self.baseStem}-part{latest_part_num + 1}.log"
            )

        self.stream = self._open()


SYNTAX_THEME = {
    Token: Style(),
    Comment: Style(color="bright_black"),
    Keyword: Style(color="cyan", bold=True),
    Keyword.Constant: Style(color="bright_magenta"),
    Keyword.Namespace: Style(color="bright_red"),
    Operator: Style(bold=True),
    Operator.Word: Style(color="cyan", bold=True),
    Name.Builtin: Style(bold=True),
    Name.Builtin.Pseudo: Style(color="bright_red"),
    Name.Exception: Style(bold=True),
    Name.Class: Style(color="bright_green"),
    Name.Function: Style(color="bright_green"),
    String: Style(color="yellow"),
    Number: Style(color="cyan"),
    Error: Style(bgcolor="red"),
}


class FixedMonokaiStyle(MonokaiStyle):
    styles = {**MonokaiStyle.styles, Token: "#f8f8f2"}


class RedTraceback(Traceback):
    # DEP-WARN
    @group()
    def _render_stack(self, stack):
        for obj in super()._render_stack.__wrapped__(self, stack):
            if obj != "":
                yield obj


class RedLogRender(LogRender):
    def __call__(
        self,
        console,
        renderables,
        log_time=None,
        time_format=None,
        level="",
        path=None,
        line_no=None,
        link_path=None,
        logger_name=None,
    ):
        output = Text()
        if self.show_time:
            log_time = log_time or console.get_datetime()
            log_time_display = log_time.strftime(time_format or self.time_format)
            if log_time_display == self._last_time:
                output.append(" " * (len(log_time_display) + 1))
            else:
                output.append(f"{log_time_display} ", style="log.time")
                self._last_time = log_time_display
        if self.show_level:
            # The space needs to be added separately so that log level is colored by
            # Rich.
            output.append(level)
            output.append(" ")
        if logger_name:
            output.append(f"[{logger_name}] ", style="bright_black")

        output.append(*renderables)
        if self.show_path and path:
            path_text = Text()
            path_text.append(path, style=f"link file://{link_path}" if link_path else "")
            if line_no:
                path_text.append(f":{line_no}")
            output.append(path_text)
        return output


class RedRichHandler(RichHandler):
    """Adaptation of Rich's RichHandler to manually adjust the path to a logger name"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._log_render = RedLogRender(
            show_time=self._log_render.show_time,
            show_level=self._log_render.show_level,
            show_path=self._log_render.show_path,
            level_width=self._log_render.level_width,
        )

    def get_level_text(self, record: LogRecord) -> Text:
        """Get the level name from the record.

        Args:
            record (LogRecord): LogRecord instance.

        Returns:
            Text: A tuple of the style and level name.
        """
        level_text = super().get_level_text(record)
        level_text.stylize("bold")
        return level_text

    def emit(self, record: LogRecord) -> None:
        """Invoked by logging."""
        path = pathlib.Path(record.pathname).name
        level = self.get_level_text(record)
        message = self.format(record)
        time_format = None if self.formatter is None else self.formatter.datefmt
        log_time = datetime.fromtimestamp(record.created)

        traceback = None
        if self.rich_tracebacks and record.exc_info and record.exc_info != (None, None, None):
            exc_type, exc_value, exc_traceback = record.exc_info
            assert exc_type is not None
            assert exc_value is not None
            traceback = RedTraceback.from_exception(
                exc_type,
                exc_value,
                exc_traceback,
                width=self.tracebacks_width,
                extra_lines=self.tracebacks_extra_lines,
                theme=self.tracebacks_theme,
                word_wrap=self.tracebacks_word_wrap,
                show_locals=self.tracebacks_show_locals,
                locals_max_length=self.locals_max_length,
                locals_max_string=self.locals_max_string,
                indent_guides=False,
            )
            message = record.getMessage()

        use_markup = getattr(record, "markup") if hasattr(record, "markup") else self.markup
        if use_markup:
            message_text = Text.from_markup(message)
        else:
            message_text = Text(message)

        if self.highlighter:
            message_text = self.highlighter(message_text)
        if self.KEYWORDS:
            message_text.highlight_words(self.KEYWORDS, "logging.keyword")

        self.console.print(
            self._log_render(
                self.console,
                [message_text],
                log_time=log_time,
                time_format=time_format,
                level=level,
                path=path,
                line_no=record.lineno,
                link_path=record.pathname if self.enable_link_path else None,
                logger_name=record.name,
            ),
            soft_wrap=True,
        )
        if traceback:
            self.console.print(traceback)


def init_logging(level: int, location: pathlib.Path, cli_flags: argparse.Namespace) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    # DEBUG logging for discord.py is a bit too ridiculous :)
    dpy_logger = logging.getLogger("discord")
    dpy_logger.setLevel(logging.INFO)

    rich_console = rich.get_console()
    rich.reconfigure(tab_size=4)
    rich_console.push_theme(
        Theme(
            {
                "log.time": Style(dim=True),
                "logging.level.warning": Style(color="yellow"),
                "logging.level.critical": Style(color="white", bgcolor="red"),
                "logging.level.verbose": Style(color="magenta", italic=True, dim=True),
                "logging.level.trace": Style(color="white", italic=True, dim=True),
                "repr.number": Style(color="cyan"),
                "repr.url": Style(underline=True, italic=True, bold=False, color="cyan"),
            }
        )
    )
    rich_console.file = sys.stdout
    # This is terrible solution, but it's the best we can do if we want the paths in tracebacks
    # to be visible. Rich uses `pygments.string` style  which is fine, but it also uses
    # this highlighter which dims most of the path and therefore makes it unreadable on Mac.
    PathHighlighter.highlights = []

    enable_rich_logging = False

    if isatty(0) and cli_flags.rich_logging is None:
        # Check if the bot thinks it has a active terminal.
        enable_rich_logging = True
    elif cli_flags.rich_logging is True:
        enable_rich_logging = True

    file_formatter = logging.Formatter(
        "[{asctime}] [{levelname}] {name}: {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{"
    )
    if enable_rich_logging is True:
        rich_formatter = logging.Formatter("{message}", datefmt="[%X]", style="{")

        stdout_handler = RedRichHandler(
            rich_tracebacks=True,
            show_path=False,
            highlighter=NullHighlighter(),
            tracebacks_extra_lines=cli_flags.rich_traceback_extra_lines,
            tracebacks_show_locals=cli_flags.rich_traceback_show_locals,
            tracebacks_theme=(
                PygmentsSyntaxTheme(FixedMonokaiStyle)
                if rich_console.color_system == "truecolor"
                else ANSISyntaxTheme(SYNTAX_THEME)
            ),
        )
        stdout_handler.setFormatter(rich_formatter)
    else:
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(file_formatter)

    root_logger.addHandler(stdout_handler)
    logging.captureWarnings(True)

    if not location.exists():
        location.mkdir(parents=True, exist_ok=True)
    # Rotate latest logs to previous logs
    previous_logs: List[pathlib.Path] = []
    latest_logs: List[Tuple[pathlib.Path, str]] = []
    for path in location.iterdir():
        match = re.match(r"latest(?P<part>-part\d+)?\.log", path.name)
        if match:
            part = match.groupdict(default="")["part"]
            latest_logs.append((path, part))
        match = re.match(r"previous(?:-part\d+)?.log", path.name)
        if match:
            previous_logs.append(path)
    # Delete all previous.log files
    for path in previous_logs:
        path.unlink()
    # Rename latest.log files to previous.log
    for path, part in latest_logs:
        path.replace(location / f"previous{part}.log")

    latest_fhandler = RotatingFileHandler(
        stem="latest",
        directory=location,
        maxBytes=1_000_000,  # About 1MB per logfile
        backupCount=MAX_OLD_LOGS,
        encoding="utf-8",
    )
    all_fhandler = RotatingFileHandler(
        stem="red",
        directory=location,
        maxBytes=1_000_000,
        backupCount=MAX_OLD_LOGS,
        encoding="utf-8",
    )

    for fhandler in (latest_fhandler, all_fhandler):
        fhandler.setFormatter(file_formatter)
        root_logger.addHandler(fhandler)
