"""Tests for choo.output Rich formatters."""

from io import StringIO

from rich.console import Console

from choo.output import (
    _status_text,
    format_board,
    format_next,
    format_service,
)
from traintimes.models import (
    LocationResponse,
    LocationService,
    ServiceResponse,
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
        "destination": [
            {"tiploc": "WINDSRE", "description": "Windsor & Eton Riverside"}
        ],
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
        "destination": [
            {"tiploc": "WINDSRE", "description": "Windsor & Eton Riverside"}
        ],
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

    def test_none_lateness_not_cancelled(self):
        """Line 32: lateness is None and not cancelled returns empty."""
        t = _status_text(None, False)
        assert t.plain == ""


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


class TestFormatNext_Extended:
    def test_no_platform(self):
        """Line 103->105: service with no platform."""
        svc = _make_location_service()
        svc_data = svc.model_dump(by_alias=True)
        svc_data["locationDetail"]["platform"] = None
        resp = _make_location_response(services=[svc_data])
        con = _console()
        format_next(con, resp)
        output = con.file.getvalue()
        assert "14:32" in output
        # no platform prefix expected
        assert "14:32" in output

    def test_no_countdown(self):
        """Line 106->108: service with no countdown minutes."""
        svc = _make_location_service(countdownMinutes=None)
        resp = _make_location_response(services=[svc.model_dump(by_alias=True)])
        con = _console()
        format_next(con, resp)
        output = con.file.getvalue()
        # Should still render without "(Xm)"
        assert "14:32" in output

    def test_cancelled_service(self):
        """Line 32: _status_text for None lateness (no realtime data)."""
        svc = _make_location_service()
        svc_data = svc.model_dump(by_alias=True)
        svc_data["locationDetail"]["realtimeGbttDepartureLateness"] = None
        svc_data["locationDetail"]["displayAs"] = "CANCELLED_CALL"
        resp = _make_location_response(services=[svc_data])
        con = _console()
        format_next(con, resp)
        output = con.file.getvalue()
        assert "Cancelled" in output


class TestFormatBoard_Extended:
    def test_no_destination(self):
        """Line 76: _dest_name with no destination."""
        svc = _make_location_service()
        svc_data = svc.model_dump(by_alias=True)
        svc_data["destination"] = []
        resp = _make_location_response(services=[svc_data])
        con = _console()
        format_board(con, resp)
        output = con.file.getvalue()
        assert "W12345" in output

    def test_dest_fallback_to_location_detail(self):
        """_dest_name falls back to locationDetail.destination."""
        svc = _make_location_service()
        svc_data = svc.model_dump(by_alias=True)
        svc_data["destination"] = None
        svc_data["locationDetail"]["destination"] = [
            {"tiploc": "MOORGT", "description": "Moorgate"}
        ]
        resp = _make_location_response(services=[svc_data])
        con = _console()
        format_board(con, resp)
        output = con.file.getvalue()
        assert "Moorgate" in output

    def test_arrival_time_short_raw(self):
        """Line 55/69: _arrival_time / _booked_arr_time with short raw string."""
        svc = _make_location_service()
        svc_data = svc.model_dump(by_alias=True)
        svc_data["locationDetail"]["realtimeDeparture"] = None
        svc_data["locationDetail"]["gbttBookedDeparture"] = None
        resp = _make_location_response(services=[svc_data])
        con = _console()
        format_board(con, resp)
        # Should not crash


class TestFormatService:
    def test_renders_station_names_and_times(self):
        resp = _make_service_response()
        con = _console()
        format_service(con, resp)
        output = con.file.getvalue()
        assert "London Waterloo" in output
        assert "Windsor" in output
        assert "14:30" in output

    def test_at_platform_indicator(self):
        """Line 160: AT_PLATFORM progress indicator."""
        resp = _make_service_response(
            locations=[
                {
                    "realtimeActivated": True,
                    "tiploc": "WATRLMN",
                    "description": "London Waterloo",
                    "gbttBookedDeparture": "1430",
                    "realtimeDeparture": "1430",
                    "realtimeGbttDepartureLateness": 0,
                    "displayAs": "ORIGIN",
                    "serviceLocation": "AT_PLAT",
                },
            ]
        )
        con = _console()
        format_service(con, resp)
        output = con.file.getvalue()
        assert "AT PLATFORM" in output

    def test_approaching_platform_indicator(self):
        """Line 162: APPROACHING_PLATFORM progress indicator."""
        resp = _make_service_response(
            locations=[
                {
                    "realtimeActivated": True,
                    "tiploc": "WATRLMN",
                    "description": "London Waterloo",
                    "gbttBookedDeparture": "1430",
                    "realtimeDeparture": "1430",
                    "realtimeGbttDepartureLateness": 0,
                    "displayAs": "ORIGIN",
                    "serviceLocation": "APPR_PLAT",
                },
            ]
        )
        con = _console()
        format_service(con, resp)
        output = con.file.getvalue()
        assert "APPROACHING" in output

    def test_departed_checkmark(self):
        """Line 164: departed station shows checkmark."""
        resp = _make_service_response(
            locations=[
                {
                    "realtimeActivated": True,
                    "tiploc": "WATRLMN",
                    "description": "London Waterloo",
                    "gbttBookedDeparture": "1430",
                    "realtimeDeparture": "1431",
                    "realtimeGbttDepartureLateness": 1,
                    "realtimeDepartureActual": True,
                    "displayAs": "ORIGIN",
                },
            ]
        )
        con = _console()
        format_service(con, resp)
        output = con.file.getvalue()
        assert "\u2713" in output

    def test_late_service_red(self):
        """Line 155: lateness > 5 shows red."""
        resp = _make_service_response(
            locations=[
                {
                    "realtimeActivated": True,
                    "tiploc": "WATRLMN",
                    "description": "London Waterloo",
                    "gbttBookedDeparture": "1430",
                    "realtimeDeparture": "1440",
                    "realtimeGbttDepartureLateness": 10,
                    "displayAs": "ORIGIN",
                },
            ]
        )
        con = _console()
        format_service(con, resp)
        output = con.file.getvalue()
        assert "14:40" in output

    def test_no_booked_no_realtime(self):
        """Lines 168->170, 170->173: location with no times."""
        resp = _make_service_response(
            locations=[
                {
                    "realtimeActivated": True,
                    "tiploc": "MIDWAY",
                    "description": "Midway Point",
                    "displayAs": "PASS",
                },
            ]
        )
        con = _console()
        format_service(con, resp)
        output = con.file.getvalue()
        assert "Midway Point" in output

    def test_no_progress_no_realtime_actual(self):
        """Line 174: location with lateness but no realtimeDepartureActual."""
        resp = _make_service_response(
            locations=[
                {
                    "realtimeActivated": True,
                    "tiploc": "WATRLMN",
                    "description": "London Waterloo",
                    "gbttBookedDeparture": "1430",
                    "realtimeDeparture": "1433",
                    "realtimeGbttDepartureLateness": 3,
                    "displayAs": "CALL",
                },
            ]
        )
        con = _console()
        format_service(con, resp)
        output = con.file.getvalue()
        assert "14:33" in output

    def test_no_origin_no_destination(self):
        """Line 137-138: missing origin/destination shows '?'."""
        resp = _make_service_response(origin=[], destination=[])
        con = _console()
        format_service(con, resp)
        output = con.file.getvalue()
        assert "?" in output
