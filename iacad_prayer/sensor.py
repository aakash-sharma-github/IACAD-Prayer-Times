"""Prayer-time sensor entities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Final
from zoneinfo import ZoneInfo

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PrayerTimesCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


@dataclass(frozen=True, kw_only=True)
class PrayerTimeSensorEntityDescription(SensorEntityDescription):
    """Describe a calculated prayer or solar-event timestamp sensor."""

    prayer_key: str


SENSOR_DESCRIPTIONS: Final = (
    PrayerTimeSensorEntityDescription(
        key="fajr",
        translation_key="fajr",
        prayer_key="fajr",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    PrayerTimeSensorEntityDescription(
        key="sunrise",
        translation_key="sunrise",
        prayer_key="sunrise",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    PrayerTimeSensorEntityDescription(
        key="dhuhr",
        translation_key="dhuhr",
        prayer_key="dhuhr",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    PrayerTimeSensorEntityDescription(
        key="asr",
        translation_key="asr",
        prayer_key="asr",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    PrayerTimeSensorEntityDescription(
        key="sunset",
        translation_key="sunset",
        prayer_key="sunset",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    PrayerTimeSensorEntityDescription(
        key="maghrib",
        translation_key="maghrib",
        prayer_key="maghrib",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    PrayerTimeSensorEntityDescription(
        key="isha",
        translation_key="isha",
        prayer_key="isha",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up prayer-time timestamp sensors for a config entry."""
    coordinator: PrayerTimesCoordinator = entry.runtime_data
    async_add_entities(
        PrayerTimeSensor(coordinator, entry.entry_id, description)
        for description in SENSOR_DESCRIPTIONS
    )


class PrayerTimeSensor(CoordinatorEntity[PrayerTimesCoordinator], SensorEntity):
    """Expose one calculated prayer or solar event as an aware timestamp."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    entity_description: PrayerTimeSensorEntityDescription

    def __init__(
        self,
        coordinator: PrayerTimesCoordinator,
        entry_id: str,
        description: PrayerTimeSensorEntityDescription,
    ) -> None:
        """Initialize a coordinator-backed prayer-time sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            manufacturer="azanAPI",
            model="IACAD Prayer Times",
            name="IACAD Prayer Times",
        )

    @property
    def native_value(self) -> datetime | None:
        """Return the event time as a timezone-aware datetime."""
        if self.coordinator.data is None:
            return None
        event_time = self.coordinator.data.calculated_times[
            self.entity_description.prayer_key
        ]
        return datetime.fromisoformat(
            f"{self.coordinator.data.date.isoformat()}T{event_time}"
        ).replace(tzinfo=ZoneInfo(self.coordinator.data.timezone))
