"""Unit tests for prayer-time timestamp sensors."""

from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any

CUSTOM_COMPONENTS_PATH = Path(__file__).parents[1]
INTEGRATION_PATH = CUSTOM_COMPONENTS_PATH / "iacad_prayer"
package = ModuleType("iacad_prayer")
package.__path__ = [str(INTEGRATION_PATH)]
sys.modules.setdefault("iacad_prayer", package)

homeassistant = ModuleType("homeassistant")
components = ModuleType("homeassistant.components")
sensor_component = ModuleType("homeassistant.components.sensor")
config_entries = ModuleType("homeassistant.config_entries")
core = ModuleType("homeassistant.core")
device_registry = ModuleType("homeassistant.helpers.device_registry")
entity_platform = ModuleType("homeassistant.helpers.entity_platform")
update_coordinator = ModuleType("homeassistant.helpers.update_coordinator")


@dataclass(frozen=True, kw_only=True)
class FakeSensorEntityDescription:
    """Minimal sensor entity description."""

    key: str
    translation_key: str | None = None
    device_class: str | None = None


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


class FakeSensorEntity:
    """Minimal sensor base."""

    @property
    def unique_id(self) -> str | None:
        return getattr(self, "_attr_unique_id", None)


sensor_component.SensorDeviceClass = type(
    "SensorDeviceClass", (), {"TIMESTAMP": "timestamp"}
)
sensor_component.SensorEntity = FakeSensorEntity
sensor_component.SensorEntityDescription = FakeSensorEntityDescription
config_entries.ConfigEntry = object
core.HomeAssistant = object
device_registry.DeviceInfo = dict
entity_platform.AddEntitiesCallback = object
update_coordinator.CoordinatorEntity = FakeCoordinatorEntity
sys.modules.setdefault("homeassistant", homeassistant)
sys.modules.setdefault("homeassistant.components", components)
sys.modules.setdefault("homeassistant.components.sensor", sensor_component)
sys.modules.setdefault("homeassistant.config_entries", config_entries)
sys.modules.setdefault("homeassistant.core", core)
sys.modules.setdefault("homeassistant.helpers", ModuleType("homeassistant.helpers"))
sys.modules.setdefault("homeassistant.helpers.device_registry", device_registry)
sys.modules.setdefault("homeassistant.helpers.entity_platform", entity_platform)
sys.modules.setdefault("homeassistant.helpers.update_coordinator", update_coordinator)

coordinator_module = ModuleType("iacad_prayer.coordinator")
coordinator_module.PrayerTimesCoordinator = object
sys.modules.setdefault("iacad_prayer.coordinator", coordinator_module)

from iacad_prayer.models import PrayerTimesData
from iacad_prayer.sensor import SENSOR_DESCRIPTIONS, PrayerTimeSensor


def coordinator_with_data(data: PrayerTimesData | None) -> Any:
    """Create the coordinator shape required by a sensor."""
    return type("Coordinator", (), {"data": data})()


DATA = PrayerTimesData.from_api_response(
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
            "isha": "19:34",
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


class PrayerTimeSensorTest(unittest.TestCase):
    """Verify sensor state and coordinator availability behavior."""

    def test_defines_all_seven_calculated_prayer_and_solar_event_sensors(self) -> None:
        self.assertEqual(
            [description.key for description in SENSOR_DESCRIPTIONS],
            ["fajr", "sunrise", "dhuhr", "asr", "sunset", "maghrib", "isha"],
        )

    def test_returns_a_timezone_aware_timestamp(self) -> None:
        sensor = PrayerTimeSensor(
            coordinator_with_data(DATA), "entry-id", SENSOR_DESCRIPTIONS[0]
        )

        self.assertEqual(sensor.unique_id, "entry-id_fajr")
        self.assertEqual(
            sensor.native_value,
            datetime(2026, 9, 24, 4, 50, tzinfo=sensor.native_value.tzinfo),
        )
        self.assertEqual(sensor.native_value.tzinfo.key, "Asia/Dubai")
        self.assertTrue(sensor.available)

    def test_is_unavailable_without_coordinator_data(self) -> None:
        sensor = PrayerTimeSensor(
            coordinator_with_data(None), "entry-id", SENSOR_DESCRIPTIONS[0]
        )

        self.assertIsNone(sensor.native_value)
        self.assertFalse(sensor.available)
