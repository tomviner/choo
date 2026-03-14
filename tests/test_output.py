"""Tests for choo.output Rich formatters."""

from io import StringIO

import pytest
from rich.console import Console

from choo.output import (
    _status_text,
    format_board,
    format_next,
    format_service,
)
from traintimes.models import (
    LocationEvent,
    LocationResponse,
    LocationService,
    Pair,
    ServiceResponse,
    StationSummary,
)


def _console() -> Console:
    return Console(file=StringIO(), force_terminal=True, width=80)


def _make_location_service(**kwargs) -> LocationService:
    defaults = {
        "locationDetail": {
            "realtimeActivated": True,
            "tiploc": "WATRLMN",
            "crs": "WAT",
            "description": "London Waterloo",
            "gbttBookedDeparture": "1430",
            "realtimeDeparture": "1432",
            "realtimeGbttDepartureLateness": 2,
            "platform": "7",
            "displayAs": "CALL",
        },
        "serviceUid": "W12345",
        "runDate": "2026-03-14",
        "trainIdentity": "1A23",
        "atocCode": "SW",
        "atocName": "South Western Railway",
        "serviceType": "train",
        "isPassenger": True,
        "origin": [{"tiploc": "WATRLMN", "description": "London Waterloo"}],
        "destination": [{"tiploc": "WINDSRE", "description": "Windsor & Eton Riverside"}],
        "countdownMinutes": 15,
    }
    defaults.update(kwargs)
    return LocationService.model_validate(defaults)


def _make_location_response(services=None, **kwargs) -> LocationResponse:
    data = {
        "location": {"name": "London Waterloo", "crs": "WAT"},
        "services": services or [],
    }
    data.update(kwargs)
    return LocationResponse.model_validate(data)


def _make_service_response(**kwargs) -> ServiceResponse:
    defaults = {
        "serviceUid": "W12345",
        "runDate": "2026-03-14",
        "serviceType": "train",
        "isPassenger": True,
        "atocCode": "SW",
        "atocName": "South Western Railway",
        "performanceMonitored": True,
        "origin": [{"tiploc": "WATRLMN", "description": "London Waterloo"}],
        "destination": [{"tiploc": "WINDSRE", "description": "Windsor & Eton Riverside"}],
        "locations": [
            {
                "realtimeActivated": True,
                "tiploc": "WATRLMN",
                "description": "London Waterloo",
                "gbttBookedDeparture": "1430",
                "realtimeDeparture": "1430",
                "realtimeGbttDepartureLateness": 0,
                "displayAs": "ORIGIN",
            },
            {
                "realtimeActivated": True,
                "tiploc": "WINDSRE",
                "description": "Windsor & Eton Riverside",
                "gbttBookedArrival": "1520",
                "realtimeArrival": "1522",
                "realtimeGbttArrivalLateness": 2,
                "displayAs": "DESTINATION",
            },
        ],
    }
    defaults.update(kwargs)
    return ServiceResponse.model_validate(defaults)


class TestStatusText:
    def test_on_time(self):
        t = _status_text(0, False)
        assert "On time" in t.plain

    def test_late_small(self):
        t = _status_text(3, False)
        assert "+3 min" in t.plain

    def test_late_large(self):
        t = _status_text(8, False)
        assert "+8 min" in t.plain

    def test_early(self):
        t = _status_text(-2, False)
        assert "2 min early" in t.plain

    def test_cancelled(self):
        t = _status_text(None, True)
        assert "Cancelled" in t.plain


class TestFormatNext:
    def test_renders_departure_times_and_markers(self):
        svc = _make_location_service()
        resp = _make_location_response(services=[svc.model_dump(by_alias=True)])
        con = _console()
        format_next(con, resp)
        output = con.file.getvalue()
        assert "14:32" in output
        assert "\u2776" in output  # ❶

    def test_empty_services(self):
        resp = _make_location_response(services=[])
        con = _console()
        format_next(con, resp)
        output = con.file.getvalue()
        assert "No trains found." in output

    def test_filters_planned_cancellations(self):
        svc1 = _make_location_service(plannedCancel=True, serviceUid="A11111")
        svc2 = _make_location_service(plannedCancel=False, serviceUid="B22222")
        resp = _make_location_response(
            services=[
                svc1.model_dump(by_alias=True),
                svc2.model_dump(by_alias=True),
            ]
        )
        con = _console()
        format_next(con, resp)
        output = con.file.getvalue()
        assert "14:32" in output
        # Only one marker should appear (the non-cancelled one)
        assert "\u2776" in output
        assert "\u2777" not in output  # no second marker


class TestFormatBoard:
    def test_renders_table_with_uid(self):
        svc = _make_location_service()
        resp = _make_location_response(services=[svc.model_dump(by_alias=True)])
        con = _console()
        format_board(con, resp)
        output = con.file.getvalue()
        assert "W12345" in output
        assert "TIME" in output


class TestFormatService:
    def test_renders_station_names_and_times(self):
        resp = _make_service_response()
        con = _console()
        format_service(con, resp)
        output = con.file.getvalue()
        assert "London Waterloo" in output
        assert "Windsor" in output
        assert "14:30" in output
