import datetime
import os

import pytest
from freezegun import freeze_time
from utils import date_in_range

from traintimes.models import LocationResponse, ServiceResponse
from traintimes.sdk import Location, ResponseError, Service


pytestmark = pytest.mark.skipif(
    "RTT_AUTH" not in os.environ and "CHOO_AUTH" not in os.environ,
    reason="Integration tests require CHOO_AUTH or RTT_AUTH credentials",
)


@pytest.fixture
def frozen_date():
    """Test against a known, rarely changing date, within range.

    API covers -7 to +90 days from current date.
    Requests using the free API are currently limited to 50 per day.
    So choose one datetime "per season", and use requests_cache to avoid repeat
    requests.
    """
    date = date_in_range()
    dt = datetime.datetime.combine(date, datetime.time(12, 0, 0))
    with freeze_time(dt):
        yield dt


@pytest.fixture
def past_dt(frozen_date):
    """Test against a known past date"""
    date = datetime.date.today() + datetime.timedelta(days=-150)
    return datetime.datetime.combine(date, datetime.time(12, 0, 0))


@pytest.fixture
def future_dt(frozen_date):
    """Test against a known future date"""
    date = datetime.date.today() + datetime.timedelta(days=1825)  # ~5 years
    return datetime.datetime.combine(date, datetime.time(12, 0, 0))


@pytest.fixture
def service_code(frozen_date):
    return Location('HIB', when=datetime.datetime.now()).get().services[0].service_uid


class TestLocation:
    """Integration tests for all Location endpoint combinations"""

    expected_base = 'https://api.rtt.io/api/v1/json/search/'

    def assert_valid_location(self, data):
        assert isinstance(data, LocationResponse)
        assert data.location.name
        assert isinstance(data.services, list)

    def test_station_only(self):
        """Normal queries (live departures): /json/search/<station>"""
        self.assert_valid_location(Location('HIB').get())

    def test_station_with_to_station(self):
        """Normal queries filtered to a location.

        Endpoint: /json/search/<station>/to/<toStation>
        """
        self.assert_valid_location(Location('HIB', 'CHX').get())

    def test_station_with_date(self, frozen_date):
        """Queries for all services on a specific date.

        Endpoint: /json/search/<station>/<year>/<month>/<day>
        """
        self.assert_valid_location(Location('HIB', when=datetime.date.today()).get())

    def test_station_with_to_station_and_date(self, frozen_date):
        """Filtered queries on a specific date"""
        self.assert_valid_location(Location('HIB', 'CHX', datetime.date.today()).get())

    def test_station_with_datetime(self, frozen_date):
        """Queries for services on a specific date and time.

        Endpoint: /json/search/<station>/<year>/<month>/<day>/<time>
        """
        self.assert_valid_location(Location('HIB', when=datetime.datetime.now()).get())

    def test_station_with_to_station_and_datetime(self, frozen_date):
        """Filtered queries on a specific date and time"""
        self.assert_valid_location(
            Location('HIB', 'CHX', datetime.datetime.now()).get()
        )

    def test_station_with_arrivals(self):
        """Station with /arrivals appended"""
        self.assert_valid_location(Location('HIB', arrivals=True).get())

    def test_station_with_date_and_arrivals(self, frozen_date):
        """Date query with /arrivals appended"""
        self.assert_valid_location(
            Location('HIB', when=datetime.date.today(), arrivals=True).get()
        )

    def test_station_with_datetime_and_arrivals(self, frozen_date):
        """Datetime query with /arrivals appended"""
        self.assert_valid_location(
            Location('HIB', when=datetime.datetime.now(), arrivals=True).get()
        )

    def test_station_with_to_station_datetime_and_arrivals(self, frozen_date):
        """Full combination: filtered query with date/time and arrivals"""
        self.assert_valid_location(
            Location('HIB', 'CHX', datetime.datetime.now(), True).get()
        )

    def test_before_available_window(self, past_dt):
        with pytest.raises(ResponseError) as exc:
            assert Location('HIB', 'CHX', past_dt).get()
        assert exc.value.message == 'Not Found'

    def test_after_available_window(self, future_dt):
        with pytest.raises(ResponseError) as exc:
            assert Location('HIB', 'CHX', future_dt).get()
        assert exc.value.message == 'Not Found'


class TestService:
    """Integration tests for the service endpoint.

    Endpoint: /json/service/<serviceUid>/<year>/<month>/<day>
    """

    expected_base = 'https://api.rtt.io/api/v1/json/service/'

    def assert_valid_service(self, data):
        assert isinstance(data, ServiceResponse)
        assert data.service_uid
        assert data.origin
        assert data.destination
        assert data.locations

    def test_service_with_date(self, frozen_date, service_code):
        """Service query with date: /json/service/<serviceUid>/<year>/<month>/<day>"""
        self.assert_valid_service(Service(service_code, datetime.date.today()).get())

    def test_service_with_datetime(self, frozen_date, service_code):
        """Service query with datetime (date part extracted).

        Endpoint: /json/service/<serviceUid>/<year>/<month>/<day>
        """
        self.assert_valid_service(Service(service_code, datetime.datetime.now()).get())

    def test_no_schedule_found_for_far_future(self, future_dt, service_code):
        """Service query for far future date returns error"""
        with pytest.raises(ResponseError) as exc:
            assert Service(service_code, future_dt).get()
        assert exc.value.message == '<no errcode>: No schedule found'

    def test_no_schedule_found_for_bad_service(self, frozen_date):
        """Service query with invalid serviceUid returns error"""
        with pytest.raises(ResponseError) as exc:
            assert Service('Q98765', datetime.datetime.now()).get()
        assert exc.value.message == '<no errcode>: No schedule found'
