"""Tests for choo.config module."""

import json

import pytest

from choo.config import (
    RESERVED_ALIAS_NAMES,
    config_get,
    config_list,
    config_set,
    config_unset,
    get_aliases,
    get_auth,
    get_default_count,
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


class TestConfigGetSet:
    def test_set_and_get(self, tmp_path):
        config_set("next.count", "5")
        assert config_get("next.count") == "5"

    def test_get_missing_returns_none(self):
        assert config_get("nonexistent.key") is None

    def test_alias_set_uppercases(self, tmp_path):
        config_set("alias.home", "hib")
        assert config_get("alias.home") == "HIB"

    def test_alias_env_overrides(self, monkeypatch):
        config_set("alias.home", "HIB")
        monkeypatch.setenv("CHOO_ALIAS_HOME", "BTN")
        assert config_get("alias.home") == "BTN"

    def test_reserved_alias_raises(self):
        with pytest.raises(ValueError, match="reserved"):
            config_set("alias.config", "HIB")

    def test_all_reserved_names(self):
        assert RESERVED_ALIAS_NAMES == {
            "next",
            "board",
            "service",
            "config",
            "auth",
            "stations",
        }


class TestConfigUnset:
    def test_unset_existing(self):
        config_set("alias.home", "HIB")
        config_unset("alias.home")
        assert config_get("alias.home") is None

    def test_unset_nonexistent(self):
        config_unset("nonexistent.key")  # should not raise


class TestConfigList:
    def test_lists_all(self):
        config_set("alias.home", "HIB")
        config_set("alias.work", "MOG")
        config_set("next.count", "5")
        items = config_list()
        assert items["alias.home"] == "HIB"
        assert items["alias.work"] == "MOG"
        assert items["next.count"] == "5"

    def test_env_aliases_overlay(self, monkeypatch):
        config_set("alias.home", "HIB")
        monkeypatch.setenv("CHOO_ALIAS_HOME", "BTN")
        items = config_list()
        assert items["alias.home"] == "BTN"

    def test_empty_config(self):
        assert config_list() == {}


class TestGetAliases:
    def test_from_config(self):
        config_set("alias.home", "HIB")
        config_set("alias.work", "MOG")
        aliases = get_aliases()
        assert aliases == {"home": "HIB", "work": "MOG"}

    def test_env_override(self, monkeypatch):
        config_set("alias.home", "HIB")
        monkeypatch.setenv("CHOO_ALIAS_HOME", "BTN")
        assert get_aliases()["home"] == "BTN"

    def test_migrates_old_aliases_json(self, tmp_path):
        """Old aliases.json is migrated to config.json format."""
        config_dir = tmp_path / "choo"
        config_dir.mkdir(parents=True)
        (config_dir / "aliases.json").write_text(json.dumps({"home": "HIB"}))
        aliases = get_aliases()
        assert aliases["home"] == "HIB"


class TestGetDefaultCount:
    def test_default(self):
        assert get_default_count() == 5

    def test_configured(self):
        config_set("next.count", "10")
        assert get_default_count() == 10

    def test_invalid_value_returns_default(self):
        config_set("next.count", "abc")
        assert get_default_count() == 5
