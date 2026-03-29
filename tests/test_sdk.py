import datetime

import pytest
from freezegun import freeze_time

from traintimes.models import (
    LocationRequest,
    LocationResponse,
    ServiceRequest,
    ServiceResponse,
)
from traintimes.sdk import Location, ResponseError, Service


@pytest.fixture
def dt():
    with freeze_time("2025-10-16 21:52:00"):
        yield


class TestLocation:
    """Test Location endpoint URI generation for all endpoint combinations"""

    expected_base = 'https://api.rtt.io/api/v1/json/search/'

    def test_repr(self):
        assert Location('HIB').uri == repr(Location('HIB'))

    def test_station_only(self):
        """Normal queries (live departures): /json/search/<station>"""
        assert Location('HIB').uri == self.expected_base + 'HIB'

    def test_station_with_to_station(self):
        """Normal queries filtered to a location.

        Endpoint: /json/search/<station>/to/<toStation>
        """
        assert Location('HIB', 'CHX').uri == self.expected_base + 'HIB/to/CHX'

    def test_station_with_date(self, dt):
        """Queries for all services on a specific date.

        Endpoint: /json/search/<station>/<year>/<month>/<day>
        """
        assert (
            Location('HIB', when=datetime.date.today()).uri
            == self.expected_base + 'HIB/2025/10/16'
        )

    def test_station_with_to_station_and_date(self, dt):
        """Filtered queries on a specific date"""
        assert (
            Location('HIB', 'CHX', datetime.date.today()).uri
            == self.expected_base + 'HIB/to/CHX/2025/10/16'
        )

    def test_station_with_datetime(self, dt):
        """Queries for services on a specific date and time.

        Endpoint: /json/search/<station>/<year>/<month>/<day>/<time>
        """
        assert (
            Location('HIB', when=datetime.datetime.now()).uri
            == self.expected_base + 'HIB/2025/10/16/2152'
        )

    def test_station_with_to_station_and_datetime(self, dt):
        """Filtered queries on a specific date and time"""
        assert (
            Location('HIB', 'CHX', datetime.datetime.now()).uri
            == self.expected_base + 'HIB/to/CHX/2025/10/16/2152'
        )

    def test_station_with_arrivals(self):
        """Station with /arrivals appended"""
        assert Location('HIB', arrivals=True).uri == self.expected_base + 'HIB/arrivals'

    def test_station_with_date_and_arrivals(self, dt):
        """Date query with /arrivals appended"""
        assert (
            Location('HIB', when=datetime.date.today(), arrivals=True).uri
            == self.expected_base + 'HIB/2025/10/16/arrivals'
        )

    def test_station_with_datetime_and_arrivals(self, dt):
        """Datetime query with /arrivals appended"""
        assert (
            Location('HIB', when=datetime.datetime.now(), arrivals=True).uri
            == self.expected_base + 'HIB/2025/10/16/2152/arrivals'
        )

    def test_station_with_to_station_datetime_and_arrivals(self, dt):
        """Full combination: filtered query with date/time and arrivals"""
        assert (
            Location('HIB', 'CHX', datetime.datetime.now(), True).uri
            == self.expected_base + 'HIB/to/CHX/2025/10/16/2152/arrivals'
        )

    def test_get_returns_location_response(self, requests_mock):
        subject = Location('HIB')
        sample = {
            'location': {
                'name': 'Highbury & Islington',
                'crs': 'HIB',
                'tiploc': 'HIBURY',
            },
            'filter': None,
            'services': [
                {
                    'locationDetail': {
                        'realtimeActivated': True,
                        'tiploc': 'HIBURY',
                        'crs': 'HIB',
                        'description': 'Highbury & Islington',
                        'origin': [],
                        'destination': [],
                        'isCall': True,
                        'isPublicCall': True,
                    },
                    'serviceUid': 'A12345',
                    'runDate': '2024-01-01',
                    'trainIdentity': '1A23',
                    'runningIdentity': '1A23',
                    'atocCode': 'ZZ',
                    'atocName': 'Zed Rail',
                    'serviceType': 'train',
                    'isPassenger': True,
                }
            ],
        }
        requests_mock.get(subject.uri, json=sample)
        response = subject.get()

        assert isinstance(response, LocationResponse)
        assert response.services[0].service_uid == 'A12345'
        assert (
            response.services[0].location_detail.description == 'Highbury & Islington'
        )

    def test_request_invalid_when_type(self):
        with pytest.raises(TypeError):
            LocationRequest.from_inputs('HIB', when=object())


class TestService:
    """Test Service endpoint URI generation"""

    expected_base = 'https://api.rtt.io/api/v1/json/service/'

    def test_service_with_date(self, dt):
        """Service with date: /json/service/<serviceUid>/<year>/<month>/<day>"""
        assert (
            Service('W12345', datetime.date.today()).uri
            == self.expected_base + 'W12345/2025/10/16'
        )

    def test_service_with_datetime(self, dt):
        """Service with datetime (date part extracted).

        Endpoint: /json/service/<serviceUid>/<year>/<month>/<day>
        """
        assert (
            Service('W12345', datetime.datetime.now()).uri
            == self.expected_base + 'W12345/2025/10/16'
        )

    def test_get_returns_service_response(self, requests_mock):
        subject = Service('A12345', datetime.date(2024, 1, 1))
        sample = {
            'serviceUid': 'A12345',
            'runDate': '2024-01-01',
            'serviceType': 'train',
            'isPassenger': True,
            'trainIdentity': '1A23',
            'powerType': 'EMU',
            'trainClass': 'SD',
            'sleeper': None,
            'atocCode': 'ZZ',
            'atocName': 'Zed Rail',
            'performanceMonitored': True,
            'origin': [
                {
                    'tiploc': 'ORIGIN',
                    'description': 'Origin',
                    'workingTime': '080000',
                    'publicTime': '0800',
                }
            ],
            'destination': [
                {
                    'tiploc': 'DEST',
                    'description': 'Destination',
                    'workingTime': '090000',
                    'publicTime': '0900',
                }
            ],
            'locations': [
                {
                    'realtimeActivated': True,
                    'tiploc': 'ORIGIN',
                    'crs': 'ORG',
                    'description': 'Origin',
                    'origin': [],
                    'destination': [],
                    'isCall': True,
                    'isPublicCall': True,
                }
            ],
            'realtimeActivated': True,
            'runningIdentity': '1A23',
        }
        requests_mock.get(subject.uri, json=sample)
        response = subject.get()

        assert isinstance(response, ServiceResponse)
        assert response.service_uid == 'A12345'
        assert response.locations[0].tiploc == 'ORIGIN'

    def test_service_request_invalid_date_type(self):
        with pytest.raises(TypeError):
            ServiceRequest.from_inputs('A12345', '2024-01-01')


class TestAuth:
    """Test lazy auth loading and env var precedence"""

    def test_missing_auth_raises_on_get(self, monkeypatch, requests_mock):
        """Missing auth raises ResponseError on .get(), not on import/instantiation"""
        monkeypatch.delenv('RTT_AUTH', raising=False)
        monkeypatch.delenv('CHOO_AUTH', raising=False)
        subject = Location('HIB')  # no error here
        with pytest.raises(ResponseError, match="No API credentials found"):
            subject.get()

    def test_choo_auth_takes_precedence(self, monkeypatch):
        """CHOO_AUTH takes precedence over RTT_AUTH"""
        monkeypatch.setenv('CHOO_AUTH', 'choo_user:choo_pass')
        monkeypatch.setenv('RTT_AUTH', 'rtt_user:rtt_pass')
        subject = Location('HIB')
        assert subject.auth == ('choo_user', 'choo_pass')

    def test_rtt_auth_fallback(self, monkeypatch):
        """RTT_AUTH works as fallback when CHOO_AUTH is not set"""
        monkeypatch.delenv('CHOO_AUTH', raising=False)
        monkeypatch.setenv('RTT_AUTH', 'rtt_user:rtt_pass')
        subject = Location('HIB')
        assert subject.auth == ('rtt_user', 'rtt_pass')


class TestErrorHandling:
    """Test error scenarios in the get() method"""

    def test_non_ok_response_with_json_error(self, requests_mock):
        """Test handling of non-OK response with JSON error payload"""
        subject = Location('HIB')
        requests_mock.get(
            subject.uri,
            json={'error': 'Service unavailable', 'errcode': '503'},
            status_code=503,
        )
        with pytest.raises(ResponseError) as exc:
            subject.get()
        assert exc.value.message == '503: Service unavailable'

    def test_non_ok_response_with_non_json(self, requests_mock):
        """Test handling of non-OK response with non-JSON body"""
        subject = Location('HIB')
        requests_mock.get(
            subject.uri, text='<html>Error</html>', status_code=404, reason='Not Found'
        )
        with pytest.raises(ResponseError) as exc:
            subject.get()
        assert exc.value.message == 'Not Found'

    def test_non_ok_response_with_json_but_no_error_key(self, requests_mock):
        """Test handling of non-OK response with JSON but no error key"""
        subject = Location('HIB')
        requests_mock.get(
            subject.uri,
            json={'message': 'Something went wrong'},
            status_code=500,
            reason='Internal Server Error',
        )
        with pytest.raises(ResponseError) as exc:
            subject.get()
        assert exc.value.message == '500: Internal Server Error'

    def test_ok_response_with_invalid_json(self, requests_mock):
        """Test handling of OK response with invalid JSON"""
        subject = Location('HIB')
        requests_mock.get(subject.uri, text='<html>Not JSON</html>', status_code=200)
        with pytest.raises(ResponseError) as exc:
            subject.get()
        assert 'response.text=' in exc.value.message

    def test_ok_response_with_json_error_key(self, requests_mock):
        """Test handling of OK response that contains an error key"""
        subject = Location('HIB')
        requests_mock.get(
            subject.uri,
            json={'error': 'Something weird', 'errcode': '999'},
            status_code=200,
        )
        with pytest.raises(ResponseError) as exc:
            subject.get()
        assert exc.value.message == '999: Something weird'
