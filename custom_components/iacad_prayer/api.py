"""Asynchronous client for the azanAPI v1 endpoints."""

from __future__ import annotations

import asyncio
from datetime import date
from typing import TYPE_CHECKING, Any, Protocol

try:
    from aiohttp import ClientError
except ImportError:  # pragma: no cover - Home Assistant installs aiohttp.

    class ClientError(Exception):
        """Fallback for running the standalone unit tests without aiohttp."""


from .const import API_BASE_URL
from .models import PrayerTimesData, PrayerTimesRequest, PrayerTimesResponseError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

REQUEST_TIMEOUT_SECONDS = 10


class PrayerTimesApiError(Exception):
    """Base class for prayer-times API failures."""


class PrayerTimesApiConnectionError(PrayerTimesApiError):
    """The API could not be reached."""


class PrayerTimesApiTimeoutError(PrayerTimesApiConnectionError):
    """The API did not respond before the request timeout."""


class PrayerTimesApiRequestError(PrayerTimesApiError):
    """The API returned a non-success HTTP response."""

    def __init__(self, status: int, code: str | None, message: str) -> None:
        self.status = status
        self.code = code
        self.message = message
        super().__init__(f"HTTP {status}: {message}")


class PrayerTimesApiRateLimitError(PrayerTimesApiRequestError):
    """The API rejected the request because of rate limiting."""


class PrayerTimesApiResponseError(PrayerTimesApiError):
    """The API returned a malformed or inconsistent response."""


class _Response(Protocol):
    status: int

    async def json(self, **kwargs: Any) -> Any:
        """Return the response JSON."""


class _RequestContextManager(Protocol):
    async def __aenter__(self) -> _Response:
        """Enter the request context."""

    async def __aexit__(self, *args: object) -> None:
        """Exit the request context."""


class _Session(Protocol):
    def get(self, url: str, **kwargs: Any) -> _RequestContextManager:
        """Begin an asynchronous HTTP GET request."""


class PrayerTimesApiClient:
    """Fetch and validate data from the azanAPI v1 prayer-time endpoint."""

    def __init__(self, session: _Session, request: PrayerTimesRequest) -> None:
        self._session = session
        self._request = request

    @classmethod
    def from_hass(
        cls, hass: HomeAssistant, request: PrayerTimesRequest
    ) -> PrayerTimesApiClient:
        """Create a client using Home Assistant's shared aiohttp session."""
        from homeassistant.helpers.aiohttp_client import async_get_clientsession

        return cls(async_get_clientsession(hass), request)

    async def async_get_prayer_times(self, calculation_date: date) -> PrayerTimesData:
        """Fetch prayer times for an explicit local calendar date."""
        params = {
            "latitude": self._request.latitude,
            "longitude": self._request.longitude,
            "timezone": self._request.timezone,
            "date": calculation_date.isoformat(),
            "calculation_method": self._request.calculation_method,
            "madhab": self._request.madhab,
            "high_latitude_rule": self._request.high_latitude_rule,
        }
        payload = await self._async_get_json("/api/v1/prayer-times", params)

        try:
            prayer_times = PrayerTimesData.from_api_response(payload)
        except PrayerTimesResponseError as err:
            raise PrayerTimesApiResponseError(str(err)) from err

        self._validate_response_matches_request(prayer_times, calculation_date)
        return prayer_times

    async def _async_get_json(self, path: str, params: dict[str, Any]) -> Any:
        """Request JSON and map transport and API errors to client exceptions."""
        try:
            async with self._session.get(
                f"{API_BASE_URL}{path}", params=params, timeout=REQUEST_TIMEOUT_SECONDS
            ) as response:
                try:
                    payload = await response.json(content_type=None)
                except (TypeError, ValueError) as err:
                    raise PrayerTimesApiResponseError(
                        "API response is not valid JSON"
                    ) from err
        except asyncio.TimeoutError as err:
            raise PrayerTimesApiTimeoutError("API request timed out") from err
        except (ClientError, OSError) as err:
            raise PrayerTimesApiConnectionError("Unable to connect to the API") from err

        if response.status == 429:
            code, message = self._error_details(payload)
            raise PrayerTimesApiRateLimitError(response.status, code, message)
        if not 200 <= response.status < 300:
            code, message = self._error_details(payload)
            raise PrayerTimesApiRequestError(response.status, code, message)
        return payload

    def _validate_response_matches_request(
        self, prayer_times: PrayerTimesData, calculation_date: date
    ) -> None:
        """Reject a successful response that does not match its explicit request."""
        if prayer_times.date != calculation_date:
            raise PrayerTimesApiResponseError(
                "response date does not match the requested date"
            )
        if prayer_times.timezone != self._request.timezone:
            raise PrayerTimesApiResponseError(
                "response timezone does not match the requested timezone"
            )
        if (
            prayer_times.latitude != self._request.latitude
            or prayer_times.longitude != self._request.longitude
        ):
            raise PrayerTimesApiResponseError(
                "response coordinates do not match the request"
            )
        for field in ("calculation_method", "madhab", "high_latitude_rule"):
            if getattr(prayer_times, field) != getattr(self._request, field):
                raise PrayerTimesApiResponseError(
                    f"response {field} does not match the request"
                )

    @staticmethod
    def _error_details(payload: Any) -> tuple[str | None, str]:
        """Extract a safe error summary from the API's documented envelope."""
        if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
            error = payload["error"]
            code = error.get("code") if isinstance(error.get("code"), str) else None
            message = error.get("message")
            if isinstance(message, str):
                return code, message
        return None, "API request failed"
