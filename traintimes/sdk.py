import os

import requests
from dotenv import load_dotenv
from purl import Template

from .models import (
    LocationRequest,
    LocationResponse,
    ServiceRequest,
    ServiceResponse,
)


class ResponseError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


load_dotenv()


class RTTBase:
    """Base Class for RealTimeTrains API

    See https://www.realtimetrains.co.uk/about/developer/pull/docs/

    Apply for API access at https://api.rtt.io/
    Set environ variable:
        export RTT_AUTH=user:password
    """

    # URI template language as per RFC6570
    base_uri_template = 'https://api.rtt.io/api/{version}/{accept}'
    @property
    def auth(self):
        for var in ('CHOO_AUTH', 'RTT_AUTH'):
            value = os.environ.get(var)
            if value:
                return tuple(value.split(':'))
        raise ResponseError(
            "No API credentials found. Set CHOO_AUTH or RTT_AUTH environment variable (format: user:password)"
        )

    def __init__(self, version='v1', accept='json'):
        self.context = {'version': version, 'accept': accept}

    def add_to_context(self, key, value):
        self.context[key] = value

    @property
    def uri(self):
        uri_template = Template(self.base_uri_template + self.uri_template)
        return uri_template.expand(self.context).as_string()

    def __repr__(self):
        return self.uri

    def get(self):
        response = requests.get(self.uri, auth=self.auth)
        if not response.ok:
            try:
                json_data = response.json()
            except ValueError:
                raise ResponseError(response.reason)
            if 'error' in json_data:
                raise ResponseError(
                    '{}: {}'.format(
                        json_data.get('errcode', '<no errcode>'), json_data['error']
                    )
                )
            # If we got here, response is not OK but no 'error' key in JSON
            raise ResponseError(f'{response.status_code}: {response.reason}')

        try:
            json_data = response.json()
        except ValueError:
            raise ResponseError(f'{response.text=}')
        if 'error' in json_data:
            raise ResponseError(
                '{}: {}'.format(
                    json_data.get('errcode', '<no errcode>'), json_data['error']
                )
            )
        return json_data


class Location(RTTBase):
    """Location List API

    Endpoints:
    - Normal queries (live departures):
      /json/search/<station>
    - Normal queries filtered to a location:
      /json/search/<station>/to/<toStation>
    - Queries for all services on a specific date:
      /json/search/<station>/<year>/<month>/<day>
    - Queries for services on a specific date and time:
      /json/search/<station>/<year>/<month>/<day>/<time>

    You can append /arrivals to any of these endpoints to retrieve info about arrivals.
    You can apply the to/from filtering to any of the endpoints, they must be before
    any date/time modifiers.

    See: https://www.realtimetrains.co.uk/about/developer/pull/docs/locationlist/
    """

    uri_template = '/search/{station}{+tostation}{+date}{+time}{/arrivals}'

    def __init__(self, station, to_station=None, when=None, arrivals=False, **kwargs):
        super(Location, self).__init__(**kwargs)

        self.request = LocationRequest.from_inputs(
            station=station, to_station=to_station, when=when, arrivals=arrivals
        )

        self.add_to_context('station', self.request.station)

        if self.request.to_station:
            self.add_to_context('tostation', f"/to/{self.request.to_station}")

        if self.request.date:
            self.add_to_context('date', f"{self.request.date:/%Y/%m/%d}")

        if self.request.time:
            self.add_to_context('time', f"/{self.request.time:%H%M}")

        if self.request.arrivals:
            self.add_to_context('arrivals', 'arrivals')

    def get(self):
        json_data = super().get()
        return LocationResponse.model_validate(json_data)


class Service(RTTBase):
    """Service Information API

    Endpoint:
    /json/service/<serviceUid>/<year>/<month>/<day>

    Parameters:
    - serviceUid (required): Service UID, as obtained from a location search
    - date (required): In format yyyy/mm/dd, example: 2013/06/14

    See: https://www.realtimetrains.co.uk/about/developer/pull/docs/serviceinfo/
    """

    uri_template = '/service{/service}{+date}'

    def __init__(self, service, date, **kwargs):
        super(Service, self).__init__(**kwargs)

        self.request = ServiceRequest.from_inputs(service, date)

        self.add_to_context('service', self.request.service_uid)

        self.add_to_context(
            'date',
            f"/{self.request.date:%Y/%m/%d}",
        )

    def get(self):
        json_data = super().get()
        return ServiceResponse.model_validate(json_data)
