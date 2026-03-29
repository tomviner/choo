# choo

UK train times from your terminal.

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
# 1. Get API credentials (free at https://api.rtt.io/)
choo auth

# 2. Set up aliases
choo alias set home HIB
choo alias set work KGX

# 3. Go
choo              # home -> work (default)
choo home work    # same thing, explicit
choo KGX YRK     # King's Cross to York
```

## Commands

### `choo` / `choo next FROM TO`

Show next trains between two stations.

```bash
choo PAD BRI                     # Paddington to Bristol
choo next PAD BRI --at 08:30     # departing around 08:30
choo next PAD BRI --on tomorrow  # tomorrow's trains
choo next PAD BRI --count 5      # show 5 results
```

### `choo board STATION`

Departure board for a station.

```bash
choo board KGX
choo board KGX --to YRK          # filter to York services
choo board KGX --arrivals         # arrivals instead of departures
```

### `choo service UID`

Full calling pattern for a service.

```bash
choo service G54821
choo service G54821 --on 2025-03-15
```

### `choo alias`

Manage station aliases.

```bash
choo alias set home HIB
choo alias set work KGX
choo alias list
choo alias remove work
```

### `choo auth`

Interactive setup for RTT API credentials. Saves to `~/.config/choo/auth`.

### `choo --version`

Print version and exit.

## Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--at` | `-t` | Time filter (`HH:MM`) |
| `--on` | `-d` | Date filter (`today`, `tomorrow`, day name, or ISO date) |
| `--count` | `-n` | Number of results (default: 3) |
| `--arrivals` | | Show arrivals instead of departures |
| `--json` | | Output raw JSON |
| `--verbose` | `-v` | Enable debug logging |

## Station resolution

Stations can be specified as:

- **CRS codes**: `KGX`, `PAD`, `BRI`
- **Aliases**: `home`, `work` (see `choo alias`)
- **Fuzzy names**: `kings cross`, `paddington` — choo uses fuzzy matching and will suggest corrections for ambiguous or unknown input

## Configuration

**Config directory**: `~/.config/choo/` (follows XDG via `platformdirs`)

- `auth` — API credentials (`user:password`)
- `aliases.json` — saved station aliases

**Environment variables** (override config files):

| Variable | Description |
|----------|-------------|
| `CHOO_AUTH` | API credentials (`user:password`), highest priority |
| `RTT_AUTH` | API credentials, fallback |
| `CHOO_ALIAS_HOME` | Override the `home` alias (any `CHOO_ALIAS_*` works) |

## Credits

- Train data from the [RealTimeTrains API](https://api.rtt.io/)
- Station data from [davwheat/uk-railway-stations](https://github.com/davwheat/uk-railway-stations) (ODbL)
