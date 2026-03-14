"""Station name resolution: alias -> CRS -> fuzzy match."""

import re

from choo.config import get_aliases
from choo.stations import fuzzy_search


class StationNotFound(Exception):
    def __init__(self, query: str, suggestions: list[tuple[str, str, float]]):
        self.query = query
        self.suggestions = suggestions
        super().__init__(f"Station not found: {query!r}")


class AmbiguousStation(Exception):
    def __init__(self, query: str, matches: list[tuple[str, str, float]]):
        self.query = query
        self.matches = matches
        super().__init__(f"Multiple matches for {query!r}")


_CRS_RE = re.compile(r"^[A-Z]{3}$")
_FUZZY_THRESHOLD = 80
_AMBIGUITY_GAP = 10


def resolve_station(input_: str) -> str:
    """Resolve user input to a CRS code."""
    # 1 & 2: Check aliases
    aliases = get_aliases()
    if input_.lower() in aliases:
        return aliases[input_.lower()]

    # 3: CRS code passthrough
    if _CRS_RE.match(input_):
        return input_

    # 4: Fuzzy match
    results = fuzzy_search(input_, limit=5)
    if not results:
        raise StationNotFound(input_, [])

    best_name, best_crs, best_score = results[0]

    if best_score < _FUZZY_THRESHOLD:
        raise StationNotFound(input_, results)

    # Check for ambiguity
    if len(results) > 1:
        _, _, second_score = results[1]
        if best_score - second_score < _AMBIGUITY_GAP:
            close_matches = [
                (n, c, s) for n, c, s in results if best_score - s < _AMBIGUITY_GAP
            ]
            raise AmbiguousStation(input_, close_matches)

    return best_crs
