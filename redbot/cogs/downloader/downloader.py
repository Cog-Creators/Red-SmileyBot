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
from redbot.core import checks, commands, Config, version_info as red_version_info
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.i18n import Translator, cog_i18n
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
    " which are marked for removal in Red 3.4: {repo_list}.\n"
    " You should inform maintainers of these repos about this message."
)


@cog_i18n(_)
class Downloader(commands.Cog):
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

    def create_init_task(self):
        def _done_callback(task: asyncio.Task) -> None:
            exc = task.exception()
            if exc is not None:
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
        # remove in Red 3.4
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
            if module.repo.commit != module.commit and await module.repo.is_ancestor(
                module.commit, module.repo.commit
            ):
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

    @commands.command()
    @checks.is_owner()
    async def pipinstall(self, ctx: commands.Context, *deps: str) -> None:
        """Install a group of dependencies using pip."""
        if not deps:
            await ctx.send_help()
            return
        repo = Repo("", "", "", "", Path.cwd())
        async with ctx.typing():
            success = await repo.install_raw_requirements(deps, self.LIB_PATH)

        if success:
            await ctx.send(_("Libraries installed."))
        else:
            await ctx.send(
                _(
                    "Some libraries failed to install. Please check"
                    " your logs for a complete list."
                )
            )

    @commands.group()
    @checks.is_owner()
    async def repo(self, ctx: commands.Context) -> None:
        """Repo management commands."""
        pass

    @repo.command(name="add")
    async def _repo_add(
        self, ctx: commands.Context, name: str, repo_url: str, branch: str = None
    ) -> None:
        """Add a new repo.

        Repo names can only contain characters A-z, numbers, underscores, and hyphens.
        The branch will be the default branch if not specified.
        """
        agreed = await do_install_agreement(ctx)
        if not agreed:
            return
        if re.match(r"^[a-zA-Z0-9_\-]*$", name) is None:
            await ctx.send(
                _("Repo names can only contain characters A-z, numbers, underscores, and hyphens.")
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
                "Something went wrong trying to add repo %s under name %s", repo_url, name,
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
                await ctx.send(repo.install_msg.replace("[p]", ctx.clean_prefix))

    @repo.command(name="delete", aliases=["remove", "del"], usage="<repo_name>")
    async def _repo_del(self, ctx: commands.Context, repo: Repo) -> None:
        """Remove a repo and its files."""
        await self._repo_manager.delete_repo(repo.name)

        await ctx.send(
            _("The repo `{repo.name}` has been deleted successfully.").format(repo=repo)
        )

    @repo.command(name="list")
    async def _repo_list(self, ctx: commands.Context) -> None:
        """List all installed repos."""
        repos = self._repo_manager.repos
        sorted_repos = sorted(repos, key=lambda r: str.lower(r.name))
        if len(repos) == 0:
            joined = _("There is no repo installed.")
        else:
            if len(repos) > 1:
                joined = _("Installed Repos:\n\n")
            else:
                joined = _("Installed Repo:\n\n")
        for repo in sorted_repos:
            joined += "+ {}: {}\n".format(repo.name, repo.short or "")

        for page in pagify(joined, ["\n"], shorten_by=16):
            await ctx.send(box(page.lstrip(" "), lang="diff"))

    @repo.command(name="info", usage="<repo_name>")
    async def _repo_info(self, ctx: commands.Context, repo: Repo) -> None:
        """Show information about a repo."""
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
        """Update all repos, or ones of your choosing."""
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
    @checks.is_owner()
    async def cog(self, ctx: commands.Context) -> None:
        """Cog installation management commands."""
        pass

    @cog.command(name="reinstallreqs")
    async def _cog_reinstallreqs(self, ctx: commands.Context) -> None:
        """
        This command will reinstall cog requirements and shared libraries for all installed cogs.

        Red might ask user to use this when it clears contents of lib folder
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
            message += _("Failed to install requirements: ") + humanize_list(
                tuple(map(inline, failed_reqs))
            )
        if all_failed_libs:
            libnames = [lib.name for lib in failed_libs]
            message += _("\nFailed to install shared libraries: ") + humanize_list(
                tuple(map(inline, libnames))
            )
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

    @cog.command(name="install", usage="<repo_name> <cogs>")
    async def _cog_install(self, ctx: commands.Context, repo: Repo, *cog_names: str) -> None:
        """Install a cog from the given repo."""
        await self._cog_installrev(ctx, repo, None, cog_names)

    @cog.command(name="installversion", usage="<repo_name> <revision> <cogs>")
    async def _cog_installversion(
        self, ctx: commands.Context, repo: Repo, rev: str, *cog_names: str
    ) -> None:
        """Install a cog from the specified revision of given repo."""
        await self._cog_installrev(ctx, repo, rev, cog_names)

    async def _cog_installrev(
        self, ctx: commands.Context, repo: Repo, rev: Optional[str], cog_names: Iterable[str]
    ) -> None:
        if not cog_names:
            await ctx.send_help()
            return
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
                    message += _("\nFailed to install requirements: ") + humanize_list(
                        tuple(map(inline, failed_reqs))
                    )
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
                    _("\nFailed to install shared libraries for `{repo.name}` repo: ").format(
                        repo=repo
                    )
                    + humanize_list(libnames)
                    + message
                )
            if failed_cogs:
                cognames = [inline(cog.name) for cog in failed_cogs]
                message = _("\nFailed to install cogs: ") + humanize_list(cognames) + message
            if installed_cogs:
                cognames = [inline(cog.name) for cog in installed_cogs]
                message = (
                    _("Successfully installed cogs: ")
                    + humanize_list(cognames)
                    + (
                        _(
                            "\nThese cogs are now pinned and won't get updated automatically."
                            " To change this, use `{prefix}cog unpin <cog>`"
                        ).format(prefix=ctx.clean_prefix)
                        if rev is not None
                        else ""
                    )
                    + _("\nYou can load them using `{prefix}load <cogs>`").format(
                        prefix=ctx.clean_prefix
                    )
                    + message
                )
        # "---" added to separate cog install messages from Downloader's message
        await self.send_pagified(ctx, f"{message}{deprecation_notice}\n---")
        for cog in installed_cogs:
            if cog.install_msg:
                await ctx.send(cog.install_msg.replace("[p]", ctx.clean_prefix))

    @cog.command(name="uninstall", usage="<cogs>")
    async def _cog_uninstall(self, ctx: commands.Context, *cogs: InstalledCog) -> None:
        """Uninstall cogs.

        You may only uninstall cogs which were previously installed
        by Downloader.
        """
        if not cogs:
            await ctx.send_help()
            return
        async with ctx.typing():
            uninstalled_cogs = []
            failed_cogs = []
            for cog in set(cogs):
                real_name = cog.name

                poss_installed_path = (await self.cog_install_path()) / real_name
                if poss_installed_path.exists():
                    with contextlib.suppress(commands.ExtensionNotLoaded):
                        ctx.bot.unload_extension(real_name)
                        await ctx.bot.remove_loaded_package(real_name)
                    await self._delete_cog(poss_installed_path)
                    uninstalled_cogs.append(inline(real_name))
                else:
                    failed_cogs.append(real_name)
            await self._remove_from_installed(cogs)

            message = ""
            if uninstalled_cogs:
                if len(uninstalled_cogs) > 1:
                    message += _("Successfully uninstalled cogs: ") + humanize_list(
                        uninstalled_cogs
                    )
                else:
                    message += _("Successfully uninstalled cog ") + uninstalled_cogs[0]
            if failed_cogs:
                if len(failed_cogs) > 1:
                    message += (
                        _(
                            "\nDownloader has removed these cogs from the installed cogs list"
                            " but it wasn't able to find their files: "
                        )
                        + humanize_list(tuple(map(inline, failed_cogs)))
                        + _(
                            "\nThey were most likely removed without using `{prefix}cog uninstall`.\n"
                            "You may need to remove those files manually if the cogs are still usable."
                            " If so, ensure the cogs have been unloaded with `{prefix}unload {cogs}`."
                        ).format(prefix=ctx.clean_prefix, cogs=" ".join(failed_cogs))
                    )
                else:
                    message += _(
                        "\nDownloader has removed the cog {cog} from the installed cogs list"
                        " but it wasn't able to find his files."
                    ).format(cog=inline(failed_cogs[0])) + _(
                        "\nIt was most likely removed without using `{prefix}cog uninstall`.\n"
                        "You may need to remove those files manually if the cog are still usable."
                        " If so, ensure the cog have been unloaded with `{prefix}unload {cog}`."
                    ).format(
                        prefix=ctx.clean_prefix, cog=failed_cogs[0]
                    )
        await self.send_pagified(ctx, message)

    @cog.command(name="pin", usage="<cogs>")
    async def _cog_pin(self, ctx: commands.Context, *cogs: InstalledCog) -> None:
        """Pin cogs - this will lock cogs on their current version."""
        if not cogs:
            await ctx.send_help()
            return
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
            if len(pinned) > 1:
                message += _("Pinned cogs: ")
            else:
                message += _("Pinned {cog}").format(cognames[0])
        if already_pinned:
            if len(already_pinned) > 1:
                message += _("\nThese cogs were already pinned: ") + humanize_list(already_pinned)
            else:
                message += _("\n{cog} was already pinned.").format(cog=already_pinned[0])
        await self.send_pagified(ctx, message)

    @cog.command(name="unpin", usage="<cogs>")
    async def _cog_unpin(self, ctx: commands.Context, *cogs: InstalledCog) -> None:
        """Unpin cogs - this will remove update lock from cogs."""
        if not cogs:
            await ctx.send_help()
            return
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
            if len(unpinned) > 1:
                message += _("Unpinned cogs: ")
            else:
                message += _("Unpinned {cog}").format(cognames[0])
        if not_pinned:
            if len(unpinned) > 1:
                message += _("\nThese cogs weren't pinned: ") + humanize_list(not_pinned)
            else:
                message += _("\n{cog} was already not pinned.").format(cog=not_pinned[0])
        await self.send_pagified(ctx, message)

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
                if len(cogs_to_update) > 1:
                    message += _("These cogs can be updated: ") + humanize_list(
                        tuple(map(inline, cognames))
                    )
                else:
                    message += _("{cog} can be updated.").format(cog=inline(cognames[0]))
            if libs_to_update:
                libnames = [cog.name for cog in libs_to_update]
                if len(libnames) > 1:
                    message += _("\nThese shared libraries can be updated: ") + humanize_list(
                        tuple(map(inline, libnames))
                    )
                else:
                    message += _("\nShared library {library} can be updated.").format(
                        library=inline(libnames[0])
                    )
            if not (cogs_to_update or libs_to_update) and filter_message:
                message += _("No cogs can be updated.")
            message += filter_message

            if not message:
                message = _("All installed cogs are up to date.")

            if failed:
                message += "\n" + self.format_failed_repos(failed)

        await self.send_pagified(ctx, message)

    @cog.command(name="update")
    async def _cog_update(self, ctx: commands.Context, *cogs: InstalledCog) -> None:
        """Update all cogs, or ones of your choosing."""
        await self._cog_update_logic(ctx, cogs=cogs)

    @cog.command(name="updateallfromrepos", usage="<repos>")
    async def _cog_updateallfromrepos(self, ctx: commands.Context, *repos: Repo) -> None:
        """Update all cogs from repos of your choosing."""
        if not repos:
            await ctx.send_help()
            return
        await self._cog_update_logic(ctx, repos=repos)

    @cog.command(name="updatetoversion", usage="<repo_name> <revision> [cogs]")
    async def _cog_updatetoversion(
        self, ctx: commands.Context, repo: Repo, rev: str, *cogs: InstalledCog
    ) -> None:
        """Update all cogs, or ones of your choosing to chosen revision of one repo.

        Note that update doesn't mean downgrade and therefore revision
        has to be newer than the one that cog currently has. If you want to
        downgrade the cog, uninstall and install it again.
        """
        await self._cog_update_logic(ctx, repo=repo, rev=rev, cogs=cogs)

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
                    message += _(
                        "\nThese cogs are pinned and therefore weren't checked: "
                    ) + humanize_list(tuple(map(inline, cognames)))
            else:
                cogs_to_update, libs_to_update = await self._available_updates(cogs_to_check)

                updates_available = cogs_to_update or libs_to_update
                cogs_to_update, filter_message = self._filter_incorrect_cogs(cogs_to_update)

                if updates_available:
                    updated_cognames, message = await self._update_cogs_and_libs(
                        cogs_to_update, libs_to_update
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
                    message += _(
                        "\nThese cogs are pinned and therefore weren't checked: "
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

    @cog.command(name="list", usage="<repo_name>")
    async def _cog_list(self, ctx: commands.Context, repo: Repo) -> None:
        """List all available cogs from a single repo."""
        available_cogs = 0
        installed = await self.installed_cogs()
        installed_str = "\n".join(
            [
                "- {}{}".format(i.name, ": {}".format(i.short) if i.short else "")
                for i in installed
                if i.repo_name == repo.name
            ]
        )
        if installed_str == "":
            installed_str = _("No cogs installed.")
        elif len(installed) > 1:
            installed_str = (
                _("Installed Cogs: ({installed_number})\n").format(installed_number=len(installed))
                + installed_str
            )
        else:
            installed_str = (
                _("Installed Cog: ({installed_number})\n").format(installed_number=len(installed))
                + installed_str
            )
        available_str = "\n".join(
            [
                "+ {}: {}".format(cog.name, cog.short or "")
                for cog in repo.available_cogs
                if not (cog.hidden or cog in installed)
            ]
        )
        for cog in repo.available_cogs:
            if not (cog.hidden or cog in installed):
                available_cogs += 1
        if available_str == "":
            cogs = _("No cogs available.")
        elif available_cogs > 1:
            cogs = (
                _("Available Cogs: ({available_number})\n").format(available_number=available_cogs)
                + available_str
            )
        else:
            cogs = (
                _("Available Cog: ({available_number})\n").format(available_number=available_cogs)
                + available_str
            )
        cogs = cogs + "\n\n" + installed_str
        for page in pagify(cogs, ["\n"], shorten_by=16):
            await ctx.send(box(page.lstrip(" "), lang="diff"))

    @cog.command(name="info", usage="<repo_name> <cog_name>")
    async def _cog_info(self, ctx: commands.Context, repo: Repo, cog_name: str) -> None:
        """List information about a single cog."""
        cog = discord.utils.get(repo.available_cogs, name=cog_name)
        if cog is None:
            await ctx.send(
                _("There is no cog `{cog_name}` in the repo `{repo.name}`").format(
                    cog_name=cog_name, repo=repo
                )
            )
            return

        msg = _(
            "Information on {cog_name}:\n{description}\n\n"
            "Made by: {author}\nRequirements: {requirements}"
        ).format(
            cog_name=cog.name,
            description=cog.description or "",
            author=", ".join(cog.author) or _("Missing from info.json"),
            requirements=", ".join(cog.requirements) or "None",
        )
        await ctx.send(box(msg))

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
            if len(unavailable_cogs) > 1:
                message += _("\nCouldn't find these cogs in {repo.name}: ").format(
                    repo=repo
                ) + humanize_list(unavailable_cogs)
            else:
                message += _("\nCouldn't find {cog} cog in {repo.name}").format(
                    cog=unavailable_cogs[0], repo=repo
                )
        if already_installed:
            if len(already_installed) > 1:
                message += _("\nThese cogs were already installed: ") + humanize_list(
                    already_installed
                )
            else:
                message += _("\n{cog} was already installed.").format(cog=already_installed[0])
        if name_already_used:
            if len(name_already_used) > 1:
                message += _(
                    "\nSome cogs with these names are already installed from different repos: "
                ) + humanize_list(name_already_used)
            else:
                message += -(
                    "Cog with name {cog} is already installed from a different repo."
                ).format(cog=name_already_used[0])
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
            if len(outdated_python_version) > 1:
                message += _(
                    "\nThese cogs require higher python version than you have: "
                ) + humanize_list(outdated_python_version)
            else:
                message += _("{cog} require higher python version than you have.").format(
                    outdated_python_version[0]
                )
        if outdated_bot_version:
            if len(outdated_bot_version) > 1:
                message += _(
                    "\nThese cogs require different Red version"
                    " than you currently have ({current_version}): "
                ).format(current_version=red_version_info) + humanize_list(outdated_bot_version)
            else:
                message += _(
                    "{cog} require different Red version than you currently "
                    "have ({current_version})"
                ).format(cog=outdated_bot_version, current_version=red_version_info)
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
        self, cogs_to_update: Iterable[Installable], libs_to_update: Iterable[Installable]
    ) -> Tuple[Set[str], str]:
        failed_reqs = await self._install_requirements(cogs_to_update)
        if failed_reqs:
            return (
                set(),
                _("Failed to install requirements: ")
                + humanize_list(tuple(map(inline, failed_reqs))),
            )
        installed_cogs, failed_cogs = await self._install_cogs(cogs_to_update)
        installed_libs, failed_libs = await self._reinstall_libraries(libs_to_update)
        await self._save_to_installed(installed_cogs + installed_libs)
        message = _("Cog update completed successfully.")

        updated_cognames: Set[str] = set()
        if installed_cogs:
            updated_cognames = {cog.name for cog in installed_cogs}
            if len(installed_cogs) > 1:
                message += _("\nUpdated: ") + humanize_list(tuple(map(inline, updated_cognames)))
            else:
                message += _("\n{cog} updated.").format(
                    cog=humanize_list(tuple(map(inline, updated_cognames)))
                )
        if failed_cogs:
            cognames = [cog.name for cog in failed_cogs]
            if len(failed_cogs) > 1:
                message += _("\nFailed to update cogs: ") + humanize_list(
                    tuple(map(inline, cognames))
                )
            else:
                message += _("\nFailed to update cog: ") + humanize_list(
                    tuple(map(inline, cognames))
                )
        if not cogs_to_update:
            message = _("No cogs were updated.")
        if installed_libs:
            if len(installed_libs) > 1:
                message += _(
                    "\nSome shared libraries were updated, you should restart the bot "
                    "to bring the changes into effect."
                )
            else:
                message += _(
                    "\nA shared library was updated, you should restart the "
                    "bot to bring the changes into effect."
                )
        if failed_libs:
            libnames = [lib.name for lib in failed_libs]
            if len(failed_cogs) > 1:
                message += _("\nFailed to install shared libraries: ") + humanize_list(
                    tuple(map(inline, libnames))
                )
            else:
                message += _("\nFailed to install shared library: ") + humanize_list(
                    tuple(map(inline, libnames))
                )
        return (updated_cognames, message)

    async def _ask_for_cog_reload(self, ctx: commands.Context, updated_cognames: Set[str]) -> None:
        updated_cognames &= ctx.bot.extensions.keys()  # only reload loaded cogs
        if not updated_cognames:
            await ctx.send(_("None of the updated cogs were previously loaded. Update complete."))
            return

        if not ctx.assume_yes:
            if len(updated_cognames) > 1:
                message = _("Would you like to reload the updated cogs?")
            else:
                message = _("Would you like to reload {cog}?").format(
                    cog=humanize_list(tuple(map(inline, updated_cognames)))
                )
            can_react = ctx.channel.permissions_for(ctx.me).add_reactions
            if not can_react:
                message += " (y/n)"
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
                await query.delete()
                return

            if not pred.result:
                if can_react:
                    await query.delete()
                else:
                    await ctx.send(_("OK then."))
                return
            else:
                if can_react:
                    with contextlib.suppress(discord.Forbidden):
                        await query.clear_reactions()

        await ctx.invoke(ctx.bot.get_cog("Core").reload, *updated_cognames)

    def format_findcog_info(
        self, command_name: str, cog_installable: Union[Installable, object] = None
    ) -> str:
        """Format a cog's info for output to discord.

        Parameters
        ----------
        command_name : str
            Name of the command which belongs to the cog.
        cog_installable : `Installable` or `object`
            Can be an `Installable` instance or a Cog instance.

        Returns
        -------
        str
            A formatted message for the user.

        """
        if isinstance(cog_installable, Installable):
            is_installable = True
            made_by = ", ".join(cog_installable.author) or _("Missing from info.json")
            repo_url = (
                _("Missing from installed repos")
                if cog_installable.repo is None
                else cog_installable.repo.clean_url
            )
            cog_name = cog_installable.name
        else:
            is_installable = False
            made_by = "26 & co."
            repo_url = "https://github.com/Cog-Creators/Red-DiscordBot"
            cog_name = cog_installable.__class__.__name__

        msg = _(
            "Command: {command}\nCog name: {cog}\nMade by: {author}\nRepo: {repo_url}\n"
        ).format(command=command_name, author=made_by, repo_url=repo_url, cog=cog_name)
        if is_installable and cog_installable.repo is not None and cog_installable.repo.branch:
            msg += _("Repo branch: {branch_name}\n").format(
                branch_name=cog_installable.repo.branch
            )

        return msg

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
        """
        command = ctx.bot.all_commands.get(command_name)

        if command is None:
            await ctx.send(_("That command doesn't seem to exist."))
            return

        # Check if in installed cogs
        cog = command.cog
        if cog:
            cog_name = self.cog_name_from_instance(cog)
            installed, cog_installable = await self.is_installed(cog_name)
            if installed:
                msg = self.format_findcog_info(command_name, cog_installable)
            else:
                # Assume it's in a base cog
                msg = self.format_findcog_info(command_name, cog)
        else:
            msg = _("This command is not provided by a cog.")

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
