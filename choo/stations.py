"""Bundled station list with fuzzy matching."""

import csv
from functools import lru_cache
from importlib import resources

from rapidfuzz import fuzz, process


@lru_cache
def load_stations() -> dict[str, str]:
    """Load CRS -> name mapping from bundled CSV."""
    stations = {}
    data_file = resources.files("choo._data").joinpath("stations.csv")
    with resources.as_file(data_file) as path:
        with open(path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                stations[row["CRS"]] = row["Name"]
    return stations


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
