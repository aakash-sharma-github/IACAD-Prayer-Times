"""Validated data models for the azanAPI v1 contract."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Any

_TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_CALCULATED_PRAYERS = frozenset(
    {"fajr", "sunrise", "dhuhr", "asr", "sunset", "maghrib", "isha"}
)
_AZAN_PRAYERS = frozenset({"fajr", "dhuhr", "asr", "maghrib", "isha"})


class PrayerTimesResponseError(ValueError):
    """Raised when the API response does not meet the v1 contract."""


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise PrayerTimesResponseError(f"{field} must be an object")
    return value


def _parse_times(
    value: Any, field: str, expected_keys: frozenset[str]
) -> Mapping[str, str]:
    times = _require_mapping(value, field)
    if set(times) != expected_keys:
        raise PrayerTimesResponseError(
            f"{field} must contain exactly {sorted(expected_keys)}"
        )
    if not all(
        isinstance(time, str) and _TIME_PATTERN.fullmatch(time)
        for time in times.values()
    ):
        raise PrayerTimesResponseError(f"{field} values must be HH:MM strings")
    return MappingProxyType(dict(times))


def _parse_adjustments(value: Any) -> Mapping[str, int]:
    adjustments = _require_mapping(value, "adjustments_minutes")
    if set(adjustments) != _AZAN_PRAYERS:
        raise PrayerTimesResponseError(
            f"adjustments_minutes must contain exactly {sorted(_AZAN_PRAYERS)}"
        )
    if not all(
        isinstance(adjustment, int)
        and not isinstance(adjustment, bool)
        and -1440 <= adjustment <= 1440
        for adjustment in adjustments.values()
    ):
        raise PrayerTimesResponseError(
            "adjustments_minutes values must be integers from -1440 to 1440"
        )
    return MappingProxyType(dict(adjustments))


@dataclass(frozen=True)
class PrayerTimesRequest:
    """A v1 prayer-time request excluding the local calendar date."""

    latitude: float
    longitude: float
    timezone: str
    calculation_method: str
    madhab: str
    high_latitude_rule: str


@dataclass(frozen=True)
class PrayerTimesData:
    """A validated one-day prayer-time response."""

    date: date
    timezone: str
    latitude: float
    longitude: float
    calculation_method: str
    madhab: str
    high_latitude_rule: str
    calculated_times: Mapping[str, str]
    azan_times: Mapping[str, str]
    adjustments_minutes: Mapping[str, int]

    @classmethod
    def from_api_response(cls, value: Any) -> PrayerTimesData:
        """Parse and validate the documented v1 prayer-time response."""
        response = _require_mapping(value, "response")
        expected_fields = {
            "date",
            "timezone",
            "coordinates",
            "calculation_method",
            "madhab",
            "high_latitude_rule",
            "calculated_times",
            "azan_times",
            "adjustments_minutes",
        }
        if set(response) != expected_fields:
            raise PrayerTimesResponseError(
                "response fields do not match the v1 contract"
            )

        try:
            response_date = date.fromisoformat(response["date"])
        except (TypeError, ValueError) as err:
            raise PrayerTimesResponseError("date must be an ISO-8601 date") from err

        coordinates = _require_mapping(response["coordinates"], "coordinates")
        if set(coordinates) != {"latitude", "longitude"}:
            raise PrayerTimesResponseError(
                "coordinates must contain latitude and longitude"
            )
        latitude = coordinates["latitude"]
        longitude = coordinates["longitude"]
        if (
            isinstance(latitude, bool)
            or not isinstance(latitude, (int, float))
            or isinstance(longitude, bool)
            or not isinstance(longitude, (int, float))
        ):
            raise PrayerTimesResponseError("coordinates must be numbers")

        settings = ("timezone", "calculation_method", "madhab", "high_latitude_rule")
        if not all(isinstance(response[field], str) for field in settings):
            raise PrayerTimesResponseError("response settings must be strings")

        return cls(
            date=response_date,
            timezone=response["timezone"],
            latitude=float(latitude),
            longitude=float(longitude),
            calculation_method=response["calculation_method"],
            madhab=response["madhab"],
            high_latitude_rule=response["high_latitude_rule"],
            calculated_times=_parse_times(
                response["calculated_times"], "calculated_times", _CALCULATED_PRAYERS
            ),
            azan_times=_parse_times(
                response["azan_times"], "azan_times", _AZAN_PRAYERS
            ),
            adjustments_minutes=_parse_adjustments(response["adjustments_minutes"]),
        )
