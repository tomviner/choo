"""Configuration management using XDG base directories.

Config is stored as a flat JSON object with dotted keys:
    alias.home = HIB
    alias.work = MOG
    next.count = 5
"""

import json
import os
from pathlib import Path

from platformdirs import user_config_dir


RESERVED_ALIAS_NAMES = {"next", "board", "service", "config", "auth", "stations"}
DEFAULT_COUNT = 5

_APP_NAME = "choo"


def _config_dir() -> Path:
    return Path(user_config_dir(_APP_NAME))


def _config_file() -> Path:
    return _config_dir() / "config.json"


def _load_config() -> dict[str, str]:
    """Load the config file."""
    path = _config_file()
    if path.exists():
        return json.loads(path.read_text())
    # Migrate from old aliases.json if it exists
    old = _config_dir() / "aliases.json"
    if old.exists():
        aliases = json.loads(old.read_text())
        return {f"alias.{k}": v for k, v in aliases.items()}
    return {}


def _save_config(config: dict[str, str]) -> None:
    """Save the config file."""
    config_dir = _config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    _config_file().write_text(json.dumps(config, indent=2) + "\n")


def config_get(key: str) -> str | None:
    """Get a config value by dotted key."""
    # Env vars override: alias.home → CHOO_ALIAS_HOME
    if key.startswith("alias."):
        alias_name = key[6:]
        env_key = f"CHOO_ALIAS_{alias_name.upper()}"
        env_val = os.environ.get(env_key)
        if env_val:
            return env_val
    config = _load_config()
    return config.get(key)


def config_set(key: str, value: str) -> None:
    """Set a config value."""
    if key.startswith("alias."):
        alias_name = key[6:]
        if alias_name.lower() in RESERVED_ALIAS_NAMES:
            raise ValueError(
                f"'{alias_name}' is a reserved command name. "
                f"Choose a different alias name."
            )
        value = value.upper()
    config = _load_config()
    config[key] = value
    _save_config(config)


def config_unset(key: str) -> None:
    """Remove a config value."""
    config = _load_config()
    config.pop(key, None)
    _save_config(config)


def config_list() -> dict[str, str]:
    """Get all config values, with env var overrides applied."""
    config = _load_config()
    # Overlay env aliases
    prefix = "CHOO_ALIAS_"
    for env_key, env_val in os.environ.items():
        if env_key.startswith(prefix):
            name = env_key[len(prefix) :].lower()
            config[f"alias.{name}"] = env_val
    return config


# Convenience functions used by the rest of the app


def get_auth() -> tuple[str, str] | None:
    """Get API credentials. Priority: CHOO_AUTH > RTT_AUTH > config file."""
    auth_str = os.environ.get("CHOO_AUTH") or os.environ.get("RTT_AUTH")
    if auth_str:
        return tuple(auth_str.split(":"))

    auth_file = _config_dir() / "auth"
    if auth_file.exists():
        return tuple(auth_file.read_text().strip().split(":"))

    return None


def get_aliases() -> dict[str, str]:
    """Get all aliases as a plain dict."""
    all_config = config_list()
    return {k[6:]: v for k, v in all_config.items() if k.startswith("alias.")}


def get_default_count() -> int:
    """Get the default count for the next command."""
    val = config_get("next.count")
    if val is not None:
        try:
            return int(val)
        except ValueError:
            pass
    return DEFAULT_COUNT
