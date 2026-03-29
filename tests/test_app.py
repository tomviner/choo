"""CLI integration tests for choo commands."""

import datetime as dt
import json
from unittest.mock import patch

import pytest
import requests_mock as rm
from freezegun import freeze_time
from typer.testing import CliRunner

from choo.app import _build_when, app
from traintimes.sdk import ResponseError


runner = CliRunner()

SAMPLE_LOCATION_JSON = {
    "location": {"name": "Highbury & Islington", "crs": "HIB", "tiploc": "HAGGERS"},
    "filter": None,
    "services": [
        {
            "locationDetail": {
                "realtimeActivated": True,
                "tiploc": "HAGGERS",
                "crs": "HIB",
                "description": "Highbury & Islington",
                "gbttBookedDeparture": "1430",
                "realtimeDeparture": "1431",
                "realtimeGbttDepartureLateness": 1,
                "platform": "2",
                "displayAs": "CALL",
                "origin": [
                    {"tiploc": "HIGHBYA", "description": "Highbury & Islington"}
                ],
                "destination": [{"tiploc": "MOORGAT", "description": "Moorgate"}],
            },
            "serviceUid": "W12345",
            "runDate": "2026-03-14",
            "trainIdentity": "9X00",
            "runningIdentity": "9X00",
            "atocCode": "LO",
            "atocName": "London Overground",
            "serviceType": "train",
            "isPassenger": True,
            "origin": [{"tiploc": "HIGHBYA", "description": "Highbury & Islington"}],
            "destination": [{"tiploc": "MOORGAT", "description": "Moorgate"}],
            "countdownMinutes": 5,
        }
    ],
}


@pytest.fixture
def mock_location(monkeypatch):
    monkeypatch.setenv("CHOO_AUTH", "test:test")
    with rm.Mocker() as m:
        m.get(rm.ANY, json=SAMPLE_LOCATION_JSON)
        yield m


def test_next_explicit(mock_location):
    result = runner.invoke(app, ["next", "HIB", "MOG"])
    assert result.exit_code == 0
    assert "14:3" in result.output


def test_next_defaults_to_aliases(mock_location, monkeypatch):
    """next without FROM/TO uses home/work aliases."""
    monkeypatch.setenv("CHOO_ALIAS_HOME", "HIB")
    monkeypatch.setenv("CHOO_ALIAS_WORK", "MOG")
    result = runner.invoke(app, ["next", "--on", "today"])
    assert result.exit_code == 0


def test_next_no_args_no_aliases(monkeypatch, tmp_path):
    """next without args or aliases gives helpful error."""
    monkeypatch.setenv("CHOO_AUTH", "test:test")
    monkeypatch.setattr("choo.config._config_dir", lambda: tmp_path / "choo")
    result = runner.invoke(app, ["next"])
    assert result.exit_code == 1
    assert "alias" in result.output.lower()


def test_next_json(mock_location):
    result = runner.invoke(app, ["next", "HIB", "MOG", "--json"])
    assert result.exit_code == 0
    # Find the JSON line (stderr interpretation line may be mixed in)
    json_line = [ln for ln in result.output.splitlines() if ln.startswith("{")][0]
    data = json.loads(json_line)
    assert "services" in data


def test_no_auth(monkeypatch, tmp_path):
    monkeypatch.delenv("CHOO_AUTH", raising=False)
    monkeypatch.delenv("RTT_AUTH", raising=False)
    monkeypatch.setattr("choo.config._config_dir", lambda: tmp_path / "choo")
    result = runner.invoke(app, ["next", "HIB", "MOG"])
    assert result.exit_code == 1
    assert "choo auth" in result.output.lower() or "CHOO_AUTH" in result.output
    assert "api-portal.rtt.io" in result.output


def test_board(mock_location):
    result = runner.invoke(app, ["board", "HIB"])
    assert result.exit_code == 0
    assert "W12345" in result.output


def test_board_json(mock_location):
    result = runner.invoke(app, ["board", "HIB", "--json"])
    assert result.exit_code == 0
    json_line = [ln for ln in result.output.splitlines() if ln.startswith("{")][0]
    data = json.loads(json_line)
    assert "services" in data


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "choo" in result.output


def test_verbose_flag(mock_location):
    """--verbose enables debug logging."""
    result = runner.invoke(app, ["--verbose", "next", "HIB", "MOG"])
    assert result.exit_code == 0


SAMPLE_SERVICE_JSON = {
    "serviceUid": "A12345",
    "runDate": "2026-03-14",
    "serviceType": "train",
    "isPassenger": True,
    "trainIdentity": "1A23",
    "atocCode": "NT",
    "atocName": "Northern",
    "performanceMonitored": True,
    "origin": [{"tiploc": "ORIGIN", "description": "High Barnet"}],
    "destination": [{"tiploc": "DEST", "description": "Moorgate"}],
    "locations": [
        {
            "realtimeActivated": True,
            "tiploc": "ORIGIN",
            "description": "High Barnet",
            "gbttBookedDeparture": "1820",
            "realtimeDeparture": "1820",
            "displayAs": "ORIGIN",
            "origin": [],
            "destination": [],
        },
        {
            "realtimeActivated": True,
            "tiploc": "DEST",
            "description": "Moorgate",
            "gbttBookedArrival": "1849",
            "realtimeArrival": "1849",
            "displayAs": "DESTINATION",
            "origin": [],
            "destination": [],
        },
    ],
    "realtimeActivated": True,
}


@pytest.fixture
def mock_service(monkeypatch):
    monkeypatch.setenv("CHOO_AUTH", "test:test")
    with freeze_time("2026-03-14"), rm.Mocker() as m:
        m.get(
            "https://api.rtt.io/api/v1/json/service/A12345/2026/03/14",
            json=SAMPLE_SERVICE_JSON,
        )
        yield m


class TestServiceCommand:
    def test_service(self, mock_service):
        result = runner.invoke(app, ["service", "A12345"])
        assert result.exit_code == 0, result.output
        assert "High Barnet" in result.output or "Moorgate" in result.output

    def test_service_json(self, mock_service):
        result = runner.invoke(app, ["service", "A12345", "--json"])
        assert result.exit_code == 0, result.output
        # Extract JSON from output (stderr interpretation line may be mixed in)
        json_start = result.output.index("{")
        data = json.loads(result.output[json_start:])
        assert data["serviceUid"] == "A12345"


class TestAliasCommand:
    def test_alias_set_and_list(self, monkeypatch, tmp_path):
        monkeypatch.setattr("choo.config._config_dir", lambda: tmp_path / "choo")
        result = runner.invoke(app, ["alias", "set", "home", "HIB"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["alias", "list"])
        assert result.exit_code == 0
        assert "home" in result.output
        assert "HIB" in result.output

    def test_alias_remove(self, monkeypatch, tmp_path):
        monkeypatch.setattr("choo.config._config_dir", lambda: tmp_path / "choo")
        runner.invoke(app, ["alias", "set", "home", "HIB"])
        result = runner.invoke(app, ["alias", "remove", "home"])
        assert result.exit_code == 0

    def test_alias_reserved_name(self, monkeypatch, tmp_path):
        monkeypatch.setattr("choo.config._config_dir", lambda: tmp_path / "choo")
        result = runner.invoke(app, ["alias", "set", "board", "HIB"])
        assert result.exit_code != 0
        assert "reserved" in result.output.lower()

    def test_alias_list_empty(self, monkeypatch, tmp_path):
        monkeypatch.setattr("choo.config._config_dir", lambda: tmp_path / "choo")
        result = runner.invoke(app, ["alias", "list"])
        assert result.exit_code == 0
        assert "No aliases" in result.output


class TestResolveOrExit:
    """Tests for _resolve_or_exit (station not found / ambiguous)."""

    def test_station_not_found(self, monkeypatch):
        monkeypatch.setenv("CHOO_AUTH", "test:test")
        result = runner.invoke(app, ["next", "xyzzyspoon", "MOG"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_station_not_found_no_suggestions(self, monkeypatch):
        """Line 60->64: station not found with empty suggestions."""
        from choo.resolve import StationNotFound

        monkeypatch.setenv("CHOO_AUTH", "test:test")
        monkeypatch.setattr(
            "choo.app.resolve_station",
            lambda s: (_ for _ in ()).throw(StationNotFound(s, [])),
        )
        result = runner.invoke(app, ["next", "zzz123", "MOG"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()
        assert "Did you mean" not in result.output

    def test_station_not_found_with_suggestions(self, monkeypatch):
        """Lines 60-63: station not found but with suggestions shown."""
        from choo.resolve import StationNotFound

        monkeypatch.setenv("CHOO_AUTH", "test:test")
        monkeypatch.setattr(
            "choo.app.resolve_station",
            lambda s: (_ for _ in ()).throw(
                StationNotFound(s, [("London Paddington", "PAD", 50.0)])
            ),
        )
        result = runner.invoke(app, ["next", "paddingtun", "MOG"])
        assert result.exit_code == 1
        assert "Did you mean" in result.output
        assert "PAD" in result.output

    def test_ambiguous_station(self, monkeypatch):
        monkeypatch.setenv("CHOO_AUTH", "test:test")
        result = runner.invoke(app, ["next", "Birmingham", "MOG"])
        assert result.exit_code == 1
        assert "ambiguous" in result.output.lower() or "Did you mean" in result.output


class TestBuildWhen:
    @freeze_time("2026-03-14")  # a Saturday
    def test_today(self):
        result = _build_when(None, "today")
        assert result == dt.date(2026, 3, 14)

    @freeze_time("2026-03-14")
    def test_tomorrow(self):
        result = _build_when(None, "tomorrow")
        assert result == dt.date(2026, 3, 15)

    @freeze_time("2026-03-14")  # Saturday
    def test_day_name(self):
        result = _build_when(None, "monday")
        assert result == dt.date(2026, 3, 16)

    @freeze_time("2026-03-14")  # Saturday
    def test_day_name_same_day_goes_next_week(self):
        """Line 91: days_ahead == 0 means next week."""
        result = _build_when(None, "saturday")
        assert result == dt.date(2026, 3, 21)

    def test_iso_date(self):
        result = _build_when(None, "2026-04-01")
        assert result == dt.date(2026, 4, 1)

    @freeze_time("2026-03-14")
    def test_at_only(self):
        result = _build_when("14:30", None)
        assert result == dt.datetime(2026, 3, 14, 14, 30)

    @freeze_time("2026-03-14")
    def test_at_and_on(self):
        result = _build_when("09:15", "tomorrow")
        assert result == dt.datetime(2026, 3, 15, 9, 15)

    @freeze_time("2026-03-14")
    def test_date_only_returns_date(self):
        result = _build_when(None, "2026-05-01")
        assert isinstance(result, dt.date) and not isinstance(result, dt.datetime)

    def test_none_none(self):
        assert _build_when(None, None) is None


class TestPrintInterpretation:
    """Test _print_interpretation via next command (covers lines 119, 121)."""

    @freeze_time("2026-03-14")
    def test_with_datetime(self, mock_location):
        result = runner.invoke(app, ["next", "HIB", "MOG", "--at", "14:30"])
        assert result.exit_code == 0

    @freeze_time("2026-03-14")
    def test_with_date_only(self, mock_location):
        result = runner.invoke(app, ["next", "HIB", "MOG", "--on", "tomorrow"])
        assert result.exit_code == 0


class TestNextApiError:
    def test_api_error_next(self, monkeypatch):
        monkeypatch.setenv("CHOO_AUTH", "test:test")
        with patch("choo.app.Location") as mock_loc:
            mock_loc.return_value.get.side_effect = ResponseError("server error")
            result = runner.invoke(app, ["next", "HIB", "MOG"])
        assert result.exit_code == 1
        assert "API error" in result.output

    def test_api_error_board(self, monkeypatch):
        monkeypatch.setenv("CHOO_AUTH", "test:test")
        with patch("choo.app.Location") as mock_loc:
            mock_loc.return_value.get.side_effect = ResponseError("server error")
            result = runner.invoke(app, ["board", "HIB"])
        assert result.exit_code == 1
        assert "API error" in result.output


    def test_board_no_args_with_alias(self, monkeypatch):
        monkeypatch.setenv("CHOO_AUTH", "test:test")
        monkeypatch.setenv("CHOO_ALIAS_HOME", "HIB")
        with rm.Mocker() as m:
            m.get(rm.ANY, json=SAMPLE_LOCATION_JSON)
            result = runner.invoke(app, ["board"])
        assert result.exit_code == 0

    def test_board_no_args_no_alias(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CHOO_AUTH", "test:test")
        monkeypatch.setattr("choo.config._config_dir", lambda: tmp_path / "choo")
        result = runner.invoke(app, ["board"])
        assert result.exit_code == 1
        assert "alias" in result.output.lower()


class TestArrivals:
    def test_next_arrivals(self, mock_location):
        result = runner.invoke(app, ["next", "HIB", "MOG", "--arrivals"])
        assert result.exit_code == 0


class TestBoardTomorrowFallback:
    def test_board_shows_tomorrow(self, monkeypatch):
        monkeypatch.setenv("CHOO_AUTH", "test:test")
        call_count = {"n": 0}

        def route_response(request, context):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return EMPTY_LOCATION_JSON
            return SAMPLE_LOCATION_JSON

        with rm.Mocker() as m:
            m.get(rm.ANY, json=route_response)
            result = runner.invoke(app, ["board", "HIB"])
        assert result.exit_code == 0
        assert "No more trains today" in result.output

    def test_board_tomorrow_api_error(self, monkeypatch):
        monkeypatch.setenv("CHOO_AUTH", "test:test")
        call_count = {"n": 0}

        def route_response(request, context):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return EMPTY_LOCATION_JSON
            context.status_code = 500
            context.reason = "Server Error"
            return {"error": "fail"}

        with rm.Mocker() as m:
            m.get(rm.ANY, json=route_response)
            result = runner.invoke(app, ["board", "HIB"])
        assert result.exit_code == 0


class TestDefaultCommand:
    def test_default_with_aliases(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CHOO_AUTH", "test:test")
        monkeypatch.setenv("CHOO_ALIAS_HOME", "HIB")
        monkeypatch.setenv("CHOO_ALIAS_WORK", "MOG")
        with rm.Mocker() as m:
            m.get(rm.ANY, json=SAMPLE_LOCATION_JSON)
            result = runner.invoke(app, [])
        assert result.exit_code == 0

    def test_default_without_aliases(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CHOO_AUTH", "test:test")
        monkeypatch.setattr("choo.config._config_dir", lambda: tmp_path / "choo")
        result = runner.invoke(app, [])
        assert result.exit_code == 1
        assert "home" in result.output.lower() and "work" in result.output.lower()

    def test_unknown_subcommand_routes_to_next(self, monkeypatch):
        """choo home work routes to choo next home work."""
        monkeypatch.setenv("CHOO_AUTH", "test:test")
        monkeypatch.setenv("CHOO_ALIAS_HOME", "HIB")
        monkeypatch.setenv("CHOO_ALIAS_WORK", "MOG")
        with rm.Mocker() as m:
            m.get(rm.ANY, json=SAMPLE_LOCATION_JSON)
            result = runner.invoke(app, ["home", "work"])
        assert result.exit_code == 0

    def test_default_no_auth(self, monkeypatch, tmp_path):
        monkeypatch.delenv("CHOO_AUTH", raising=False)
        monkeypatch.delenv("RTT_AUTH", raising=False)
        monkeypatch.setattr("choo.config._config_dir", lambda: tmp_path / "choo")
        result = runner.invoke(app, [])
        assert result.exit_code == 1


EMPTY_LOCATION_JSON = {
    "location": {"name": "Highbury & Islington", "crs": "HIB"},
    "services": None,
}


class TestTomorrowFallback:
    def test_shows_tomorrow_trains(self, monkeypatch):
        """No trains today → shows tomorrow's trains."""
        monkeypatch.setenv("CHOO_AUTH", "test:test")
        call_count = {"n": 0}

        def route_response(request, context):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return EMPTY_LOCATION_JSON
            return SAMPLE_LOCATION_JSON

        with rm.Mocker() as m:
            m.get(rm.ANY, json=route_response)
            result = runner.invoke(app, ["next", "HIB", "MOG"])
        assert result.exit_code == 0
        assert "No more trains today" in result.output
        assert "14:3" in result.output  # tomorrow's train time

    def test_tomorrow_api_error(self, monkeypatch):
        """No trains today, tomorrow API fails → just 'No trains found'."""
        monkeypatch.setenv("CHOO_AUTH", "test:test")
        call_count = {"n": 0}

        def route_response(request, context):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return EMPTY_LOCATION_JSON
            context.status_code = 500
            context.reason = "Server Error"
            return {"error": "fail"}

        with rm.Mocker() as m:
            m.get(rm.ANY, json=route_response)
            result = runner.invoke(app, ["next", "HIB", "MOG"])
        assert result.exit_code == 0
        assert "No trains found" in result.output

    def test_tomorrow_also_empty(self, monkeypatch):
        """No trains today or tomorrow → just 'No trains found'."""
        monkeypatch.setenv("CHOO_AUTH", "test:test")
        with rm.Mocker() as m:
            m.get(rm.ANY, json=EMPTY_LOCATION_JSON)
            result = runner.invoke(app, ["next", "HIB", "MOG"])
        assert result.exit_code == 0
        assert "No trains found" in result.output

    def test_no_fallback_when_date_specified(self, monkeypatch):
        """With --on, don't try tomorrow."""
        monkeypatch.setenv("CHOO_AUTH", "test:test")
        with rm.Mocker() as m:
            m.get(rm.ANY, json=EMPTY_LOCATION_JSON)
            result = runner.invoke(app, ["next", "HIB", "MOG", "--on", "today"])
        assert result.exit_code == 0
        assert "No trains found" in result.output
        assert "tomorrow" not in result.output.lower()


class TestServiceCommandExtended:
    def test_service_with_on_date(self, monkeypatch):
        monkeypatch.setenv("CHOO_AUTH", "test:test")
        with freeze_time("2026-03-14"), rm.Mocker() as m:
            m.get(
                "https://api.rtt.io/api/v1/json/service/A12345/2026/03/15",
                json={**SAMPLE_SERVICE_JSON, "runDate": "2026-03-15"},
            )
            result = runner.invoke(app, ["service", "A12345", "--on", "2026-03-15"])
        assert result.exit_code == 0, result.output

    @freeze_time("2026-03-14")
    def test_service_with_on_datetime(self, monkeypatch):
        """Lines 237-238: service --on where _build_when returns datetime."""
        import choo.app as app_module

        monkeypatch.setenv("CHOO_AUTH", "test:test")
        monkeypatch.setattr(
            app_module,
            "_build_when",
            lambda at, on: dt.datetime(2026, 3, 15, 10, 0),
        )
        with rm.Mocker() as m:
            m.get(
                "https://api.rtt.io/api/v1/json/service/A12345/2026/03/15",
                json={**SAMPLE_SERVICE_JSON, "runDate": "2026-03-15"},
            )
            result = runner.invoke(app, ["service", "A12345", "--on", "ignored"])
        assert result.exit_code == 0, result.output

    def test_service_api_error(self, monkeypatch):
        monkeypatch.setenv("CHOO_AUTH", "test:test")
        with freeze_time("2026-03-14"), patch("choo.app.Service") as mock_svc:
            mock_svc.return_value.get.side_effect = ResponseError("not found")
            result = runner.invoke(app, ["service", "A12345"])
        assert result.exit_code == 1
        assert "API error" in result.output


class TestAuthCommand:
    def test_auth_saves_credentials_verified(self, monkeypatch, tmp_path):
        monkeypatch.setattr("choo.config._config_dir", lambda: tmp_path / "choo")
        with rm.Mocker() as m:
            m.get(rm.ANY, json=SAMPLE_LOCATION_JSON)
            result = runner.invoke(app, ["auth"], input="myuser\nmypass\n")
        assert result.exit_code == 0
        assert "verified" in result.output.lower()
        auth_file = tmp_path / "choo" / "auth"
        assert auth_file.exists()
        assert auth_file.read_text() == "myuser:mypass"

    def test_auth_saves_credentials_verification_fails(self, monkeypatch, tmp_path):
        monkeypatch.setattr("choo.config._config_dir", lambda: tmp_path / "choo")
        with patch("choo.app.Location") as mock_loc:
            mock_loc.return_value.get.side_effect = ResponseError("unauthorized")
            result = runner.invoke(app, ["auth"], input="myuser\nmypass\n")
        assert result.exit_code == 0
        assert "saved but verification failed" in result.output.lower()
        auth_file = tmp_path / "choo" / "auth"
        assert auth_file.exists()
        assert auth_file.read_text() == "myuser:mypass"

    def test_auth_shows_instructions(self, monkeypatch, tmp_path):
        monkeypatch.setattr("choo.config._config_dir", lambda: tmp_path / "choo")
        with rm.Mocker() as m:
            m.get(rm.ANY, json=SAMPLE_LOCATION_JSON)
            result = runner.invoke(app, ["auth"], input="myuser\nmypass\n")
        assert "api-portal.rtt.io" in result.output
        assert "realtimetrains.co.uk" in result.output
        assert "non-commercial" in result.output
