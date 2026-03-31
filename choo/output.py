"""Rich-formatted display functions for CLI views."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.text import Text

from traintimes.models import (
    LocationEvent,
    LocationResponse,
    LocationService,
    ServiceLocationState,
    ServiceResponse,
)


_MARKERS = "\u2776\u2777\u2778\u2779\u277a\u277b\u277c\u277d\u277e\u277f"


def stderr_console() -> Console:
    """Return a Console writing to stderr in dim style."""
    return Console(stderr=True, style="dim")


def _status_text(lateness: int | None, cancelled: bool) -> Text:
    """Return colored Text for delay status."""
    if cancelled:
        return Text("Cancelled", style="red")
    if lateness is None:
        return Text("")
    if lateness == 0:
        return Text("On time", style="green")
    if lateness < 0:
        return Text(f"{abs(lateness)} min early", style="green")
    if lateness <= 5:
        return Text(f"+{lateness} min", style="yellow")
    return Text(f"+{lateness} min", style="red")


def _departure_time(event: LocationEvent) -> str:
    """Extract HH:MM display time from LocationEvent."""
    raw = event.realtime_departure or event.gbtt_booked_departure or ""
    if len(raw) >= 4:
        return f"{raw[:2]}:{raw[2:4]}"
    return raw


def _arrival_time(event: LocationEvent) -> str:
    """Extract HH:MM arrival time from LocationEvent."""
    raw = event.realtime_arrival or event.gbtt_booked_arrival or ""
    if len(raw) >= 4:
        return f"{raw[:2]}:{raw[2:4]}"
    return raw


def _booked_dep_time(event: LocationEvent) -> str:
    raw = event.gbtt_booked_departure or ""
    if len(raw) >= 4:
        return f"{raw[:2]}:{raw[2:4]}"
    return raw


def _booked_arr_time(event: LocationEvent) -> str:
    raw = event.gbtt_booked_arrival or ""
    if len(raw) >= 4:
        return f"{raw[:2]}:{raw[2:4]}"
    return raw


def _dest_name(service: LocationService) -> str:
    """Get destination name from LocationService."""
    if service.destination:
        return service.destination[0].description
    if service.location_detail.destination:
        return service.location_detail.destination[0].description
    return ""


def format_next(
    console: Console,
    response: LocationResponse,
    to_station: str | None = None,
) -> None:
    """Compact 'next train' display."""
    services = [s for s in response.services if not s.planned_cancel]
    if not services:
        console.print("No trains found.")
        return

    for i, svc in enumerate(services):
        marker = _MARKERS[i] if i < len(_MARKERS) else f"({i + 1})"
        evt = svc.location_detail
        dep = _departure_time(evt)
        plat = f"Plat {evt.platform}" if evt.platform else ""
        lateness = evt.realtime_gbtt_departure_lateness
        _CANCEL = ("CANCELLED_CALL", "CANCELLED_PASS")
        cancelled = evt.display_as in _CANCEL if evt.display_as else False
        status = _status_text(lateness, cancelled)
        countdown = (
            f"{svc.countdown_minutes}m" if svc.countdown_minutes is not None else ""
        )

        line = Text()
        line.append(f"{marker} ")
        line.append(f"{dep} ")
        if plat:
            line.append(f"{plat} ")
        line.append_text(status)
        if countdown:
            line.append(f" ({countdown})")
        console.print(line)


def format_board(console: Console, response: LocationResponse) -> None:
    """Departure board table."""
    table = Table()
    table.add_column("TIME")
    table.add_column("DEST")
    table.add_column("PLATFORM")
    table.add_column("STATUS")
    table.add_column("OPERATOR")
    table.add_column("UID", style="dim cyan")

    for svc in response.services:
        evt = svc.location_detail
        dep = _departure_time(evt)
        dest = _dest_name(svc)
        plat = evt.platform or ""
        lateness = evt.realtime_gbtt_departure_lateness
        _CANCEL = ("CANCELLED_CALL", "CANCELLED_PASS")
        cancelled = evt.display_as in _CANCEL if evt.display_as else False
        status = _status_text(lateness, cancelled)

        table.add_row(
            dep,
            dest,
            plat,
            status,
            svc.atoc_name,
            svc.service_uid,
        )

    console.print(table)


def format_service(console: Console, response: ServiceResponse) -> None:
    """Full calling pattern display."""
    origin = response.origin[0].description if response.origin else "?"
    dest = response.destination[0].description if response.destination else "?"
    console.print(Text(f"{origin} \u2192 {dest}", style="bold"))

    for loc in response.locations:
        name = (loc.description or loc.tiploc)[:20].ljust(20)

        # Determine dep or arr time
        booked = _booked_dep_time(loc) or _booked_arr_time(loc)
        realtime = _departure_time(loc) or _arrival_time(loc)
        lateness = (
            loc.realtime_gbtt_departure_lateness or loc.realtime_gbtt_arrival_lateness
        )

        # Time coloring
        if lateness is None or lateness == 0:
            time_style = "green"
        elif lateness <= 5:
            time_style = "yellow"
        else:
            time_style = "red"

        # Progress indicator
        progress = ""
        if loc.service_location == ServiceLocationState.AT_PLATFORM:
            progress = "\u25c0 AT PLATFORM"
        elif loc.service_location == ServiceLocationState.APPROACHING_PLATFORM:
            progress = "\u25c0 APPROACHING"
        elif lateness is not None and loc.realtime_departure_actual:
            progress = "\u2713"

        line = Text()
        line.append(f"{name} ")
        if booked:
            line.append(f"{booked} ")
        if realtime:
            line.append(realtime, style=time_style)
            line.append(" ")
        if progress:
            line.append(progress)
        console.print(line)
