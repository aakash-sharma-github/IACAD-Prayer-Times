"""Unit tests for privacy-safe integration diagnostics."""

from __future__ import annotations

import asyncio
import sys
import unittest
from datetime import date
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
redact_data = ModuleType("homeassistant.helpers.redact_data")


def redact(value: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    """Small equivalent of Home Assistant's diagnostics redactor."""
    return {key: "**REDACTED**" if key in keys else item for key, item in value.items()}


config_entries.ConfigEntry = object
core.HomeAssistant = object
redact_data.async_redact_data = redact
sys.modules.setdefault("homeassistant", homeassistant)
sys.modules.setdefault("homeassistant.config_entries", config_entries)
sys.modules.setdefault("homeassistant.core", core)
sys.modules.setdefault("homeassistant.helpers", ModuleType("homeassistant.helpers"))
sys.modules.setdefault("homeassistant.helpers.redact_data", redact_data)

from iacad_prayer.diagnostics import async_get_config_entry_diagnostics
from iacad_prayer.models import PrayerTimesData


class FakeEntry:
    """Minimal entry and coordinator state for diagnostics tests."""

    data: ClassVar = {
        "latitude": 25.2048,
        "longitude": 55.2708,
        "timezone": "Asia/Dubai",
        "calculation_method": "iacad_dubai",
        "madhab": "shafi",
        "high_latitude_rule": "middle_of_the_night",
    }
    options: ClassVar = {}

    def __init__(self, data: PrayerTimesData | None) -> None:
        self.runtime_data = type(
            "Coordinator", (), {"data": data, "last_update_success": data is not None}
        )()


def prayer_data() -> PrayerTimesData:
    """Create a valid coordinator value for diagnostic assertions."""
    return PrayerTimesData.from_api_response(
        {
            "date": date(2026, 9, 24).isoformat(),
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


class DiagnosticsTest(unittest.TestCase):
    """Verify diagnostics retain useful data but redact location."""

    def test_diagnostics_redact_location_and_include_coordinator_status(self) -> None:
        result = asyncio.run(
            async_get_config_entry_diagnostics(object(), FakeEntry(prayer_data()))
        )

        self.assertEqual(result["entry"]["latitude"], "**REDACTED**")
        self.assertEqual(result["entry"]["longitude"], "**REDACTED**")
        self.assertTrue(result["coordinator"]["last_update_success"])
        self.assertNotIn("coordinates", result["coordinator"]["data"])

    def test_diagnostics_support_unavailable_coordinator(self) -> None:
        result = asyncio.run(
            async_get_config_entry_diagnostics(object(), FakeEntry(None))
        )

        self.assertFalse(result["coordinator"]["last_update_success"])
        self.assertIsNone(result["coordinator"]["data"])
