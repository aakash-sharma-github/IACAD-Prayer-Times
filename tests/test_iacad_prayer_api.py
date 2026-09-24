"""Unit tests for the asynchronous prayer-times API client."""

from __future__ import annotations

import asyncio
import sys
import unittest
from datetime import date
from pathlib import Path
from types import ModuleType
from typing import Any, Self

CUSTOM_COMPONENTS_PATH = Path(__file__).parents[1] / "custom_components"
INTEGRATION_PATH = CUSTOM_COMPONENTS_PATH / "iacad_prayer"
package = ModuleType("iacad_prayer")
package.__path__ = [str(INTEGRATION_PATH)]
sys.modules.setdefault("iacad_prayer", package)

from iacad_prayer.api import (
    ClientError,
    PrayerTimesApiClient,
    PrayerTimesApiConnectionError,
    PrayerTimesApiRateLimitError,
    PrayerTimesApiRequestError,
    PrayerTimesApiResponseError,
    PrayerTimesApiTimeoutError,
)
from iacad_prayer.models import PrayerTimesRequest

REQUEST = PrayerTimesRequest(
    latitude=25.2048,
    longitude=55.2708,
    timezone="Asia/Dubai",
    calculation_method="iacad_dubai",
    madhab="shafi",
    high_latitude_rule="middle_of_the_night",
)
RESPONSE = {
    "date": "2026-09-23",
    "timezone": "Asia/Dubai",
    "coordinates": {"latitude": 25.2048, "longitude": 55.2708},
    "calculation_method": "iacad_dubai",
    "madhab": "shafi",
    "high_latitude_rule": "middle_of_the_night",
    "calculated_times": {
        "fajr": "04:49",
        "sunrise": "06:04",
        "dhuhr": "12:15",
        "asr": "15:40",
        "sunset": "18:17",
        "maghrib": "18:21",
        "isha": "19:35",
    },
    "azan_times": {
        "fajr": "04:49",
        "dhuhr": "12:15",
        "asr": "15:40",
        "maghrib": "18:21",
        "isha": "19:35",
    },
    "adjustments_minutes": {
        "fajr": 0,
        "dhuhr": 0,
        "asr": 0,
        "maghrib": 0,
        "isha": 0,
    },
}


class FakeResponse:
    """In-memory async HTTP response."""

    def __init__(self, status: int, payload: Any) -> None:
        self.status = status
        self._payload = payload

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def json(self, **kwargs: Any) -> Any:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    """In-memory async HTTP session."""

    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append((url, kwargs))
        return self.response


class FailingSession:
    """Session that fails before an HTTP response is available."""

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        raise OSError("network unreachable")


class ClientErrorSession:
    """Session that raises an aiohttp-compatible connection error."""

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        raise ClientError("connection reset")


class TimeoutResponse(FakeResponse):
    """Response context that simulates an HTTP timeout."""

    async def __aenter__(self) -> FakeResponse:
        raise asyncio.TimeoutError


class PrayerTimesApiClientTest(unittest.TestCase):
    """Verify requests, parsing, and error mapping without network access."""

    def test_fetches_and_parses_a_valid_response(self) -> None:
        session = FakeSession(FakeResponse(200, RESPONSE))

        result = asyncio.run(
            PrayerTimesApiClient(session, REQUEST).async_get_prayer_times(
                date(2026, 9, 23)
            )
        )

        self.assertEqual(result.date, date(2026, 9, 23))
        self.assertEqual(result.calculated_times["fajr"], "04:49")
        self.assertEqual(result.azan_times["isha"], "19:35")
        self.assertEqual(
            session.calls[0][0], "https://api.aakashsharma.com.np/api/v1/prayer-times"
        )
        self.assertEqual(session.calls[0][1]["params"]["date"], "2026-09-23")

    def test_rejects_malformed_response(self) -> None:
        malformed = {**RESPONSE, "calculated_times": {"fajr": "4:49"}}

        with self.assertRaises(PrayerTimesApiResponseError):
            asyncio.run(
                PrayerTimesApiClient(
                    FakeSession(FakeResponse(200, malformed)), REQUEST
                ).async_get_prayer_times(date(2026, 9, 23))
            )

    def test_maps_http_errors(self) -> None:
        with self.assertRaises(PrayerTimesApiRequestError) as error:
            asyncio.run(
                PrayerTimesApiClient(
                    FakeSession(
                        FakeResponse(
                            400,
                            {
                                "error": {
                                    "code": "INVALID_TIMEZONE",
                                    "message": "Bad timezone",
                                }
                            },
                        )
                    ),
                    REQUEST,
                ).async_get_prayer_times(date(2026, 9, 23))
            )

        self.assertEqual(error.exception.status, 400)
        self.assertEqual(error.exception.code, "INVALID_TIMEZONE")

    def test_maps_rate_limits_and_timeouts(self) -> None:
        with self.assertRaises(PrayerTimesApiRateLimitError):
            asyncio.run(
                PrayerTimesApiClient(
                    FakeSession(FakeResponse(429, {"error": {"message": "Slow down"}})),
                    REQUEST,
                ).async_get_prayer_times(date(2026, 9, 23))
            )

    def test_maps_connection_and_invalid_json_errors(self) -> None:
        with self.assertRaises(PrayerTimesApiConnectionError):
            asyncio.run(
                PrayerTimesApiClient(FailingSession(), REQUEST).async_get_prayer_times(
                    date(2026, 9, 23)
                )
            )
        with self.assertRaises(PrayerTimesApiConnectionError):
            asyncio.run(
                PrayerTimesApiClient(
                    ClientErrorSession(), REQUEST
                ).async_get_prayer_times(date(2026, 9, 23))
            )
        with self.assertRaisesRegex(PrayerTimesApiResponseError, "valid JSON"):
            asyncio.run(
                PrayerTimesApiClient(
                    FakeSession(FakeResponse(200, ValueError("not JSON"))), REQUEST
                ).async_get_prayer_times(date(2026, 9, 23))
            )
        with self.assertRaises(PrayerTimesApiTimeoutError):
            asyncio.run(
                PrayerTimesApiClient(
                    FakeSession(TimeoutResponse(200, RESPONSE)), REQUEST
                ).async_get_prayer_times(date(2026, 9, 23))
            )

    def test_rejects_response_for_another_date(self) -> None:
        wrong_date = {**RESPONSE, "date": "2026-09-24"}

        with self.assertRaisesRegex(PrayerTimesApiResponseError, "date"):
            asyncio.run(
                PrayerTimesApiClient(
                    FakeSession(FakeResponse(200, wrong_date)), REQUEST
                ).async_get_prayer_times(date(2026, 9, 23))
            )
