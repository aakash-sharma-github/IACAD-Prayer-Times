"""Unit tests for the editable IACAD Prayer Times options flow."""

from __future__ import annotations

import asyncio
import sys
import unittest
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
data_entry_flow = ModuleType("homeassistant.data_entry_flow")
vol = ModuleType("voluptuous")


class FakeSchema:
    """Minimal voluptuous schema object."""

    def __init__(self, value: Any) -> None:
        self.value = value


vol.Schema = FakeSchema
vol.Required = lambda value, **kwargs: value
vol.All = lambda *values: values
vol.Coerce = lambda value: value
vol.Range = lambda **kwargs: kwargs
vol.In = lambda values: values
vol.Invalid = ValueError
sys.modules["voluptuous"] = vol


class FakeConfigFlow:
    """Minimal ConfigFlow base class."""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        return None

    async def async_set_unique_id(self, unique_id: str) -> None:
        return None

    def _abort_if_unique_id_configured(self) -> None:
        return None

    def async_create_entry(self, **kwargs: Any) -> dict[str, Any]:
        return {"type": "create_entry", **kwargs}

    def async_show_form(self, **kwargs: Any) -> dict[str, Any]:
        return {"type": "form", **kwargs}


class FakeOptionsFlowWithReload:
    """Minimal OptionsFlowWithReload base class."""

    config_entry: Any

    def add_suggested_values_to_schema(
        self, schema: FakeSchema, values: dict[str, Any]
    ) -> FakeSchema:
        return schema

    def async_create_entry(self, **kwargs: Any) -> dict[str, Any]:
        return {"type": "create_entry", **kwargs}

    def async_show_form(self, **kwargs: Any) -> dict[str, Any]:
        return {"type": "form", **kwargs}


config_entries.ConfigFlow = FakeConfigFlow
config_entries.ConfigEntry = object
config_entries.OptionsFlowWithReload = FakeOptionsFlowWithReload
core.callback = lambda function: function
data_entry_flow.FlowResult = dict[str, Any]
sys.modules["homeassistant"] = homeassistant
sys.modules["homeassistant.config_entries"] = config_entries
sys.modules["homeassistant.core"] = core
sys.modules["homeassistant.data_entry_flow"] = data_entry_flow
sys.modules.pop("iacad_prayer.config_flow", None)

from iacad_prayer.config_flow import IacadPrayerOptionsFlow


class FakeEntry:
    """Minimal config entry for options flow tests."""

    data: ClassVar = {
        "latitude": 25.2048,
        "longitude": 55.2708,
        "timezone": "Asia/Dubai",
        "calculation_method": "iacad_dubai",
        "madhab": "shafi",
        "high_latitude_rule": "middle_of_the_night",
    }
    options: ClassVar = {"timezone": "Europe/London", "madhab": "hanafi"}


class OptionsFlowTest(unittest.TestCase):
    """Verify options can be stored without recreating the integration entry."""

    def test_form_uses_existing_effective_configuration(self) -> None:
        flow = IacadPrayerOptionsFlow()
        flow.config_entry = FakeEntry()

        result = asyncio.run(flow.async_step_init())

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "init")

    def test_submitted_options_are_created_as_options_data(self) -> None:
        flow = IacadPrayerOptionsFlow()
        new_options = {
            "latitude": 51.5072,
            "longitude": -0.1276,
            "timezone": "Europe/London",
            "calculation_method": "north_america",
            "madhab": "hanafi",
            "high_latitude_rule": "twilight_angle",
        }

        result = asyncio.run(flow.async_step_init(new_options))

        self.assertEqual(result, {"type": "create_entry", "data": new_options})
