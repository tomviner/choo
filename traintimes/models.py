"""Typed models for the RealTimeTrains Pull API.

The models in this module are derived from the official API documentation:
https://www.realtimetrains.co.uk/about/developer/pull/docs/

They provide structure around both the request parameters we can supply to the
API and the responses returned from the location line-up and service
information endpoints.
"""

import datetime as _dt
import re
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


_SERVICE_UID_RE = re.compile(r"^[A-Z][0-9]{5}$")


class ServiceType(str, Enum):
    """Types of services reported by the API."""

    TRAIN = "train"
    BUS = "bus"
    SHIP = "ship"


class DisplayAs(str, Enum):
    """Possible presentation states for a location event."""

    CALL = "CALL"
    PASS = "PASS"
    ORIGIN = "ORIGIN"
    DESTINATION = "DESTINATION"
    STARTS = "STARTS"
    TERMINATES = "TERMINATES"
    CANCELLED_CALL = "CANCELLED_CALL"
    CANCELLED_PASS = "CANCELLED_PASS"


class ServiceLocationState(str, Enum):
    """Known realtime service location indicators."""

    APPROACHING_STATION = "APPR_STAT"
    APPROACHING_PLATFORM = "APPR_PLAT"
    AT_PLATFORM = "AT_PLAT"
    DEPARTURE_PREPARING = "DEP_PREP"
    DEPARTURE_READY = "DEP_READY"


class StationSummary(BaseModel):
    """Minimal station information returned by the API."""

    model_config = ConfigDict(extra="ignore")

    name: str
    crs: str | None = None
    tiploc: str | list[str] | None = None


class StationFilter(BaseModel):
    """Filter block accompanying a location line-up response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    from_: StationSummary | None = Field(default=None, alias="from")
    to: StationSummary | None = None


class Pair(BaseModel):
    """Origin/destination pairs used throughout the API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    tiploc: str
    description: str
    working_time: str | None = Field(default=None, alias="workingTime")
    public_time: str | None = Field(default=None, alias="publicTime")


class LocationEvent(BaseModel):
    """Detailed information about a service at a specific location."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    realtime_activated: bool = Field(default=False, alias="realtimeActivated")
    tiploc: str
    crs: str | None = None
    description: str | None = None
    wtt_booked_arrival: str | None = Field(default=None, alias="wttBookedArrival")
    wtt_booked_departure: str | None = Field(default=None, alias="wttBookedDeparture")
    wtt_booked_pass: str | None = Field(default=None, alias="wttBookedPass")
    gbtt_booked_arrival: str | None = Field(default=None, alias="gbttBookedArrival")
    gbtt_booked_departure: str | None = Field(default=None, alias="gbttBookedDeparture")
    origin: list[Pair] = Field(default_factory=list)
    destination: list[Pair] = Field(default_factory=list)
    is_call: bool | None = Field(default=None, alias="isCall")
    is_public_call: bool | None = Field(default=None, alias="isPublicCall")
    realtime_arrival: str | None = Field(default=None, alias="realtimeArrival")
    realtime_arrival_actual: bool | None = Field(
        default=None, alias="realtimeArrivalActual"
    )
    realtime_arrival_no_report: bool | None = Field(
        default=None, alias="realtimeArrivalNoReport"
    )
    realtime_wtt_arrival_lateness: int | None = Field(
        default=None, alias="realtimeWttArrivalLateness"
    )
    realtime_gbtt_arrival_lateness: int | None = Field(
        default=None, alias="realtimeGbttArrivalLateness"
    )
    realtime_departure: str | None = Field(default=None, alias="realtimeDeparture")
    realtime_departure_actual: bool | None = Field(
        default=None, alias="realtimeDepartureActual"
    )
    realtime_departure_no_report: bool | None = Field(
        default=None, alias="realtimeDepartureNoReport"
    )
    realtime_wtt_departure_lateness: int | None = Field(
        default=None, alias="realtimeWttDepartureLateness"
    )
    realtime_gbtt_departure_lateness: int | None = Field(
        default=None, alias="realtimeGbttDepartureLateness"
    )
    realtime_pass: str | None = Field(default=None, alias="realtimePass")
    realtime_pass_actual: bool | None = Field(default=None, alias="realtimePassActual")
    realtime_pass_no_report: bool | None = Field(
        default=None, alias="realtimePassNoReport"
    )
    platform: str | None = None
    platform_confirmed: bool | None = Field(default=None, alias="platformConfirmed")
    platform_changed: bool | None = Field(default=None, alias="platformChanged")
    line: str | None = None
    line_confirmed: bool | None = Field(default=None, alias="lineConfirmed")
    path: str | None = None
    path_confirmed: bool | None = Field(default=None, alias="pathConfirmed")
    cancel_reason_code: str | None = Field(default=None, alias="cancelReasonCode")
    cancel_reason_short_text: str | None = Field(
        default=None, alias="cancelReasonShortText"
    )
    cancel_reason_long_text: str | None = Field(
        default=None, alias="cancelReasonLongText"
    )
    display_as: DisplayAs | None = Field(default=None, alias="displayAs")
    service_location: ServiceLocationState | None = Field(
        default=None, alias="serviceLocation"
    )


class LocationService(BaseModel):
    """A service entry returned by the location line-up endpoint."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    location_detail: LocationEvent = Field(alias="locationDetail")
    service_uid: Annotated[str, Field(alias="serviceUid")]
    run_date: _dt.date = Field(alias="runDate")
    train_identity: str | None = Field(default=None, alias="trainIdentity")
    running_identity: str | None = Field(default=None, alias="runningIdentity")
    atoc_code: str = Field(alias="atocCode")
    atoc_name: str = Field(alias="atocName")
    service_type: ServiceType = Field(alias="serviceType")
    is_passenger: bool = Field(alias="isPassenger")
    planned_cancel: bool | None = Field(default=None, alias="plannedCancel")
    origin: list[Pair] | None = Field(default=None, alias="origin")
    destination: list[Pair] | None = Field(default=None, alias="destination")
    countdown_minutes: int | None = Field(default=None, alias="countdownMinutes")


class LocationResponse(BaseModel):
    """Full response payload for the location line-up endpoint."""

    model_config = ConfigDict(extra="ignore")

    location: StationSummary
    filter: StationFilter | None = None
    services: list[LocationService] = Field(default_factory=list)

    @field_validator("services", mode="before")
    @classmethod
    def _coerce_null_services(
        cls, value: list[LocationService] | None
    ) -> list[LocationService]:
        """The API can return ``null`` for the services array when empty."""
        if value is None:
            return []
        return value


class ServiceResponse(BaseModel):
    """Full response payload for the service information endpoint."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    service_uid: Annotated[str, Field(alias="serviceUid")]
    run_date: _dt.date = Field(alias="runDate")
    service_type: ServiceType = Field(alias="serviceType")
    is_passenger: bool = Field(alias="isPassenger")
    train_identity: str | None = Field(default=None, alias="trainIdentity")
    power_type: str | None = Field(default=None, alias="powerType")
    train_class: str | None = Field(default=None, alias="trainClass")
    sleeper: str | None = None
    atoc_code: str = Field(alias="atocCode")
    atoc_name: str = Field(alias="atocName")
    performance_monitored: bool = Field(alias="performanceMonitored")
    origin: list[Pair]
    destination: list[Pair]
    locations: list[LocationEvent]
    realtime_activated: bool = Field(default=False, alias="realtimeActivated")
    running_identity: str | None = Field(default=None, alias="runningIdentity")


class LocationRequest(BaseModel):
    """Validated request payload for a location line-up query."""

    model_config = ConfigDict(populate_by_name=True)

    station: str
    to_station: str | None = Field(default=None, alias="toStation")
    date: _dt.date | None = None
    time: _dt.time | None = None
    arrivals: bool = False

    @field_validator("station", "to_station")
    @classmethod
    def _strip_whitespace(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip()

    @classmethod
    def from_inputs(
        cls,
        station: str,
        to_station: str | None = None,
        when: _dt.date | _dt.datetime | None = None,
        arrivals: bool = False,
    ) -> "LocationRequest":
        date: _dt.date | None = None
        time: _dt.time | None = None
        if isinstance(when, _dt.datetime):
            date = when.date()
            time = when.time().replace(second=0, microsecond=0)
        elif isinstance(when, _dt.date):
            date = when
        elif when is not None:
            raise TypeError("when must be a date, datetime or None")
        return cls(
            station=station,
            to_station=to_station,
            date=date,
            time=time,
            arrivals=arrivals,
        )


class ServiceRequest(BaseModel):
    """Validated request payload for a service information query."""

    model_config = ConfigDict(populate_by_name=True)

    service_uid: Annotated[
        str, Field(alias="serviceUid", pattern=_SERVICE_UID_RE.pattern)
    ]
    date: _dt.date

    @classmethod
    def from_inputs(
        cls, service_uid: str, date: _dt.date | _dt.datetime
    ) -> "ServiceRequest":
        if isinstance(date, _dt.datetime):
            parsed_date = date.date()
        elif isinstance(date, _dt.date):
            parsed_date = date
        else:
            raise TypeError("date must be a date or datetime instance")
        return cls(service_uid=service_uid, date=parsed_date)
