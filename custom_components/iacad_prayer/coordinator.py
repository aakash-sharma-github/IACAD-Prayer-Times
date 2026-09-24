"""Data update coordinator for Adhan Prayer Time."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    PrayerTimesApiClient,
    PrayerTimesApiConnectionError,
    PrayerTimesApiError,
    PrayerTimesApiResponseError,
)
from .configuration import effective_entry_data
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
        schedule_at: Callable[
            [HomeAssistant, Callable[[datetime], None], datetime], Callable[[], None]
        ] = async_track_point_in_time,
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
        config = effective_entry_data(entry)
        self._timezone = ZoneInfo(config[CONF_TIMEZONE])
        self._date_provider = date_provider
        self._schedule_at = schedule_at
        self._unsub_midnight_refresh: Callable[[], None] | None = None
        self._api_client = api_client or PrayerTimesApiClient.from_hass(
            hass,
            PrayerTimesRequest(
                latitude=config[CONF_LATITUDE],
                longitude=config[CONF_LONGITUDE],
                timezone=config[CONF_TIMEZONE],
                calculation_method=config[CONF_CALCULATION_METHOD],
                madhab=config[CONF_MADHAB],
                high_latitude_rule=config[CONF_HIGH_LATITUDE_RULE],
            ),
        )

    async def _async_update_data(self) -> PrayerTimesData:
        """Fetch a new local date once, retaining valid data for the current date."""
        requested_date = self._date_provider(self._timezone)
        if self.data is not None and self.data.date == requested_date:
            self._schedule_next_midnight_refresh()
            return self.data

        try:
            data = await self._api_client.async_get_prayer_times(requested_date)
        except PrayerTimesApiConnectionError as err:
            raise UpdateFailed(f"Unable to reach azanAPI: {err}") from err
        except PrayerTimesApiResponseError as err:
            raise UpdateFailed(f"Invalid azanAPI response: {err}") from err
        except PrayerTimesApiError as err:
            raise UpdateFailed(f"azanAPI request failed: {err}") from err
        self._schedule_next_midnight_refresh()
        return data

    @callback
    def _schedule_next_midnight_refresh(self) -> None:
        """Schedule one refresh at the next midnight in the configured timezone."""
        if self._unsub_midnight_refresh is not None:
            self._unsub_midnight_refresh()

        next_midnight = datetime.combine(
            self._date_provider(self._timezone) + timedelta(days=1),
            time.min,
            tzinfo=self._timezone,
        )
        self._unsub_midnight_refresh = self._schedule_at(
            self.hass, self._async_handle_midnight_refresh, next_midnight
        )

    @callback
    def _async_handle_midnight_refresh(self, now: datetime) -> None:
        """Request an API refresh when the configured local date changes."""
        self.hass.async_create_task(self._async_refresh_after_midnight())

    async def _async_refresh_after_midnight(self) -> None:
        """Refresh at midnight and retain a future rollover schedule after failures."""
        try:
            await self.async_request_refresh()
        except Exception:
            self._schedule_next_midnight_refresh()
            raise

    @callback
    def async_cancel_midnight_refresh(self) -> None:
        """Cancel the pending midnight callback while unloading the entry."""
        if self._unsub_midnight_refresh is not None:
            self._unsub_midnight_refresh()
            self._unsub_midnight_refresh = None
