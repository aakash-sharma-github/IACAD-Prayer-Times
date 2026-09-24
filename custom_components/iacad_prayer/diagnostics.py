"""Diagnostics support for IACAD Prayer Times."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.helpers.redact_data import async_redact_data

from .configuration import effective_entry_data
from .const import CONF_LATITUDE, CONF_LONGITUDE

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


_TO_REDACT = (CONF_LATITUDE, CONF_LONGITUDE)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return support data without exposing the configured location."""
    del hass
    coordinator = entry.runtime_data
    data = coordinator.data

    return {
        "entry": async_redact_data(effective_entry_data(entry), _TO_REDACT),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "data": None
            if data is None
            else {
                "date": data.date.isoformat(),
                "timezone": data.timezone,
                "calculation_method": data.calculation_method,
                "madhab": data.madhab,
                "high_latitude_rule": data.high_latitude_rule,
                "calculated_times": dict(data.calculated_times),
                "azan_times": dict(data.azan_times),
                "adjustments_minutes": dict(data.adjustments_minutes),
            },
        },
    }
