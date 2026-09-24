"""Prayer-active binary sensor entities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Final
from zoneinfo import ZoneInfo

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PrayerTimesCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class PrayerActiveBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe an Azan prayer active-window binary sensor."""

    prayer_key: str


BINARY_SENSOR_DESCRIPTIONS: Final = (
    PrayerActiveBinarySensorEntityDescription(
        key="fajr_active", translation_key="fajr_active", prayer_key="fajr"
    ),
    PrayerActiveBinarySensorEntityDescription(
        key="dhuhr_active", translation_key="dhuhr_active", prayer_key="dhuhr"
    ),
    PrayerActiveBinarySensorEntityDescription(
        key="asr_active", translation_key="asr_active", prayer_key="asr"
    ),
    PrayerActiveBinarySensorEntityDescription(
        key="maghrib_active", translation_key="maghrib_active", prayer_key="maghrib"
    ),
    PrayerActiveBinarySensorEntityDescription(
        key="isha_active", translation_key="isha_active", prayer_key="isha"
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up adjusted-Azan active-window binary sensors."""
    coordinator: PrayerTimesCoordinator = entry.runtime_data
    async_add_entities(
        PrayerActiveBinarySensor(coordinator, entry.entry_id, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class PrayerActiveBinarySensor(
    CoordinatorEntity[PrayerTimesCoordinator], BinarySensorEntity
):
    """Report whether the current local time is within an Azan's one-minute window."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    entity_description: PrayerActiveBinarySensorEntityDescription
    _unsub_timer: Callable[[], None] | None = None

    def __init__(
        self,
        coordinator: PrayerTimesCoordinator,
        entry_id: str,
        description: PrayerActiveBinarySensorEntityDescription,
    ) -> None:
        """Initialize a coordinator-backed active-window binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            manufacturer="Aakash Sharma",
            model="IACAD Prayer Times",
            name="IACAD Prayer Times",
        )

    async def async_added_to_hass(self) -> None:
        """Refresh the active state each minute without an API request."""
        await super().async_added_to_hass()
        self._unsub_timer = async_track_time_interval(
            self.hass, self._async_handle_time_change, timedelta(minutes=1)
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe the local timer when the entity is removed."""
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None
        await super().async_will_remove_from_hass()

    async def _async_handle_time_change(self, now: datetime) -> None:
        """Write the locally recalculated active state."""
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool | None:
        """Return whether the current local time is inside the one-minute Azan window."""
        if self.coordinator.data is None:
            return None
        timezone = ZoneInfo(self.coordinator.data.timezone)
        return self._is_active_at(datetime.now(timezone))

    def _is_active_at(self, now: datetime) -> bool:
        """Evaluate the exact inclusive-start, exclusive-end active window."""
        if self.coordinator.data is None:
            return False
        azan_time = self._azan_datetime()
        return azan_time <= now < azan_time + timedelta(minutes=1)

    def _azan_datetime(self) -> datetime:
        """Return the dated final Azan time, including any midnight rollover."""
        assert self.coordinator.data is not None
        data = self.coordinator.data
        timezone = ZoneInfo(data.timezone)
        prayer_key = self.entity_description.prayer_key
        azan = datetime.fromisoformat(
            f"{data.date.isoformat()}T{data.azan_times[prayer_key]}"
        ).replace(tzinfo=timezone)

        calculated = datetime.fromisoformat(
            f"{data.date.isoformat()}T{data.calculated_times[prayer_key]}"
        ).replace(tzinfo=timezone)
        adjusted = calculated + timedelta(minutes=data.adjustments_minutes[prayer_key])
        if adjusted.time() == azan.time():
            return adjusted
        return azan
