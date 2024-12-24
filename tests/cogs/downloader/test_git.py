from pathlib import Path
import subprocess as sp

import pytest

from redbot.cogs.downloader.repo_manager import ProcessFormatter, Repo
from redbot.pytest.downloader import (
    GIT_VERSION,
    cloned_git_repo,
    git_repo,
    git_repo_with_remote,
    _session_git_repo,
)


async def test_git_clone_nobranch(git_repo, tmp_path):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_CLONE_NO_BRANCH,
            url=git_repo.folder_path,
            folder=tmp_path / "cloned_repo_test",
        )
    )
    assert p.returncode == 0


async def test_git_clone_branch(git_repo, tmp_path):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_CLONE,
            branch="master",
            url=git_repo.folder_path,
            folder=tmp_path / "cloned_repo_test",
        )
    )
    assert p.returncode == 0


async def test_git_clone_non_existent_branch(git_repo, tmp_path):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_CLONE,
            branch="non-existent-branch",
            url=git_repo.folder_path,
            folder=tmp_path / "cloned_repo_test",
        )
    )
    assert p.returncode == 128


async def test_git_clone_notgit_repo(git_repo, tmp_path):
    notgit_repo = tmp_path / "test_clone_folder"
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_CLONE, branch=None, url=notgit_repo, folder=tmp_path / "cloned_repo_test"
        )
    )
    assert p.returncode == 128


async def test_git_current_branch_master(git_repo):
    p = await git_repo._run(
        ProcessFormatter().format(git_repo.GIT_CURRENT_BRANCH, path=git_repo.folder_path)
    )
    assert p.returncode == 0
    assert p.stdout.decode().strip() == "master"


async def test_git_current_branch_detached(git_repo):
    await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_CHECKOUT,
            path=git_repo.folder_path,
            rev="c950fc05a540dd76b944719c2a3302da2e2f3090",
        )
    )
    p = await git_repo._run(
        ProcessFormatter().format(git_repo.GIT_CURRENT_BRANCH, path=git_repo.folder_path)
    )
    assert p.returncode == 128
    assert p.stderr.decode().strip() == "fatal: ref HEAD is not a symbolic ref"


async def test_git_current_commit_on_branch(git_repo):
    # HEAD on dont_add_commits (a0ccc2390883c85a361f5a90c72e1b07958939fa)
    # setup
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_CHECKOUT, path=git_repo.folder_path, rev="dont_add_commits"
        )
    )
    assert p.returncode == 0

    p = await git_repo._run(
        ProcessFormatter().format(git_repo.GIT_CURRENT_COMMIT, path=git_repo.folder_path)
    )
    assert p.returncode == 0
    assert p.stdout.decode().strip() == "a0ccc2390883c85a361f5a90c72e1b07958939fa"


async def test_git_current_commit_detached(git_repo):
    # detached HEAD state (c950fc05a540dd76b944719c2a3302da2e2f3090)
    await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_CHECKOUT,
            path=git_repo.folder_path,
            rev="c950fc05a540dd76b944719c2a3302da2e2f3090",
        )
    )
    p = await git_repo._run(
        ProcessFormatter().format(git_repo.GIT_CURRENT_COMMIT, path=git_repo.folder_path)
    )
    assert p.returncode == 0
    assert p.stdout.decode().strip() == "c950fc05a540dd76b944719c2a3302da2e2f3090"


async def test_git_latest_commit(git_repo):
    # HEAD on dont_add_commits (a0ccc2390883c85a361f5a90c72e1b07958939fa)
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_LATEST_COMMIT, path=git_repo.folder_path, branch="dont_add_commits"
        )
    )
    assert p.returncode == 0
    assert p.stdout.decode().strip() == "a0ccc2390883c85a361f5a90c72e1b07958939fa"


async def test_git_hard_reset(cloned_git_repo, tmp_path):
    staged_file = cloned_git_repo.folder_path / "staged_file.txt"
    staged_file.touch()
    git_dirparams = ("git", "-C", str(cloned_git_repo.folder_path))
    sp.run((*git_dirparams, "add", "staged_file.txt"), check=True)
    assert staged_file.exists() is True
    p = await cloned_git_repo._run(
        ProcessFormatter().format(
            cloned_git_repo.GIT_HARD_RESET, path=cloned_git_repo.folder_path, branch="master"
        )
    )
    assert p.returncode == 0
    assert staged_file.exists() is False


async def test_git_pull(git_repo_with_remote, tmp_path):
    # setup
    staged_file = Path(git_repo_with_remote.url) / "staged_file.txt"
    staged_file.touch()
    git_dirparams = ("git", "-C", git_repo_with_remote.url)
    sp.run((*git_dirparams, "add", "staged_file.txt"), check=True)
    sp.run(
        (*git_dirparams, "commit", "-m", "test commit", "--no-gpg-sign", "--no-verify"), check=True
    )
    assert not (git_repo_with_remote.folder_path / "staged_file.txt").exists()

    p = await git_repo_with_remote._run(
        ProcessFormatter().format(
            git_repo_with_remote.GIT_PULL, path=git_repo_with_remote.folder_path
        )
    )
    assert p.returncode == 0
    assert (git_repo_with_remote.folder_path / "staged_file.txt").exists()


async def test_git_diff_file_status(git_repo):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_DIFF_FILE_STATUS,
            path=git_repo.folder_path,
            old_rev="c950fc05a540dd76b944719c2a3302da2e2f3090",
            new_rev="fb99eb7d2d5bed514efc98fe6686b368f8425745",
        )
    )
    assert p.returncode == 0
    stdout = p.stdout.strip(b"\t\n\x00 ").decode()
    assert stdout == (
        "A\x00added_file.txt\x00\t"
        "M\x00mycog/__init__.py\x00\t"
        "D\x00sample_file1.txt\x00\t"
        "D\x00sample_file2.txt\x00\t"
        "A\x00sample_file3.txt"
    )


# might need to add test for test_git_log, but it's unused method currently


async def test_git_discover_remote_url(cloned_git_repo, tmp_path):
    p = await cloned_git_repo._run(
        ProcessFormatter().format(
            cloned_git_repo.GIT_DISCOVER_REMOTE_URL, path=cloned_git_repo.folder_path
        )
    )
    assert p.returncode == 0
    assert p.stdout.decode().strip() == cloned_git_repo.url


async def test_git_checkout_detached_head(git_repo):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_CHECKOUT,
            path=git_repo.folder_path,
            rev="c950fc05a540dd76b944719c2a3302da2e2f3090",
        )
    )
    assert p.returncode == 0


async def test_git_checkout_branch(git_repo):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_CHECKOUT, path=git_repo.folder_path, rev="dont_add_commits"
        )
    )
    assert p.returncode == 0


async def test_git_checkout_non_existent_branch(git_repo):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_CHECKOUT, path=git_repo.folder_path, rev="non-existent-branch"
        )
    )
    assert p.returncode == 1


async def test_git_get_full_sha1_from_branch_name(git_repo):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_GET_FULL_SHA1, path=git_repo.folder_path, rev="dont_add_commits"
        )
    )
    assert p.returncode == 0
    assert p.stdout.decode().strip() == "a0ccc2390883c85a361f5a90c72e1b07958939fa"


async def test_git_get_full_sha1_from_full_hash(git_repo):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_GET_FULL_SHA1,
            path=git_repo.folder_path,
            rev="c950fc05a540dd76b944719c2a3302da2e2f3090",
        )
    )
    assert p.returncode == 0
    assert p.stdout.decode().strip() == "c950fc05a540dd76b944719c2a3302da2e2f3090"


async def test_git_get_full_sha1_from_short_hash(git_repo):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_GET_FULL_SHA1, path=git_repo.folder_path, rev="c950"
        )
    )
    assert p.returncode == 0
    assert p.stdout.decode().strip() == "c950fc05a540dd76b944719c2a3302da2e2f3090"


async def test_git_get_full_sha1_from_too_short_hash(git_repo):
    p = await git_repo._run(
        ProcessFormatter().format(git_repo.GIT_GET_FULL_SHA1, path=git_repo.folder_path, rev="c95")
    )
    assert p.returncode == 128
    assert p.stderr.decode().strip() == "fatal: Needed a single revision"


async def test_git_get_full_sha1_from_lightweight_tag(git_repo):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_GET_FULL_SHA1, path=git_repo.folder_path, rev="lightweight"
        )
    )
    assert p.returncode == 0
    assert p.stdout.decode().strip() == "fb99eb7d2d5bed514efc98fe6686b368f8425745"


async def test_git_get_full_sha1_from_annotated_tag(git_repo):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_GET_FULL_SHA1, path=git_repo.folder_path, rev="annotated"
        )
    )
    assert p.returncode == 0
    assert p.stdout.decode().strip() == "a7120330cc179396914e0d6af80cfa282adc124b"


async def test_git_get_full_sha1_from_invalid_ref(git_repo):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_GET_FULL_SHA1, path=git_repo.folder_path, rev="invalid"
        )
    )
    assert p.returncode == 128
    assert p.stderr.decode().strip() == "fatal: Needed a single revision"


@pytest.mark.skipif(
    GIT_VERSION < (2, 31), reason="This is test for output from Git 2.31 and newer."
)
async def test_git_get_full_sha1_from_ambiguous_commits(git_repo):
    # 2 ambiguous refs:
    # branch ambiguous_1 - 95da0b576271cb5bee5f3e075074c03ee05fed05
    # branch ambiguous_2 - 95da0b57a416d9c8ce950554228d1fc195c30b43
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_GET_FULL_SHA1, path=git_repo.folder_path, rev="95da0b57"
        )
    )
    assert p.returncode == 128
    assert p.stderr.decode().strip() == (
        "error: short object ID 95da0b57 is ambiguous\n"
        "hint: The candidates are:\n"
        "hint:   95da0b576 commit 2019-10-22 - Ambiguous commit 16955\n"
        "hint:   95da0b57a commit 2019-10-22 - Ambiguous commit 44414\n"
        "fatal: Needed a single revision"
    )


@pytest.mark.skipif(
    GIT_VERSION < (2, 36), reason="This is test for output from Git 2.36 and newer."
)
async def test_git_get_full_sha1_from_ambiguous_tag_and_commit(git_repo):
    # 2 ambiguous refs:
    # branch ambiguous_with_tag - c6f0e5ec04d99bdf8c6c78ff20d66d286eecb3ea
    # tag ambiguous_tag_66387 - c6f0e5ec04d99bdf8c6c78ff20d66d286eecb3ea
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_GET_FULL_SHA1, path=git_repo.folder_path, rev="c6f0"
        )
    )
    assert p.returncode == 128
    assert p.stderr.decode().strip() == (
        "error: short object ID c6f0 is ambiguous\n"
        "hint: The candidates are:\n"
        "hint:   c6f028f tag 2019-10-24 - ambiguous_tag_66387\n"
        "hint:   c6f0e5e commit 2019-10-24 - Commit ambiguous with tag.\n"
        "fatal: Needed a single revision"
    )


@pytest.mark.skipif(
    not ((2, 31) <= GIT_VERSION < (2, 36)), reason="This is test for output from Git >=2.31,<2.36."
)
async def test_git_get_full_sha1_from_ambiguous_tag_and_commit_pre_2_36(git_repo):
    # 2 ambiguous refs:
    # branch ambiguous_with_tag - c6f0e5ec04d99bdf8c6c78ff20d66d286eecb3ea
    # tag ambiguous_tag_66387 - c6f0e5ec04d99bdf8c6c78ff20d66d286eecb3ea
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_GET_FULL_SHA1, path=git_repo.folder_path, rev="c6f0"
        )
    )
    assert p.returncode == 128
    assert p.stderr.decode().strip() == (
        "error: short object ID c6f0 is ambiguous\n"
        "hint: The candidates are:\n"
        "hint:   c6f028f tag ambiguous_tag_66387\n"
        "hint:   c6f0e5e commit 2019-10-24 - Commit ambiguous with tag.\n"
        "fatal: Needed a single revision"
    )


@pytest.mark.skipif(
    GIT_VERSION >= (2, 31), reason="This is test for output from Git older than 2.31."
)
async def test_git_get_full_sha1_from_ambiguous_commits_pre_2_31(git_repo):
    # 2 ambiguous refs:
    # branch ambiguous_1 - 95da0b576271cb5bee5f3e075074c03ee05fed05
    # branch ambiguous_2 - 95da0b57a416d9c8ce950554228d1fc195c30b43
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_GET_FULL_SHA1, path=git_repo.folder_path, rev="95da0b57"
        )
    )
    assert p.returncode == 128
    assert p.stderr.decode().strip() == (
        "error: short SHA1 95da0b57 is ambiguous\n"
        "hint: The candidates are:\n"
        "hint:   95da0b576 commit 2019-10-22 - Ambiguous commit 16955\n"
        "hint:   95da0b57a commit 2019-10-22 - Ambiguous commit 44414\n"
        "fatal: Needed a single revision"
    )


@pytest.mark.skipif(
    GIT_VERSION >= (2, 31), reason="This is test for output from Git older than 2.31."
)
async def test_git_get_full_sha1_from_ambiguous_tag_and_commit_pre_2_31(git_repo):
    # 2 ambiguous refs:
    # branch ambiguous_with_tag - c6f0e5ec04d99bdf8c6c78ff20d66d286eecb3ea
    # tag ambiguous_tag_66387 - c6f0e5ec04d99bdf8c6c78ff20d66d286eecb3ea
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_GET_FULL_SHA1, path=git_repo.folder_path, rev="c6f0"
        )
    )
    assert p.returncode == 128
    assert p.stderr.decode().strip() == (
        "error: short SHA1 c6f0 is ambiguous\n"
        "hint: The candidates are:\n"
        "hint:   c6f028f tag ambiguous_tag_66387\n"
        "hint:   c6f0e5e commit 2019-10-24 - Commit ambiguous with tag.\n"
        "fatal: Needed a single revision"
    )


async def test_git_is_ancestor_true(git_repo):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_IS_ANCESTOR,
            path=git_repo.folder_path,
            maybe_ancestor_rev="c950fc05a540dd76b944719c2a3302da2e2f3090",
            descendant_rev="fb99eb7d2d5bed514efc98fe6686b368f8425745",
        )
    )
    assert p.returncode == 0


async def test_git_is_ancestor_false(git_repo):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_IS_ANCESTOR,
            path=git_repo.folder_path,
            maybe_ancestor_rev="fb99eb7d2d5bed514efc98fe6686b368f8425745",
            descendant_rev="c950fc05a540dd76b944719c2a3302da2e2f3090",
        )
    )
    assert p.returncode == 1


async def test_git_is_ancestor_invalid_object(git_repo):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_IS_ANCESTOR,
            path=git_repo.folder_path,
            maybe_ancestor_rev="invalid1",
            descendant_rev="invalid2",
        )
    )
    assert p.returncode == 128
    assert p.stderr.decode().strip() == "fatal: Not a valid object name invalid1"


async def test_git_is_ancestor_invalid_commit(git_repo):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_IS_ANCESTOR,
            path=git_repo.folder_path,
            maybe_ancestor_rev="0123456789abcde0123456789abcde0123456789",
            descendant_rev="c950fc05a540dd76b944719c2a3302da2e2f3090",
        )
    )
    assert p.returncode == 128
    assert p.stderr.decode().strip() == (
        "fatal: Not a valid commit name 0123456789abcde0123456789abcde0123456789"
    )


async def test_git_check_if_module_exists_true(git_repo):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_CHECK_IF_MODULE_EXISTS,
            path=git_repo.folder_path,
            rev="fb99eb7d2d5bed514efc98fe6686b368f8425745",
            module_name="mycog",
        )
    )
    assert p.returncode == 0


@pytest.mark.skipif(
    GIT_VERSION < (2, 36), reason="This is test for output from Git 2.36 and newer."
)
async def test_git_check_if_module_exists_false(git_repo):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_CHECK_IF_MODULE_EXISTS,
            path=git_repo.folder_path,
            rev="a7120330cc179396914e0d6af80cfa282adc124b",
            module_name="mycog",
        )
    )
    assert p.returncode == 128
    assert p.stderr.decode().strip() == (
        "fatal: path 'mycog/__init__.py' does not exist in 'a7120330cc179396914e0d6af80cfa282adc124b'"
    )


@pytest.mark.skipif(
    GIT_VERSION >= (2, 36), reason="This is test for output from Git older than 2.31."
)
async def test_git_check_if_module_exists_false_pre_2_36(git_repo):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_CHECK_IF_MODULE_EXISTS,
            path=git_repo.folder_path,
            rev="a7120330cc179396914e0d6af80cfa282adc124b",
            module_name="mycog",
        )
    )
    assert p.returncode == 128
    assert p.stderr.decode().strip() == (
        "fatal: Not a valid object name a7120330cc179396914e0d6af80cfa282adc124b:mycog/__init__.py"
    )


async def test_git_find_last_occurrence_existent(git_repo):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_GET_LAST_MODULE_OCCURRENCE_COMMIT,
            path=git_repo.folder_path,
            descendant_rev="2db662c1d341b1db7d225ccc1af4019ba5228c70",
            module_name="mycog",
        )
    )
    assert p.returncode == 0
    # the command gives a commit after last occurrence
    assert p.stdout.decode().strip() == "a7120330cc179396914e0d6af80cfa282adc124b"


async def test_git_find_last_occurrence_non_existent(git_repo):
    p = await git_repo._run(
        ProcessFormatter().format(
            git_repo.GIT_GET_LAST_MODULE_OCCURRENCE_COMMIT,
            path=git_repo.folder_path,
            descendant_rev="c950fc05a540dd76b944719c2a3302da2e2f3090",
            module_name="mycog",
        )
    )
    assert p.returncode == 0
    assert p.stdout.decode().strip() == ""
