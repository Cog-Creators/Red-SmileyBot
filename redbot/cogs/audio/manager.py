import asyncio
import asyncio.subprocess  # disables for # https://github.com/PyCQA/pylint/issues/1469
import contextlib
import itertools
import json
import pathlib
import platform
import re
import shlex
import shutil
import tempfile
from typing import ClassVar, Final, List, Optional, Pattern, Tuple, Union, TYPE_CHECKING
from typing_extensions import Self

import aiohttp
import lavalink
import rich.progress
import yaml
from discord.backoff import ExponentialBackoff
from red_commons.logging import getLogger

from redbot.core import data_manager, Config
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import humanize_list

from . import managed_node
from .errors import (
    LavalinkDownloadFailed,
    InvalidArchitectureException,
    ManagedLavalinkAlreadyRunningException,
    ManagedLavalinkPreviouslyShutdownException,
    UnsupportedJavaException,
    ManagedLavalinkStartFailure,
    UnexpectedJavaResponseException,
    EarlyExitException,
    ManagedLavalinkNodeException,
    NoProcessFound,
    NodeUnhealthy,
)
from .managed_node import version_pins
from .managed_node.ll_version import LAVALINK_BUILD_LINE, LavalinkVersion, LavalinkOldVersion
from .utils import (
    get_max_allocation_size,
    replace_p_with_prefix,
)
from ...core.utils import AsyncIter

if TYPE_CHECKING:
    from . import Audio


_ = Translator("Audio", pathlib.Path(__file__))
log = getLogger("red.Audio.manager")

_LL_READY_LOG: Final[bytes] = b"Lavalink is ready to accept connections."
_LL_PLUGIN_LOG: Final[Pattern[bytes]] = re.compile(
    rb"Found plugin '(?P<name>.+)' version (?P<version>\S+)$", re.MULTILINE
)
_FAILED_TO_START: Final[Pattern[bytes]] = re.compile(rb"Web server failed to start\. (.*)")

# Java version regexes
#
# We expect the output to look something like:
#     $ java -version
#     ...
#     ... version "VERSION STRING HERE" ...
#     ...
#
# There are two version formats that we might get here:
#
# - Version scheme pre JEP 223 - used by Java 8 and older
#
# examples:
# 1.8.0
# 1.8.0_275
# 1.8.0_272-b10
# 1.8.0_202-internal-201903130451-b08
# 1.8.0_272-ea-202010231715-b10
# 1.8.0_272-ea-b10
#
# Implementation based on J2SE SDK/JRE Version String Naming Convention document:
# https://www.oracle.com/java/technologies/javase/versioning-naming.html
_RE_JAVA_VERSION_LINE_PRE223: Final[Pattern] = re.compile(
    r'version "1\.(?P<major>[0-8])\.(?P<minor>0)(?:_(?:\d+))?(?:-.*)?"'
)
# - Version scheme introduced by JEP 223 - used by Java 9 and newer
#
# examples:
# 11
# 11.0.9
# 11.0.9.1
# 11.0.9-ea
# 11.0.9-202011050024
#
# Implementation based on JEP 223 document:
# https://openjdk.java.net/jeps/223
_RE_JAVA_VERSION_LINE_223: Final[Pattern] = re.compile(
    r'version "(?P<major>\d+)(?:\.(?P<minor>\d+))?(?:\.\d+)*(\-[a-zA-Z0-9]+)?"'
)

LAVALINK_BRANCH_LINE: Final[Pattern] = re.compile(rb"^Branch\s+(?P<branch>\S+)$", re.MULTILINE)
LAVALINK_JAVA_LINE: Final[Pattern] = re.compile(rb"^JVM:\s+(?P<jvm>\S+)$", re.MULTILINE)
LAVALINK_LAVAPLAYER_LINE: Final[Pattern] = re.compile(
    rb"^Lavaplayer\s+(?P<lavaplayer>\S+)$", re.MULTILINE
)
LAVALINK_BUILD_TIME_LINE: Final[Pattern] = re.compile(
    rb"^Build time:\s+(?P<build_time>\d+[.\d+]*).*$", re.MULTILINE
)


class ServerManager:
    LAVALINK_DOWNLOAD_URL: Final[str] = (
        "https://github.com/Cog-Creators/Lavalink-Jars/releases/download/"
        f"{version_pins.JAR_VERSION}/"
        "Lavalink.jar"
    )

    _java_available: ClassVar[Optional[bool]] = None
    _java_version: ClassVar[Optional[Tuple[int, int]]] = None
    _up_to_date: ClassVar[Optional[bool]] = None
    _blacklisted_archs: List[str] = []

    _lavaplayer: ClassVar[Optional[str]] = None
    _lavalink_version: ClassVar[Optional[Union[LavalinkOldVersion, LavalinkVersion]]] = None
    _jvm: ClassVar[Optional[str]] = None
    _lavalink_branch: ClassVar[Optional[str]] = None
    _buildtime: ClassVar[Optional[str]] = None
    _java_exc: ClassVar[str] = "java"

    def __init__(
        self,
        config: Config,
        cog: "Audio",
        timeout: Optional[int] = None,
        download_timeout: Optional[int] = None,
    ) -> None:
        self.ready: asyncio.Event = asyncio.Event()
        self.downloaded: asyncio.Event = asyncio.Event()
        self._config = config
        self._proc: Optional[asyncio.subprocess.Process] = None  # pylint:disable=no-member
        self._shutdown: bool = False
        self.start_monitor_task = None
        self.timeout = timeout
        self.download_timeout = download_timeout
        self.cog = cog
        self._args = []
        self._pipe_task = None
        self.plugins: dict[str, str] = {}

    @property
    def lavalink_download_dir(self) -> pathlib.Path:
        return data_manager.cog_data_path(raw_name="Audio")

    @property
    def lavalink_jar_file(self) -> pathlib.Path:
        return self.lavalink_download_dir / "Lavalink.jar"

    @property
    def lavalink_app_yml(self) -> pathlib.Path:
        return self.lavalink_download_dir / "application.yml"

    @property
    def path(self) -> Optional[str]:
        return self._java_exc

    @property
    def jvm(self) -> Optional[str]:
        return self._jvm

    @property
    def lavaplayer(self) -> Optional[str]:
        return self._lavaplayer

    @property
    def ll_version(self) -> Optional[Union[LavalinkOldVersion, LavalinkVersion]]:
        return self._lavalink_version

    @property
    def ll_branch(self) -> Optional[str]:
        return self._lavalink_branch

    @property
    def build_time(self) -> Optional[str]:
        return self._buildtime

    async def _pipe_output(self):
        with contextlib.suppress(asyncio.CancelledError):
            async for __ in self._proc.stdout:
                pass

    async def _start(self, java_path: str) -> None:
        arch_name = platform.machine()
        self._java_exc = java_path
        if arch_name in self._blacklisted_archs:
            raise InvalidArchitectureException(
                "You are attempting to run the managed Lavalink node on an unsupported machine architecture."
            )

        if self._proc is not None:
            if self._proc.returncode is None:
                raise ManagedLavalinkAlreadyRunningException(
                    "Managed Lavalink node is already running"
                )
            elif self._shutdown:
                raise ManagedLavalinkPreviouslyShutdownException(
                    "Server manager has already been used - create another one"
                )
        await self.process_settings()
        await self.maybe_download_jar()
        args, msg = await self._get_jar_args()
        if msg is not None:
            log.warning(msg)
        command_string = shlex.join(args)
        log.info("Managed Lavalink node startup command: %s", command_string)
        if "-Xmx" not in command_string and msg is None:
            log.warning(
                await replace_p_with_prefix(
                    self.cog.bot,
                    "Managed Lavalink node maximum allowed RAM not set or higher than available RAM, "
                    "please use '[p]llset heapsize' to set a maximum value to avoid out of RAM crashes.",
                )
            )
        try:
            self._proc = (
                await asyncio.subprocess.create_subprocess_exec(  # pylint:disable=no-member
                    *args,
                    cwd=str(self.lavalink_download_dir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
            )
            log.info("Managed Lavalink node started. PID: %s", self._proc.pid)
            try:
                await asyncio.wait_for(self._wait_for_launcher(), timeout=self.timeout)
            except asyncio.TimeoutError:
                log.warning(
                    "Timeout occurred whilst waiting for managed Lavalink node to be ready"
                )
                raise
        except asyncio.TimeoutError:
            await self._partial_shutdown()
        except Exception:
            await self._partial_shutdown()
            raise

    async def process_settings(self):
        data = managed_node.generate_server_config(await self._config.yaml.all())

        with open(self.lavalink_app_yml, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

    async def _get_jar_args(self) -> Tuple[List[str], Optional[str]]:
        (java_available, java_version) = await self._has_java()

        if not java_available:
            if self._java_version is None:
                extras = ""
            else:
                version = ".".join(map(str, self._java_version))
                extras = f" however you have version {version} (executable: {self._java_exc})"
            supported_versions = humanize_list(
                list(map(str, version_pins.SUPPORTED_JAVA_VERSIONS)),
                locale="en-US",
                style="or-short",
            )
            latest_version = str(version_pins.LATEST_SUPPORTED_JAVA_VERSION)
            older_versions = humanize_list(
                list(map(str, reversed(version_pins.OLDER_SUPPORTED_JAVA_VERSIONS))),
                locale="en-US",
                style="or-short",
            )
            raise UnsupportedJavaException(
                await replace_p_with_prefix(
                    self.cog.bot,
                    f"The managed Lavalink node requires Java {supported_versions} to run{extras};\n"
                    f"Either install version {latest_version} (or {older_versions})"
                    " and restart the bot or connect to an external Lavalink node"
                    " (https://docs.discord.red/en/stable/install_guides/index.html)\n"
                    f"If you already have Java {supported_versions} installed"
                    " then you will need to specify the executable path,"
                    f" use '[p]llset java' to set the correct Java {supported_versions} executable.",
                )  # TODO: Replace with Audio docs when they are out
            )
        java_xms, java_xmx = list((await self._config.java.all()).values())
        match = re.match(r"^(\d+)([MG])$", java_xmx, flags=re.IGNORECASE)
        command_args = [self._java_exc]
        if self._java_version[0] < 12:
            command_args.append("-Djdk.tls.client.protocols=TLSv1.2")
        command_args.append(f"-Xms{java_xms}")
        meta = 0, None
        invalid = None
        if match and (
            (int(match.group(1)) * 1024 ** (2 if match.group(2).lower() == "m" else 3))
            <= (meta := get_max_allocation_size(self._java_exc))[0]
        ):
            command_args.append(f"-Xmx{java_xmx}")
        elif meta[0] is not None:
            invalid = await replace_p_with_prefix(
                self.cog.bot,
                "Managed Lavalink node RAM allocation ignored due to system limitations, "
                "please fix this by setting the correct value with '[p]llset heapsize'.",
            )

        command_args.extend(["-jar", str(self.lavalink_jar_file)])
        self._args = command_args
        return command_args, invalid

    async def _has_java(self) -> Tuple[bool, Optional[Tuple[int, int]]]:
        if self._java_available:
            # Return cached value if we've checked this before
            return self._java_available, self._java_version
        java_exec = shutil.which(self._java_exc)
        java_available = java_exec is not None
        if not java_available:
            self._java_available = False
            self._java_version = None
        else:
            self._java_version = await self._get_java_version()
            self._java_available = self._java_version[0] in version_pins.SUPPORTED_JAVA_VERSIONS
            self._java_exc = java_exec
        return self._java_available, self._java_version

    async def _get_java_version(self) -> Tuple[int, int]:
        """This assumes we've already checked that java exists."""
        _proc: asyncio.subprocess.Process = (
            await asyncio.create_subprocess_exec(  # pylint:disable=no-member
                self._java_exc,
                "-version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        )
        # java -version outputs to stderr
        _, err = await _proc.communicate()

        version_info: str = err.decode("utf-8")
        lines = version_info.splitlines()
        for line in lines:
            match = _RE_JAVA_VERSION_LINE_PRE223.search(line)
            if match is None:
                match = _RE_JAVA_VERSION_LINE_223.search(line)
            if match is None:
                continue
            major = int(match["major"])
            minor = 0
            if minor_str := match["minor"]:
                minor = int(minor_str)

            return major, minor

        raise UnexpectedJavaResponseException(
            f"The output of `{self._java_exc} -version` was unexpected\n{version_info}."
        )

    async def _wait_for_launcher(self) -> None:
        log.info("Waiting for Managed Lavalink node to be ready")
        for i in itertools.cycle(range(50)):
            line = await self._proc.stdout.readline()
            if _LL_READY_LOG in line:
                self.ready.set()
                log.info("Managed Lavalink node is ready to receive requests.")
                self._pipe_task = asyncio.create_task(self._pipe_output())
                break
            if match := _LL_PLUGIN_LOG.search(line):
                self.plugins[match["name"].decode()] = match["version"].decode()
            elif _FAILED_TO_START.search(line):
                raise ManagedLavalinkStartFailure(
                    f"Lavalink failed to start: {line.decode().strip()}"
                )
            if self._proc.returncode is not None:
                # Avoid Console spam only print once every 2 seconds
                raise EarlyExitException("Managed Lavalink node server exited early.")
            if i == 49:
                # Sleep after 50 lines to prevent busylooping
                await asyncio.sleep(0.1)

    async def shutdown(self) -> None:
        if self.start_monitor_task is not None:
            self.start_monitor_task.cancel()
        await self._partial_shutdown()

    async def _partial_shutdown(self) -> None:
        self.ready.clear()
        self.downloaded.clear()
        if self._shutdown is True:
            # For convenience, calling this method more than once or calling it before starting it
            # does nothing.
            return
        if self._pipe_task:
            self._pipe_task.cancel()
        if self._proc is not None:
            self._proc.terminate()
            await self._proc.wait()
        self._proc = None
        self._shutdown = True

    async def _download_jar(self) -> None:
        log.info("Downloading Lavalink.jar...")
        async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
            async with session.get(self.LAVALINK_DOWNLOAD_URL) as response:
                if response.status == 404:
                    # A 404 means our LAVALINK_DOWNLOAD_URL is invalid, so likely the jar version
                    # hasn't been published yet
                    raise LavalinkDownloadFailed(
                        f"Lavalink jar version {version_pins.JAR_VERSION}"
                        " hasn't been published yet",
                        response=response,
                        should_retry=False,
                    )
                elif 400 <= response.status < 600:
                    # Other bad responses should be raised but we should retry just incase
                    raise LavalinkDownloadFailed(response=response, should_retry=True)
                fd, path = tempfile.mkstemp()
                file = open(fd, "wb")
                nbytes = 0
                with rich.progress.Progress(
                    rich.progress.SpinnerColumn(),
                    rich.progress.TextColumn("[progress.description]{task.description}"),
                    rich.progress.BarColumn(),
                    rich.progress.TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    rich.progress.TimeRemainingColumn(),
                    rich.progress.TimeElapsedColumn(),
                ) as progress:
                    progress_task_id = progress.add_task(
                        "[red]Downloading Lavalink.jar", total=response.content_length
                    )
                    try:
                        chunk = await response.content.read(1024)
                        while chunk:
                            chunk_size = file.write(chunk)
                            nbytes += chunk_size
                            progress.update(progress_task_id, advance=chunk_size)
                            chunk = await response.content.read(1024)
                        file.flush()
                    finally:
                        file.close()

                shutil.move(path, str(self.lavalink_jar_file), copy_function=shutil.copyfile)

        log.info("Successfully downloaded Lavalink.jar (%s bytes written)", format(nbytes, ","))
        await self._is_up_to_date()
        self.downloaded.set()

    async def _is_up_to_date(self):
        if self._up_to_date is True:
            # Return cached value if we've checked this before
            return True
        args, _ = await self._get_jar_args()
        args.append("--version")
        _proc = await asyncio.subprocess.create_subprocess_exec(  # pylint:disable=no-member
            *args,
            cwd=str(self.lavalink_download_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout = (await _proc.communicate())[0]
        if (branch := LAVALINK_BRANCH_LINE.search(stdout)) is None:
            # Output is unexpected, suspect corrupted jarfile
            raise ValueError(
                "Could not find 'Branch' line in the `--version` output,"
                " or invalid branch name given."
            )
        if (java := LAVALINK_JAVA_LINE.search(stdout)) is None:
            # Output is unexpected, suspect corrupted jarfile
            raise ValueError(
                "Could not find 'JVM' line in the `--version` output,"
                " or invalid version number given."
            )
        if (lavaplayer := LAVALINK_LAVAPLAYER_LINE.search(stdout)) is None:
            # Output is unexpected, suspect corrupted jarfile
            raise ValueError(
                "Could not find 'Lavaplayer' line in the `--version` output,"
                " or invalid version number given."
            )
        if (buildtime := LAVALINK_BUILD_TIME_LINE.search(stdout)) is None:
            # Output is unexpected, suspect corrupted jarfile
            raise ValueError(
                "Could not find 'Build time' line in the `--version` output,"
                " or invalid build time given."
            )

        self._lavalink_version = (
            LavalinkOldVersion.from_version_output(stdout)
            if LAVALINK_BUILD_LINE.search(stdout) is not None
            else LavalinkVersion.from_version_output(stdout)
        )
        date = buildtime["build_time"].decode()
        date = date.replace(".", "/")
        self._lavalink_branch = branch["branch"].decode()
        self._jvm = java["jvm"].decode()
        self._lavaplayer = lavaplayer["lavaplayer"].decode()
        self._buildtime = date
        self._up_to_date = self._lavalink_version >= version_pins.JAR_VERSION
        return self._up_to_date

    async def maybe_download_jar(self):
        if not self.lavalink_jar_file.exists():
            log.info("Triggering first-time download of Lavalink...")
            await self._download_jar()
            return

        try:
            up_to_date = await self._is_up_to_date()
        except ValueError as exc:
            log.warning("Failed to get Lavalink version: %s\nTriggering update...", exc)
            await self._download_jar()
            return

        if not up_to_date:
            log.info(
                "Lavalink version outdated, triggering update from %s to %s...",
                self._lavalink_version,
                version_pins.JAR_VERSION,
            )
            await self._download_jar()
        else:
            self.downloaded.set()

    async def wait_until_ready(
        self, timeout: Optional[float] = None, download_timeout: Optional[float] = None
    ):
        download_timeout = download_timeout or self.download_timeout
        await asyncio.wait_for(self.downloaded.wait(), timeout=download_timeout)
        await asyncio.wait_for(self.ready.wait(), timeout=timeout or self.timeout)

    async def start_monitor(self, java_path: str):
        retry_count = 0
        backoff = ExponentialBackoff(base=7)
        while True:
            try:
                self._shutdown = False
                if self._proc is None or self._proc.returncode is not None:
                    self.ready.clear()
                    self.downloaded.clear()
                    await self._start(java_path=java_path)
                while True:
                    await self.wait_until_ready(timeout=self.timeout)
                    if self._proc.returncode is not None:
                        raise NoProcessFound
                    try:
                        node = lavalink.get_all_nodes()[0]
                        if node.ready:
                            # Hoping this throws an exception which will then trigger a restart
                            await node._ws.ping()
                            backoff = ExponentialBackoff(
                                base=7
                            )  # Reassign Backoff to reset it on successful ping.
                            # ExponentialBackoff.reset() would be a nice method to have
                            await asyncio.sleep(1)
                        else:
                            await asyncio.sleep(5)
                    except IndexError:
                        # In case lavalink.get_all_nodes() returns 0 Nodes
                        #  (During a connect or multiple connect failures)
                        try:
                            log.debug(
                                "Managed node monitor detected RLL is not connected to any nodes"
                            )
                            await lavalink.wait_until_ready(timeout=60, wait_if_no_node=60)
                        except asyncio.TimeoutError:
                            self.cog.lavalink_restart_connect(manual=True)
                            return  # lavalink_restart_connect will cause a new monitor task to be created.
                    except Exception as exc:
                        log.debug(exc, exc_info=exc)
                        raise NodeUnhealthy(str(exc))
            except NoProcessFound:
                await self._partial_shutdown()
            except asyncio.TimeoutError:
                delay = backoff.delay()
                await self._partial_shutdown()
                log.warning(
                    "Lavalink Managed node health check timeout, restarting in %s seconds",
                    delay,
                )
                await asyncio.sleep(delay)
            except NodeUnhealthy:
                delay = backoff.delay()
                await self._partial_shutdown()
                log.warning(
                    "Lavalink Managed node health check failed, restarting in %s seconds",
                    delay,
                )
                await asyncio.sleep(delay)
            except LavalinkDownloadFailed as exc:
                delay = backoff.delay()
                if exc.should_retry:
                    log.warning(
                        "Lavalink Managed node download failed retrying in %s seconds\n%s",
                        delay,
                        exc.response,
                    )
                    retry_count += 1
                    await self._partial_shutdown()
                    await asyncio.sleep(delay)
                else:
                    log.critical(
                        "Fatal exception whilst starting managed Lavalink node, "
                        "aborting...\n%s",
                        exc.response,
                    )
                    self.cog.lavalink_connection_aborted = True
                    return await self.shutdown()
            except InvalidArchitectureException:
                log.critical("Invalid machine architecture, cannot run a managed Lavalink node.")
                self.cog.lavalink_connection_aborted = True
                return await self.shutdown()
            except (UnsupportedJavaException, UnexpectedJavaResponseException) as exc:
                log.critical(exc)
                self.cog.lavalink_connection_aborted = True
                return await self.shutdown()
            except ManagedLavalinkNodeException as exc:
                delay = backoff.delay()
                log.critical(
                    exc,
                )
                await self._partial_shutdown()
                log.warning(
                    "Lavalink Managed node startup failed retrying in %s seconds",
                    delay,
                )
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                return
            except Exception as exc:
                delay = backoff.delay()
                log.warning(
                    "Lavalink Managed node startup failed retrying in %s seconds",
                    delay,
                )
                log.debug(exc, exc_info=exc)
                await self._partial_shutdown()
                await asyncio.sleep(delay)

    async def start(self, java_path: str):
        if self.start_monitor_task is not None:
            await self.shutdown()
        self.start_monitor_task = asyncio.create_task(self.start_monitor(java_path))
