"""Prayer-time sensor entities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Final
from zoneinfo import ZoneInfo

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PrayerTimesCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


PARALLEL_UPDATES = 0


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

REMAINING_SENSOR_DESCRIPTIONS: Final = (
    PrayerTimeSensorEntityDescription(
        key="fajr_remaining",
        translation_key="fajr_remaining",
        prayer_key="fajr",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="min",
    ),
    PrayerTimeSensorEntityDescription(
        key="dhuhr_remaining",
        translation_key="dhuhr_remaining",
        prayer_key="dhuhr",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="min",
    ),
    PrayerTimeSensorEntityDescription(
        key="asr_remaining",
        translation_key="asr_remaining",
        prayer_key="asr",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="min",
    ),
    PrayerTimeSensorEntityDescription(
        key="maghrib_remaining",
        translation_key="maghrib_remaining",
        prayer_key="maghrib",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="min",
    ),
    PrayerTimeSensorEntityDescription(
        key="isha_remaining",
        translation_key="isha_remaining",
        prayer_key="isha",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="min",
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
    async_add_entities(
        PrayerTimeRemainingSensor(coordinator, entry.entry_id, description)
        for description in REMAINING_SENSOR_DESCRIPTIONS
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


class PrayerTimeRemainingSensor(PrayerTimeSensor):
    """Expose minutes until the next occurrence of one Azan prayer."""

    _unsub_timer: Callable[[], None] | None = None

    async def async_added_to_hass(self) -> None:
        """Refresh the duration state each minute without an API request."""
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
        """Write the locally recalculated remaining duration."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> int | None:
        """Return whole minutes until the next local occurrence of this prayer."""
        if self.coordinator.data is None:
            return None
        now = datetime.now(ZoneInfo(self.coordinator.data.timezone))
        prayer_time = self._next_prayer_time(now)
        return max(0, int((prayer_time - now).total_seconds() // 60))

    def _next_prayer_time(self, now: datetime) -> datetime:
        """Return today's or tomorrow's occurrence from coordinator prayer data."""
        assert self.coordinator.data is not None
        event_time = self.coordinator.data.calculated_times[
            self.entity_description.prayer_key
        ]
        event = datetime.fromisoformat(
            f"{self.coordinator.data.date.isoformat()}T{event_time}"
        ).replace(tzinfo=ZoneInfo(self.coordinator.data.timezone))
        while event < now:
            event += timedelta(days=1)
        return event
