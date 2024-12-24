from __future__ import annotations

from typing import Any, Dict, Final

from . import version_pins

__all__ = (
    "DEFAULT_LAVALINK_YAML",
    "get_default_server_config",
    "generate_server_config",
    "change_dict_naming_convention",
)

YT_PLUGIN_REPOSITORY: Final[str] = "https://maven.lavalink.dev/releases"

DEFAULT_LAVALINK_YAML = {
    # The nesting structure of this dict is very important, it's a 1:1 mirror of application.yaml in JSON
    "yaml__server__address": "localhost",
    "yaml__server__port": 2333,
    "yaml__lavalink__server__password": "youshallnotpass",
    "yaml__lavalink__server__sources__http": True,
    "yaml__lavalink__server__sources__bandcamp": True,
    "yaml__lavalink__server__sources__local": True,
    "yaml__lavalink__server__sources__soundcloud": True,
    "yaml__lavalink__server__sources__youtube": True,
    "yaml__lavalink__server__sources__twitch": True,
    "yaml__lavalink__server__sources__vimeo": True,
    "yaml__lavalink__server__bufferDurationMs": 400,
    "yaml__lavalink__server__frameBufferDurationMs": 1000,
    # 100 pages - 100 entries per page = 10,000 tracks which is the Audio Limit for a single playlist.
    "yaml__lavalink__server__youtubePlaylistLoadLimit": 100,
    "yaml__lavalink__server__playerUpdateInterval": 1,
    "yaml__lavalink__server__youtubeSearchEnabled": True,
    "yaml__lavalink__server__soundcloudSearchEnabled": True,
    "yaml__lavalink__server__gc_warnings": True,
    "yaml__metrics__prometheus__enabled": False,
    "yaml__metrics__prometheus__endpoint": "/metrics",
    "yaml__sentry__dsn": "",
    "yaml__sentry__environment": "",
    "yaml__logging__file__path": "./logs/",
    "yaml__logging__level__root": "INFO",
    "yaml__logging__level__lavalink": "INFO",
    "yaml__logging__logback__rollingpolicy__max_history": 15,
    "yaml__logging__logback__rollingpolicy__max_size": "10MB",
    # plugin configuration - note that the plugin may be disabled by the manager
    "yaml__plugins__youtube__enabled": True,
    "yaml__plugins__youtube__allowSearch": True,
    "yaml__plugins__youtube__allowDirectVideoIds": True,
    "yaml__plugins__youtube__allowDirectPlaylistIds": True,
    "yaml__plugins__youtube__clients": [
        "MUSIC",
        "WEB",
        "WEBEMBEDDED",
        "MWEB",
        "TVHTML5EMBEDDED",
        "TV",
        "IOS",
    ],
    "yaml__plugins__youtube__MUSIC__playback": False,
    "yaml__plugins__youtube__MUSIC__playlistLoading": False,
    "yaml__plugins__youtube__MUSIC__searching": True,
    "yaml__plugins__youtube__MUSIC__videoLoading": False,
    "yaml__plugins__youtube__MWEB__playback": True,
    "yaml__plugins__youtube__MWEB__playlistLoading": True,
    "yaml__plugins__youtube__MWEB__searching": False,
    "yaml__plugins__youtube__MWEB__videoLoading": False,
    "yaml__plugins__youtube__TV__playback": True,
    "yaml__plugins__youtube__TV__playlistLoading": False,
    "yaml__plugins__youtube__TV__searching": False,
    "yaml__plugins__youtube__TV__videoLoading": False,
    "yaml__plugins__youtube__TVHTML5EMBEDDED__playback": True,
    "yaml__plugins__youtube__TVHTML5EMBEDDED__playlistLoading": False,
    "yaml__plugins__youtube__TVHTML5EMBEDDED__searching": False,
    "yaml__plugins__youtube__TVHTML5EMBEDDED__videoLoading": False,
    "yaml__plugins__youtube__WEB__playback": True,
    "yaml__plugins__youtube__WEB__playlistLoading": True,
    "yaml__plugins__youtube__WEB__searching": False,
    "yaml__plugins__youtube__WEB__videoLoading": False,
    "yaml__plugins__youtube__WEBEMBEDDED__playback": True,
    "yaml__plugins__youtube__WEBEMBEDDED__playlistLoading": False,
    "yaml__plugins__youtube__WEBEMBEDDED__searching": False,
    "yaml__plugins__youtube__WEBEMBEDDED__videoLoading": False,
}


def _unflatten_config_defaults(config_defaults: Dict[str, Any]) -> Dict[str, Any]:
    ret: Dict[str, Any] = {}

    # based on Config._get_defaults_dict()
    for flat_key, value in config_defaults.items():
        keys = flat_key.split("__")
        partial = ret
        for idx, key in enumerate(keys, start=1):
            if idx == len(keys):
                partial[key] = value
            else:
                partial = partial.setdefault(key, {})

    return ret


def get_default_server_config() -> Dict[str, Any]:
    return generate_server_config(_unflatten_config_defaults(DEFAULT_LAVALINK_YAML)["yaml"])


def generate_server_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    data = change_dict_naming_convention(config_data)
    ll_config = data["lavalink"]
    sources = ll_config["server"]["sources"]
    plugins = ll_config.setdefault("plugins", [])

    enable_yt_plugin = sources["youtube"]
    if enable_yt_plugin:
        sources["youtube"] = False
        yt_plugin = {
            "dependency": f"dev.lavalink.youtube:youtube-plugin:{version_pins.YT_PLUGIN_VERSION}",
            "repository": YT_PLUGIN_REPOSITORY,
        }
        plugins.append(yt_plugin)

    return data


# This assumes all keys with `_` should be converted from `part1_part2` to `part1-part2`
def _convert_function(key: str) -> str:
    return key.replace("_", "-")


def change_dict_naming_convention(data: Any) -> Any:
    ret: Any = data
    if isinstance(data, dict):
        ret = {}
        for key, value in data.items():
            ret[_convert_function(key)] = change_dict_naming_convention(value)
    elif isinstance(data, list):
        ret = []
        for value in data:
            ret.append(change_dict_naming_convention(value))
    return ret
