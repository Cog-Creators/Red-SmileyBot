import sys
from pathlib import Path

import yaml

ROOT_FOLDER = Path(__file__).parents[3].absolute()
AUDIO_FOLDER = ROOT_FOLDER / "redbot/cogs/audio"

# We want to import `redbot.cogs.audio.managed_node` package as if it were top-level package
# so we have to the `redbot/cogs/audio` directory to Python's path.
sys.path.insert(0, str(AUDIO_FOLDER))


def main() -> int:
    try:
        output_file = sys.argv[1]
    except IndexError:
        print("Usage:", sys.argv[0], "<output_file>", file=sys.stderr)
        return 2

    import managed_node

    server_config = managed_node.get_default_server_config()
    with open(output_file, "w", encoding="utf-8") as fp:
        yaml.safe_dump(server_config, fp)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
