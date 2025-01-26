import asyncio
import contextlib
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Tuple, Union, Iterable, Collection, Optional, Dict, Set, List, cast
from collections import defaultdict

import discord
from redbot.core import commands, Config, version_info as red_version_info
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils import can_user_react_in
from redbot.core.utils.chat_formatting import box, pagify, humanize_list, inline
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate

from . import errors
from .checks import do_install_agreement
from .converters import InstalledCog
from .installable import InstallableType, Installable, InstalledModule
from .log import log
from .repo_manager import RepoManager, Repo

_ = Translator("Downloader", __file__)


DEPRECATION_NOTICE = _(
    "\n**WARNING:** The following repos are using shared libraries"
    " which are marked for removal in the future: {repo_list}.\n"
    " You should inform maintainers of these repos about this message."
)


@cog_i18n(_)
class Downloader(commands.Cog):
    """Install community cogs made by Cog Creators.

    Community cogs, also called third party cogs, are not included
    in the default Red install.

    Community cogs come in repositories. Repos are a group of cogs
    you can install. You always need to add the creator's repository
    using the `[p]repo` command before you can install one or more
    cogs from the creator.
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot

        self.config = Config.get_conf(self, identifier=998240343, force_registration=True)

        self.config.register_global(schema_version=0, installed_cogs={}, installed_libraries={})

        self.already_agreed = False

        self.LIB_PATH = cog_data_path(self) / "lib"
        self.SHAREDLIB_PATH = self.LIB_PATH / "cog_shared"
        self.SHAREDLIB_INIT = self.SHAREDLIB_PATH / "__init__.py"

        self._create_lib_folder()

        self._repo_manager = RepoManager()
        self._ready = asyncio.Event()
        self._init_task = None
        self._ready_raised = False

    def _create_lib_folder(self, *, remove_first: bool = False) -> None:
        if remove_first:
            shutil.rmtree(str(self.LIB_PATH))
        self.SHAREDLIB_PATH.mkdir(parents=True, exist_ok=True)
        if not self.SHAREDLIB_INIT.exists():
            with self.SHAREDLIB_INIT.open(mode="w", encoding="utf-8") as _:
                pass

    async def cog_before_invoke(self, ctx: commands.Context) -> None:
        if not self._ready.is_set():
            async with ctx.typing():
                await self._ready.wait()
        if self._ready_raised:
            await ctx.send(
                "There was an error during Downloader's initialization."
                " Check logs for more information."
            )
            raise commands.CheckFailure()

    def cog_unload(self):
        if self._init_task is not None:
            self._init_task.cancel()

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    def create_init_task(self):
        def _done_callback(task: asyncio.Task) -> None:
            try:
                exc = task.exception()
            except asyncio.CancelledError:
                pass
            else:
                if exc is None:
                    return
                log.error(
                    "An unexpected error occurred during Downloader's initialization.",
                    exc_info=exc,
                )
            self._ready_raised = True
            self._ready.set()

        self._init_task = asyncio.create_task(self.initialize())
        self._init_task.add_done_callback(_done_callback)

    async def initialize(self) -> None:
        await self._repo_manager.initialize()
        await self._maybe_update_config()
        self._ready.set()

    async def _maybe_update_config(self) -> None:
        schema_version = await self.config.schema_version()

        if schema_version == 0:
            await self._schema_0_to_1()
            schema_version += 1
            await self.config.schema_version.set(schema_version)

    async def _schema_0_to_1(self):
        """
        This contains migration to allow saving state
        of both installed cogs and shared libraries.
        """
        old_conf = await self.config.get_raw("installed", default=[])
        if not old_conf:
            return
        async with self.config.installed_cogs() as new_cog_conf:
            for cog_json in old_conf:
                repo_name = cog_json["repo_name"]
                module_name = cog_json["cog_name"]
                if repo_name not in new_cog_conf:
                    new_cog_conf[repo_name] = {}
                new_cog_conf[repo_name][module_name] = {
                    "repo_name": repo_name,
                    "module_name": module_name,
                    "commit": "",
                    "pinned": False,
                }
        await self.config.clear_raw("installed")
        # no reliable way to get installed libraries (i.a. missing repo name)
        # but it only helps `[p]cog update` run faster so it's not an issue

    async def cog_install_path(self) -> Path:
        """Get the current cog install path.

        Returns
        -------
        pathlib.Path
            The default cog install path.

        """
        return await self.bot._cog_mgr.install_path()

    async def installed_cogs(self) -> Tuple[InstalledModule, ...]:
        """Get info on installed cogs.

        Returns
        -------
        `tuple` of `InstalledModule`
            All installed cogs.

        """
        installed = await self.config.installed_cogs()
        # noinspection PyTypeChecker
        return tuple(
            InstalledModule.from_json(cog_json, self._repo_manager)
            for repo_json in installed.values()
            for cog_json in repo_json.values()
        )

    async def installed_libraries(self) -> Tuple[InstalledModule, ...]:
        """Get info on installed shared libraries.

        Returns
        -------
        `tuple` of `InstalledModule`
            All installed shared libraries.

        """
        installed = await self.config.installed_libraries()
        # noinspection PyTypeChecker
        return tuple(
            InstalledModule.from_json(lib_json, self._repo_manager)
            for repo_json in installed.values()
            for lib_json in repo_json.values()
        )

    async def installed_modules(self) -> Tuple[InstalledModule, ...]:
        """Get info on installed cogs and shared libraries.

        Returns
        -------
        `tuple` of `InstalledModule`
            All installed cogs and shared libraries.

        """
        return await self.installed_cogs() + await self.installed_libraries()

    async def _save_to_installed(self, modules: Iterable[InstalledModule]) -> None:
        """Mark modules as installed or updates their json in Config.

        Parameters
        ----------
        modules : `list` of `InstalledModule`
            The modules to check off.

        """
        async with self.config.all() as global_data:
            installed_cogs = global_data["installed_cogs"]
            installed_libraries = global_data["installed_libraries"]
            for module in modules:
                if module.type == InstallableType.COG:
                    installed = installed_cogs
                elif module.type == InstallableType.SHARED_LIBRARY:
                    installed = installed_libraries
                else:
                    continue
                module_json = module.to_json()
                repo_json = installed.setdefault(module.repo_name, {})
                repo_json[module.name] = module_json

    async def _remove_from_installed(self, modules: Iterable[InstalledModule]) -> None:
        """Remove modules from the saved list
        of installed modules (corresponding to type of module).

        Parameters
        ----------
        modules : `list` of `InstalledModule`
            The modules to remove.

        """
        async with self.config.all() as global_data:
            installed_cogs = global_data["installed_cogs"]
            installed_libraries = global_data["installed_libraries"]
            for module in modules:
                if module.type == InstallableType.COG:
                    installed = installed_cogs
                elif module.type == InstallableType.SHARED_LIBRARY:
                    installed = installed_libraries
                else:
                    continue
                with contextlib.suppress(KeyError):
                    installed[module._json_repo_name].pop(module.name)

    async def _shared_lib_load_check(self, cog_name: str) -> Optional[Repo]:
        is_installed, cog = await self.is_installed(cog_name)
        # it's not gonna be None when `is_installed` is True
        # if we'll use typing_extensions in future, `Literal` can solve this
        cog = cast(InstalledModule, cog)
        if is_installed and cog.repo is not None and cog.repo.available_libraries:
            return cog.repo
        return None

    async def _available_updates(
        self, cogs: Iterable[InstalledModule]
    ) -> Tuple[Tuple[Installable, ...], Tuple[Installable, ...]]:
        """
        Get cogs and libraries which can be updated.

        Parameters
        ----------
        cogs : `list` of `InstalledModule`
            List of cogs, which should be checked against the updates.

        Returns
        -------
        tuple
            2-tuple of cogs and libraries which can be updated.

        """
        repos = {cog.repo for cog in cogs if cog.repo is not None}
        installed_libraries = await self.installed_libraries()

        modules: Set[InstalledModule] = set()
        cogs_to_update: Set[Installable] = set()
        libraries_to_update: Set[Installable] = set()
        # split libraries and cogs into 2 categories:
        # 1. `cogs_to_update`, `libraries_to_update` - module needs update, skip diffs
        # 2. `modules` - module MAY need update, check diffs
        for repo in repos:
            for lib in repo.available_libraries:
                try:
                    index = installed_libraries.index(lib)
                except ValueError:
                    libraries_to_update.add(lib)
                else:
                    modules.add(installed_libraries[index])
        for cog in cogs:
            if cog.repo is None:
                # cog had its repo removed, can't check for updates
                continue
            if cog.commit:
                modules.add(cog)
                continue
            # marking cog for update if there's no commit data saved (back-compat, see GH-2571)
            last_cog_occurrence = await cog.repo.get_last_module_occurrence(cog.name)
            if last_cog_occurrence is not None and not last_cog_occurrence.disabled:
                cogs_to_update.add(last_cog_occurrence)

        # Reduces diff requests to a single dict with no repeats
        hashes: Dict[Tuple[Repo, str], Set[InstalledModule]] = defaultdict(set)
        for module in modules:
            module.repo = cast(Repo, module.repo)
            if module.repo.commit != module.commit:
                try:
                    should_add = await module.repo.is_ancestor(module.commit, module.repo.commit)
                except errors.UnknownRevision:
                    # marking module for update if the saved commit data is invalid
                    last_module_occurrence = await module.repo.get_last_module_occurrence(
                        module.name
                    )
                    if last_module_occurrence is not None and not last_module_occurrence.disabled:
                        if last_module_occurrence.type == InstallableType.COG:
                            cogs_to_update.add(last_module_occurrence)
                        elif last_module_occurrence.type == InstallableType.SHARED_LIBRARY:
                            libraries_to_update.add(last_module_occurrence)
                else:
                    if should_add:
                        hashes[(module.repo, module.commit)].add(module)

        update_commits = []
        for (repo, old_hash), modules_to_check in hashes.items():
            modified = await repo.get_modified_modules(old_hash, repo.commit)
            for module in modules_to_check:
                try:
                    index = modified.index(module)
                except ValueError:
                    # module wasn't modified - we just need to update its commit
                    module.commit = repo.commit
                    update_commits.append(module)
                else:
                    modified_module = modified[index]
                    if modified_module.type == InstallableType.COG:
                        if not modified_module.disabled:
                            cogs_to_update.add(modified_module)
                    elif modified_module.type == InstallableType.SHARED_LIBRARY:
                        libraries_to_update.add(modified_module)

        await self._save_to_installed(update_commits)

        return (tuple(cogs_to_update), tuple(libraries_to_update))

    async def _install_cogs(
        self, cogs: Iterable[Installable]
    ) -> Tuple[Tuple[InstalledModule, ...], Tuple[Installable, ...]]:
        """Installs a list of cogs.

        Parameters
        ----------
        cogs : `list` of `Installable`
            Cogs to install. ``repo`` property of those objects can't be `None`
        Returns
        -------
        tuple
            2-tuple of installed and failed cogs.
        """
        repos: Dict[str, Tuple[Repo, Dict[str, List[Installable]]]] = {}
        for cog in cogs:
            try:
                repo_by_commit = repos[cog.repo_name]
            except KeyError:
                cog.repo = cast(Repo, cog.repo)  # docstring specifies this already
                repo_by_commit = repos[cog.repo_name] = (cog.repo, defaultdict(list))
            cogs_by_commit = repo_by_commit[1]
            cogs_by_commit[cog.commit].append(cog)
        installed = []
        failed = []
        for repo, cogs_by_commit in repos.values():
            exit_to_commit = repo.commit
            for commit, cogs_to_install in cogs_by_commit.items():
                await repo.checkout(commit)
                for cog in cogs_to_install:
                    if await cog.copy_to(await self.cog_install_path()):
                        installed.append(InstalledModule.from_installable(cog))
                    else:
                        failed.append(cog)
            await repo.checkout(exit_to_commit)

        # noinspection PyTypeChecker
        return (tuple(installed), tuple(failed))

    async def _reinstall_libraries(
        self, libraries: Iterable[Installable]
    ) -> Tuple[Tuple[InstalledModule, ...], Tuple[Installable, ...]]:
        """Installs a list of shared libraries, used when updating.

        Parameters
        ----------
        libraries : `list` of `Installable`
            Libraries to reinstall. ``repo`` property of those objects can't be `None`
        Returns
        -------
        tuple
            2-tuple of installed and failed libraries.
        """
        repos: Dict[str, Tuple[Repo, Dict[str, Set[Installable]]]] = {}
        for lib in libraries:
            try:
                repo_by_commit = repos[lib.repo_name]
            except KeyError:
                lib.repo = cast(Repo, lib.repo)  # docstring specifies this already
                repo_by_commit = repos[lib.repo_name] = (lib.repo, defaultdict(set))
            libs_by_commit = repo_by_commit[1]
            libs_by_commit[lib.commit].add(lib)

        all_installed: List[InstalledModule] = []
        all_failed: List[Installable] = []
        for repo, libs_by_commit in repos.values():
            exit_to_commit = repo.commit
            for commit, libs in libs_by_commit.items():
                await repo.checkout(commit)
                installed, failed = await repo.install_libraries(
                    target_dir=self.SHAREDLIB_PATH, req_target_dir=self.LIB_PATH, libraries=libs
                )
                all_installed += installed
                all_failed += failed
            await repo.checkout(exit_to_commit)

        # noinspection PyTypeChecker
        return (tuple(all_installed), tuple(all_failed))

    async def _install_requirements(self, cogs: Iterable[Installable]) -> Tuple[str, ...]:
        """
        Installs requirements for given cogs.

        Parameters
        ----------
        cogs : `list` of `Installable`
            Cogs whose requirements should be installed.
        Returns
        -------
        tuple
            Tuple of failed requirements.
        """

        # Reduces requirements to a single list with no repeats
        requirements = {requirement for cog in cogs for requirement in cog.requirements}
        repos: List[Tuple[Repo, List[str]]] = [(repo, []) for repo in self._repo_manager.repos]

        # This for loop distributes the requirements across all repos
        # which will allow us to concurrently install requirements
        for i, req in enumerate(requirements):
            repo_index = i % len(repos)
            repos[repo_index][1].append(req)

        has_reqs = list(filter(lambda item: len(item[1]) > 0, repos))

        failed_reqs = []
        for repo, reqs in has_reqs:
            for req in reqs:
                if not await repo.install_raw_requirements([req], self.LIB_PATH):
                    failed_reqs.append(req)
        return tuple(failed_reqs)

    @staticmethod
    async def _delete_cog(target: Path) -> None:
        """
        Removes an (installed) cog.
        :param target: Path pointing to an existing file or directory
        :return:
        """
        if not target.exists():
            return

        if target.is_dir():
            shutil.rmtree(str(target))
        elif target.is_file():
            os.remove(str(target))

    @staticmethod
    async def send_pagified(target: discord.abc.Messageable, content: str) -> None:
        for page in pagify(content):
            await target.send(page)

    @commands.command(require_var_positional=True)
    @commands.is_owner()
    async def pipinstall(self, ctx: commands.Context, *deps: str) -> None:
        """
        Install a group of dependencies using pip.

        Examples:
        - `[p]pipinstall bs4`
        - `[p]pipinstall py-cpuinfo psutil`

        Improper usage of this command can break your bot, be careful.

        **Arguments**

        - `<deps...>` The package or packages you wish to install.
        """
        repo = Repo("", "", "", "", Path.cwd())
        async with ctx.typing():
            success = await repo.install_raw_requirements(deps, self.LIB_PATH)

        if success:
            await ctx.send(_("Libraries installed.") if len(deps) > 1 else _("Library installed."))
        else:
            await ctx.send(
                _(
                    "Some libraries failed to install. Please check"
                    " your logs for a complete list."
                )
                if len(deps) > 1
                else _(
                    "The library failed to install. Please check your logs for a complete list."
                )
            )

    @commands.group()
    @commands.is_owner()
    async def repo(self, ctx: commands.Context) -> None:
        """Base command for repository management."""
        pass

    @repo.command(name="add")
    async def _repo_add(
        self, ctx: commands.Context, name: str, repo_url: str, branch: str = None
    ) -> None:
        """Add a new repo.

        Examples:
        - `[p]repo add 26-Cogs https://github.com/Twentysix26/x26-Cogs`
        - `[p]repo add Laggrons-Dumb-Cogs https://github.com/retke/Laggrons-Dumb-Cogs v3`

        Repo names can only contain characters A-z, numbers, underscores, hyphens, and dots (but they cannot start or end with a dot).

        The branch will be the default branch if not specified.

        **Arguments**

        - `<name>` The name given to the repo.
        - `<repo_url>` URL to the cog branch. Usually GitHub or GitLab.
        - `[branch]` Optional branch to install cogs from.
        """
        agreed = await do_install_agreement(ctx)
        if not agreed:
            return
        if name.startswith(".") or name.endswith("."):
            await ctx.send(_("Repo names cannot start or end with a dot."))
            return
        if re.match(r"^[a-zA-Z0-9_\-\.]+$", name) is None:
            await ctx.send(
                _(
                    "Repo names can only contain characters A-z, numbers, underscores, hyphens,"
                    " and dots."
                )
            )
            return
        try:
            async with ctx.typing():
                # noinspection PyTypeChecker
                repo = await self._repo_manager.add_repo(name=name, url=repo_url, branch=branch)
        except errors.ExistingGitRepo:
            await ctx.send(
                _("The repo name you provided is already in use. Please choose another name.")
            )
        except errors.AuthenticationError as err:
            await ctx.send(
                _(
                    "Failed to authenticate or repository does not exist."
                    " See logs for more information."
                )
            )
            log.exception(
                "Something went wrong whilst cloning %s (to revision: %s)",
                repo_url,
                branch,
                exc_info=err,
            )

        except errors.CloningError as err:
            await ctx.send(
                _(
                    "Something went wrong during the cloning process."
                    " See logs for more information."
                )
            )
            log.exception(
                "Something went wrong whilst cloning %s (to revision: %s)",
                repo_url,
                branch,
                exc_info=err,
            )
        except OSError:
            log.exception(
                "Something went wrong trying to add repo %s under name %s",
                repo_url,
                name,
            )
            await ctx.send(
                _(
                    "Something went wrong trying to add that repo."
                    " See logs for more information."
                )
            )
        else:
            await ctx.send(_("Repo `{name}` successfully added.").format(name=name))
            if repo.install_msg:
                await ctx.send(
                    repo.install_msg.replace("[p]", ctx.clean_prefix).replace(
                        "[botname]", ctx.me.display_name
                    )
                )

    @repo.command(name="delete", aliases=["remove", "del"], require_var_positional=True)
    async def _repo_del(self, ctx: commands.Context, *repos: Repo) -> None:
        """
        Remove repos and their files.

        Examples:
        - `[p]repo delete 26-Cogs`
        - `[p]repo delete 26-Cogs Laggrons-Dumb-Cogs`

        **Arguments**

        - `<repos...>` The repo or repos to remove.
        """
        for repo in set(repos):
            await self._repo_manager.delete_repo(repo.name)

        await ctx.send(
            (
                _("Successfully deleted repos: ")
                if len(repos) > 1
                else _("Successfully deleted the repo: ")
            )
            + humanize_list([inline(i.name) for i in set(repos)])
        )

    @repo.command(name="list")
    async def _repo_list(self, ctx: commands.Context) -> None:
        """List all installed repos."""
        repos = self._repo_manager.repos
        sorted_repos = sorted(repos, key=lambda r: str.lower(r.name))
        if len(repos) == 0:
            joined = _("There are no repos installed.")
        else:
            if len(repos) > 1:
                joined = _("## Installed Repos\n")
            else:
                joined = _("## Installed Repo\n")
            for repo in sorted_repos:
                joined += "- **{}:** {}\n  - {}\n".format(
                    repo.name,
                    repo.short or "",
                    (
                        f"<{repo.clean_url}>"
                        if repo.clean_url.startswith(("http://", "https://"))
                        else repo.clean_url
                    ),
                )

        for page in pagify(joined, ["\n"], shorten_by=16):
            await ctx.send(page)

    @repo.command(name="info")
    async def _repo_info(self, ctx: commands.Context, repo: Repo) -> None:
        """Show information about a repo.

        Example:
        - `[p]repo info 26-Cogs`

        **Arguments**

        - `<repo>` The name of the repo to show info about.
        """
        made_by = ", ".join(repo.author) or _("Missing from info.json")

        information = _("Repo url: {repo_url}\n").format(repo_url=repo.clean_url)
        if repo.branch:
            information += _("Branch: {branch_name}\n").format(branch_name=repo.branch)
        information += _("Made by: {author}\nDescription:\n{description}").format(
            author=made_by, description=repo.description or ""
        )

        msg = _("Information on {repo_name} repo:{information}").format(
            repo_name=inline(repo.name), information=box(information)
        )

        await ctx.send(msg)

    @repo.command(name="update")
    async def _repo_update(self, ctx: commands.Context, *repos: Repo) -> None:
        """Update all repos, or ones of your choosing.

        This will *not* update the cogs installed from those repos.

        Examples:
        - `[p]repo update`
        - `[p]repo update 26-Cogs`
        - `[p]repo update 26-Cogs Laggrons-Dumb-Cogs`

        **Arguments**

        - `[repos...]` The name or names of repos to update. If omitted, all repos are updated.
        """
        async with ctx.typing():
            updated: Set[str]

            updated_repos, failed = await self._repo_manager.update_repos(repos)
            updated = {repo.name for repo in updated_repos}

            if updated:
                message = _("Repo update completed successfully.")
                message += _("\nUpdated: ") + humanize_list(tuple(map(inline, updated)))
            elif not repos:
                message = _("All installed repos are already up to date.")
            else:
                if len(updated_repos) > 1:
                    message = _("These repos are already up to date.")
                else:
                    message = _("This repo is already up to date.")

            if failed:
                message += "\n" + self.format_failed_repos(failed)

        await self.send_pagified(ctx, message)

    @commands.group()
    @commands.is_owner()
    async def cog(self, ctx: commands.Context) -> None:
        """Base command for cog installation management commands."""
        pass

    @cog.command(name="reinstallreqs", hidden=True)
    async def _cog_reinstallreqs(self, ctx: commands.Context) -> None:
        """
        This command should not be used unless Red specifically asks for it.

        This command will reinstall cog requirements and shared libraries for all installed cogs.

        Red might ask the owner to use this when it clears contents of the lib folder
        because of change in minor version of Python.
        """
        async with ctx.typing():
            self._create_lib_folder(remove_first=True)
            installed_cogs = await self.installed_cogs()
            cogs = []
            repos = set()
            for cog in installed_cogs:
                if cog.repo is None:
                    continue
                repos.add(cog.repo)
                cogs.append(cog)
            failed_reqs = await self._install_requirements(cogs)
            all_installed_libs: List[InstalledModule] = []
            all_failed_libs: List[Installable] = []
            for repo in repos:
                installed_libs, failed_libs = await repo.install_libraries(
                    target_dir=self.SHAREDLIB_PATH, req_target_dir=self.LIB_PATH
                )
                all_installed_libs += installed_libs
                all_failed_libs += failed_libs
        message = ""
        if failed_reqs:
            message += (
                _("Failed to install requirements: ")
                if len(failed_reqs) > 1
                else _("Failed to install the requirement: ")
            ) + humanize_list(tuple(map(inline, failed_reqs)))
        if all_failed_libs:
            libnames = [lib.name for lib in failed_libs]
            message += (
                _("\nFailed to install shared libraries: ")
                if len(all_failed_libs) > 1
                else _("\nFailed to install shared library: ")
            ) + humanize_list(tuple(map(inline, libnames)))
        if message:
            await self.send_pagified(
                ctx,
                _(
                    "Cog requirements and shared libraries for all installed cogs"
                    " have been reinstalled but there were some errors:\n"
                )
                + message,
            )
        else:
            await ctx.send(
                _(
                    "Cog requirements and shared libraries"
                    " for all installed cogs have been reinstalled."
                )
            )

    @cog.command(name="install", usage="<repo> <cogs...>", require_var_positional=True)
    async def _cog_install(self, ctx: commands.Context, repo: Repo, *cog_names: str) -> None:
        """Install a cog from the given repo.

        Examples:
        - `[p]cog install 26-Cogs defender`
        - `[p]cog install Laggrons-Dumb-Cogs say roleinvite`

        **Arguments**

        - `<repo>` The name of the repo to install cogs from.
        - `<cogs...>` The cog or cogs to install.
        """
        await self._cog_installrev(ctx, repo, None, cog_names)

    @cog.command(
        name="installversion", usage="<repo> <revision> <cogs...>", require_var_positional=True
    )
    async def _cog_installversion(
        self, ctx: commands.Context, repo: Repo, revision: str, *cog_names: str
    ) -> None:
        """Install a cog from the specified revision of given repo.

        Revisions are "commit ids" that point to the point in the code when a specific change was made.
        The latest revision can be found in the URL bar for any GitHub repo by [pressing "y" on that repo](https://docs.github.com/en/free-pro-team@latest/github/managing-files-in-a-repository/getting-permanent-links-to-files#press-y-to-permalink-to-a-file-in-a-specific-commit).

        Older revisions can be found in the URL bar by [viewing the commit history of any repo](https://cdn.discordapp.com/attachments/133251234164375552/775760247787749406/unknown.png)

        Example:
        - `[p]cog installversion Broken-Repo e798cc268e199612b1316a3d1f193da0770c7016 cog_name`

        **Arguments**

        - `<repo>` The name of the repo to install cogs from.
        - `<revision>` The revision to install from.
        - `<cogs...>` The cog or cogs to install.
        """
        await self._cog_installrev(ctx, repo, revision, cog_names)

    async def _cog_installrev(
        self, ctx: commands.Context, repo: Repo, rev: Optional[str], cog_names: Iterable[str]
    ) -> None:
        commit = None
        async with ctx.typing():
            if rev is not None:
                try:
                    commit = await repo.get_full_sha1(rev)
                except errors.AmbiguousRevision as e:
                    msg = _(
                        "Error: short sha1 `{rev}` is ambiguous. Possible candidates:\n"
                    ).format(rev=rev)
                    for candidate in e.candidates:
                        msg += (
                            f"**{candidate.object_type} {candidate.rev}**"
                            f" - {candidate.description}\n"
                        )
                    await self.send_pagified(ctx, msg)
                    return
                except errors.UnknownRevision:
                    await ctx.send(
                        _("Error: there is no revision `{rev}` in repo `{repo.name}`").format(
                            rev=rev, repo=repo
                        )
                    )
                    return
            cog_names = set(cog_names)

            async with repo.checkout(commit, exit_to_rev=repo.branch):
                cogs, message = await self._filter_incorrect_cogs_by_names(repo, cog_names)
                if not cogs:
                    await self.send_pagified(ctx, message)
                    return
                failed_reqs = await self._install_requirements(cogs)
                if failed_reqs:
                    message += (
                        _("\nFailed to install requirements: ")
                        if len(failed_reqs) > 1
                        else _("\nFailed to install the requirement: ")
                    ) + humanize_list(tuple(map(inline, failed_reqs)))
                    await self.send_pagified(ctx, message)
                    return

                installed_cogs, failed_cogs = await self._install_cogs(cogs)

            deprecation_notice = ""
            if repo.available_libraries:
                deprecation_notice = DEPRECATION_NOTICE.format(repo_list=inline(repo.name))
            installed_libs, failed_libs = await repo.install_libraries(
                target_dir=self.SHAREDLIB_PATH, req_target_dir=self.LIB_PATH
            )
            if rev is not None:
                for cog in installed_cogs:
                    cog.pinned = True
            await self._save_to_installed(installed_cogs + installed_libs)
            if failed_libs:
                libnames = [inline(lib.name) for lib in failed_libs]
                message = (
                    (
                        _("\nFailed to install shared libraries for `{repo.name}` repo: ")
                        if len(libnames) > 1
                        else _("\nFailed to install shared library for `{repo.name}` repo: ")
                    ).format(repo=repo)
                    + humanize_list(libnames)
                    + message
                )
            if failed_cogs:
                cognames = [inline(cog.name) for cog in failed_cogs]
                message = (
                    (
                        _("\nFailed to install cogs: ")
                        if len(failed_cogs) > 1
                        else _("\nFailed to install the cog: ")
                    )
                    + humanize_list(cognames)
                    + message
                )
            if installed_cogs:
                cognames = [inline(cog.name) for cog in installed_cogs]
                message = (
                    (
                        _("Successfully installed cogs: ")
                        if len(installed_cogs) > 1
                        else _("Successfully installed the cog: ")
                    )
                    + humanize_list(cognames)
                    + (
                        _(
                            "\nThese cogs are now pinned and won't get updated automatically."
                            " To change this, use `{prefix}cog unpin <cog>`"
                        ).format(prefix=ctx.clean_prefix)
                        if rev is not None
                        else ""
                    )
                    + _(
                        "\nYou can load them using {command_1}."
                        " To see end user data statements, you can use {command_2}."
                    ).format(
                        command_1=inline(f"{ctx.clean_prefix}load <cogs...>"),
                        command_2=inline(f"{ctx.clean_prefix}cog info <repo> <cog>"),
                    )
                    + message
                )
        # "---" added to separate cog install messages from Downloader's message
        await self.send_pagified(ctx, f"{message}{deprecation_notice}\n---")
        for cog in installed_cogs:
            if cog.install_msg:
                await ctx.send(
                    cog.install_msg.replace("[p]", ctx.clean_prefix).replace(
                        "[botname]", ctx.me.display_name
                    )
                )

    @cog.command(name="uninstall", require_var_positional=True)
    async def _cog_uninstall(self, ctx: commands.Context, *cogs: InstalledCog) -> None:
        """Uninstall cogs.

        You may only uninstall cogs which were previously installed
        by Downloader.

        Examples:
        - `[p]cog uninstall defender`
        - `[p]cog uninstall say roleinvite`

        **Arguments**

        - `<cogs...>` The cog or cogs to uninstall.
        """
        async with ctx.typing():
            uninstalled_cogs = []
            failed_cogs = []
            for cog in set(cogs):
                real_name = cog.name

                poss_installed_path = (await self.cog_install_path()) / real_name
                if poss_installed_path.exists():
                    with contextlib.suppress(commands.ExtensionNotLoaded):
                        await ctx.bot.unload_extension(real_name)
                        await ctx.bot.remove_loaded_package(real_name)
                    await self._delete_cog(poss_installed_path)
                    uninstalled_cogs.append(inline(real_name))
                else:
                    failed_cogs.append(real_name)
            await self._remove_from_installed(cogs)

            message = ""
            if uninstalled_cogs:
                message += (
                    _("Successfully uninstalled cogs: ")
                    if len(uninstalled_cogs) > 1
                    else _("Successfully uninstalled the cog: ")
                ) + humanize_list(uninstalled_cogs)
            if failed_cogs:
                if len(failed_cogs) > 1:
                    message += (
                        _(
                            "\nDownloader has removed these cogs from the installed cogs list"
                            " but it wasn't able to find their files: "
                        )
                        + humanize_list(tuple(map(inline, failed_cogs)))
                        + _(
                            "\nThey were most likely removed without using {command_1}.\n"
                            "You may need to remove those files manually if the cogs are still usable."
                            " If so, ensure the cogs have been unloaded with {command_2}."
                        ).format(
                            command_1=inline(f"{ctx.clean_prefix}cog uninstall"),
                            command_2=inline(f"{ctx.clean_prefix}unload {' '.join(failed_cogs)}"),
                        )
                    )
                else:
                    message += (
                        _(
                            "\nDownloader has removed this cog from the installed cogs list"
                            " but it wasn't able to find its files: "
                        )
                        + inline(failed_cogs[0])
                        + _(
                            "\nIt was most likely removed without using {command_1}.\n"
                            "You may need to remove those files manually if the cog is still usable."
                            " If so, ensure the cog has been unloaded with {command_2}."
                        ).format(
                            command_1=inline(f"{ctx.clean_prefix}cog uninstall"),
                            command_2=inline(f"{ctx.clean_prefix}unload {failed_cogs[0]}"),
                        )
                    )
        await self.send_pagified(ctx, message)

    @cog.command(name="pin", require_var_positional=True)
    async def _cog_pin(self, ctx: commands.Context, *cogs: InstalledCog) -> None:
        """Pin cogs - this will lock cogs on their current version.

        Examples:
        - `[p]cog pin defender`
        - `[p]cog pin outdated_cog1 outdated_cog2`

        **Arguments**

        - `<cogs...>` The cog or cogs to pin. Must already be installed.
        """
        already_pinned = []
        pinned = []
        for cog in set(cogs):
            if cog.pinned:
                already_pinned.append(inline(cog.name))
                continue
            cog.pinned = True
            pinned.append(cog)
        message = ""
        if pinned:
            await self._save_to_installed(pinned)
            cognames = [inline(cog.name) for cog in pinned]
            message += (
                _("Pinned cogs: ") if len(pinned) > 1 else _("Pinned cog: ")
            ) + humanize_list(cognames)
        if already_pinned:
            message += (
                _("\nThese cogs were already pinned: ")
                if len(already_pinned) > 1
                else _("\nThis cog was already pinned: ")
            ) + humanize_list(already_pinned)
        await self.send_pagified(ctx, message)

    @cog.command(name="unpin", require_var_positional=True)
    async def _cog_unpin(self, ctx: commands.Context, *cogs: InstalledCog) -> None:
        """Unpin cogs - this will remove the update lock from those cogs.

        Examples:
        - `[p]cog unpin defender`
        - `[p]cog unpin updated_cog1 updated_cog2`

        **Arguments**

        - `<cogs...>` The cog or cogs to unpin. Must already be installed and pinned."""
        not_pinned = []
        unpinned = []
        for cog in set(cogs):
            if not cog.pinned:
                not_pinned.append(inline(cog.name))
                continue
            cog.pinned = False
            unpinned.append(cog)
        message = ""
        if unpinned:
            await self._save_to_installed(unpinned)
            cognames = [inline(cog.name) for cog in unpinned]
            message += (
                _("Unpinned cogs: ") if len(unpinned) > 1 else _("Unpinned cog: ")
            ) + humanize_list(cognames)
        if not_pinned:
            message += (
                _("\nThese cogs weren't pinned: ")
                if len(not_pinned) > 1
                else _("\nThis cog was already not pinned: ")
            ) + humanize_list(not_pinned)
        await self.send_pagified(ctx, message)

    @cog.command(name="listpinned")
    async def _cog_listpinned(self, ctx: commands.Context):
        """List currently pinned cogs."""
        installed = await self.installed_cogs()
        pinned_list = sorted(
            [cog for cog in installed if cog.pinned], key=lambda cog: cog.name.lower()
        )
        if pinned_list:
            message = "\n".join(
                f"({inline(cog.commit[:7] or _('unknown'))}) {cog.name}" for cog in pinned_list
            )
        else:
            message = _("None.")
        if await ctx.embed_requested():
            embed = discord.Embed(color=(await ctx.embed_colour()))
            for page in pagify(message, page_length=900):
                name = _("(continued)") if page.startswith("\n") else _("Pinned Cogs:")
                embed.add_field(name=name, value=page, inline=False)
            await ctx.send(embed=embed)
        else:
            for page in pagify(message, page_length=1900):
                if not page.startswith("\n"):
                    page = _("Pinned Cogs: \n") + page
                await ctx.send(page)

    @cog.command(name="checkforupdates")
    async def _cog_checkforupdates(self, ctx: commands.Context) -> None:
        """
        Check for available cog updates (including pinned cogs).

        This command doesn't update cogs, it only checks for updates.
        Use `[p]cog update` to update cogs.
        """

        async with ctx.typing():
            cogs_to_check, failed = await self._get_cogs_to_check()
            cogs_to_update, libs_to_update = await self._available_updates(cogs_to_check)
            cogs_to_update, filter_message = self._filter_incorrect_cogs(cogs_to_update)

            message = ""
            if cogs_to_update:
                cognames = [cog.name for cog in cogs_to_update]
                message += (
                    _("These cogs can be updated: ")
                    if len(cognames) > 1
                    else _("This cog can be updated: ")
                ) + humanize_list(tuple(map(inline, cognames)))
            if libs_to_update:
                libnames = [cog.name for cog in libs_to_update]
                message += (
                    _("\nThese shared libraries can be updated: ")
                    if len(libnames) > 1
                    else _("\nThis shared library can be updated: ")
                ) + humanize_list(tuple(map(inline, libnames)))
            if not (cogs_to_update or libs_to_update) and filter_message:
                message += _("No cogs can be updated.")
            message += filter_message

            if not message:
                message = _("All installed cogs are up to date.")

            if failed:
                message += "\n" + self.format_failed_repos(failed)

        await self.send_pagified(ctx, message)

    @cog.command(name="update")
    async def _cog_update(
        self, ctx: commands.Context, reload: Optional[bool], *cogs: InstalledCog
    ) -> None:
        """Update all cogs, or ones of your choosing.

        Examples:
        - `[p]cog update`
        - `[p]cog update True`
        - `[p]cog update defender`
        - `[p]cog update True defender`

        **Arguments**

        - `[reload]` Whether to reload cogs immediately after update or not.
        - `[cogs...]` The cog or cogs to update. If omitted, all cogs are updated.
        """
        if reload:
            ctx.assume_yes = True
        await self._cog_update_logic(ctx, cogs=cogs)

    @cog.command(name="updateallfromrepos", require_var_positional=True)
    async def _cog_updateallfromrepos(
        self, ctx: commands.Context, reload: Optional[bool], *repos: Repo
    ) -> None:
        """Update all cogs from repos of your choosing.

        Examples:
        - `[p]cog updateallfromrepos 26-Cogs`
        - `[p]cog updateallfromrepos True 26-Cogs`
        - `[p]cog updateallfromrepos Laggrons-Dumb-Cogs 26-Cogs`

        **Arguments**

        - `[reload]` Whether to reload cogs immediately after update or not.
        - `<repos...>` The repo or repos to update all cogs from.
        """
        if reload:
            ctx.assume_yes = True
        await self._cog_update_logic(ctx, repos=repos)

    @cog.command(name="updatetoversion")
    async def _cog_updatetoversion(
        self,
        ctx: commands.Context,
        reload: Optional[bool],
        repo: Repo,
        revision: str,
        *cogs: InstalledCog,
    ) -> None:
        """Update all cogs, or ones of your choosing to chosen revision of one repo.

        Note that update doesn't mean downgrade and therefore `revision`
        has to be newer than the version that cog currently has installed. If you want to
        downgrade the cog, uninstall and install it again.

        See `[p]cog installversion` for an explanation of `revision`.

        Examples:
        - `[p]cog updatetoversion Broken-Repo e798cc268e199612b1316a3d1f193da0770c7016 cog_name`
        - `[p]cog updatetoversion True Broken-Repo 6107c0770ad391f1d3a6131b216991e862cc897e cog_name`

        **Arguments**

        - `[reload]` Whether to reload cogs immediately after update or not.
        - `<repo>` The repo or repos to update all cogs from.
        - `<revision>` The revision to update to.
        - `[cogs...]` The cog or cogs to update.
        """
        if reload:
            ctx.assume_yes = True
        await self._cog_update_logic(ctx, repo=repo, rev=revision, cogs=cogs)

    async def _cog_update_logic(
        self,
        ctx: commands.Context,
        *,
        repo: Optional[Repo] = None,
        repos: Optional[List[Repo]] = None,
        rev: Optional[str] = None,
        cogs: Optional[List[InstalledModule]] = None,
    ) -> None:
        failed_repos = set()
        updates_available = set()

        async with ctx.typing():
            # this is enough to be sure that `rev` is not None (based on calls to this method)
            if repo is not None:
                rev = cast(str, rev)

                try:
                    await repo.update()
                except errors.UpdateError:
                    message = self.format_failed_repos([repo.name])
                    await self.send_pagified(ctx, message)
                    return

                try:
                    commit = await repo.get_full_sha1(rev)
                except errors.AmbiguousRevision as e:
                    msg = _(
                        "Error: short sha1 `{rev}` is ambiguous. Possible candidates:\n"
                    ).format(rev=rev)
                    for candidate in e.candidates:
                        msg += (
                            f"**{candidate.object_type} {candidate.rev}**"
                            f" - {candidate.description}\n"
                        )
                    await self.send_pagified(ctx, msg)
                    return
                except errors.UnknownRevision:
                    message = _(
                        "Error: there is no revision `{rev}` in repo `{repo.name}`"
                    ).format(rev=rev, repo=repo)
                    await ctx.send(message)
                    return

                await repo.checkout(commit)
                cogs_to_check, __ = await self._get_cogs_to_check(
                    repos=[repo], cogs=cogs, update_repos=False
                )

            else:
                cogs_to_check, check_failed = await self._get_cogs_to_check(repos=repos, cogs=cogs)
                failed_repos.update(check_failed)

            pinned_cogs = {cog for cog in cogs_to_check if cog.pinned}
            cogs_to_check -= pinned_cogs

            message = ""
            if not cogs_to_check:
                cogs_to_update = libs_to_update = ()
                message += _("There were no cogs to check.")
                if pinned_cogs:
                    cognames = [cog.name for cog in pinned_cogs]
                    message += (
                        _("\nThese cogs are pinned and therefore weren't checked: ")
                        if len(cognames) > 1
                        else _("\nThis cog is pinned and therefore wasn't checked: ")
                    ) + humanize_list(tuple(map(inline, cognames)))
            else:
                cogs_to_update, libs_to_update = await self._available_updates(cogs_to_check)

                updates_available = cogs_to_update or libs_to_update
                cogs_to_update, filter_message = self._filter_incorrect_cogs(cogs_to_update)

                if updates_available:
                    updated_cognames, message = await self._update_cogs_and_libs(
                        ctx, cogs_to_update, libs_to_update, current_cog_versions=cogs_to_check
                    )
                else:
                    if repos:
                        message += _("Cogs from provided repos are already up to date.")
                    elif repo:
                        if cogs:
                            message += _(
                                "Provided cogs are already up to date with this revision."
                            )
                        else:
                            message += _(
                                "Cogs from provided repo are already up to date with this revision."
                            )
                    else:
                        if cogs:
                            message += _("Provided cogs are already up to date.")
                        else:
                            message += _("All installed cogs are already up to date.")
                if repo is not None:
                    await repo.checkout(repo.branch)
                if pinned_cogs:
                    cognames = [cog.name for cog in pinned_cogs]
                    message += (
                        _("\nThese cogs are pinned and therefore weren't checked: ")
                        if len(cognames) > 1
                        else _("\nThis cog is pinned and therefore wasn't checked: ")
                    ) + humanize_list(tuple(map(inline, cognames)))
                message += filter_message

        if failed_repos:
            message += "\n" + self.format_failed_repos(failed_repos)

        repos_with_libs = {
            inline(module.repo.name)
            for module in cogs_to_update + libs_to_update
            if module.repo.available_libraries
        }
        if repos_with_libs:
            message += DEPRECATION_NOTICE.format(repo_list=humanize_list(list(repos_with_libs)))

        await self.send_pagified(ctx, message)

        if updates_available and updated_cognames:
            await self._ask_for_cog_reload(ctx, updated_cognames)

    @cog.command(name="list")
    async def _cog_list(self, ctx: commands.Context, repo: Repo) -> None:
        """List all available cogs from a single repo.

        Example:
        - `[p]cog list 26-Cogs`

        **Arguments**

        - `<repo>` The repo to list cogs from.
        """
        sort_function = lambda x: x.name.lower()
        all_installed_cogs = await self.installed_cogs()
        installed_cogs_in_repo = [cog for cog in all_installed_cogs if cog.repo_name == repo.name]
        installed_str = "\n".join(
            "- {}{}".format(i.name, ": {}".format(i.short) if i.short else "")
            for i in sorted(installed_cogs_in_repo, key=sort_function)
        )

        if len(installed_cogs_in_repo) > 1:
            installed_str = _("# Installed Cogs\n{text}").format(text=installed_str)
        elif installed_cogs_in_repo:
            installed_str = _("# Installed Cog\n{text}").format(text=installed_str)

        available_cogs = [
            cog for cog in repo.available_cogs if not (cog.hidden or cog in installed_cogs_in_repo)
        ]
        available_str = "\n".join(
            "+ {}{}".format(cog.name, ": {}".format(cog.short) if cog.short else "")
            for cog in sorted(available_cogs, key=sort_function)
        )

        if not available_str:
            cogs = _("> Available Cogs\nNo cogs are available.")
        elif len(available_cogs) > 1:
            cogs = _("> Available Cogs\n{text}").format(text=available_str)
        else:
            cogs = _("> Available Cog\n{text}").format(text=available_str)
        cogs = cogs + "\n\n" + installed_str
        for page in pagify(cogs, ["\n"], shorten_by=16):
            await ctx.send(box(page.lstrip(" "), lang="markdown"))

    @cog.command(name="info", usage="<repo> <cog>")
    async def _cog_info(self, ctx: commands.Context, repo: Repo, cog_name: str) -> None:
        """List information about a single cog.

        Example:
        - `[p]cog info 26-Cogs defender`

        **Arguments**

        - `<repo>` The repo to get cog info from.
        - `<cog>` The cog to get info on.
        """
        cog = discord.utils.get(repo.available_cogs, name=cog_name)
        if cog is None:
            await ctx.send(
                _("There is no cog `{cog_name}` in the repo `{repo.name}`").format(
                    cog_name=cog_name, repo=repo
                )
            )
            return

        msg = _(
            "Information on {cog_name}:\n"
            "{description}\n\n"
            "End user data statement:\n"
            "{end_user_data_statement}\n\n"
            "Made by: {author}\n"
            "Requirements: {requirements}"
        ).format(
            cog_name=cog.name,
            description=cog.description or "",
            end_user_data_statement=(
                cog.end_user_data_statement
                or _("Author of the cog didn't provide end user data statement.")
            ),
            author=", ".join(cog.author) or _("Missing from info.json"),
            requirements=", ".join(cog.requirements) or "None",
        )
        for page in pagify(msg):
            await ctx.send(box(page))

    async def is_installed(
        self, cog_name: str
    ) -> Union[Tuple[bool, InstalledModule], Tuple[bool, None]]:
        """Check to see if a cog has been installed through Downloader.

        Parameters
        ----------
        cog_name : str
            The name of the cog to check for.

        Returns
        -------
        `tuple` of (`bool`, `InstalledModule`)
            :code:`(True, InstalledModule)` if the cog is installed, else
            :code:`(False, None)`.

        """
        for installed_cog in await self.installed_cogs():
            if installed_cog.name == cog_name:
                return True, installed_cog
        return False, None

    async def _filter_incorrect_cogs_by_names(
        self, repo: Repo, cog_names: Iterable[str]
    ) -> Tuple[Tuple[Installable, ...], str]:
        """Filter out incorrect cogs from list.

        Parameters
        ----------
        repo : `Repo`
            Repo which should be searched for `cog_names`
        cog_names : `list` of `str`
            Cog names to search for in repo.
        Returns
        -------
        tuple
            2-tuple of cogs to install and error message for incorrect cogs.
        """
        installed_cogs = await self.installed_cogs()
        cogs: List[Installable] = []
        unavailable_cogs: List[str] = []
        already_installed: List[str] = []
        name_already_used: List[str] = []

        for cog_name in cog_names:
            cog: Optional[Installable] = discord.utils.get(repo.available_cogs, name=cog_name)
            if cog is None:
                unavailable_cogs.append(inline(cog_name))
                continue
            if cog in installed_cogs:
                already_installed.append(inline(cog_name))
                continue
            if discord.utils.get(installed_cogs, name=cog.name):
                name_already_used.append(inline(cog_name))
                continue
            cogs.append(cog)

        message = ""

        if unavailable_cogs:
            message = (
                _("\nCouldn't find these cogs in {repo.name}: ")
                if len(unavailable_cogs) > 1
                else _("\nCouldn't find this cog in {repo.name}: ")
            ).format(repo=repo) + humanize_list(unavailable_cogs)
        if already_installed:
            message += (
                _("\nThese cogs were already installed: ")
                if len(already_installed) > 1
                else _("\nThis cog was already installed: ")
            ) + humanize_list(already_installed)
        if name_already_used:
            message += (
                _("\nSome cogs with these names are already installed from different repos: ")
                if len(name_already_used) > 1
                else _("\nCog with this name is already installed from a different repo: ")
            ) + humanize_list(name_already_used)
        correct_cogs, add_to_message = self._filter_incorrect_cogs(cogs)
        if add_to_message:
            return correct_cogs, f"{message}{add_to_message}"
        return correct_cogs, message

    def _filter_incorrect_cogs(
        self, cogs: Iterable[Installable]
    ) -> Tuple[Tuple[Installable, ...], str]:
        correct_cogs: List[Installable] = []
        outdated_python_version: List[str] = []
        outdated_bot_version: List[str] = []
        for cog in cogs:
            if cog.min_python_version > sys.version_info:
                outdated_python_version.append(
                    inline(cog.name)
                    + _(" (Minimum: {min_version})").format(
                        min_version=".".join([str(n) for n in cog.min_python_version])
                    )
                )
                continue
            ignore_max = cog.min_bot_version > cog.max_bot_version
            if (
                cog.min_bot_version > red_version_info
                or not ignore_max
                and cog.max_bot_version < red_version_info
            ):
                outdated_bot_version.append(
                    inline(cog.name)
                    + _(" (Minimum: {min_version}").format(min_version=cog.min_bot_version)
                    + (
                        ""
                        if ignore_max
                        else _(", at most: {max_version}").format(max_version=cog.max_bot_version)
                    )
                    + ")"
                )
                continue
            correct_cogs.append(cog)
        message = ""
        if outdated_python_version:
            message += (
                _("\nThese cogs require higher python version than you have: ")
                if len(outdated_python_version)
                else _("\nThis cog requires higher python version than you have: ")
            ) + humanize_list(outdated_python_version)
        if outdated_bot_version:
            message += (
                _(
                    "\nThese cogs require different Red version"
                    " than you currently have ({current_version}): "
                )
                if len(outdated_bot_version) > 1
                else _(
                    "\nThis cog requires different Red version than you currently "
                    "have ({current_version}): "
                )
            ).format(current_version=red_version_info) + humanize_list(outdated_bot_version)

        return tuple(correct_cogs), message

    async def _get_cogs_to_check(
        self,
        *,
        repos: Optional[Iterable[Repo]] = None,
        cogs: Optional[Iterable[InstalledModule]] = None,
        update_repos: bool = True,
    ) -> Tuple[Set[InstalledModule], List[str]]:
        failed = []
        if not (cogs or repos):
            if update_repos:
                __, failed = await self._repo_manager.update_repos()

            cogs_to_check = {
                cog
                for cog in await self.installed_cogs()
                if cog.repo is not None and cog.repo.name not in failed
            }
        else:
            # this is enough to be sure that `cogs` is not None (based on if above)
            if not repos:
                cogs = cast(Iterable[InstalledModule], cogs)
                repos = {cog.repo for cog in cogs if cog.repo is not None}

            if update_repos:
                __, failed = await self._repo_manager.update_repos(repos)

            if failed:
                # remove failed repos
                repos = {repo for repo in repos if repo.name not in failed}

            if cogs:
                cogs_to_check = {cog for cog in cogs if cog.repo is not None and cog.repo in repos}
            else:
                cogs_to_check = {
                    cog
                    for cog in await self.installed_cogs()
                    if cog.repo is not None and cog.repo in repos
                }

        return (cogs_to_check, failed)

    async def _update_cogs_and_libs(
        self,
        ctx: commands.Context,
        cogs_to_update: Iterable[Installable],
        libs_to_update: Iterable[Installable],
        current_cog_versions: Iterable[InstalledModule],
    ) -> Tuple[Set[str], str]:
        current_cog_versions_map = {cog.name: cog for cog in current_cog_versions}
        failed_reqs = await self._install_requirements(cogs_to_update)
        if failed_reqs:
            return (
                set(),
                (
                    _("Failed to install requirements: ")
                    if len(failed_reqs) > 1
                    else _("Failed to install the requirement: ")
                )
                + humanize_list(tuple(map(inline, failed_reqs))),
            )
        installed_cogs, failed_cogs = await self._install_cogs(cogs_to_update)
        installed_libs, failed_libs = await self._reinstall_libraries(libs_to_update)
        await self._save_to_installed(installed_cogs + installed_libs)
        message = _("Cog update completed successfully.")

        updated_cognames: Set[str] = set()
        if installed_cogs:
            updated_cognames = set()
            cogs_with_changed_eud_statement = set()
            for cog in installed_cogs:
                updated_cognames.add(cog.name)
                current_eud_statement = current_cog_versions_map[cog.name].end_user_data_statement
                if current_eud_statement != cog.end_user_data_statement:
                    cogs_with_changed_eud_statement.add(cog.name)
            message += _("\nUpdated: ") + humanize_list(tuple(map(inline, updated_cognames)))
            if cogs_with_changed_eud_statement:
                if len(cogs_with_changed_eud_statement) > 1:
                    message += (
                        _("\nEnd user data statements of these cogs have changed: ")
                        + humanize_list(tuple(map(inline, cogs_with_changed_eud_statement)))
                        + _("\nYou can use {command} to see the updated statements.\n").format(
                            command=inline(f"{ctx.clean_prefix}cog info <repo> <cog>")
                        )
                    )
                else:
                    message += (
                        _("\nEnd user data statement of this cog has changed:")
                        + inline(next(iter(cogs_with_changed_eud_statement)))
                        + _("\nYou can use {command} to see the updated statement.\n").format(
                            command=inline(f"{ctx.clean_prefix}cog info <repo> <cog>")
                        )
                    )
            # If the bot has any slash commands enabled, warn them to sync
            enabled_slash = await self.bot.list_enabled_app_commands()
            if any(enabled_slash.values()):
                message += _(
                    "\nYou may need to resync your slash commands with `{prefix}slash sync`."
                ).format(prefix=ctx.prefix)
        if failed_cogs:
            cognames = [cog.name for cog in failed_cogs]
            message += (
                _("\nFailed to update cogs: ")
                if len(failed_cogs) > 1
                else _("\nFailed to update cog: ")
            ) + humanize_list(tuple(map(inline, cognames)))
        if not cogs_to_update:
            message = _("No cogs were updated.")
        if installed_libs:
            message += (
                _(
                    "\nSome shared libraries were updated, you should restart the bot "
                    "to bring the changes into effect."
                )
                if len(installed_libs) > 1
                else _(
                    "\nA shared library was updated, you should restart the "
                    "bot to bring the changes into effect."
                )
            )
        if failed_libs:
            libnames = [lib.name for lib in failed_libs]
            message += (
                _("\nFailed to install shared libraries: ")
                if len(failed_cogs) > 1
                else _("\nFailed to install shared library: ")
            ) + humanize_list(tuple(map(inline, libnames)))
        return (updated_cognames, message)

    async def _ask_for_cog_reload(self, ctx: commands.Context, updated_cognames: Set[str]) -> None:
        updated_cognames &= ctx.bot.extensions.keys()  # only reload loaded cogs
        if not updated_cognames:
            await ctx.send(_("None of the updated cogs were previously loaded. Update complete."))
            return

        if not ctx.assume_yes:
            message = (
                _("Would you like to reload the updated cogs?")
                if len(updated_cognames) > 1
                else _("Would you like to reload the updated cog?")
            )
            can_react = can_user_react_in(ctx.me, ctx.channel)
            if not can_react:
                message += " (yes/no)"
            query: discord.Message = await ctx.send(message)
            if can_react:
                # noinspection PyAsyncCall
                start_adding_reactions(query, ReactionPredicate.YES_OR_NO_EMOJIS)
                pred = ReactionPredicate.yes_or_no(query, ctx.author)
                event = "reaction_add"
            else:
                pred = MessagePredicate.yes_or_no(ctx)
                event = "message"
            try:
                await ctx.bot.wait_for(event, check=pred, timeout=30)
            except asyncio.TimeoutError:
                with contextlib.suppress(discord.NotFound):
                    await query.delete()
                return

            if not pred.result:
                if can_react:
                    with contextlib.suppress(discord.NotFound):
                        await query.delete()
                else:
                    await ctx.send(_("OK then."))
                return
            else:
                if can_react:
                    with contextlib.suppress(discord.Forbidden):
                        await query.clear_reactions()

        await ctx.invoke(ctx.bot.get_cog("Core").reload, *updated_cognames)

    def cog_name_from_instance(self, instance: object) -> str:
        """Determines the cog name that Downloader knows from the cog instance.

        Probably.

        Parameters
        ----------
        instance : object
            The cog instance.

        Returns
        -------
        str
            The name of the cog according to Downloader..

        """
        splitted = instance.__module__.split(".")
        return splitted[0]

    @commands.command()
    async def findcog(self, ctx: commands.Context, command_name: str) -> None:
        """Find which cog a command comes from.

        This will only work with loaded cogs.

        Example:
        - `[p]findcog ping`

        **Arguments**

        - `<command_name>` The command to search for.
        """
        command = ctx.bot.all_commands.get(command_name)

        if command is None:
            await ctx.send(_("That command doesn't seem to exist."))
            return

        # Check if in installed cogs
        cog = command.cog
        if cog:
            cog_pkg_name = self.cog_name_from_instance(cog)
            installed, cog_installable = await self.is_installed(cog_pkg_name)
            if installed:
                made_by = (
                    humanize_list(cog_installable.author)
                    if cog_installable.author
                    else _("Missing from info.json")
                )
                repo_url = (
                    _("Missing from installed repos")
                    if cog_installable.repo is None
                    else cog_installable.repo.clean_url
                )
                repo_name = (
                    _("Missing from installed repos")
                    if cog_installable.repo is None
                    else cog_installable.repo.name
                )
                cog_pkg_name = cog_installable.name
            elif cog.__module__.startswith("redbot."):  # core commands or core cog
                made_by = "Cog Creators"
                repo_url = "https://github.com/Cog-Creators/Red-DiscordBot"
                module_fragments = cog.__module__.split(".")
                if module_fragments[1] == "core":
                    cog_pkg_name = "N/A - Built-in commands"
                else:
                    cog_pkg_name = module_fragments[2]
                repo_name = "Red-DiscordBot"
            else:  # assume not installed via downloader
                made_by = _("Unknown")
                repo_url = _("None - this cog wasn't installed via downloader")
                repo_name = _("Unknown")
            cog_name = cog.__class__.__name__
        else:
            msg = _("This command is not provided by a cog.")
            await ctx.send(msg)
            return

        if await ctx.embed_requested():
            embed = discord.Embed(color=(await ctx.embed_colour()))
            embed.add_field(name=_("Command:"), value=command_name, inline=False)
            embed.add_field(name=_("Cog package name:"), value=cog_pkg_name, inline=True)
            embed.add_field(name=_("Cog name:"), value=cog_name, inline=True)
            embed.add_field(name=_("Made by:"), value=made_by, inline=False)
            embed.add_field(name=_("Repo name:"), value=repo_name, inline=False)
            embed.add_field(name=_("Repo URL:"), value=repo_url, inline=False)
            if installed and cog_installable.repo is not None and cog_installable.repo.branch:
                embed.add_field(
                    name=_("Repo branch:"), value=cog_installable.repo.branch, inline=False
                )
            await ctx.send(embed=embed)

        else:
            msg = _(
                "Command:          {command}\n"
                "Cog package name: {cog_pkg}\n"
                "Cog name:         {cog}\n"
                "Made by:          {author}\n"
                "Repo name:        {repo_name}\n"
                "Repo URL:         {repo_url}\n"
            ).format(
                command=command_name,
                cog_pkg=cog_pkg_name,
                cog=cog_name,
                author=made_by,
                repo_url=repo_url,
                repo_name=repo_name,
            )
            if installed and cog_installable.repo is not None and cog_installable.repo.branch:
                msg += _("Repo branch: {branch_name}\n").format(
                    branch_name=cog_installable.repo.branch
                )
            await ctx.send(box(msg))

    @staticmethod
    def format_failed_repos(failed: Collection[str]) -> str:
        """Format collection of ``Repo.name``'s into failed message.

        Parameters
        ----------
        failed : Collection
            Collection of ``Repo.name``

        Returns
        -------
        str
            formatted message
        """

        message = (
            _("Failed to update the following repositories:")
            if len(failed) > 1
            else _("Failed to update the following repository:")
        )
        message += " " + humanize_list(tuple(map(inline, failed))) + "\n"
        message += _(
            "The repository's branch might have been removed or"
            " the repository is no longer accessible at set url."
            " See logs for more information."
        )
        return message
