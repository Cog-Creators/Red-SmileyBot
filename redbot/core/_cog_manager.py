import contextlib
import keyword
import pkgutil
import sys
import textwrap
from importlib import import_module, invalidate_caches
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Union, List, Optional

import redbot.cogs
from redbot.core.commands import positive_int
from redbot.core.utils import deduplicate_iterables
from redbot.core.utils.views import ConfirmView
import discord

from . import commands
from .config import Config
from .i18n import Translator, cog_i18n
from .data_manager import cog_data_path, data_path

from .utils.chat_formatting import box, pagify, humanize_list, inline

__all__ = ("CogManager", "CogManagerUI")


class NoSuchCog(ImportError):
    """Thrown when a cog is missing.

    Different from ImportError because some ImportErrors can happen inside cogs.
    """


class CogManager:
    """Directory manager for Red's cogs.

    This module allows you to load cogs from multiple directories and even from
    outside the bot directory. You may also set a directory for downloader to
    install new cogs to, the default being the :code:`cogs/` folder in the root
    bot directory.
    """

    CORE_PATH = Path(redbot.cogs.__path__[0]).resolve()

    def __init__(self):
        self.config = Config.get_conf(self, 2938473984732, True)
        tmp_cog_install_path = cog_data_path(self) / "cogs"
        tmp_cog_install_path.mkdir(parents=True, exist_ok=True)
        self.config.register_global(paths=[], install_path=str(tmp_cog_install_path))

    async def paths(self) -> List[Path]:
        """Get all currently valid path directories, in order of priority

        Returns
        -------
        List[pathlib.Path]
            A list of paths where cog packages can be found. The
            install path is highest priority, followed by the
            user-defined paths, and the core path has the lowest
            priority.

        """
        return deduplicate_iterables(
            [await self.install_path()], await self.user_defined_paths(), [self.CORE_PATH]
        )

    async def install_path(self) -> Path:
        """Get the install path for 3rd party cogs.

        Returns
        -------
        pathlib.Path
            The path to the directory where 3rd party cogs are stored.

        """
        return Path(await self.config.install_path()).resolve()

    async def user_defined_paths(self) -> List[Path]:
        """Get a list of user-defined cog paths.

        All paths will be absolute and unique, in order of priority.

        Returns
        -------
        List[pathlib.Path]
            A list of user-defined paths.

        """
        return list(map(Path, deduplicate_iterables(await self.config.paths())))

    async def set_install_path(self, path: Path) -> Path:
        """Set the install path for 3rd party cogs.

        Note
        ----
        The bot will not remember your old cog install path which means
        that **all previously installed cogs** will no longer be found.

        Parameters
        ----------
        path : pathlib.Path
            The new directory for cog installs.

        Returns
        -------
        pathlib.Path
            Absolute path to the new install directory.

        Raises
        ------
        ValueError
            If :code:`path` is not an existing directory.

        """
        if not path.is_dir():
            raise ValueError("The install path must be an existing directory.")
        resolved = path.resolve()
        await self.config.install_path.set(str(resolved))
        return resolved

    @staticmethod
    def _ensure_path_obj(path: Union[Path, str]) -> Path:
        """Guarantee an object will be a path object.

        Parameters
        ----------
        path : `pathlib.Path` or `str`

        Returns
        -------
        pathlib.Path

        """
        return Path(path)

    async def add_path(self, path: Union[Path, str]) -> None:
        """Add a cog path to current list.

        This will ignore duplicates.

        Parameters
        ----------
        path : `pathlib.Path` or `str`
            Path to add.

        Raises
        ------
        ValueError
            If :code:`path` does not resolve to an existing directory.

        """
        path = self._ensure_path_obj(path)

        # This makes the path absolute, will break if a bot install
        # changes OS/Computer?
        path = path.resolve()

        if not path.is_dir():
            raise ValueError("'{}' is not a valid directory.".format(path))

        if path == await self.install_path():
            raise ValueError("Cannot add the install path as an additional path.")
        if path == self.CORE_PATH:
            raise ValueError("Cannot add the core path as an additional path.")

        current_paths = await self.user_defined_paths()
        if path not in current_paths:
            current_paths.append(path)
            await self.set_paths(current_paths)

    async def remove_path(self, path: Union[Path, str]) -> None:
        """Remove a path from the current paths list.

        Parameters
        ----------
        path : `pathlib.Path` or `str`
            Path to remove.

        """
        path = self._ensure_path_obj(path)
        paths = await self.user_defined_paths()

        paths.remove(path)
        await self.set_paths(paths)

    async def set_paths(self, paths_: List[Path]):
        """Set the current paths list.

        Parameters
        ----------
        paths_ : `list` of `pathlib.Path`
            List of paths to set.

        """
        str_paths = list(map(str, paths_))
        await self.config.paths.set(str_paths)

    async def _find_ext_cog(self, name: str) -> ModuleSpec:
        """
        Attempts to find a spec for a third party installed cog.

        Parameters
        ----------
        name : str
            Name of the cog package to look for.

        Returns
        -------
        importlib.machinery.ModuleSpec
            Module spec to be used for cog loading.

        Raises
        ------
        NoSuchCog
            When no cog with the requested name was found.

        """
        if not name.isidentifier() or keyword.iskeyword(name):
            # reject package names that can't be valid python identifiers
            raise NoSuchCog(
                f"No 3rd party module by the name of '{name}' was found in any available path.",
                name=name,
            )

        real_paths = list(map(str, [await self.install_path()] + await self.user_defined_paths()))

        for finder, module_name, _ in pkgutil.iter_modules(real_paths):
            if name == module_name:
                spec = finder.find_spec(name)
                if spec:
                    return spec

        raise NoSuchCog(
            f"No 3rd party module by the name of '{name}' was found in any available path.",
            name=name,
        )

    @staticmethod
    async def _find_core_cog(name: str) -> ModuleSpec:
        """
        Attempts to find a spec for a core cog.

        Parameters
        ----------
        name : str

        Returns
        -------
        importlib.machinery.ModuleSpec

        Raises
        ------
        RuntimeError
            When no matching spec can be found.
        """
        real_name = ".{}".format(name)
        package = "redbot.cogs"

        try:
            mod = import_module(real_name, package=package)
            if mod.__spec__.name == "redbot.cogs.locales":
                raise NoSuchCog(
                    "No core cog by the name of '{}' could be found.".format(name),
                    path=mod.__spec__.origin,
                    name=name,
                )
        except ImportError as e:
            if e.name == package + real_name:
                raise NoSuchCog(
                    "No core cog by the name of '{}' could be found.".format(name),
                    path=e.path,
                    name=e.name,
                ) from e

            raise

        return mod.__spec__

    # noinspection PyUnreachableCode
    async def find_cog(self, name: str) -> Optional[ModuleSpec]:
        """Find a cog in the list of available paths.

        Parameters
        ----------
        name : str
            Name of the cog to find.

        Returns
        -------
        Optional[importlib.machinery.ModuleSpec]
            A module spec to be used for specialized cog loading, if found.

        """
        with contextlib.suppress(NoSuchCog):
            return await self._find_ext_cog(name)

        with contextlib.suppress(NoSuchCog):
            return await self._find_core_cog(name)

    async def available_modules(self) -> List[str]:
        """Finds the names of all available modules to load."""
        paths = list(map(str, await self.paths()))

        ret = []
        for finder, module_name, _ in pkgutil.iter_modules(paths):
            # reject package names that can't be valid python identifiers
            if module_name.isidentifier() and not keyword.iskeyword(module_name):
                ret.append(module_name)
        return ret

    @staticmethod
    def invalidate_caches():
        """Re-evaluate modules in the py cache.

        This is an alias for an importlib internal and should be called
        any time that a new module has been installed to a cog directory.
        """
        invalidate_caches()


_ = Translator("CogManagerUI", __file__)


@cog_i18n(_)
class CogManagerUI(commands.Cog):
    """Commands to interface with Red's cog manager."""

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete (Core Config is handled in a bot method )"""
        return

    @commands.command()
    @commands.is_owner()
    async def paths(self, ctx: commands.Context):
        """
        Lists current cog paths in order of priority.
        """
        cog_mgr = ctx.bot._cog_mgr
        install_path = await cog_mgr.install_path()
        core_path = cog_mgr.CORE_PATH
        cog_paths = await cog_mgr.user_defined_paths()

        msg = _("Install Path: {install_path}\nCore Path: {core_path}\n\n").format(
            install_path=install_path, core_path=core_path
        )

        partial = []
        for i, p in enumerate(cog_paths, start=1):
            partial.append("{}. {}".format(i, p))

        msg += "\n".join(partial)
        await ctx.send(box(msg))

    @commands.command()
    @commands.is_owner()
    async def addpath(self, ctx: commands.Context, *, path: Path):
        """
        Add a path to the list of available cog paths.
        """
        if not path.is_dir():
            await ctx.send(_("That path does not exist or does not point to a valid directory."))
            return

        path = path.resolve()

        # Path.is_relative_to() is 3.9+
        bot_data_path = data_path()
        if path == bot_data_path or bot_data_path in path.parents:
            await ctx.send(
                _("A cog path cannot be part of bot's data path ({bot_data_path}).").format(
                    bot_data_path=inline(str(bot_data_path))
                )
            )
            return

        # Path.is_relative_to() is 3.9+
        core_path = ctx.bot._cog_mgr.CORE_PATH
        if path == core_path or core_path in path.parents:
            await ctx.send(
                _("A cog path cannot be part of bot's core path ({core_path}).").format(
                    core_path=inline(str(core_path))
                )
            )
            return

        if (path / "__init__.py").is_file():
            view = ConfirmView(ctx.author)
            # Technically, we only know the path is a package,
            # not that it's a cog package specifically.
            # However, this is more likely to cause the user to rethink their choice.
            if sys.platform == "win32":
                example_cog_path = "D:\\red-cogs"
                example_dir_structure = textwrap.dedent(
                    """\
                    - D:\\
                    -- red-env
                    -- red-data
                    -- red-cogs
                    ---- mycog
                    ------ __init__.py
                    ------ mycog.py
                    ---- coolcog
                    ------ __init__.py
                    ------ coolcog.py"""
                )
            else:
                example_cog_path = "/home/user/red-cogs"
                example_dir_structure = textwrap.dedent(
                    """\
                    - /home/user/
                    -- red-env
                    -- red-data
                    -- red-cogs
                    ---- mycog
                    ------ __init__.py
                    ------ mycog.py
                    ---- coolcog
                    ------ __init__.py
                    ------ coolcog.py"""
                )
            content = (
                _(
                    "The provided path appears to be a cog package,"
                    " are you sure that this is the path that you want to add as a **cog path**?\n"
                    "\nFor example, in the following case,"
                    " you should be adding the {path} as a **cog path**:\n"
                ).format(path=inline(example_cog_path))
                + box(example_dir_structure)
                + _("\nPlease consult the Cog Manager UI documentation, if you're unsure: ")
                + "https://docs.discord.red/en/stable/cog_guides/cog_manager_ui.html"
            )
            view.message = await ctx.send(content, view=view)
            await view.wait()
            if not view.result:
                await ctx.send(_("Okay, the path will not be added."))
                return
            await view.message.delete()

        try:
            await ctx.bot._cog_mgr.add_path(path)
        except ValueError as e:
            await ctx.send(str(e))
        else:
            await ctx.send(_("Path successfully added."))

    @commands.command(require_var_positional=True)
    @commands.is_owner()
    async def removepath(self, ctx: commands.Context, *path_numbers: positive_int):
        """
        Removes one or more paths from the available cog paths given the `path_numbers` from `[p]paths`.
        """
        valid: List[Path] = []
        invalid: List[int] = []

        cog_paths = await ctx.bot._cog_mgr.user_defined_paths()
        # dict.fromkeys removes duplicates while preserving the order
        for path_number in dict.fromkeys(sorted(path_numbers)):
            idx = path_number - 1
            try:
                to_remove = cog_paths[idx]
            except IndexError:
                invalid.append(path_number)
            else:
                await ctx.bot._cog_mgr.remove_path(to_remove)
                valid.append(to_remove)

        parts = []
        if valid:
            parts.append(
                _("The following paths were removed: {paths}").format(
                    paths=humanize_list([inline(str(path)) for path in valid])
                )
            )
        if invalid:
            parts.append(
                _("The following path numbers did not exist: {path_numbers}").format(
                    path_numbers=humanize_list([inline(str(path)) for path in invalid])
                )
            )

        for page in pagify("\n\n".join(parts), ["\n", " "]):
            await ctx.send(page)

    @commands.command(usage="<from> <to>")
    @commands.is_owner()
    async def reorderpath(self, ctx: commands.Context, from_: positive_int, to: positive_int):
        """
        Reorders paths internally to allow discovery of different cogs.
        """
        # Doing this because in the paths command they're 1 indexed
        from_ -= 1
        to -= 1

        all_paths = await ctx.bot._cog_mgr.user_defined_paths()
        try:
            to_move = all_paths.pop(from_)
        except IndexError:
            await ctx.send(_("Invalid 'from' index."))
            return

        try:
            all_paths.insert(to, to_move)
        except IndexError:
            await ctx.send(_("Invalid 'to' index."))
            return

        await ctx.bot._cog_mgr.set_paths(all_paths)
        await ctx.send(_("Paths reordered."))

    @commands.command()
    @commands.is_owner()
    async def installpath(self, ctx: commands.Context, path: Path = None):
        """
        Returns the current install path or sets it if one is provided.

        The provided path must be absolute or relative to the bot's
        directory and it must already exist.

        No installed cogs will be transferred in the process.
        """
        if path:
            if not path.is_absolute():
                path = (ctx.bot._main_dir / path).resolve()
            try:
                await ctx.bot._cog_mgr.set_install_path(path)
            except ValueError:
                await ctx.send(_("That path does not exist."))
                return

        install_path = await ctx.bot._cog_mgr.install_path()
        await ctx.send(
            _("The bot will install new cogs to the `{}` directory.").format(install_path)
        )

    @commands.command()
    @commands.is_owner()
    async def cogs(self, ctx: commands.Context):
        """
        Lists all loaded and available cogs.
        """
        loaded = set(ctx.bot.extensions.keys())

        all_cogs = set(await ctx.bot._cog_mgr.available_modules())

        unloaded = all_cogs - loaded

        loaded = sorted(list(loaded), key=str.lower)
        unloaded = sorted(list(unloaded), key=str.lower)

        if await ctx.embed_requested():
            loaded = _("**{} loaded:**\n").format(len(loaded)) + ", ".join(loaded)
            unloaded = _("**{} unloaded:**\n").format(len(unloaded)) + ", ".join(unloaded)

            for page in pagify(loaded, delims=[", ", "\n"], page_length=1800):
                if page.startswith(", "):
                    page = page[2:]
                e = discord.Embed(description=page, colour=discord.Colour.dark_green())
                await ctx.send(embed=e)

            for page in pagify(unloaded, delims=[", ", "\n"], page_length=1800):
                if page.startswith(", "):
                    page = page[2:]
                e = discord.Embed(description=page, colour=discord.Colour.dark_red())
                await ctx.send(embed=e)
        else:
            loaded_count = _("**{} loaded:**\n").format(len(loaded))
            loaded = ", ".join(loaded)
            unloaded_count = _("**{} unloaded:**\n").format(len(unloaded))
            unloaded = ", ".join(unloaded)
            loaded_count_sent = False
            unloaded_count_sent = False
            for page in pagify(loaded, delims=[", ", "\n"], page_length=1800):
                if page.startswith(", "):
                    page = page[2:]
                if not loaded_count_sent:
                    await ctx.send(loaded_count + box(page, lang="css"))
                    loaded_count_sent = True
                else:
                    await ctx.send(box(page, lang="css"))

            for page in pagify(unloaded, delims=[", ", "\n"], page_length=1800):
                if page.startswith(", "):
                    page = page[2:]
                if not unloaded_count_sent:
                    await ctx.send(unloaded_count + box(page, lang="ldif"))
                    unloaded_count_sent = True
                else:
                    await ctx.send(box(page, lang="ldif"))
