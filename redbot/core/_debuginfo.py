from __future__ import annotations

import getpass
import os
import platform
import sys
from typing import Optional

import discord
import pip
import psutil

from redbot import __version__
from redbot.core import data_manager
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box


def noop_box(text: str, **kwargs) -> str:
    return text


def _datasize(num: int):
    for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
        if abs(num) < 1024.0:
            return "{0:.1f}{1}".format(num, unit)
        num /= 1024.0
    return "{0:.1f}{1}".format(num, "YB")


class DebugInfoSection:
    def __init__(self, section_name: str, *section_parts: str) -> None:
        self.section_name = section_name
        self.section_parts = section_parts

    def get_command_text(self) -> str:
        parts = [box(f"## {self.section_name}:", lang="md")]
        for part in self.section_parts:
            parts.append(box(part))
        return "".join(parts)

    def get_cli_text(self) -> str:
        parts = [f"\x1b[32m## {self.section_name}:\x1b[0m"]
        for part in self.section_parts:
            parts.append(part)
        return "\n".join(parts)


class DebugInfo:
    def __init__(self, bot: Optional[Red] = None) -> None:
        self.bot = bot

    @property
    def is_logged_in(self) -> bool:
        return self.bot is not None and self.bot.application_id is not None

    @property
    def is_connected(self) -> bool:
        return self.bot is not None and self.bot.is_ready()

    async def get_cli_text(self) -> str:
        parts = ["\x1b[31m# Debug Info for Red:\x1b[0m"]
        for section in (
            self._get_system_metadata_section(),
            self._get_os_variables_section(),
            await self._get_red_vars_section(),
        ):
            parts.append("")
            parts.append(section.get_cli_text())

        return "\n".join(parts)

    async def get_command_text(self) -> str:
        parts = [box("# Debug Info for Red:", lang="md")]
        for section in (
            self._get_system_metadata_section(),
            self._get_os_variables_section(),
            await self._get_red_vars_section(),
        ):
            parts.append("\n")
            parts.append(section.get_command_text())

        return "".join(parts)

    def _get_system_metadata_section(self) -> DebugInfoSection:
        memory_ram = psutil.virtual_memory()
        ram_string = "{used}/{total} ({percent}%)".format(
            used=_datasize(memory_ram.used),
            total=_datasize(memory_ram.total),
            percent=memory_ram.percent,
        )
        return DebugInfoSection(
            "System Metadata",
            f"CPU Cores: {psutil.cpu_count()} ({platform.machine()})\nRAM: {ram_string}",
        )

    def _get_os_variables_section(self) -> DebugInfoSection:
        IS_WINDOWS = os.name == "nt"
        IS_MAC = sys.platform == "darwin"
        IS_LINUX = sys.platform == "linux"

        python_version = ".".join(map(str, sys.version_info[:3]))
        pyver = f"{python_version} ({platform.architecture()[0]})"
        pipver = pip.__version__
        redver = __version__
        dpy_version = discord.__version__
        if IS_WINDOWS:
            os_info = platform.uname()
            osver = f"{os_info.system} {os_info.release} (version {os_info.version})"
        elif IS_MAC:
            os_info = platform.mac_ver()
            osver = f"Mac OSX {os_info[0]} {os_info[2]}"
        elif IS_LINUX:
            import distro

            osver = f"{distro.name()} {distro.version()}".strip()
        else:
            osver = "Could not parse OS, report this on Github."
        user_who_ran = getpass.getuser()

        resp_os = f"OS version: {osver}\nUser: {user_who_ran}\n"  # Ran where off to?!
        resp_py_metadata = (
            f"Python executable: {sys.executable}\n"
            f"Python version: {pyver}\n"
            f"Pip version: {pipver}\n"
        )
        resp_red_metadata = f"Red version: {redver}\nDiscord.py version: {dpy_version}"
        return DebugInfoSection(
            "OS variables",
            resp_os,
            resp_py_metadata,
            resp_red_metadata,
        )

    async def _get_red_vars_section(self) -> DebugInfoSection:
        instance_name = data_manager.instance_name()
        if instance_name is None:
            return DebugInfoSection(
                "Red variables",
                f"Metadata file: {data_manager.config_file}",
            )

        parts = [f"Instance name: {instance_name}"]

        if self.bot is not None:
            # sys.original_argv is available since 3.10 and shows the actual command line arguments
            # rather than a Python-transformed version (i.e. with '-c' or path to `__main__.py`
            # as first element). We could just not show the first argument for consistency
            # but it can be useful.
            cli_args = getattr(sys, "orig_argv", sys.argv).copy()
            # best effort attempt to expunge a token argument
            for idx, arg in enumerate(cli_args):
                if not arg.startswith("--to"):
                    continue
                arg_name, sep, arg_value = arg.partition("=")
                if arg_name not in ("--to", "--tok", "--toke", "--token"):
                    continue
                if sep:
                    cli_args[idx] = f"{arg_name}{sep}[EXPUNGED]"
                elif len(cli_args) > idx + 1:
                    cli_args[idx + 1] = f"[EXPUNGED]"
            parts.append(f"Command line arguments: {cli_args!r}")

            # This formatting is a bit ugly but this is a debug information command
            # and calling repr() on prefix strings ensures that the list isn't ambiguous.
            prefixes = ", ".join(map(repr, await self.bot._config.prefix()))
            parts.append(f"Global prefix(es): {prefixes}")

        if self.is_logged_in:
            owners = []
            for uid in self.bot.owner_ids:
                try:
                    u = await self.bot.get_or_fetch_user(uid)
                    owners.append(f"{u.id} ({u})")
                except discord.HTTPException:
                    owners.append(f"{uid} (Unresolvable)")
            owners_string = ", ".join(owners) or "None"
            parts.append(f"Owner(s): {', '.join(owners) or 'None'}")

        if self.is_connected:
            disabled_intents = (
                ", ".join(
                    intent_name.replace("_", " ").title()
                    for intent_name, enabled in self.bot.intents
                    if not enabled
                )
                or "None"
            )
            parts.append(f"Disabled intents: {disabled_intents}")

        parts.append(f"Storage type: {data_manager.storage_type()}")
        parts.append(f"Data path: {data_manager.basic_config['DATA_PATH']}")
        parts.append(f"Metadata file: {data_manager.config_file}")

        return DebugInfoSection(
            "Red variables",
            "\n".join(parts),
        )
