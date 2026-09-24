"""Unit tests for config-entry setup and restart behavior."""

from __future__ import annotations

import asyncio
import importlib
import sys
import unittest
from types import ModuleType
from typing import Any

homeassistant = ModuleType("homeassistant")
config_entries = ModuleType("homeassistant.config_entries")
core = ModuleType("homeassistant.core")
coordinator_module = ModuleType("iacad_prayer.coordinator")


class FakeCoordinator:
    """Coordinator double used to exercise integration setup."""

    fail_refresh = False

    def __init__(self, hass: Any, entry: Any) -> None:
        self.entry = entry
        self.cancelled = False

    async def async_config_entry_first_refresh(self) -> None:
        if self.fail_refresh:
            raise RuntimeError("service unavailable")

    def async_cancel_midnight_refresh(self) -> None:
        self.cancelled = True


config_entries.ConfigEntry = object
core.HomeAssistant = object
coordinator_module.PrayerTimesCoordinator = FakeCoordinator
sys.modules["homeassistant"] = homeassistant
sys.modules["homeassistant.config_entries"] = config_entries
sys.modules["homeassistant.core"] = core
sys.modules["iacad_prayer.coordinator"] = coordinator_module
sys.modules.pop("iacad_prayer", None)

integration = importlib.import_module("iacad_prayer")


class FakeConfigEntries:
    """Record Home Assistant's platform lifecycle calls."""

    def __init__(self) -> None:
        self.forwarded: list[tuple[Any, tuple[str, ...]]] = []
        self.unloaded: list[tuple[Any, tuple[str, ...]]] = []
        self.unload_result = True

    async def async_forward_entry_setups(
        self, entry: Any, platforms: tuple[str, ...]
    ) -> None:
        self.forwarded.append((entry, platforms))

    async def async_unload_platforms(
        self, entry: Any, platforms: tuple[str, ...]
    ) -> bool:
        self.unloaded.append((entry, platforms))
        return self.unload_result


class FakeHass:
    """Minimal Home Assistant object for lifecycle tests."""

    def __init__(self) -> None:
        self.config_entries = FakeConfigEntries()


class FakeEntry:
    """Minimal mutable config entry."""

    runtime_data: FakeCoordinator


class SetupTest(unittest.TestCase):
    """Verify a Home Assistant restart creates a fresh coordinator safely."""

    def setUp(self) -> None:
        FakeCoordinator.fail_refresh = False

    def test_setup_after_restart_refreshes_and_forwards_platforms(self) -> None:
        hass = FakeHass()
        entry = FakeEntry()

        result = asyncio.run(integration.async_setup_entry(hass, entry))

        self.assertTrue(result)
        self.assertIsInstance(entry.runtime_data, FakeCoordinator)
        self.assertEqual(
            hass.config_entries.forwarded, [(entry, ("sensor", "binary_sensor"))]
        )

    def test_failed_initial_refresh_is_propagated_for_home_assistant_retry(
        self,
    ) -> None:
        FakeCoordinator.fail_refresh = True

        with self.assertRaisesRegex(RuntimeError, "service unavailable"):
            asyncio.run(integration.async_setup_entry(FakeHass(), FakeEntry()))

    def test_unload_cancels_the_restart_created_midnight_schedule(self) -> None:
        hass = FakeHass()
        entry = FakeEntry()
        asyncio.run(integration.async_setup_entry(hass, entry))

        result = asyncio.run(integration.async_unload_entry(hass, entry))

        self.assertTrue(result)
        self.assertTrue(entry.runtime_data.cancelled)
