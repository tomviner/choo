"""Bundled station list with fuzzy matching."""

import csv
import io
from functools import lru_cache
from importlib import resources
from pathlib import Path

import httpx
from platformdirs import user_cache_dir
from rapidfuzz import fuzz, process


STATIONS_URL = (
    "https://raw.githubusercontent.com/davwheat/uk-railway-stations/main/stations.csv"
)


def cached_stations_path() -> Path:
    """Return XDG cache path for stations CSV."""
    return Path(user_cache_dir("choo")) / "stations.csv"


@lru_cache
def load_stations() -> dict[str, str]:
    """Load CRS -> name mapping, preferring cached file over bundled CSV."""
    cached = cached_stations_path()
    if cached.exists():
        stations = {}
        with open(cached) as f:
            reader = csv.DictReader(f)
            for row in reader:
                stations[row["CRS"]] = row["Name"]
        return stations

    stations = {}
    data_file = resources.files("choo._data").joinpath("stations.csv")
    with resources.as_file(data_file) as path:
        with open(path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                stations[row["CRS"]] = row["Name"]
    return stations


def fetch_stations() -> int:
    """Download stations from GitHub, save to cache, return count."""
    response = httpx.get(STATIONS_URL)
    response.raise_for_status()

    stations = {}
    reader = csv.DictReader(io.StringIO(response.text))
    for row in reader:
        crs = row.get("crsCode", "").strip()
        name = row.get("stationName", "").strip()
        if crs:
            stations[crs] = name

    path = cached_stations_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["CRS", "Name"])
        writer.writeheader()
        for crs, name in sorted(stations.items()):
            writer.writerow({"CRS": crs, "Name": name})

    load_stations.cache_clear()
    return len(stations)


def fuzzy_search(query: str, limit: int = 5) -> list[tuple[str, str, float]]:
    """Return [(name, crs, score), ...] sorted by match quality."""
    stations = load_stations()
    name_to_crs = {name: crs for crs, name in stations.items()}
    results = process.extract(
        query,
        name_to_crs.keys(),
        scorer=fuzz.WRatio,
        limit=limit,
    )
    return [(name, name_to_crs[name], score) for name, score, _ in results]
