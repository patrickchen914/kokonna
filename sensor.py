"""Sensor platform for Kokonna."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity_registry import EntityCategory

from .const import DOMAIN
from . import KokonnaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class SensorDetails:
    description: SensorEntityDescription
    state_value_func: Callable[[dict], Any] | None = None


ENTITY_DETAILS: list[SensorDetails] = [
    SensorDetails(
        description=SensorEntityDescription(
            key="firmware",
            name="Firmware",
            icon="mdi:chip",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        state_value_func=lambda d: d.get("firmware"),
    ),
    SensorDetails(
        description=SensorEntityDescription(
            key="nickname",
            name="Frame Name",
            icon="mdi:rename-box",
        ),
        state_value_func=lambda d: d.get("nickname"),
    ),
    SensorDetails(
        description=SensorEntityDescription(
            key="isCharging",
            name="Is Charging",
            icon="mdi:battery-charging",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        state_value_func=lambda d: "Charging" if d.get("isCharging") is True else "Not charging",
    ),
    SensorDetails(
        description=SensorEntityDescription(
            key="batteryLevel",
            name="Battery Level",
            device_class=SensorDeviceClass.BATTERY,
            native_unit_of_measurement=PERCENTAGE,
            icon="mdi:battery",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        state_value_func=lambda d: d.get("batteryLevel"),
    ),
    SensorDetails(
        description=SensorEntityDescription(
            key="switchType",
            name="Switch Type",
            icon="mdi:dip-switch",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        state_value_func=lambda d: d.get("switchType"),
    ),
    SensorDetails(
        description=SensorEntityDescription(
            key="switchMinute",
            name="Switch Minute",
            icon="mdi:timer-outline",
            native_unit_of_measurement=UnitOfTime.MINUTES,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        state_value_func=lambda d: d.get("switchMinute"),
    ),
    SensorDetails(
        description=SensorEntityDescription(
            key="imageId",
            name="Image ID",
            icon="mdi:image",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        state_value_func=lambda d: d.get("imageId"),
    ),
    SensorDetails(
        description=SensorEntityDescription(
            key="screenWidth",
            name="Screen Width",
            icon="mdi:arrow-expand-horizontal",
            native_unit_of_measurement="px",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        state_value_func=lambda d: d.get("screenWidth"),
    ),
    SensorDetails(
        description=SensorEntityDescription(
            key="screenHeight",
            name="Screen Height",
            icon="mdi:arrow-expand-vertical",
            native_unit_of_measurement="px",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        state_value_func=lambda d: d.get("screenHeight"),
    ),
    SensorDetails(
        description=SensorEntityDescription(
            key="screenRotate",
            name="Screen Rotate",
            icon="mdi:screen-rotation",
            native_unit_of_measurement="°",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        state_value_func=lambda d: d.get("screenRotate"),
    ),
    SensorDetails(
        description=SensorEntityDescription(
            key="online",
            name="Online",
            icon="mdi:cloud-check",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        state_value_func=lambda d: d.get("online", False),
    ),
    SensorDetails(
        description=SensorEntityDescription(
            key="status",
            name="Status",
            icon="mdi:information",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        state_value_func=lambda d: "Online" if d.get("online") is True else "Offline",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: KokonnaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for details in ENTITY_DETAILS:
        sensor = KokonnaSensor(
            coordinator,
            entry,
            details.description,
            details.state_value_func,
        )
        entities.append(sensor)
    async_add_entities(entities)
    _LOGGER.debug("Added %d sensors", len(entities))


class KokonnaSensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        coordinator: KokonnaDataUpdateCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
        state_value_func: Callable[[dict], Any] | None = None,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._state_value_func = state_value_func
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data["name"],
            "manufacturer": "Kokonna",
            "model": "Digital Frame",
        }

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        device_data = self.coordinator.data.get("device", {})
        if self._state_value_func:
            return self._state_value_func(device_data)
        return device_data.get(self.entity_description.key)

    @property
    def available(self):
        return self.coordinator.last_update_success and self.coordinator.data is not None