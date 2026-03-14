"""CLI integration tests for choo commands."""

import json

import pytest
import requests_mock as rm
from typer.testing import CliRunner

from choo.app import app

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
                "origin": [{"tiploc": "HIGHBYA", "description": "Highbury & Islington"}],
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


def test_next_json(mock_location):
    result = runner.invoke(app, ["next", "HIB", "MOG", "--json"])
    assert result.exit_code == 0
    # Find the JSON line (stderr interpretation line may be mixed in)
    json_line = [l for l in result.output.splitlines() if l.startswith("{")][0]
    data = json.loads(json_line)
    assert "services" in data


def test_no_auth(monkeypatch):
    monkeypatch.delenv("CHOO_AUTH", raising=False)
    monkeypatch.delenv("RTT_AUTH", raising=False)
    result = runner.invoke(app, ["next", "HIB", "MOG"])
    assert result.exit_code == 1
    assert "credentials" in result.output.lower() or "CHOO_AUTH" in result.output


def test_board(mock_location):
    result = runner.invoke(app, ["board", "HIB"])
    assert result.exit_code == 0
    assert "W12345" in result.output


def test_board_json(mock_location):
    result = runner.invoke(app, ["board", "HIB", "--json"])
    assert result.exit_code == 0
    json_line = [l for l in result.output.splitlines() if l.startswith("{")][0]
    data = json.loads(json_line)
    assert "services" in data


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "choo" in result.output
