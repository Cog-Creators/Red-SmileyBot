import itertools
import operator
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from typing_extensions import Self

import rich
import yaml
from rich.console import Console, ConsoleOptions, RenderResult
from rich.tree import Tree
from pathspec import PathSpec
from pathspec.patterns.gitwildmatch import GitWildMatchPattern


ROOT_PATH = Path(__file__).resolve().parents[3]


class Matcher:
    def __init__(self, *, any: Iterable[str] = (), all: Iterable[str] = ()) -> None:
        self.any_patterns = tuple(any)
        self.any_specs = self._get_pathspecs(self.any_patterns)
        self.all_patterns = tuple(all)
        self.all_specs = self._get_pathspecs(self.all_patterns)

    def __repr__(self) -> str:
        return f"Matcher(any={self.any_patterns!r}, all={self.all_patterns!r})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return (
                self.any_patterns == other.any_patterns and self.all_patterns == other.all_patterns
            )
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.any_patterns, self.all_patterns))

    @classmethod
    def _get_pathspecs(cls, patterns: Iterable[str]) -> List[PathSpec]:
        return tuple(
            PathSpec.from_lines(GitWildMatchPattern, cls._get_pattern_lines(pattern))
            for pattern in patterns
        )

    @staticmethod
    def _get_pattern_lines(pattern: str) -> List[str]:
        # an approximation of actions/labeler's minimatch globs
        if pattern.startswith("!"):
            pattern_lines = ["*", f"!/{pattern[1:]}"]
        else:
            pattern_lines = [f"/{pattern}"]
            if pattern.endswith("*") and "**" not in pattern:
                pattern_lines.append(f"!/{pattern}/")
        return pattern_lines

    @classmethod
    def get_label_matchers(cls) -> Dict[str, List[Self]]:
        with open(ROOT_PATH / ".github/labeler.yml", encoding="utf-8") as fp:
            label_definitions = yaml.safe_load(fp)
        label_matchers: Dict[str, List[Matcher]] = {}
        for label_name, matcher_definitions in label_definitions.items():
            matchers = label_matchers[label_name] = []
            for idx, matcher_data in enumerate(matcher_definitions):
                if isinstance(matcher_data, str):
                    matchers.append(cls(any=[matcher_data]))
                elif isinstance(matcher_data, dict):
                    matchers.append(
                        cls(any=matcher_data.pop("any", []), all=matcher_data.pop("all", []))
                    )
                    if matcher_data:
                        raise RuntimeError(
                            f"Unexpected keys at index {idx} for label {label_name!r}: "
                            + ", ".join(map(repr, matcher_data))
                        )
                elif matcher_data is not None:
                    raise RuntimeError(f"Unexpected type at index {idx} for label {label_name!r}")

        return label_matchers


class PathNode:
    def __init__(self, parent_tree: Tree, path: Path, *, label: Optional[str] = None) -> None:
        self.parent_tree = parent_tree
        self.path = path
        self.label = label

    def __rich__(self) -> str:
        if self.label is not None:
            return self.label
        return self.path.name


class DirectoryTree:
    def __init__(self, label: str) -> None:
        self.root = Tree(PathNode(Tree(""), Path(), label=label))
        self._previous = self.root

    def __bool__(self) -> bool:
        return bool(self.root.children)

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        yield from self.root.__rich_console__(console, options)

    def add(self, file: Path) -> Tree:
        common_path = Path(os.path.commonpath([file.parent, self._previous.label.path]))

        parent_tree = self._previous
        while parent_tree != self.root and parent_tree.label.path != common_path:
            parent_tree = parent_tree.label.parent_tree

        for part in file.relative_to(common_path).parts:
            if parent_tree.label.path.name == "locales":
                if not parent_tree.children:
                    parent_tree.add(PathNode(parent_tree, parent_tree.label.path / "*.po"))
                continue
            parent_tree = parent_tree.add(PathNode(parent_tree, parent_tree.label.path / part))

        self._previous = parent_tree
        return parent_tree


class App:
    def __init__(self) -> None:
        self.exit_code = 0
        self.label_matchers = Matcher.get_label_matchers()
        self.tracked_files = [
            Path(filename)
            for filename in subprocess.check_output(
                ("git", "ls-tree", "-r", "HEAD", "--name-only"), encoding="utf-8", cwd=ROOT_PATH
            ).splitlines()
        ]
        self.matches_per_label = {label_name: set() for label_name in self.label_matchers}
        self.matches_per_file = []
        self.used_matchers = set()

    def run(self) -> int:
        old_cwd = os.getcwd()
        try:
            os.chdir(ROOT_PATH)
            self._run()
        finally:
            os.chdir(old_cwd)
        return self.exit_code

    def _run(self) -> None:
        self._collect_match_information()
        self._show_matches_per_label()
        self._show_files_without_labels()
        self._show_files_with_multiple_labels()
        self._show_unused_matchers()

    def _collect_match_information(self) -> None:
        tmp_matches_per_file = {file: [] for file in self.tracked_files}

        for file in self.tracked_files:
            for label_name, matchers in self.label_matchers.items():
                matched = False
                for matcher in matchers:
                    if all(
                        path_spec.match_file(file)
                        for path_spec in itertools.chain(matcher.all_specs, matcher.any_specs)
                    ):
                        self.matches_per_label[label_name].add(file)
                        matched = True
                        self.used_matchers.add(matcher)
                if matched:
                    tmp_matches_per_file[file].append(label_name)

        self.matches_per_file = sorted(tmp_matches_per_file.items(), key=operator.itemgetter(0))

    def _show_matches_per_label(self) -> None:
        for label_name, files in self.matches_per_label.items():
            top_tree = DirectoryTree(f"{label_name}:")
            for file in sorted(files):
                top_tree.add(file)
            rich.print(top_tree)
        print()

    def _show_files_without_labels(self) -> None:
        top_tree = DirectoryTree("\n--- Not matched ---")
        for file, labels in self.matches_per_file:
            if not labels:
                top_tree.add(file)
        if top_tree:
            self.exit_code = 1
            rich.print(top_tree)
        else:
            print("--- All files match at least one label's patterns ---")

    def _show_files_with_multiple_labels(self) -> None:
        top_tree = DirectoryTree("\n--- Matched by more than one label ---")
        for file, labels in self.matches_per_file:
            if len(labels) > 1:
                tree = top_tree.add(file)
                for label_name in labels:
                    tree.add(label_name)
        if top_tree:
            rich.print(top_tree)
        else:
            print("--- None of the files are matched by more than one label's patterns ---")

    def _show_unused_matchers(self) -> None:
        for label_name, matchers in self.label_matchers.items():
            for idx, matcher in enumerate(matchers):
                if matcher not in self.used_matchers:
                    print(
                        f"--- Matcher {idx} for label {label_name!r} does not match any files! ---"
                    )
                    self.exit_code = 1


if __name__ == "__main__":
    raise SystemExit(App().run())
