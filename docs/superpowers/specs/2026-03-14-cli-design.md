# CLI Design Spec: `choo`

A CLI for querying UK train times, wrapping the RealTimeTrains Pull API.

**Package name:** `choo` (PyPI) — installable via `uvx choo`
**Command:** `choo`

## Commands

### `choo [from] [to]` (default: `next`)

Show the next 1-3 trains between two stations. This is the default command — `choo home work` is equivalent to `choo next home work`.

Default time is now.

```
$ choo home work
  Highbury & Islington → Moorgate, today at 18:36        ← stderr, dim
  ❶ 18:42  Plat 2  On time   (6 min)
  ❷ 18:49  Plat 2  On time   (13 min)
  ❸ 18:57  Plat 1  +2 min    (21 min)
```

Flags:
- `--at HH:MM` / `-t` — time of day
- `--on DATE` / `-d` — date (ISO format, day name, or "tomorrow")
- `--arrivals` — show arrivals instead of departures
- `--json` — JSON output for scripting

### `choo board [station]`

Full departure board for a station. Shows all upcoming services.

```
$ choo board home
  Highbury & Islington — Departures, today at 18:36      ← stderr, dim
  TIME   DEST          PLAT  STATUS     OPERATOR    UID
  18:42  Moorgate       2    On time    Northern    G54821
  18:45  New Barnet     1    On time    Northern    G54830
  18:49  Moorgate       2    On time    Northern    G54825
  18:52  Welwyn G.C.    1    +3 min     Northern    G54832
  ...
```

Flags:
- `--to STATION` — filter to a destination
- `--arrivals` — arrival board instead
- `--at HH:MM` / `-t` — time of day
- `--on DATE` / `-d` — date
- `--json` — JSON output

### `choo service [UID]`

Full calling pattern for a single service. Shows every stop with scheduled and realtime times, platform, and live progress indicator.

```
$ choo service G54821
  G54821 — Northern — 14 Mar 2026                        ← stderr, dim
  High Barnet → Moorgate

  High Barnet      dep 18:20  18:20  ✓
  Totteridge       dep 18:24  18:24  ✓
  Woodside Park    dep 18:27  18:27  ✓
  ...
  Highbury & Isl.  dep 18:42  18:42  ◀ AT PLATFORM
  Essex Road       dep 18:44
  Old Street       dep 18:47
  Moorgate         arr 18:49
```

Flags:
- `--on DATE` / `-d` — date (default: today)
- `--json` — JSON output

### `choo alias`

Manage station aliases. Stored in XDG config directory (`~/.config/choo/aliases.json`). Also readable from environment variables (e.g., `CHOO_ALIAS_HOME=HIB`).

```
choo alias set home HIB
choo alias set work MOG
choo alias list
choo alias remove home
```

### `choo auth`

Guided setup for RTT API credentials. Walks the user through getting a token from the RTT website and storing it.

Credentials stored in XDG config or read from `RTT_AUTH` environment variable (existing SDK convention preserved).

## Station Resolution

Stations can be specified as:
1. **CRS code** — `HIB`, `MOG`, `KGX` (3-letter codes, passed directly to API)
2. **Alias** — `home`, `work` (resolved from config/env)
3. **Fuzzy name** — `highbury`, `kings cross` (matched against a station list)

Station list sourced from RTT API if possible (data changes over time). Implementation detail deferred — should not block initial development. Can start with a bundled list and upgrade later.

### Resolution rules

- Check aliases first
- If input is 3 uppercase letters, treat as CRS code
- Otherwise, fuzzy match against station names
- If no match: error with suggestions
- If ambiguous (multiple matches): error listing the matches with their CRS codes

## Answer Types

The CLI supports three answer types at different display densities:

| Type | Density | Count | Command |
|------|---------|-------|---------|
| Next | Compact | 1-3 | `choo [from] [to]` |
| Board | Compact | many | `choo board [station]` |
| Service | Full | 1 | `choo service [uid]` |

### Next (compact, 1-3 services)

Used when two stations are provided. Shows the next catchable trains with countdown, platform, and delay status. Designed for the "standing 5 minutes from the platform" use case — a single train leaving in 2 minutes isn't enough.

### Board (compact, many services)

Departure or arrival board. Table format with time, destination/origin, platform, status, operator, and service UID. The UID enables drill-down via `choo service`.

### Service (full, 1 service)

Complete calling pattern for one train. Every stop with:
- Scheduled time (GBTT)
- Realtime time (if available)
- Platform
- Live progress indicator (approaching, at platform, departed)
- Cancellation info with reason text

## Query Interpretation

Every command prints a dim, human-readable interpretation of the query to stderr:

```
Highbury & Islington → Moorgate, today at 14:30
```

This lets users verify what was understood without cluttering stdout. Especially useful when:
- Fuzzy matching resolved a name
- No results found ("no trains found for ...")
- An alias was expanded

## Error Handling

### No credentials

```
$ choo home work
  ✗ No RTT API credentials found.

  To get started:
  1. Register at https://api.rtt.io/
  2. Run: choo auth
```

### Station not found

```
$ choo flurble work
  ✗ Station not found: "flurble"

  Did you mean?
    Trimble       TRI
    Tumble        TUM
```

### Ambiguous station

```
$ choo king work
  ✗ Multiple matches for "king":

    Kings Cross        KGX
    Kings Langley      KGL
    Kings Norton       KNN
    Kings Sutton       KGS

  Use a CRS code or be more specific.
```

### No trains found

```
$ choo home work --at 02:00
  Highbury & Islington → Moorgate, today at 02:00        ← stderr
  No trains found.
```

## Output Modes

- **Default (Rich):** Coloured, formatted terminal output. Delays in yellow/red, on-time in green, countdowns, platform numbers.
- **`--json`:** Raw JSON to stdout. Stderr interpretation still printed (can be suppressed with `2>/dev/null`). Suitable for piping to `jq`.

## Configuration

### Storage

XDG Base Directory convention:
- Config: `~/.config/choo/` (aliases, auth)
- Overridable via `XDG_CONFIG_HOME`

### Environment variables

- `RTT_AUTH=user:password` — API credentials (existing convention)
- `CHOO_ALIAS_<NAME>=CRS` — station aliases via env (e.g., `CHOO_ALIAS_HOME=HIB`)
- Env vars take precedence over config files

## Technical Stack

- **CLI framework:** Typer
- **Output formatting:** Rich
- **Data validation:** Pydantic (existing models)
- **HTTP client:** requests (existing SDK)
- **Caching:** requests-cache (existing)
- **Config:** XDG base dirs
- **Station matching:** fuzzy matching library (e.g., thefuzz or rapidfuzz)
- **Python:** >=3.10

## Scope

### v1 (this spec)

- `next`, `board`, `service` commands
- `alias` management
- `auth` setup
- Station fuzzy matching
- Rich terminal output
- `--json` output mode
- Query interpretation on stderr

### Deferred (v2+)

- Aggregate/overview stats ("how's it running today?")
- Multi-leg journey planning
- Cancellation alternatives ("your train's cancelled, next option is...")
- Live/watch mode (auto-refresh)
