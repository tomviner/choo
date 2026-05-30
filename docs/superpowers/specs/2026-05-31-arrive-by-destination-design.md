# Anchor `--at` + `--arrivals` on destination arrival

Reference: [tomviner/choo#16](https://github.com/tomviner/choo/issues/16)

## Problem

`choo next FROM TO --at 11:00 --arrivals` is meant to mean "trains arriving at TO around 11:00", but today both `--at` and `--arrivals` anchor on the **origin** (board) station, so the listed times are departures from FROM near 11:00 — not arrivals into TO. Users get plausible-looking but wrong results, and there's no way to express the natural commuter question "what gets me to X by 11?".

Root cause: the RTT location endpoint anchors time and the `/arrivals` suffix on `<station>` in `/search/<station>/to/<toStation>/<date>/<time>/arrivals`. The CLI passes the FROM as `<station>`, so the anchor lands on the wrong end of the journey. See `traintimes/sdk.py:95-112` and `choo/app.py:170-214`.

## Goals

- `--at HH:MM --arrivals` combined with a TO station means "around arrival HH:MM at TO" — the obvious read.
- Solve it with one API call per query (no per-service lookup loop).
- Don't break any existing behaviour.

## Non-goals

- A new `--arrive-by` / `--arrive-around` flag.
- "Arrive by" semantics (latest train ≤ HH:MM); the API's window around the anchor is acceptable.
- A new `Journey` SDK abstraction; YAGNI for one CLI consumer.
- Changing `board STATION --arrivals` (no TO) — already coherent.

## UX

| Command | Today | After |
|---|---|---|
| `choo next HIB WAE --at 11:00 --arrivals` | dep from HIB ~11:00 (mislabeled) | arr WAE ~11:00 (from HIB) |
| `choo next HIB WAE --arrivals` (no `--at`) | nonsense | next arrivals into WAE from HIB |
| `choo next HIB WAE --at 11:00` (no `--arrivals`) | dep HIB ~11:00 | **unchanged** |
| `choo board HIB WAE --at 11:00 --arrivals` | dep board at HIB | arr WAE ~11:00 (from HIB) |
| `choo board WAT --arrivals` (no TO) | arrivals at WAT | **unchanged** |
| `choo` / `choo choo` with same flags | follow `_run_next` | follow `_run_next` (changed via shared code) |

Rule: **`--arrivals` combined with a TO destination anchors on arrival at TO.** Without TO it retains its current meaning (arrivals at the board station).

`_print_interpretation` switches its time phrasing in arrivals-with-TO mode:

```
HIB → WAE, arrive Sunday at 11:00
```

`--arrivals` help text becomes: *"Show arrivals (at destination when TO is given)."*

## Implementation

### SDK: support `/from/<crs>` filter

`traintimes/models.py` — extend `LocationRequest`:

```python
class LocationRequest(BaseModel):
    ...
    station: str
    to_station: str | None = Field(default=None, alias="toStation")
    from_station: str | None = Field(default=None, alias="fromStation")
    date: _dt.date | None = None
    time: _dt.time | None = None
    arrivals: bool = False

    @field_validator("station", "to_station", "from_station")
    @classmethod
    def _strip_whitespace(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value

    @classmethod
    def from_inputs(
        cls,
        station: str,
        to_station: str | None = None,
        from_station: str | None = None,
        when: _dt.date | _dt.datetime | None = None,
        arrivals: bool = False,
    ) -> "LocationRequest":
        if to_station and from_station:
            raise ValueError("Cannot combine to_station and from_station in one query")
        ...
```

`traintimes/sdk.py` — extend `Location`:

- `uri_template = '/search/{station}{+tostation}{+fromstation}{+date}{+time}{/arrivals}'`
- `__init__` accepts `from_station`, sets `context['fromstation'] = f'/from/{crs}'` when present.
- Update class docstring to mention the `/from/<crs>` form ("you can apply to OR from filtering").

Server response shape is unchanged, so no `LocationResponse` model changes.

### CLI: swap-at-the-edge

`choo/app.py` — `_run_next` and `board_cmd`. When `arrivals AND to_crs`:

```python
response = Location(
    station=to_crs,
    from_station=from_crs,
    when=when,
    arrivals=True,
).get()
```

Otherwise the existing `Location(from_crs, to_crs, when=when, arrivals=arrivals)` call is unchanged. The auto-retry-tomorrow branch uses the same swapped args. Both commands then pass `arrivals=arrivals` into the formatter.

`_print_interpretation` gains a small change so that, in arrivals-with-TO mode, the time clause reads "arrive Sunday at 11:00" instead of "Sunday at 11:00".

### Output: arrivals-aware formatters

`choo/output.py`:

- `format_next(console, response, *, arrivals=False, to_station=None)`:
  - In arrivals mode, the time on each line is `_arrival_time(evt)` and we append `from <origin>` where `<origin>` is `evt.origin[0].description` (or the service's `origin`).
  - Example line: `❶ 11:00 from Hastings  Plat 4  On time`.
- `format_board(console, response, *, arrivals=False)`:
  - In arrivals mode, table columns become `TIME | ORIGIN | PLATFORM | STATUS | OPERATOR | UID`.
  - Add a `_origin_name(svc)` helper mirroring the existing `_dest_name`.

## Edge cases

- `--arrivals` + TO but no `--at`: works; RTT defaults to "now" at the destination.
- `FROM == TO`: let the API error surface; not worth special-casing.
- Cancelled services: existing `planned_cancel` / `display_as` checks apply unchanged.
- `to_station and from_station` both set: model raises `ValueError` (defensive — the CLI never does this, but the SDK is now public surface for both filters).

## Tests

Add to existing `tests/`:

- **SDK** — `LocationRequest.from_inputs(station="WAE", from_station="HIB", when=...)`:
  - Produces URL `/search/WAE/from/HIB/2026/05/31/1100/arrivals` when arrivals=True and time set.
  - Combining `to_station` and `from_station` raises `ValueError`.
- **CLI** — patching `Location` to record args:
  - `_run_next(from="HIB", to="WAE", arrivals=True, at="11:00")` calls `Location(station="WAE", from_station="HIB", when=..., arrivals=True)`.
  - `_run_next(... arrivals=False ...)` calls `Location(station="HIB", to_station="WAE", ...)` (unchanged).
  - Same two cases for `board_cmd`.
- **Output** — recorded fixture response (one `LocationResponse` JSON, mocked) for HIB→WAE arrivals ~11:00:
  - `format_next(..., arrivals=True)` lines start with the arrival time and include `from <origin>`.
  - `format_board(..., arrivals=True)` table headers include `ORIGIN`.

No changes expected in existing tests; if any break, it points at an unintended behaviour change in the non-arrivals path.

## Release notes (for v0.1.5)

> `--at HH:MM --arrivals` combined with a destination now anchors on arrival time at the destination (was: departure time at the origin). `choo board STATION --arrivals` without a destination is unchanged.
