"""Config flow for IACAD Prayer Times."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, OptionsFlowWithReload
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .configuration import effective_entry_data

from .const import (
    CALCULATION_METHODS,
    CONF_CALCULATION_METHOD,
    CONF_HIGH_LATITUDE_RULE,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MADHAB,
    CONF_TIMEZONE,
    DEFAULT_CALCULATION_METHOD,
    DEFAULT_HIGH_LATITUDE_RULE,
    DEFAULT_MADHAB,
    DOMAIN,
    HIGH_LATITUDE_RULES,
    MADHABS,
)
from .validation import is_valid_timezone


def _validate_timezone(value: str) -> str:
    """Validate that a value is an IANA timezone name."""
    if not is_valid_timezone(value):
        raise vol.Invalid("invalid_timezone")
    return value


DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_LATITUDE): vol.All(
            vol.Coerce(float), vol.Range(min=-90, max=90)
        ),
        vol.Required(CONF_LONGITUDE): vol.All(
            vol.Coerce(float), vol.Range(min=-180, max=180)
        ),
        vol.Required(CONF_TIMEZONE): vol.All(str, _validate_timezone),
        vol.Required(
            CONF_CALCULATION_METHOD, default=DEFAULT_CALCULATION_METHOD
        ): vol.In(CALCULATION_METHODS),
        vol.Required(CONF_MADHAB, default=DEFAULT_MADHAB): vol.In(MADHABS),
        vol.Required(
            CONF_HIGH_LATITUDE_RULE, default=DEFAULT_HIGH_LATITUDE_RULE
        ): vol.In(HIGH_LATITUDE_RULES),
    }
)


class IacadPrayerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IACAD Prayer Times."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> IacadPrayerOptionsFlow:
        """Create the options flow for an existing config entry."""
        return IacadPrayerOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial user setup step."""
        if user_input is not None:
            await self.async_set_unique_id(self._unique_id(user_input))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="IACAD Prayer Times", data=user_input)

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

    @staticmethod
    def _unique_id(data: dict[str, Any]) -> str:
        """Build a stable ID for one prayer-time configuration."""
        return "|".join(
            (
                f"{data[CONF_LATITUDE]:.6f}",
                f"{data[CONF_LONGITUDE]:.6f}",
                data[CONF_TIMEZONE],
                data[CONF_CALCULATION_METHOD],
                data[CONF_MADHAB],
                data[CONF_HIGH_LATITUDE_RULE],
            )
        )


class IacadPrayerOptionsFlow(OptionsFlowWithReload):
    """Handle user-editable prayer-time configuration options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show and save the editable location and calculation settings."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                DATA_SCHEMA, effective_entry_data(self.config_entry)
            ),
        )
