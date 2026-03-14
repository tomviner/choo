"""Tests for choo.config module."""

import json

import pytest

from choo.config import (
    RESERVED_NAMES,
    get_aliases,
    get_auth,
    remove_alias,
    set_alias,
)


@pytest.fixture(autouse=True)
def _isolate_config(monkeypatch, tmp_path):
    """Use tmp_path as XDG config dir and clear relevant env vars."""
    monkeypatch.setattr("choo.config._config_dir", lambda: tmp_path / "choo")
    monkeypatch.delenv("CHOO_AUTH", raising=False)
    monkeypatch.delenv("RTT_AUTH", raising=False)
    for key in list(k for k in __import__("os").environ if k.startswith("CHOO_ALIAS_")):
        monkeypatch.delenv(key, raising=False)


class TestGetAuth:
    def test_choo_auth_env(self, monkeypatch):
        monkeypatch.setenv("CHOO_AUTH", "user:pass")
        assert get_auth() == ("user", "pass")

    def test_rtt_auth_fallback(self, monkeypatch):
        monkeypatch.setenv("RTT_AUTH", "rttuser:rttpass")
        assert get_auth() == ("rttuser", "rttpass")

    def test_choo_auth_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("CHOO_AUTH", "choo:secret")
        monkeypatch.setenv("RTT_AUTH", "rtt:other")
        assert get_auth() == ("choo", "secret")

    def test_config_file_fallback(self, tmp_path):
        config_dir = tmp_path / "choo"
        config_dir.mkdir(parents=True)
        (config_dir / "auth").write_text("fileuser:filepass\n")
        assert get_auth() == ("fileuser", "filepass")

    def test_no_auth_returns_none(self):
        assert get_auth() is None


class TestGetAliases:
    def test_env_alias(self, monkeypatch):
        monkeypatch.setenv("CHOO_ALIAS_HOME", "BTN")
        aliases = get_aliases()
        assert aliases["home"] == "BTN"

    def test_config_file_alias(self, tmp_path):
        config_dir = tmp_path / "choo"
        config_dir.mkdir(parents=True)
        (config_dir / "aliases.json").write_text(json.dumps({"work": "VIC"}))
        assert get_aliases()["work"] == "VIC"

    def test_env_overrides_config(self, monkeypatch, tmp_path):
        config_dir = tmp_path / "choo"
        config_dir.mkdir(parents=True)
        (config_dir / "aliases.json").write_text(json.dumps({"home": "VIC"}))
        monkeypatch.setenv("CHOO_ALIAS_HOME", "BTN")
        assert get_aliases()["home"] == "BTN"


class TestSetAlias:
    def test_saves_to_config(self, tmp_path):
        set_alias("home", "btn")
        alias_file = tmp_path / "choo" / "aliases.json"
        data = json.loads(alias_file.read_text())
        assert data["home"] == "BTN"

    def test_reserved_name_raises(self):
        for name in RESERVED_NAMES:
            with pytest.raises(ValueError, match="reserved"):
                set_alias(name, "BTN")


class TestRemoveAlias:
    def test_removes_from_config(self, tmp_path):
        set_alias("home", "btn")
        remove_alias("home")
        alias_file = tmp_path / "choo" / "aliases.json"
        data = json.loads(alias_file.read_text())
        assert "home" not in data

    def test_remove_alias_no_file(self, tmp_path):
        """Line 74: remove_alias returns early when no aliases file exists."""
        remove_alias("nonexistent")
        # Should not raise


class TestSetAliasExistingFile:
    def test_updates_existing_aliases_file(self, tmp_path):
        """Line 64: set_alias reads existing aliases.json before updating."""
        set_alias("home", "btn")
        set_alias("work", "pad")
        alias_file = tmp_path / "choo" / "aliases.json"
        data = json.loads(alias_file.read_text())
        assert data["home"] == "BTN"
        assert data["work"] == "PAD"


class TestReservedNames:
    def test_reserved_names(self):
        assert RESERVED_NAMES == {"next", "board", "service", "alias", "auth"}
