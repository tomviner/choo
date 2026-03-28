"""Configuration management using XDG base directories."""

import json
import os
from pathlib import Path

from platformdirs import user_config_dir


RESERVED_NAMES = {"next", "board", "service", "alias", "auth"}

_APP_NAME = "choo"


def _config_dir() -> Path:
    return Path(user_config_dir(_APP_NAME))


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
    """Get all aliases. Env vars (CHOO_ALIAS_*) override config file."""
    aliases = {}

    # Load from config file first
    alias_file = _config_dir() / "aliases.json"
    if alias_file.exists():
        aliases = json.loads(alias_file.read_text())

    # Overlay env vars (higher priority)
    prefix = "CHOO_ALIAS_"
    for key, value in os.environ.items():
        if key.startswith(prefix):
            name = key[len(prefix) :].lower()
            aliases[name] = value

    return aliases


def set_alias(name: str, crs: str) -> None:
    """Save an alias to the config file."""
    if name.lower() in RESERVED_NAMES:
        raise ValueError(
            f"'{name}' is a reserved command name. " f"Choose a different alias name."
        )
    config_dir = _config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    alias_file = config_dir / "aliases.json"

    aliases = {}
    if alias_file.exists():
        aliases = json.loads(alias_file.read_text())

    aliases[name.lower()] = crs.upper()
    alias_file.write_text(json.dumps(aliases, indent=2) + "\n")


def remove_alias(name: str) -> None:
    """Remove an alias from the config file."""
    alias_file = _config_dir() / "aliases.json"
    if not alias_file.exists():
        return
    aliases = json.loads(alias_file.read_text())
    aliases.pop(name.lower(), None)
    alias_file.write_text(json.dumps(aliases, indent=2) + "\n")
