"""Adhan Prayer Time integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import INTEGRATION_NAME, LEGACY_INTEGRATION_NAMES, PLATFORMS
from .coordinator import PrayerTimesCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Adhan Prayer Time from a config entry."""
    if entry.title in LEGACY_INTEGRATION_NAMES:
        hass.config_entries.async_update_entry(entry, title=INTEGRATION_NAME)
    coordinator = PrayerTimesCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Adhan Prayer Time config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry.runtime_data.async_cancel_midnight_refresh()
    return unload_ok
