"""Choo — UK train times CLI."""

from __future__ import annotations

import datetime as _dt
import json as _json
import logging
from typing import Optional

import typer
from rich.console import Console

from choo import __version__
from choo.config import get_aliases, get_auth, remove_alias, set_alias
from choo.output import format_board, format_next, format_service, stderr_console
from choo.resolve import AmbiguousStation, StationNotFound, resolve_station
from traintimes.sdk import Location, ResponseError, Service


class _DefaultGroup(typer.core.TyperGroup):
    """Click Group subclass that routes unknown commands to 'next'."""

    def resolve_command(self, ctx, args):
        try:
            return super().resolve_command(ctx, args)
        except Exception:
            # "choo choo" → reverse home/work route (come home!)
            if args and args[0] == "choo":
                return super().resolve_command(ctx, ["choo-choo", *args[1:]])
            # Unknown subcommand — treat all args as 'next' arguments
            return super().resolve_command(ctx, ["next", *args])


app = typer.Typer(
    name="choo",
    help="UK train times from your terminal.",
    no_args_is_help=False,
    invoke_without_command=True,
    cls=_DefaultGroup,
)


_DAY_NAMES = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def version_callback(value: bool):
    if value:
        typer.echo(f"choo {__version__}")
        raise typer.Exit()


def _check_auth() -> tuple[str, str]:
    auth = get_auth()
    if auth is None:
        stderr_console().print(
            "No API credentials found. Run [bold]choo auth[/] to set up credentials,\n"
            "or set CHOO_AUTH / RTT_AUTH environment variable (format: user:password).\n"
            "Register at https://api-portal.rtt.io/"
        )
        raise typer.Exit(code=1)
    return auth


def _resolve_or_exit(station: str) -> str:
    try:
        return resolve_station(station)
    except StationNotFound as exc:
        con = stderr_console()
        con.print(f"Station not found: {exc.query!r}")
        if exc.suggestions:
            con.print("Did you mean:")
            for name, crs, score in exc.suggestions:
                con.print(f"  {name} ({crs})")
        raise typer.Exit(code=1)
    except AmbiguousStation as exc:
        con = stderr_console()
        con.print(f"Ambiguous station: {exc.query!r}")
        con.print("Did you mean:")
        for name, crs, score in exc.matches:
            con.print(f"  {name} ({crs})")
        raise typer.Exit(code=1)


def _build_when(at: str | None, on: str | None) -> _dt.date | _dt.datetime | None:
    today = _dt.date.today()
    date_part: _dt.date | None = None
    time_part: _dt.time | None = None

    if on is not None:
        lower = on.lower()
        if lower == "today":
            date_part = today
        elif lower == "tomorrow":
            date_part = today + _dt.timedelta(days=1)
        elif lower in _DAY_NAMES:
            target = _DAY_NAMES[lower]
            days_ahead = (target - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            date_part = today + _dt.timedelta(days=days_ahead)
        else:
            date_part = _dt.date.fromisoformat(on)

    if at is not None:
        parts = at.split(":")
        time_part = _dt.time(int(parts[0]), int(parts[1]))

    if date_part and time_part:
        return _dt.datetime.combine(date_part, time_part)
    if date_part:
        return date_part
    if time_part:
        return _dt.datetime.combine(today, time_part)
    return None


def _print_interpretation(
    from_name: str,
    to_name: str | None = None,
    when: _dt.date | _dt.datetime | None = None,
) -> None:
    con = stderr_console()
    parts = [f"  {from_name}"]
    if to_name:
        parts.append(f" \u2192 {to_name}")
    if isinstance(when, _dt.datetime):
        parts.append(f", {when:%A} at {when:%H:%M}")
    elif isinstance(when, _dt.date):
        parts.append(f", {when:%A %d %b}")
    else:
        now = _dt.datetime.now()
        parts.append(f", {now:%A} at {now:%H:%M}")
    con.print("".join(parts))


def _run_next(
    from_station: str,
    to_station: str,
    at: str | None = None,
    on: str | None = None,
    count: int = 3,
    arrivals: bool = False,
    json: bool = False,
) -> None:
    _check_auth()
    from_crs = _resolve_or_exit(from_station)
    to_crs = _resolve_or_exit(to_station)
    when = _build_when(at, on)
    _print_interpretation(from_crs, to_crs, when)

    try:
        response = Location(from_crs, to_crs, when=when, arrivals=arrivals).get()
    except ResponseError as exc:
        stderr_console().print(f"API error: {exc.message}")
        raise typer.Exit(code=1)

    # Filter to requested count
    response.services = response.services[:count]

    # If no services and no explicit date, try tomorrow
    if not response.services and on is None:
        tomorrow = _dt.date.today() + _dt.timedelta(days=1)
        try:
            response = Location(
                from_crs, to_crs, when=tomorrow, arrivals=arrivals
            ).get()
        except ResponseError:
            pass
        if response.services:
            response.services = response.services[:count]
            stderr_console().print("No more trains today.")
            _print_interpretation(from_crs, to_crs, tomorrow)

    if json:
        typer.echo(_json.dumps(response.model_dump(by_alias=True), default=str))
    else:
        console = Console()
        format_next(console, response, to_station=to_crs)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    at: Optional[str] = typer.Option(None, "--at", "-t", help="Time HH:MM"),
    on: Optional[str] = typer.Option(None, "--on", "-d", help="Date"),
    count: int = typer.Option(3, "--count", "-n", help="Number of results"),
    arrivals: bool = typer.Option(False, "--arrivals", help="Show arrivals"),
    json: bool = typer.Option(False, "--json", help="Output JSON"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show debug logging"),
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
):
    """UK train times from your terminal."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    if ctx.invoked_subcommand is not None:
        return
    _check_auth()
    aliases = get_aliases()
    if "home" in aliases and "work" in aliases:
        _run_next("home", "work", at=at, on=on, count=count, arrivals=arrivals, json=json)
    else:
        stderr_console().print(
            "Set up 'home' and 'work' aliases to use the default command.\n"
            "  choo alias set home <CRS>\n"
            "  choo alias set work <CRS>"
        )
        raise typer.Exit(code=1)


@app.command("choo-choo", hidden=True)
def choo_choo_cmd(
    at: Optional[str] = typer.Option(None, "--at", "-t", help="Time HH:MM"),
    on: Optional[str] = typer.Option(None, "--on", "-d", help="Date"),
    count: int = typer.Option(3, "--count", "-n", help="Number of results"),
    arrivals: bool = typer.Option(False, "--arrivals", help="Show arrivals"),
    json: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Reverse commute — next trains from work to home."""
    _check_auth()
    aliases = get_aliases()
    if "home" in aliases and "work" in aliases:
        _run_next("work", "home", at=at, on=on, count=count, arrivals=arrivals, json=json)
    else:
        stderr_console().print(
            "Set up 'home' and 'work' aliases:\n"
            "  choo alias set home <CRS>\n"
            "  choo alias set work <CRS>"
        )
        raise typer.Exit(code=1)


@app.command("next")
def next_cmd(
    from_station: Optional[str] = typer.Argument(None, metavar="FROM"),
    to_station: Optional[str] = typer.Argument(None, metavar="TO"),
    at: Optional[str] = typer.Option(None, "--at", "-t", help="Time HH:MM"),
    on: Optional[str] = typer.Option(
        None, "--on", "-d", help="Date (today/tomorrow/day name/ISO)"
    ),
    count: int = typer.Option(3, "--count", "-n", help="Number of results"),
    arrivals: bool = typer.Option(False, "--arrivals", help="Show arrivals"),
    json: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Show next trains between two stations."""
    if from_station is None or to_station is None:
        aliases = get_aliases()
        from_station = from_station or aliases.get("home")
        to_station = to_station or aliases.get("work")
        if not from_station or not to_station:
            stderr_console().print(
                "Missing FROM and/or TO. Set aliases or provide stations:\n"
                "  choo next KGX YRK\n"
                "  choo alias set home KGX\n"
                "  choo alias set work YRK"
            )
            raise typer.Exit(code=1)
    _run_next(
        from_station,
        to_station,
        at=at,
        on=on,
        count=count,
        arrivals=arrivals,
        json=json,
    )


@app.command("board")
def board_cmd(
    from_station: Optional[str] = typer.Argument(None, metavar="FROM"),
    to_station: Optional[str] = typer.Argument(None, metavar="TO"),
    at: Optional[str] = typer.Option(None, "--at", "-t", help="Time HH:MM"),
    on: Optional[str] = typer.Option(None, "--on", "-d", help="Date"),
    arrivals: bool = typer.Option(False, "--arrivals", help="Show arrivals"),
    json: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Show departure board for a station."""
    _check_auth()
    if from_station is None:
        aliases = get_aliases()
        from_station = aliases.get("home")
        if not from_station:
            stderr_console().print(
                "Missing FROM station. Set alias or provide station:\n"
                "  choo board KGX\n"
                "  choo alias set home KGX"
            )
            raise typer.Exit(code=1)
    from_crs = _resolve_or_exit(from_station)
    to_crs = _resolve_or_exit(to_station) if to_station else None
    when = _build_when(at, on)
    _print_interpretation(from_crs, to_crs, when)

    try:
        response = Location(from_crs, to_crs, when=when, arrivals=arrivals).get()
    except ResponseError as exc:
        stderr_console().print(f"API error: {exc.message}")
        raise typer.Exit(code=1)

    # If no services and no explicit date, try tomorrow
    if not response.services and on is None:
        tomorrow = _dt.date.today() + _dt.timedelta(days=1)
        try:
            response = Location(
                from_crs, to_crs, when=tomorrow, arrivals=arrivals
            ).get()
        except ResponseError:
            pass
        if response.services:
            stderr_console().print("No more trains today.")
            _print_interpretation(from_crs, to_crs, tomorrow)

    if json:
        typer.echo(_json.dumps(response.model_dump(by_alias=True), default=str))
    else:
        console = Console()
        format_board(console, response)


@app.command()
def service(
    uid: str = typer.Argument(..., metavar="UID", help="Service UID (e.g., G54821)"),
    on: Optional[str] = typer.Option(None, "--on", "-d", help="Date (default: today)"),
    use_json: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Full calling pattern for a service."""
    _check_auth()
    date = _dt.date.today()
    if on:
        when = _build_when(at=None, on=on)
        if isinstance(when, _dt.datetime):
            date = when.date()
        else:
            date = when

    err = stderr_console()
    try:
        response = Service(uid, date).get()
    except ResponseError as e:
        err.print(f"[bold red]✗ API error: {e.message}[/]")
        raise typer.Exit(1)

    err.print(f"  {uid} — {response.atoc_name} — {response.run_date:%d %b %Y}")

    if use_json:
        print(_json.dumps(response.model_dump(by_alias=True), default=str, indent=2))
    else:
        console = Console()
        format_service(console, response)


# ── Alias subcommands ──────────────────────────────────────────────

alias_app = typer.Typer(help="Manage station aliases.")
app.add_typer(alias_app, name="alias")


@alias_app.command("set")
def alias_set(
    name: str = typer.Argument(..., help="Alias name (e.g., 'home')"),
    crs: str = typer.Argument(..., help="Station CRS code (e.g., 'HIB')"),
):
    """Save a station alias."""
    err = stderr_console()
    try:
        set_alias(name, crs)
    except ValueError as e:
        err.print(f"[bold red]✗ {e}[/]")
        raise typer.Exit(1)
    console = Console()
    console.print(f"  Alias '{name}' → {crs.upper()}")


@alias_app.command("list")
def alias_list():
    """Show all saved aliases."""
    aliases = get_aliases()
    console = Console()
    if not aliases:
        console.print("  No aliases configured.")
        return
    for name, crs in sorted(aliases.items()):
        console.print(f"  {name:<15} {crs}")


@alias_app.command("remove")
def alias_remove(
    name: str = typer.Argument(..., help="Alias name to remove"),
):
    """Remove a station alias."""
    remove_alias(name)
    console = Console()
    console.print(f"  Removed alias '{name}'")


# ── Auth command ────────────────────────────────────────────────────


@app.command()
def auth():
    """Set up RTT API credentials."""
    from choo.config import _config_dir

    err = stderr_console()
    err.print()
    err.print("  RTT API Credentials Setup")
    err.print()
    err.print("  To use choo, you need a free API token from RealTimeTrains:")
    err.print()
    err.print(
        "  1. Create an account at https://www.realtimetrains.co.uk/ (if you don't have one)"
    )
    err.print("  2. Visit https://api-portal.rtt.io/")
    err.print("  3. Sign in with your RTT account")
    err.print("  4. Request an API token")
    err.print()
    err.print("  The API is free for personal, non-commercial use.")
    err.print("  For commercial use, contact hello@realtimetrains.com")
    err.print()
    err.print("  Once you have your credentials, enter them below:")
    err.print()

    username = typer.prompt("  Username")
    password = typer.prompt("  Password", hide_input=True)

    config_dir = _config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    auth_file = config_dir / "auth"
    auth_file.write_text(f"{username}:{password}")
    auth_file.chmod(0o600)

    console = Console()
    err.print()

    # Verify credentials with a test API call
    try:
        import os

        os.environ["CHOO_AUTH"] = f"{username}:{password}"
        Location("PAD").get()
        console.print("  [green]✓ Credentials saved and verified.[/]")
    except Exception:
        console.print("  [yellow]✓ Credentials saved but verification failed.[/]")
        console.print("  [yellow]  Check your username and password are correct.[/]")


# ── Stations subcommands ───────────────────────────────────────────

stations_app = typer.Typer(help="Manage station data.")
app.add_typer(stations_app, name="stations")


@stations_app.command("update")
def stations_update():
    """Fetch latest station data from GitHub."""
    from choo.stations import fetch_stations

    console = Console()
    count = fetch_stations()
    console.print(f"  Updated {count} stations.")


@stations_app.command("list")
def stations_list():
    """Show total number of loaded stations."""
    from choo.stations import load_stations

    console = Console()
    stations = load_stations()
    console.print(f"  {len(stations)} stations loaded.")
