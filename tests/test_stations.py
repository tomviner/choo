"""Tests for stations loading, fetching, and CLI commands."""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from choo.app import app
from choo.stations import fetch_stations, load_stations


runner = CliRunner()

GITHUB_CSV = (
    "stationName,lat,long,crsCode,iataAirportCode,constituentCountry\n"
    "London Paddington,51.5154,-0.1755,PAD,,England\n"
    "Birmingham New Street,52.4778,-1.8985,BHM,,England\n"
    ",52.0,0.0,,,England\n"
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear lru_cache before each test."""
    load_stations.cache_clear()
    yield
    load_stations.cache_clear()


def test_load_stations_uses_cached_file(tmp_path):
    cached = tmp_path / "stations.csv"
    cached.write_text("CRS,Name\nTST,Test Station\n")

    with patch("choo.stations.cached_stations_path", return_value=cached):
        result = load_stations()

    assert result == {"TST": "Test Station"}


def test_load_stations_falls_back_to_bundled(tmp_path):
    cached = tmp_path / "nonexistent" / "stations.csv"

    with patch("choo.stations.cached_stations_path", return_value=cached):
        result = load_stations()

    # Should load bundled data — just check it's non-empty with known stations
    assert len(result) > 100
    assert "PAD" in result


def test_fetch_stations_with_mocked_http(tmp_path):
    cached = tmp_path / "stations.csv"

    class FakeResponse:
        text = GITHUB_CSV

        def raise_for_status(self):
            pass

    with (
        patch("choo.stations.cached_stations_path", return_value=cached),
        patch("choo.stations.httpx.get", return_value=FakeResponse()),
    ):
        count = fetch_stations()

    assert count == 2
    assert cached.exists()
    content = cached.read_text()
    assert "PAD" in content
    assert "BHM" in content
    # Row with empty crsCode should be skipped
    assert content.count("\n") == 3  # header + 2 data rows


def test_cli_stations_update(tmp_path):
    cached = tmp_path / "stations.csv"

    class FakeResponse:
        text = GITHUB_CSV

        def raise_for_status(self):
            pass

    with (
        patch("choo.stations.cached_stations_path", return_value=cached),
        patch("choo.stations.httpx.get", return_value=FakeResponse()),
    ):
        result = runner.invoke(app, ["stations", "update"])

    assert result.exit_code == 0
    assert "Updated 2 stations" in result.output


def test_cli_stations_list(tmp_path):
    cached = tmp_path / "stations.csv"
    cached.write_text("CRS,Name\nAAA,Alpha\nBBB,Beta\n")

    with patch("choo.stations.cached_stations_path", return_value=cached):
        result = runner.invoke(app, ["stations", "list"])

    assert result.exit_code == 0
    assert "2 stations loaded" in result.output
