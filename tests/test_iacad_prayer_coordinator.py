"""Unit tests for the prayer-times data update coordinator."""

from __future__ import annotations

import asyncio
import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from types import ModuleType
from typing import Any, ClassVar

CUSTOM_COMPONENTS_PATH = Path(__file__).parents[1] / "custom_components"
INTEGRATION_PATH = CUSTOM_COMPONENTS_PATH / "iacad_prayer"
package = ModuleType("iacad_prayer")
package.__path__ = [str(INTEGRATION_PATH)]
sys.modules.setdefault("iacad_prayer", package)

homeassistant = ModuleType("homeassistant")
config_entries = ModuleType("homeassistant.config_entries")
core = ModuleType("homeassistant.core")
event_helper = ModuleType("homeassistant.helpers.event")
update_coordinator = ModuleType("homeassistant.helpers.update_coordinator")


class FakeDataUpdateCoordinator:
    """Minimal coordinator base used without Home Assistant installed."""

    @classmethod
    def __class_getitem__(cls, item: object) -> type[FakeDataUpdateCoordinator]:
        return cls

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.hass = args[0]
        self.data = None
        self.update_interval = kwargs["update_interval"]

    async def async_request_refresh(self) -> None:
        self.data = await self._async_update_data()


class FakeUpdateFailed(Exception):
    """Minimal Home Assistant update failure."""


config_entries.ConfigEntry = object
core.HomeAssistant = object
core.callback = lambda function: function
event_helper.async_track_point_in_time = lambda *args: lambda: None
update_coordinator.DataUpdateCoordinator = FakeDataUpdateCoordinator
update_coordinator.UpdateFailed = FakeUpdateFailed
sys.modules["homeassistant"] = homeassistant
sys.modules["homeassistant.config_entries"] = config_entries
sys.modules["homeassistant.core"] = core
sys.modules["homeassistant.helpers"] = ModuleType("homeassistant.helpers")
sys.modules["homeassistant.helpers.event"] = event_helper
sys.modules["homeassistant.helpers.update_coordinator"] = update_coordinator
sys.modules.pop("iacad_prayer.coordinator", None)

from iacad_prayer.api import PrayerTimesApiConnectionError
from iacad_prayer.coordinator import PrayerTimesCoordinator
from iacad_prayer.models import PrayerTimesData

ENTRY_DATA = {
    "latitude": 25.2048,
    "longitude": 55.2708,
    "timezone": "Asia/Dubai",
    "calculation_method": "iacad_dubai",
    "madhab": "shafi",
    "high_latitude_rule": "middle_of_the_night",
}


class FakeEntry:
    """Minimal config entry containing immutable configuration data."""

    data = ENTRY_DATA
    options: ClassVar = {}


def prayer_times_data(day: date) -> PrayerTimesData:
    """Create a valid response model for coordinator tests."""
    return PrayerTimesData.from_api_response(
        {
            "date": day.isoformat(),
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
    )


class FakeApiClient:
    """Client double that records requested local dates."""

    def __init__(self, result: PrayerTimesData | Exception) -> None:
        self.result = result
        self.requested_dates: list[date] = []

    async def async_get_prayer_times(self, requested_date: date) -> PrayerTimesData:
        self.requested_dates.append(requested_date)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeScheduler:
    """Capture one-shot midnight schedules without Home Assistant's event loop."""

    def __init__(self) -> None:
        self.scheduled: list[tuple[object, object, datetime]] = []
        self.cancelled = 0

    def __call__(self, hass: object, callback: object, when: datetime):
        self.scheduled.append((hass, callback, when))

        def cancel() -> None:
            self.cancelled += 1

        return cancel


class FakeHass:
    """Minimal Home Assistant task scheduler."""

    def async_create_task(self, coroutine: Any) -> None:
        asyncio.run(coroutine)


class PrayerTimesCoordinatorTest(unittest.TestCase):
    """Verify caching, rollover, and error availability behavior."""

    def test_fetches_the_current_configured_local_date(self) -> None:
        current_date = date(2026, 9, 23)
        api_client = FakeApiClient(prayer_times_data(current_date))
        coordinator = PrayerTimesCoordinator(
            object(),
            FakeEntry(),
            api_client=api_client,
            date_provider=lambda _: current_date,
        )

        data = asyncio.run(coordinator._async_update_data())

        self.assertEqual(data.date, current_date)
        self.assertEqual(api_client.requested_dates, [current_date])

    def test_uses_cached_data_until_the_local_date_changes(self) -> None:
        current_date = date(2026, 9, 23)
        api_client = FakeApiClient(prayer_times_data(current_date))
        coordinator = PrayerTimesCoordinator(
            object(),
            FakeEntry(),
            api_client=api_client,
            date_provider=lambda _: current_date,
        )
        coordinator.data = prayer_times_data(current_date)

        data = asyncio.run(coordinator._async_update_data())

        self.assertIs(data, coordinator.data)
        self.assertEqual(api_client.requested_dates, [])

    def test_fetches_again_when_the_local_date_rolls_over(self) -> None:
        tomorrow = date(2026, 9, 24)
        api_client = FakeApiClient(prayer_times_data(tomorrow))
        coordinator = PrayerTimesCoordinator(
            object(),
            FakeEntry(),
            api_client=api_client,
            date_provider=lambda _: tomorrow,
        )
        coordinator.data = prayer_times_data(date(2026, 9, 23))

        data = asyncio.run(coordinator._async_update_data())

        self.assertEqual(data.date, tomorrow)
        self.assertEqual(api_client.requested_dates, [tomorrow])

    def test_maps_api_failures_to_update_failed(self) -> None:
        current_date = date(2026, 9, 23)
        coordinator = PrayerTimesCoordinator(
            object(),
            FakeEntry(),
            api_client=FakeApiClient(PrayerTimesApiConnectionError("offline")),
            date_provider=lambda _: current_date,
        )

        with self.assertRaises(FakeUpdateFailed):
            asyncio.run(coordinator._async_update_data())

    def test_schedules_the_next_configured_local_midnight_after_refresh(self) -> None:
        current_date = date(2026, 9, 24)
        scheduler = FakeScheduler()
        coordinator = PrayerTimesCoordinator(
            FakeHass(),
            FakeEntry(),
            api_client=FakeApiClient(prayer_times_data(current_date)),
            date_provider=lambda _: current_date,
            schedule_at=scheduler,
        )

        asyncio.run(coordinator._async_update_data())

        self.assertEqual(
            scheduler.scheduled[0][2],
            datetime(2026, 9, 25, 0, 0, tzinfo=scheduler.scheduled[0][2].tzinfo),
        )
        self.assertEqual(scheduler.scheduled[0][2].tzinfo.key, "Asia/Dubai")

    def test_midnight_callback_fetches_the_new_local_date_and_reschedules(self) -> None:
        current_date = date(2026, 9, 25)
        scheduler = FakeScheduler()
        api_client = FakeApiClient(prayer_times_data(date(2026, 9, 25)))
        coordinator = PrayerTimesCoordinator(
            FakeHass(),
            FakeEntry(),
            api_client=api_client,
            date_provider=lambda _: current_date,
            schedule_at=scheduler,
        )
        coordinator.data = prayer_times_data(date(2026, 9, 24))

        asyncio.run(coordinator._async_refresh_after_midnight())

        self.assertEqual(api_client.requested_dates, [date(2026, 9, 25)])
        self.assertGreaterEqual(len(scheduler.scheduled), 1)

    def test_cancels_the_midnight_callback_on_unload(self) -> None:
        current_date = date(2026, 9, 24)
        scheduler = FakeScheduler()
        coordinator = PrayerTimesCoordinator(
            FakeHass(),
            FakeEntry(),
            api_client=FakeApiClient(prayer_times_data(current_date)),
            date_provider=lambda _: current_date,
            schedule_at=scheduler,
        )
        asyncio.run(coordinator._async_update_data())

        coordinator.async_cancel_midnight_refresh()

        self.assertEqual(scheduler.cancelled, 1)

    def test_midnight_failure_still_schedules_the_following_local_midnight(
        self,
    ) -> None:
        current_date = date(2026, 9, 25)
        scheduler = FakeScheduler()
        coordinator = PrayerTimesCoordinator(
            FakeHass(),
            FakeEntry(),
            api_client=FakeApiClient(PrayerTimesApiConnectionError("offline")),
            date_provider=lambda _: current_date,
            schedule_at=scheduler,
        )

        with self.assertRaises(FakeUpdateFailed):
            asyncio.run(coordinator._async_refresh_after_midnight())

        self.assertEqual(scheduler.scheduled[0][2].date(), date(2026, 9, 26))
