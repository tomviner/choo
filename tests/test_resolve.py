"""Tests for station resolution."""

import pytest

from choo.resolve import AmbiguousStation, StationNotFound, resolve_station
from choo.stations import fuzzy_search, load_stations


class TestLoadStations:
    def test_returns_non_empty_dict(self):
        stations = load_stations()
        assert isinstance(stations, dict)
        assert len(stations) > 50

    def test_known_station(self):
        stations = load_stations()
        assert stations["PAD"] == "London Paddington"


class TestFuzzySearch:
    def test_returns_results_with_scores(self):
        results = fuzzy_search("Paddington")
        assert len(results) > 0
        name, crs, score = results[0]
        assert isinstance(name, str)
        assert isinstance(crs, str)
        assert isinstance(score, (int, float))
        assert score > 0

    def test_exact_name_scores_high(self):
        results = fuzzy_search("London Paddington")
        assert results[0][1] == "PAD"
        assert results[0][2] > 90


class TestResolveStation:
    def test_crs_passthrough(self):
        assert resolve_station("PAD") == "PAD"
        assert resolve_station("BHM") == "BHM"
        assert resolve_station("XYZ") == "XYZ"

    def test_alias_resolution(self, monkeypatch):
        monkeypatch.setenv("CHOO_ALIAS_HOME", "CLJ")
        assert resolve_station("home") == "CLJ"

    def test_fuzzy_exact_name(self):
        result = resolve_station("London Paddington")
        assert result == "PAD"

    def test_fuzzy_partial_name(self):
        result = resolve_station("Didcot Parkway")
        assert result == "DID"

    def test_station_not_found(self):
        with pytest.raises(StationNotFound) as exc_info:
            resolve_station("xyzzyspoon")
        assert exc_info.value.query == "xyzzyspoon"
        assert isinstance(exc_info.value.suggestions, list)

    def test_ambiguous_station(self):
        # "Birmingham" should match multiple Birmingham stations closely
        with pytest.raises(AmbiguousStation) as exc_info:
            resolve_station("Birmingham")
        assert exc_info.value.query == "Birmingham"
        assert len(exc_info.value.matches) >= 2

    def test_no_fuzzy_results(self, monkeypatch):
        """Line 42: fuzzy_search returns empty list."""
        monkeypatch.setattr("choo.resolve.fuzzy_search", lambda *a, **kw: [])
        with pytest.raises(StationNotFound) as exc_info:
            resolve_station("zzzzz")
        assert exc_info.value.suggestions == []

    def test_single_good_match_no_ambiguity(self, monkeypatch):
        """Line 50->58: only one result, no ambiguity check needed."""
        monkeypatch.setattr(
            "choo.resolve.fuzzy_search",
            lambda q, limit=5: [("London Paddington", "PAD", 95.0)],
        )
        result = resolve_station("London Paddington")
        assert result == "PAD"
