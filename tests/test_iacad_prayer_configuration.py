"""Tests for config-entry data and user options merging."""

from pathlib import Path
import sys
from types import ModuleType
import unittest

CUSTOM_COMPONENTS_PATH = Path(__file__).parents[1]
INTEGRATION_PATH = CUSTOM_COMPONENTS_PATH / "iacad_prayer"
package = ModuleType("iacad_prayer")
package.__path__ = [str(INTEGRATION_PATH)]
sys.modules.setdefault("iacad_prayer", package)

from iacad_prayer.configuration import effective_entry_data  # noqa: E402


class FakeEntry:
    """Minimal config entry with initial data and user options."""

    data = {
        "latitude": 25.2048,
        "longitude": 55.2708,
        "timezone": "Asia/Dubai",
        "calculation_method": "iacad_dubai",
        "madhab": "shafi",
        "high_latitude_rule": "middle_of_the_night",
    }
    options = {
        "latitude": 51.5072,
        "longitude": -0.1276,
        "timezone": "Europe/London",
        "calculation_method": "north_america",
        "madhab": "hanafi",
        "high_latitude_rule": "twilight_angle",
    }


class ConfigurationTest(unittest.TestCase):
    """Verify options become the effective coordinator configuration."""

    def test_options_override_initial_config_entry_data(self) -> None:
        configuration = effective_entry_data(FakeEntry())

        self.assertEqual(configuration, FakeEntry.options)
        self.assertEqual(FakeEntry.data["timezone"], "Asia/Dubai")
