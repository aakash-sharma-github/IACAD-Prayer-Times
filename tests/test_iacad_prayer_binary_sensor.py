"""Unit tests for one-minute adjusted-Azan active binary sensors."""

from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any
from zoneinfo import ZoneInfo

CUSTOM_COMPONENTS_PATH = Path(__file__).parents[1]
INTEGRATION_PATH = CUSTOM_COMPONENTS_PATH / "iacad_prayer"
package = ModuleType("iacad_prayer")
package.__path__ = [str(INTEGRATION_PATH)]
sys.modules.setdefault("iacad_prayer", package)

homeassistant = ModuleType("homeassistant")
components = ModuleType("homeassistant.components")
binary_sensor_component = ModuleType("homeassistant.components.binary_sensor")
config_entries = ModuleType("homeassistant.config_entries")
core = ModuleType("homeassistant.core")
device_registry = ModuleType("homeassistant.helpers.device_registry")
event_helper = ModuleType("homeassistant.helpers.event")
update_coordinator = ModuleType("homeassistant.helpers.update_coordinator")


@dataclass(frozen=True, kw_only=True)
class FakeBinarySensorEntityDescription:
    """Minimal binary sensor entity description."""

    key: str
    translation_key: str | None = None


class FakeCoordinatorEntity:
    """Minimal coordinator entity base."""

    @classmethod
    def __class_getitem__(cls, item: object) -> type[FakeCoordinatorEntity]:
        return cls

    def __init__(self, coordinator: Any) -> None:
        self.coordinator = coordinator

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None


class FakeBinarySensorEntity:
    """Minimal binary sensor base."""

    @property
    def unique_id(self) -> str | None:
        return getattr(self, "_attr_unique_id", None)


binary_sensor_component.BinarySensorEntity = FakeBinarySensorEntity
binary_sensor_component.BinarySensorEntityDescription = (
    FakeBinarySensorEntityDescription
)
config_entries.ConfigEntry = object
core.HomeAssistant = object
device_registry.DeviceInfo = dict
event_helper.async_track_time_interval = lambda *args: lambda: None
update_coordinator.CoordinatorEntity = FakeCoordinatorEntity
sys.modules.setdefault("homeassistant", homeassistant)
sys.modules.setdefault("homeassistant.components", components)
sys.modules.setdefault(
    "homeassistant.components.binary_sensor", binary_sensor_component
)
sys.modules.setdefault("homeassistant.config_entries", config_entries)
sys.modules.setdefault("homeassistant.core", core)
sys.modules.setdefault("homeassistant.helpers", ModuleType("homeassistant.helpers"))
sys.modules.setdefault("homeassistant.helpers.device_registry", device_registry)
sys.modules.setdefault("homeassistant.helpers.event", event_helper)
sys.modules.setdefault("homeassistant.helpers.update_coordinator", update_coordinator)

coordinator_module = ModuleType("iacad_prayer.coordinator")
coordinator_module.PrayerTimesCoordinator = object
sys.modules.setdefault("iacad_prayer.coordinator", coordinator_module)

from iacad_prayer.binary_sensor import (
    BINARY_SENSOR_DESCRIPTIONS,
    PrayerActiveBinarySensor,
)
from iacad_prayer.models import PrayerTimesData


def coordinator_with_data(data: PrayerTimesData | None) -> Any:
    """Create the coordinator shape required by a binary sensor."""
    return type("Coordinator", (), {"data": data})()


def prayer_data(
    *, isha_time: str = "19:34", isha_adjustment: int = 0
) -> PrayerTimesData:
    """Create coordinator data with final Azan times and adjustments."""
    return PrayerTimesData.from_api_response(
        {
            "date": "2026-09-24",
            "timezone": "Asia/Dubai",
            "coordinates": {"latitude": 25.2048, "longitude": 55.2708},
            "calculation_method": "iacad_dubai",
            "madhab": "shafi",
            "high_latitude_rule": "middle_of_the_night",
            "calculated_times": {
                "fajr": "04:50",
                "sunrise": "06:04",
                "dhuhr": "12:15",
                "asr": "15:39",
                "sunset": "18:16",
                "maghrib": "18:20",
                "isha": "19:34",
            },
            "azan_times": {
                "fajr": "04:50",
                "dhuhr": "12:15",
                "asr": "15:39",
                "maghrib": "18:20",
                "isha": isha_time,
            },
            "adjustments_minutes": {
                "fajr": 0,
                "dhuhr": 0,
                "asr": 0,
                "maghrib": 0,
                "isha": isha_adjustment,
            },
        }
    )


class PrayerActiveBinarySensorTest(unittest.TestCase):
    """Verify exact active-window boundaries and adjusted Azan behavior."""

    def setUp(self) -> None:
        self.timezone = ZoneInfo("Asia/Dubai")
        self.sensor = PrayerActiveBinarySensor(
            coordinator_with_data(prayer_data()),
            "entry-id",
            BINARY_SENSOR_DESCRIPTIONS[0],
        )

    def test_defines_exactly_five_azan_active_binary_sensors(self) -> None:
        self.assertEqual(
            [description.key for description in BINARY_SENSOR_DESCRIPTIONS],
            [
                "fajr_active",
                "dhuhr_active",
                "asr_active",
                "maghrib_active",
                "isha_active",
            ],
        )
        self.assertEqual(self.sensor.unique_id, "entry-id_fajr_active")

    def test_active_window_boundaries(self) -> None:
        self.assertFalse(
            self.sensor._is_active_at(
                datetime(2026, 9, 24, 4, 49, 59, tzinfo=self.timezone)
            )
        )
        self.assertTrue(
            self.sensor._is_active_at(
                datetime(2026, 9, 24, 4, 50, tzinfo=self.timezone)
            )
        )
        self.assertTrue(
            self.sensor._is_active_at(
                datetime(2026, 9, 24, 4, 50, 30, tzinfo=self.timezone)
            )
        )
        self.assertTrue(
            self.sensor._is_active_at(
                datetime(2026, 9, 24, 4, 50, 59, tzinfo=self.timezone)
            )
        )
        self.assertFalse(
            self.sensor._is_active_at(
                datetime(2026, 9, 24, 4, 51, tzinfo=self.timezone)
            )
        )
        self.assertFalse(
            self.sensor._is_active_at(
                datetime(2026, 9, 24, 4, 52, tzinfo=self.timezone)
            )
        )

    def test_uses_final_adjusted_azan_time(self) -> None:
        isha_sensor = PrayerActiveBinarySensor(
            coordinator_with_data(prayer_data(isha_time="19:36", isha_adjustment=2)),
            "entry-id",
            BINARY_SENSOR_DESCRIPTIONS[-1],
        )

        self.assertFalse(
            isha_sensor._is_active_at(
                datetime(2026, 9, 24, 19, 34, tzinfo=self.timezone)
            )
        )
        self.assertTrue(
            isha_sensor._is_active_at(
                datetime(2026, 9, 24, 19, 36, tzinfo=self.timezone)
            )
        )

    def test_adjusted_azan_rollover_uses_the_correct_date(self) -> None:
        isha_sensor = PrayerActiveBinarySensor(
            coordinator_with_data(prayer_data(isha_time="00:01", isha_adjustment=267)),
            "entry-id",
            BINARY_SENSOR_DESCRIPTIONS[-1],
        )

        self.assertFalse(
            isha_sensor._is_active_at(datetime(2026, 9, 24, 0, 1, tzinfo=self.timezone))
        )
        self.assertTrue(
            isha_sensor._is_active_at(datetime(2026, 9, 25, 0, 1, tzinfo=self.timezone))
        )
        self.assertFalse(
            isha_sensor._is_active_at(datetime(2026, 9, 25, 0, 2, tzinfo=self.timezone))
        )

    def test_is_unavailable_without_coordinator_data(self) -> None:
        sensor = PrayerActiveBinarySensor(
            coordinator_with_data(None), "entry-id", BINARY_SENSOR_DESCRIPTIONS[0]
        )

        self.assertIsNone(sensor.is_on)
        self.assertFalse(sensor.available)
