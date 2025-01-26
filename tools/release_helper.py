#!/usr/bin/env python3.8
"""Script helping with making releases.

This script mostly aims to help with the changelog-related tasks but it does also guide you
through the release process steps including running the 'Prepare release' workflow.
"""
import enum
import json
import os
import pydoc
import re
import shlex
import subprocess
import time
import urllib.parse
import webbrowser
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import click
import requests
import rich
from rich.markdown import Markdown
from typing_extensions import Self


class ReleaseType(enum.Enum):
    BREAKING = 1
    STANDARD = 2
    MAINTENANCE = 3
    HOTFIX = 4

    def __str__(self) -> str:
        return f"{self.name.lower()} release"

    @classmethod
    def from_str(cls, name: str) -> Self:
        return cls[name]


class ReleaseStage(enum.IntEnum):
    WELCOME = enum.auto()
    RELEASE_INFO_SET = enum.auto()
    RELEASE_BLOCKERS_CHECKED = enum.auto()
    OPEN_PULLS_CHECKED = enum.auto()
    CHANGELOG_BRANCH_EXISTS = enum.auto()
    CHANGELOG_COMMITTED = enum.auto()
    CHANGELOG_PR_OPENED = enum.auto()
    CHANGELOG_CREATED = enum.auto()
    CHANGELOG_REVIEWED = enum.auto()
    PREPARE_RELEASE_SPAWNED = enum.auto()
    PREPARE_RELEASE_RAN = enum.auto()
    AUTOMATED_PULLS_MERGED = enum.auto()
    SHORT_LIVED_BRANCH_CREATED = enum.auto()

    @classmethod
    def from_str(cls, name: str) -> Self:
        return cls[name]


GH_FORCE_TTY_ENV = {**os.environ, "GH_FORCE_TTY": "100%"}
GET_MILESTONE_CONTRIBUTORS_QUERY = """
query getMilestoneContributors(
  $milestone: String!,
  $after: String,
  $states: [PullRequestState!],
) {
  repository(owner: "Cog-Creators", name: "Red-DiscordBot") {
    milestones(first: 1, query: $milestone) {
      nodes {
        title
        pullRequests(first: 100, after: $after, states: $states) {
          nodes {
            title
            number
            author {
              login
            }
            latestOpinionatedReviews(first: 100, writersOnly: true) {
              nodes {
                author {
                  login
                }
              }
            }
          }
          pageInfo {
            endCursor
            hasNextPage
          }
        }
      }
    }
  }
}
"""
# technically not *all* but enough for what we use it for
GET_ALL_TAG_COMMITS_QUERY = """
query getAllTagCommits {
  repository(owner: "Cog-Creators", name: "Red-DiscordBot") {
    refs(
        refPrefix: "refs/tags/"
        orderBy: {direction: DESC, field: TAG_COMMIT_DATE}
        first: 100
    ) {
      nodes {
        name
        target {
          commitResourcePath
        }
      }
    }
  }
}
"""
GET_COMMIT_HISTORY_QUERY = """
query getCommitHistory($refQualifiedName: String!, $after: String) {
  repository(owner: "Cog-Creators", name: "Red-DiscordBot") {
    ref(qualifiedName: $refQualifiedName) {
      target {
        ... on Commit {
          history(first: 100, after: $after) {
            nodes {
              oid
              abbreviatedOid
              messageHeadline
              associatedPullRequests(first: 1) {
                nodes {
                  milestone {
                    title
                  }
                }
              }
            }
            pageInfo {
              endCursor
              hasNextPage
            }
          }
        }
      }
    }
  }
}
"""
GET_LAST_ISSUE_NUMBER_QUERY = """
query getLastIssueNumber {
  repository(owner: "Cog-Creators", name: "Red-DiscordBot") {
    discussions(orderBy: {field: CREATED_AT, direction: DESC}, first: 1) {
      nodes {
        number
      }
    }
    issues(orderBy: {field: CREATED_AT, direction: DESC}, first: 1) {
      nodes {
        number
      }
    }
    pullRequests(orderBy: {field: CREATED_AT, direction: DESC}, first: 1) {
      nodes {
        number
      }
    }
  }
}
"""
GH_URL = "https://github.com/Cog-Creators/Red-DiscordBot"
LINKIFY_ISSUE_REFS_RE = re.compile(r"#(\d+)")


def get_github_token() -> str:
    return subprocess.check_output(("gh", "auth", "token"), text=True).strip()


def get_version_to_release() -> str:
    import redbot  # this needs to be imported after proper branch is checked out

    version_info = redbot.VersionInfo.from_str(redbot._VERSION)
    version_info.dev_release = None
    return str(version_info)


def check_git_dirty() -> None:
    if subprocess.check_output(("git", "status", "--porcelain")):
        raise click.ClickException(
            "Your working tree contains changes,"
            " please stash or commit them before using this command."
        )


def git_current_branch() -> str:
    branch = subprocess.check_output(("git", "branch", "--show-current"), text=True).strip()
    if not branch:
        raise click.ClickException("Could not detect current branch.")
    return branch


def git_verify_branch(release_type: ReleaseType, base_branch: str = "") -> str:
    current_branch = git_current_branch()
    if base_branch and current_branch != base_branch:
        raise click.ClickException(
            f"This release were being done from {base_branch} branch"
            " but a different branch is now checked out, aborting..."
        )
    if release_type is ReleaseType.BREAKING:
        if current_branch != "V3/develop":
            raise click.ClickException(
                f"A {release_type} must be done from V3/develop, aborting..."
            )
    if re.fullmatch(r"V3/develop|3\.\d+", current_branch) is None:
        raise click.ClickException(
            f"A {release_type} must be done from V3/develop or 3.x branch, aborting..."
        )
    return current_branch


def pause() -> None:
    click.prompt(
        "\nHit Enter to continue...\n",
        default="",
        hide_input=True,
        show_default=False,
        prompt_suffix="",
    )


def print_markdown(text: str) -> None:
    rich.print(Markdown(text))


def linkify_issue_refs_cli(text: str) -> str:
    return LINKIFY_ISSUE_REFS_RE.sub(
        "\x1b]8;;" rf"{GH_URL}/issues/\1" "\x1b\\\\" r"\g<0>" "\x1b]8;;\x1b\\\\",
        text,
    )


def linkify_issue_refs_md(text: str) -> str:
    return LINKIFY_ISSUE_REFS_RE.sub(rf"[\g<0>]({GH_URL}/issues/\1)", text)


def get_git_config_value(key: str) -> str:
    try:
        return subprocess.check_output(
            ("git", "config", "--local", "--get", f"red-release-helper.{key}"), text=True
        ).strip()
    except subprocess.CalledProcessError:
        return ""


def set_git_config_value(key: str, value: str) -> None:
    subprocess.check_call(("git", "config", "--local", f"red-release-helper.{key}", value))


def wipe_git_config_values() -> None:
    try:
        subprocess.check_output(
            ("git", "config", "--local", "--remove-section", "red-release-helper")
        )
    except subprocess.CalledProcessError:
        pass


def get_release_type() -> ReleaseType:
    return ReleaseType.from_str(get_git_config_value("release-type"))


def set_release_type(release_type: ReleaseType) -> None:
    set_git_config_value("release-type", release_type.name)


def get_base_branch() -> str:
    base_branch = get_git_config_value("base-branch")
    if not base_branch:
        raise ValueError("Base branch name for this release could not be found in git config.")
    return base_branch


def set_base_branch(base_branch: str) -> None:
    set_git_config_value("base-branch", base_branch)


def get_changelog_branch() -> str:
    changelog_branch = get_git_config_value("changelog-branch")
    if not changelog_branch:
        raise ValueError(
            "Changelog branch name for this release could not be found in git config."
        )
    return changelog_branch


def set_changelog_branch(changelog_branch: str) -> None:
    set_git_config_value("changelog-branch", changelog_branch)


def get_version() -> str:
    version = get_git_config_value("release-version")
    if not version:
        raise ValueError("Release version could not be found in git config.")
    return version


def set_version(version: str) -> None:
    set_git_config_value("release-version", version)


def get_previous_workflow_run_number() -> int:
    previous_workflow_run_number = int(get_git_config_value("previous-workflow-run-number"))
    return previous_workflow_run_number


def set_previous_workflow_run_number(run_number: int) -> None:
    set_git_config_value("previous-workflow-run-number", str(run_number))


def get_release_stage() -> ReleaseStage:
    return ReleaseStage.from_str(get_git_config_value("release-stage") or "WELCOME")


def set_release_stage(stage: ReleaseStage) -> None:
    return set_git_config_value("release-stage", stage.name)


@click.group(invoke_without_command=True)
@click.option("--continue", "abort", flag_value=False, default=None)
@click.option("--abort", "abort", flag_value=True, default=None)
@click.pass_context
def cli(ctx: click.Context, *, abort: Optional[bool] = None):
    """Red's release helper, guiding you through the whole process!"""
    if ctx.invoked_subcommand is not None:
        return
    stage = get_release_stage()
    if abort is True:
        if stage is not ReleaseStage.WELCOME:
            wipe_git_config_values()
            rich.print("Cleaned the pending release.")
        else:
            rich.print("Nothing to do - there's no pending release.")
        return
    if stage is not ReleaseStage.WELCOME and abort is not False:
        raise click.ClickException(
            "It seems that there is a release in progress. You can continue the process with"
            " `--continue` flag or abort it with `--abort` flag."
        )
    if stage <= ReleaseStage.WELCOME:
        check_git_dirty()
    rich.print(
        "Welcome to Red's release helper!\n"
        "--------------------------------\n"
        "I'll be guiding you through most of the process to make it as easy as possible.\n"
        "You can find the release process documentation here:"
        " https://red-devguide.readthedocs.io/core-devs/release-process/\n"
    )
    if stage < ReleaseStage.RELEASE_INFO_SET:
        print_markdown(
            "1. Breaking release (`3.x+1.0`)\n\n"
            "   Release with breaking changes, done from `V3/develop`.\n"
            "2. Standard release (`3.x.y+1`)\n\n"
            "   Release without breaking changes that may contain both features and bugfixes.\n"
            "   This is done from `V3/develop` or `3.x` branch"
            " if a breaking release is currently in development.\n"
            "3. Maintenance release (`3.x.y+1`)\n\n"
            "   Release without breaking changes that only contains cherry-picked enhancements"
            " and bugfixes.\n"
            "   Quite similar to a standard release but it is done from a short-lived release"
            " branch using the tag of a previous version as a base.\n"
            "4. Hotfix release (`3.x.y+1`)\n\n"
            "   Release that is meant to quickly patch one of the currently supported releases"
            " (usually it is just the latest).\n"
            "   This is done from a short-lived release branch using the tag of"
            " a previous version as a base, or from `V3/develop`/`3.x`"
            " if it doesn’t contain any meaningful code changes yet."
        )
        release_type = ReleaseType(
            int(
                click.prompt(
                    "\nWhat kind of release is this?", type=click.Choice(["1", "2", "3", "4"])
                )
            )
        )
        set_base_branch(git_verify_branch(release_type))
        set_release_type(release_type)
        version = get_version_to_release()
        if not click.confirm(f"The version you want to release is {version}, is that correct?"):
            raise click.ClickException(
                "Please check out the branch that you want to release from"
                " and start this program again."
            )
        set_version(version)
        set_release_stage(ReleaseStage.RELEASE_INFO_SET)
    else:
        release_type = get_release_type()
        version = get_version()

    rich.print("Alright, let's do this!\n")

    for step in STEPS:
        step(release_type, version)

    rich.print(Markdown("# Step 8+: Follow the release process documentation"))
    rich.print(
        "You can continue following the release process documentation from step 8:\n"
        "https://red-devguide.readthedocs.io/core-devs/release-process/#write-announcement"
    )
    wipe_git_config_values()


def ensure_no_release_blockers(release_type: ReleaseType, version: str) -> None:
    rich.print(Markdown("# Step 1: Ensure there are no release blockers"))
    if get_release_stage() >= ReleaseStage.RELEASE_BLOCKERS_CHECKED:
        rich.print(":white_check_mark: Already done!")
        return
    if release_type is ReleaseType.HOTFIX:
        rich.print(
            Markdown(
                "You can *generally* skip this. Might still be worth checking in case there is"
                " some blocker related to the release workflow that could potentially affect you."
            )
        )
    else:
        rich.print(
            "Look at the milestone for the next release and check if there are any"
            " Release Blockers (labelled as 'Release Blocker' on the issue tracker)"
            " that need to be handled before the release."
        )

    output = subprocess.check_output(
        (
            "gh",
            "pr",
            "list",
            "--json=number,title,state",
            "--template",
            "{{if .}}"
            '{{tablerow "NUMBER" "STATE" "TITLE"}}{{range .}}'
            '{{tablerow (printf "#%v" .number) .state .title}}{{end}}{{tablerender}}'
            "{{end}}",
            "--limit=999",
            "--state=all",
            "--search",
            f'milestone:{version} label:"Release Blocker"',
        ),
        text=True,
    )

    rich.print(Markdown("\n## List of release blockers"))
    if output:
        print(linkify_issue_refs_cli(output))
    else:
        rich.print("There are no release blockers in current milestone.")
    pause()
    set_release_stage(ReleaseStage.RELEASE_BLOCKERS_CHECKED)


def check_state_of_open_pulls(release_type: ReleaseType, version: str) -> None:
    rich.print(Markdown("# Step 2: Check state of all open pull requests for this milestone"))
    if get_release_stage() >= ReleaseStage.OPEN_PULLS_CHECKED:
        rich.print(":white_check_mark: Already done!")
        return
    if release_type is ReleaseType.HOTFIX:
        rich.print(
            "This is a hotfix release, you should focus on getting the critical fix out,"
            " the other PRs should not be important. However, you should still update"
            " the milestone to make your and others’ job easier later."
        )
    else:
        rich.print(
            Markdown(
                "Decide which PRs should be kept for the release, cooperate with another org member(s)"
                " on this. Move any pull requests not targeted for release to a new milestone with"
                " name of the release that should come after current one."
            )
        )

    output = subprocess.check_output(
        (
            "gh",
            "pr",
            "list",
            "--json=number,title,state",
            "--template",
            "{{if .}}"
            '{{tablerow "NUMBER" "STATE" "TITLE"}}{{range .}}'
            '{{tablerow (printf "#%v" .number) .state .title}}{{end}}{{tablerender}}'
            "{{end}}",
            "--limit=999",
            "--search",
            f"milestone:{version}",
        ),
        text=True,
    )

    rich.print(Markdown(f"\n## Open pull requests in milestone {version}"))
    if output:
        print(linkify_issue_refs_cli(output))
    else:
        rich.print("There are no open pull requests left.")

    pause()
    set_release_stage(ReleaseStage.OPEN_PULLS_CHECKED)


def create_changelog(release_type: ReleaseType, version: str) -> None:
    rich.print(Markdown("# Step 3: Create changelog PR"))
    if get_release_stage() >= ReleaseStage.CHANGELOG_CREATED:
        rich.print(":white_check_mark: Already done!")
        return
    rich.print(
        Markdown(
            "The changelog PR should always be merged into `V3/develop`."
            " You should remember to later cherry-pick/backport it to a proper branch"
            " if you’re not making a release from `V3/develop`."
        )
    )
    if release_type is ReleaseType.HOTFIX:
        rich.print(
            "Hotfix releases [bold]need to[/] contain a changelog.\n"
            "It can be limited to a short description of what the hotfix release fixes,"
            " for example see:"
            " [link=https://docs.discord.red/en/stable/changelog.html#redbot-3-4-12-2021-06-17]"
            "Red 3.4.12 changelog"
            "[/]"
        )
    else:
        rich.print("Time for a changelog!")

    rich.print(
        "Do you have a [bold]finished[/] changelog already?"
        " This should include the contributor list.",
        end="",
    )
    if click.confirm(""):
        set_release_stage(ReleaseStage.CHANGELOG_CREATED)
        return
    rich.print()
    if get_release_stage() >= ReleaseStage.CHANGELOG_BRANCH_EXISTS:
        changelog_branch = get_changelog_branch()
        subprocess.check_call(("git", "checkout", changelog_branch))
    else:
        changelog_branch = f"V3/changelogs/{version}"
        subprocess.check_call(("git", "fetch", GH_URL))
        try:
            subprocess.check_call(("git", "checkout", "-b", changelog_branch, "FETCH_HEAD"))
        except subprocess.CalledProcessError:
            rich.print()
            if click.confirm(
                f"It seems that {changelog_branch} branch already exists, do you want to use it?"
            ):
                subprocess.check_call(("git", "checkout", changelog_branch))
            elif not click.confirm("Do you want to use a different branch?"):
                raise click.ClickException("Can't continue without a changelog branch...")
            elif click.confirm("Do you want to create a new branch?"):
                while True:
                    changelog_branch = click.prompt("Input the name of the new branch")
                    try:
                        subprocess.check_call(
                            ("git", "checkout", "-b", changelog_branch, "FETCH_HEAD")
                        )
                    except subprocess.CalledProcessError:
                        continue
                    else:
                        break
            else:
                while True:
                    changelog_branch = click.prompt("Input the name of the branch to check out")
                    try:
                        subprocess.check_call(("git", "checkout", changelog_branch))
                    except subprocess.CalledProcessError:
                        continue
                    else:
                        break

        set_changelog_branch(changelog_branch)
        set_release_stage(ReleaseStage.CHANGELOG_BRANCH_EXISTS)

    title = f"Red {version} - Changelog"
    commands = [
        ("git", "add", "."),
        ("git", "commit", "-m", title),
        ("git", "push", "-u", GH_URL, f"{changelog_branch}:{changelog_branch}"),
    ]
    if get_release_stage() < ReleaseStage.CHANGELOG_COMMITTED:
        rich.print(
            "\n:pencil: At this point, you should have an up-to-date milestone"
            " containing all PRs that are contained in this release. If you're not sure if all PRs"
            " are properly assigned, you might find output of the option 1 below helpful."
        )
        while True:
            rich.print(
                Markdown(
                    "1. Show unreleased commits without a milestone.\n"
                    "2. View detailed information about all issues and PRs in the milestone.\n"
                    "3. Get contributor list formatted for the changelog.\n"
                    "4. Continue."
                )
            )
            option = click.prompt("Select option", type=click.Choice(["1", "2", "3", "4"]))
            if option == "1":
                show_unreleased_commits(version, get_base_branch())
                continue
            if option == "2":
                view_milestone_issues(version)
                continue
            if option == "3":
                get_contributors(version)
                continue
            if option == "4":
                break

        print(
            "Do you want to commit everything from repo's working tree and push it?"
            " The following commands will run:"
        )
        for command in commands:
            print(shlex.join(command))
        if click.confirm("Do you want to run above commands to open a new changelog PR?"):
            subprocess.check_call(commands[0])
            subprocess.check_call(commands[1])
            set_release_stage(ReleaseStage.CHANGELOG_COMMITTED)
        else:
            print("Okay, please open a changelog PR manually then.")
    if get_release_stage() is ReleaseStage.CHANGELOG_COMMITTED:
        token = get_github_token()
        resp = requests.post(
            "https://api.github.com/graphql",
            json={"query": GET_LAST_ISSUE_NUMBER_QUERY},
            headers={"Authorization": f"Bearer {token}"},
        )
        next_issue_number = (
            max(
                next(iter(data["nodes"]), {"number": 0})["number"]
                for data in resp.json()["data"]["repository"].values()
            )
            + 1
        )
        docs_preview_url = (
            f"https://red-discordbot--{next_issue_number}.org.readthedocs.build"
            f"/en/{next_issue_number}/changelog.html"
        )
        subprocess.check_call(commands[2])
        query = {
            "expand": "1",
            "milestone": version,
            "labels": "Type: Feature,Changelog Entry: Skipped",
            "title": title,
            "body": (
                "### Description of the changes\n\n"
                f"The PR for Red {version} changelog.\n\n"
                f"Docs preview: {docs_preview_url}"
            ),
        }
        pr_url = (
            f"{GH_URL}/compare/V3/develop...{changelog_branch}?{urllib.parse.urlencode(query)}"
        )
        print(f"Create new PR: {pr_url}")
        webbrowser.open_new_tab(pr_url)
    if get_release_stage() <= ReleaseStage.CHANGELOG_PR_OPENED:
        set_release_stage(ReleaseStage.CHANGELOG_PR_OPENED)
        pause()
    if get_release_stage() <= ReleaseStage.CHANGELOG_CREATED:
        base_branch = get_base_branch()
        try:
            subprocess.check_call(("git", "checkout", base_branch))
        except subprocess.CalledProcessError:
            rich.print(
                f"Can't check out {base_branch} branch."
                " Resolve the issue and check out that branch before proceeding."
            )
            pause()
    set_release_stage(ReleaseStage.CHANGELOG_CREATED)


def review_changelog(release_type: ReleaseType, version: str) -> None:
    rich.print(Markdown("# Step 4: Review/wait for review of the changelog PR"))
    if get_release_stage() >= ReleaseStage.CHANGELOG_REVIEWED:
        rich.print(":white_check_mark: Already done!")
        return
    if release_type is ReleaseType.HOTFIX:
        rich.print(
            "Hotfix releases [bold]need to[/] contain a changelog.\n"
            "It can be limited to a short description of what the hotfix release fixes,"
            " for example see:"
            " [link=https://docs.discord.red/en/stable/changelog.html#redbot-3-4-12-2021-06-17]"
            "Red 3.4.12 changelog"
            "[/]"
        )
    else:
        rich.print(
            Markdown(
                "- Add (or ask PR author to add) any missing entries"
                " based on the release’s milestone.\n"
                "- Update the contributors list in the changelog using contributors list for"
                " the milestone that you can generate using the option 1 below\n"
                "- Merge the PR once it’s ready.\n"
            )
        )

    pause()
    set_release_stage(ReleaseStage.CHANGELOG_REVIEWED)


def run_prepare_release_workflow(release_type: ReleaseType, version: str) -> None:
    rich.print(Markdown("# Step 5: Run 'Prepare Release' workflow"))
    if get_release_stage() >= ReleaseStage.PREPARE_RELEASE_RAN:
        rich.print(":white_check_mark: Already done!")

    base_branch = get_base_branch()
    run_list_command = (
        "gh",
        "run",
        "list",
        "--limit=1",
        "--json=databaseId,number",
        "--workflow=prepare_release.yml",
        "--branch",
        base_branch,
    )
    if get_release_stage() < ReleaseStage.PREPARE_RELEASE_SPAWNED:
        rich.print(
            Markdown(
                "## Release details\n"
                f"- Version number: {version}\n"
                f"- Branch to release from: {base_branch}\n\n"
                "**Please verify the correctness of above information before confirming.**"
            )
        )
        if not click.confirm("Is the above information correct?"):
            raise click.ClickException(
                "Please check out the branch that you want to release from"
                " and start this program again."
            )
        rich.print(
            ":information_source-emoji: This step only takes care of automatically creating some PRs,"
            " it won’t release anything, don’t worry!"
        )
        if not click.confirm("Do you want to run the 'Prepare Release' workflow?"):
            raise click.ClickException(
                "Run this command again once you're ready to run this workflow."
            )

        set_previous_workflow_run_number(
            json.loads(subprocess.check_output(run_list_command, text=True))[0]["number"]
        )
        subprocess.check_call(
            ("gh", "workflow", "run", "prepare_release.yml", "--ref", base_branch)
        )
        set_release_stage(ReleaseStage.PREPARE_RELEASE_SPAWNED)
    if get_release_stage() < ReleaseStage.PREPARE_RELEASE_RAN:
        previous_run = get_previous_workflow_run_number()
        print_markdown("Waiting for GitHub Actions workflow to show...")
        time.sleep(2)
        while True:
            data = json.loads(subprocess.check_output(run_list_command, text=True))[0]
            if data["number"] > previous_run:
                run_id = data["databaseId"]
                break
            time.sleep(5)

        try:
            subprocess.check_call(("gh", "run", "watch", "--exit-status", str(run_id)))
        except subprocess.CalledProcessError:
            set_release_stage(ReleaseStage.CHANGELOG_REVIEWED)
            raise click.ClickException(
                "Github Actions workflow failed, run this command again"
                " once you're ready to try running the 'Prepare Release' workflow again."
            )

        rich.print("The automated pull requests have been created.\n")
        set_release_stage(ReleaseStage.PREPARE_RELEASE_RAN)
    rich.print(Markdown("# Step 6: Merge the automatically created PRs"))
    if get_release_stage() >= ReleaseStage.AUTOMATED_PULLS_MERGED:
        rich.print(":white_check_mark: Already done!")
        return
    output = subprocess.check_output(
        (
            "gh",
            "pr",
            "list",
            "--json=number,title,state",
            "--template",
            "{{if .}}"
            '{{tablerow "NUMBER" "STATE" "TITLE"}}{{range .}}'
            '{{tablerow (printf "#%v" .number) .state .title}}{{end}}{{tablerender}}'
            "{{end}}",
            "--limit=999",
            "--search",
            f'milestone:{version} label:"Automated PR"',
        ),
        text=True,
    )
    print(linkify_issue_refs_cli(output))
    pause()
    set_release_stage(ReleaseStage.AUTOMATED_PULLS_MERGED)


def create_short_lived_branch(release_type: ReleaseType, version: str) -> None:
    rich.print(Markdown("# Step 7: Create a short-lived release branch"))
    if get_release_stage() >= ReleaseStage.SHORT_LIVED_BRANCH_CREATED:
        rich.print(":white_check_mark: Already done!")
        return
    if release_type in (ReleaseType.BREAKING, ReleaseType.STANDARD):
        rich.print(f"This does not apply to {release_type}s.")
        set_release_stage(ReleaseStage.SHORT_LIVED_BRANCH_CREATED)
        return
    if release_type is ReleaseType.HOTFIX and click.confirm(
        "Are you releasing from the long-lived branch (V3/develop or 3.x)?"
    ):
        rich.print(f"This does not apply to {release_type}s released from a long-lived branch.")
        set_release_stage(ReleaseStage.SHORT_LIVED_BRANCH_CREATED)
        return

    rich.print(
        Markdown(
            f"- Create a branch named V3/release/{version} based off a tag of previous version.\n"
            "  This can be done with the command:\n"
            "  ```\n"
            f"  git checkout -b V3/release/{version} PREVIOUS_VERSION\n"
            "  ```\n"
            "- Cherry-pick the relevant changes, the changelog, the automated PRs, and the version bump.\n"
            "- Push the branch to upstream repository (Cog-Creators/Red-DiscordBot)\n"
            "  This can be done with the command:\n"
            "  ```\n"
            f"  git push -u {GH_URL} V3/release/{version}\n"
            "  ```"
        )
    )
    pause()
    set_release_stage(ReleaseStage.SHORT_LIVED_BRANCH_CREATED)


STEPS = (
    ensure_no_release_blockers,
    check_state_of_open_pulls,
    create_changelog,
    review_changelog,
    run_prepare_release_workflow,
    create_short_lived_branch,
)


@cli.command(name="unreleased")
@click.argument("version")
@click.argument("base_branch")
def cli_unreleased(version: str, base_branch: str) -> None:
    show_unreleased_commits(version, base_branch)


def show_unreleased_commits(version: str, base_branch: str) -> None:
    token = get_github_token()

    resp = requests.post(
        "https://api.github.com/graphql",
        json={"query": GET_ALL_TAG_COMMITS_QUERY},
        headers={"Authorization": f"Bearer {token}"},
    )
    json = resp.json()
    tag_commits = {
        node["target"]["commitResourcePath"].rsplit("/", 1)[-1]: node["name"]
        for node in json["data"]["repository"]["refs"]["nodes"]
    }

    after = None
    has_next_page = True
    commits_without_pr: List[str] = []
    commits_with_no_milestone: List[str] = []
    commits_with_different_milestone: Dict[str, List[str]] = defaultdict(list)
    while has_next_page:
        resp = requests.post(
            "https://api.github.com/graphql",
            json={
                "query": GET_COMMIT_HISTORY_QUERY,
                "variables": {
                    "after": after,
                    "refQualifiedName": f"refs/heads/{base_branch}",
                },
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        json = resp.json()
        data = json["data"]
        history = data["repository"]["ref"]["target"]["history"]

        for node in history["nodes"]:
            maybe_tag_name = tag_commits.get(node["oid"])
            if maybe_tag_name is not None:
                has_next_page = False
                break
            commits: Optional[List[str]] = None
            associated_pr = next(iter(node["associatedPullRequests"]["nodes"]), None)
            if associated_pr is None:
                commits = commits_without_pr
            elif (milestone_data := associated_pr["milestone"]) is None:
                commits = commits_with_no_milestone
            elif milestone_data["title"] != version:
                commits = commits_with_different_milestone[milestone_data["title"]]
            if commits is not None:
                commits.append(
                    f"- [{node['abbreviatedOid']}]"
                    f"({GH_URL}/commit/{node['oid']})"
                    f" - {linkify_issue_refs_md(node['messageHeadline'])}"
                )
        else:
            page_info = history["pageInfo"]
            after = page_info["endCursor"]
            has_next_page = page_info["hasNextPage"]

    parts = []
    parts.append(f"## Unreleased commits without {version} milestone")
    if commits_without_pr:
        parts.append("\n### Commits without associated PR\n")
        parts.append("\n".join(commits_without_pr))
    if commits_with_no_milestone:
        parts.append("\n### Commits with no milestone\n")
        parts.append("\n".join(commits_with_no_milestone))
    if commits_with_different_milestone:
        parts.append("\n### Commits with different milestone\n")
        for milestone_title, commits in commits_with_different_milestone.items():
            parts.append(f"\n#### {milestone_title}\n")
            parts.extend(commits)

    rich.print(Markdown("\n".join(parts)))


@cli.command(name="milestone")
@click.argument("version")
def cli_milestone(version: str) -> None:
    view_milestone_issues(version)


def view_milestone_issues(version: str) -> None:
    issue_views: List[str] = []
    for issue_type in ("pr", "issue"):
        for number in subprocess.check_output(
            (
                "gh",
                issue_type,
                "list",
                "--json=number",
                "--jq=.[].number",
                "--limit=999",
                "--state=all",
                "--search",
                f"milestone:{version}",
            ),
            text=True,
        ).splitlines():
            view = linkify_issue_refs_cli(
                subprocess.check_output(
                    ("gh", issue_type, "view", number), env=GH_FORCE_TTY_ENV, text=True
                )
            )
            if not issue_views:
                # print one issue while we're waiting to fetch all
                print(view)
            issue_views.append(view)

    pydoc.pager("\n---\n\n".join(issue_views))


@cli.command(name="contributors")
@click.argument("version")
@click.option("--show-not-merged", is_flag=True, default=False)
def cli_contributors(version: str, *, show_not_merged: bool = False) -> None:
    get_contributors(version, show_not_merged=show_not_merged)


def get_contributors(version: str, *, show_not_merged: bool = False) -> None:
    print(
        ", ".join(
            f":ghuser:`{username}`"
            for username in _get_contributors(version, show_not_merged=show_not_merged)
        )
    )


def _get_contributors(version: str, *, show_not_merged: bool = False) -> List[str]:
    after = None
    has_next_page = True
    authors: Dict[str, List[Tuple[int, str]]] = {}
    reviewers: Dict[str, List[Tuple[int, str]]] = {}
    token = get_github_token()
    states = ["MERGED"]
    if show_not_merged:
        states.append("OPEN")
    while has_next_page:
        resp = requests.post(
            "https://api.github.com/graphql",
            json={
                "query": GET_MILESTONE_CONTRIBUTORS_QUERY,
                "variables": {
                    "milestone": version,
                    "after": after,
                    "states": states,
                },
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        json = resp.json()
        try:
            milestone_data = json["data"]["repository"]["milestones"]["nodes"][0]
        except IndexError:
            raise click.ClickException("Given milestone couldn't have been found.")
        pull_requests = milestone_data["pullRequests"]
        nodes = pull_requests["nodes"]
        for pr_node in nodes:
            pr_info = (pr_node["number"], pr_node["title"])
            pr_author = pr_node["author"]["login"]
            authors.setdefault(pr_author, []).append(pr_info)
            reviews = pr_node["latestOpinionatedReviews"]["nodes"]
            for review_node in reviews:
                review_author = review_node["author"]["login"]
                reviewers.setdefault(review_author, []).append(pr_info)

        page_info = pull_requests["pageInfo"]
        after = page_info["endCursor"]
        has_next_page = page_info["hasNextPage"]

    return sorted(authors.keys() | reviewers.keys(), key=lambda t: t[0].lower())


if __name__ == "__main__":
    raise SystemExit(cli())
