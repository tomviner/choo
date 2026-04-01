# choo

UK train times from your terminal.

**`choo`** to go to work. **`choo choo`** to come home.

## Install

```
uvx choo
```

Or install permanently:

```
pip install choo
```

## Quick start

```bash
# 1. Get API credentials
choo auth

# 2. Set up your commute
choo config alias.home "Highbury & Islington"
choo config alias.work "London Bridge"

# 3. Go
choo              # next trains home → work
choo choo         # reverse: work → home
choo "kings cross" york     # fuzzy station names work too
```

## Commands

### `choo` / `choo next [FROM] [TO]`

Show next trains between two stations. Defaults to `home` → `work` aliases.

```bash
choo                                 # home → work, now
choo --on tomorrow                   # home → work, tomorrow
choo paddington bristol              # fuzzy station names
choo next paddington bristol --at 08:30   # departing around 08:30
choo next KGX YRK --on monday        # CRS codes work too
choo next KGX YRK --count 10         # show 10 results
```

No trains running? Choo automatically shows tomorrow's first services.

### `choo choo`

Reverse commute — next trains from `work` → `home`.

```bash
choo choo                            # heading home
choo choo --on friday                # Friday evening trains
choo choo board                      # departure board from work
```

### `choo board [FROM] [TO]`

Departure board for a station. Same arguments as `next`, but shows all services in a table.

```bash
choo board "kings cross"             # all departures from King's Cross
choo board "kings cross" york        # filtered to York
choo board KGX --arrivals            # arrivals instead
choo board --on tomorrow             # defaults to home station
```

### `choo service UID`

Full calling pattern for a service. Get the UID from `board` output.

```bash
choo service C41053
choo service C41053 --on 2026-03-16
```

### `choo config`

Get/set configuration, like `git config`.

```bash
choo config alias.home "Highbury & Islington"   # set station alias
choo config alias.work "London Bridge"
choo config next.count 10                       # default number of results
choo config alias.home                          # get a value
choo config                                     # list all
choo config --unset alias.home                  # remove
```

### `choo auth`

Guided setup for RTT API credentials. Walks you through registration at [api-portal.rtt.io](https://api-portal.rtt.io/) and verifies your credentials.

### `choo stations update`

Fetch the latest station data from GitHub (2,599 UK stations).

## Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--at` | `-t` | Time filter (`HH:MM`) |
| `--on` | `-d` | Date filter (`today`, `tomorrow`, day name, or `YYYY-MM-DD`) |
| `--count` | `-n` | Number of results (default: 5, configurable via `next.count`) |
| `--arrivals` | | Show arrivals instead of departures |
| `--json` | | Output JSON for scripting |
| `--verbose` | `-v` | Enable debug logging |

## Station resolution

Stations can be specified as:

- **CRS codes**: `KGX`, `PAD`, `BRI` (3 uppercase letters)
- **Aliases**: `home`, `work` (see `choo config`)
- **Fuzzy names**: `"kings cross"`, `paddington` — matched against 2,599 stations with suggestions for ambiguous input

## Configuration

**Config file**: `~/.config/choo/config.json` (XDG via `platformdirs`)

| Key | Example | Description |
|-----|---------|-------------|
| `alias.home` | `HIB` or `"Highbury & Islington"` | Station alias |
| `alias.work` | `LBG` or `"London Bridge"` | Station alias |
| `alias.*` | any CRS | Custom aliases |
| `next.count` | `5` | Default result count |

**Environment variables** (override config):

| Variable | Description |
|----------|-------------|
| `CHOO_AUTH` | API credentials (`user:password`) |
| `RTT_AUTH` | API credentials (fallback) |
| `CHOO_ALIAS_*` | Station aliases (e.g., `CHOO_ALIAS_HOME=HIB`) |

## traintimes SDK

Choo is built on the `traintimes` Python SDK, which wraps the [RealTimeTrains Pull API](https://www.realtimetrains.co.uk/about/developer/pull/docs/).

```python
from traintimes.sdk import Location, Service

# Departures from Highbury & Islington
response = Location("HIB").get()
for svc in response.services:
    print(svc.service_uid, svc.location_detail.gbtt_booked_departure)

# Full calling pattern for a service
service = Service("C41053", datetime.date.today()).get()
for loc in service.locations:
    print(loc.description, loc.gbtt_booked_departure)
```

The SDK provides Pydantic models for all API responses — see `traintimes/models.py`.

## Credits

- Train data from the [RealTimeTrains API](https://www.realtimetrains.co.uk/)
- Station data from [davwheat/uk-railway-stations](https://github.com/davwheat/uk-railway-stations), licensed under the [Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/1-0/)
