"""Choo — UK train times CLI."""

from __future__ import annotations

import datetime as _dt
import json as _json
import sys
from typing import Optional

import typer
from rich.console import Console

from choo import __version__
from choo.config import get_aliases, get_auth
from choo.output import format_board, format_next, format_service, stderr_console
from choo.resolve import AmbiguousStation, StationNotFound, resolve_station
from traintimes.sdk import Location, ResponseError, Service

app = typer.Typer(
    name="choo",
    help="UK train times from your terminal.",
    no_args_is_help=False,
    invoke_without_command=True,
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
            "No API credentials found. Set CHOO_AUTH or RTT_AUTH "
            "environment variable (format: user:password)"
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


def _build_when(
    at: str | None, on: str | None
) -> _dt.date | _dt.datetime | None:
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

    response.services = response.services[:count]

    if json:
        typer.echo(_json.dumps(response.model_dump(by_alias=True), default=str))
    else:
        console = Console()
        format_next(console, response, to_station=to_crs)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
):
    """UK train times from your terminal."""
    if ctx.invoked_subcommand is not None:
        return
    _check_auth()
    aliases = get_aliases()
    if "home" in aliases and "work" in aliases:
        _run_next("home", "work")
    else:
        stderr_console().print(
            "Set up 'home' and 'work' aliases to use the default command.\n"
            "  choo alias set home <CRS>\n"
            "  choo alias set work <CRS>"
        )
        raise typer.Exit(code=1)


@app.command("next")
def next_cmd(
    from_station: str = typer.Argument(..., metavar="FROM"),
    to_station: str = typer.Argument(..., metavar="TO"),
    at: Optional[str] = typer.Option(None, "--at", "-t", help="Time HH:MM"),
    on: Optional[str] = typer.Option(None, "--on", "-d", help="Date (today/tomorrow/day name/ISO)"),
    count: int = typer.Option(3, "--count", "-n", help="Number of results"),
    arrivals: bool = typer.Option(False, "--arrivals", help="Show arrivals"),
    json: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Show next trains between two stations."""
    _run_next(from_station, to_station, at=at, on=on, count=count, arrivals=arrivals, json=json)


@app.command("board")
def board_cmd(
    station: str = typer.Argument(..., metavar="STATION"),
    to: Optional[str] = typer.Option(None, "--to", help="Filter to destination"),
    at: Optional[str] = typer.Option(None, "--at", "-t", help="Time HH:MM"),
    on: Optional[str] = typer.Option(None, "--on", "-d", help="Date"),
    arrivals: bool = typer.Option(False, "--arrivals", help="Show arrivals"),
    json: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Show departure board for a station."""
    _check_auth()
    from_crs = _resolve_or_exit(station)
    to_crs = _resolve_or_exit(to) if to else None
    when = _build_when(at, on)
    _print_interpretation(from_crs, to_crs, when)

    try:
        response = Location(from_crs, to_crs, when=when, arrivals=arrivals).get()
    except ResponseError as exc:
        stderr_console().print(f"API error: {exc.message}")
        raise typer.Exit(code=1)

    if json:
        typer.echo(_json.dumps(response.model_dump(by_alias=True), default=str))
    else:
        console = Console()
        format_board(console, response)
