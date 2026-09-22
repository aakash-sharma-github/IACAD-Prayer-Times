"""Data update coordinator for IACAD Prayer Times."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, datetime
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    PrayerTimesApiClient,
    PrayerTimesApiConnectionError,
    PrayerTimesApiError,
    PrayerTimesApiResponseError,
)
from .const import (
    CONF_CALCULATION_METHOD,
    CONF_HIGH_LATITUDE_RULE,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MADHAB,
    CONF_TIMEZONE,
    DATE_CHECK_INTERVAL,
    DOMAIN,
)
from .models import PrayerTimesData, PrayerTimesRequest

_LOGGER = logging.getLogger(__name__)


def _current_date(timezone: ZoneInfo) -> date:
    """Return today's date in the configured prayer-time timezone."""
    return datetime.now(timezone).date()


class PrayerTimesCoordinator(DataUpdateCoordinator[PrayerTimesData]):
    """Fetch one prayer-time response and share it with all integration entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        *,
        api_client: PrayerTimesApiClient | None = None,
        date_provider: Callable[[ZoneInfo], date] = _current_date,
    ) -> None:
        """Initialize the coordinator for one configuration entry."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=DATE_CHECK_INTERVAL,
            always_update=False,
        )
        self._timezone = ZoneInfo(entry.data[CONF_TIMEZONE])
        self._date_provider = date_provider
        self._api_client = api_client or PrayerTimesApiClient.from_hass(
            hass,
            PrayerTimesRequest(
                latitude=entry.data[CONF_LATITUDE],
                longitude=entry.data[CONF_LONGITUDE],
                timezone=entry.data[CONF_TIMEZONE],
                calculation_method=entry.data[CONF_CALCULATION_METHOD],
                madhab=entry.data[CONF_MADHAB],
                high_latitude_rule=entry.data[CONF_HIGH_LATITUDE_RULE],
            ),
        )

    async def _async_update_data(self) -> PrayerTimesData:
        """Fetch a new local date once, retaining valid data for the current date."""
        requested_date = self._date_provider(self._timezone)
        if self.data is not None and self.data.date == requested_date:
            return self.data

        try:
            return await self._api_client.async_get_prayer_times(requested_date)
        except PrayerTimesApiConnectionError as err:
            raise UpdateFailed(f"Unable to reach azanAPI: {err}") from err
        except PrayerTimesApiResponseError as err:
            raise UpdateFailed(f"Invalid azanAPI response: {err}") from err
        except PrayerTimesApiError as err:
            raise UpdateFailed(f"azanAPI request failed: {err}") from err
