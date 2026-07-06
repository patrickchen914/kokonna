"""Select platform for Kokonna."""

import logging
import re
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from . import KokonnaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: KokonnaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([KokonnaSelect(coordinator, entry)])


class KokonnaSelect(CoordinatorEntity, SelectEntity):
    """Image selector - displayed in Controls region."""

    def __init__(self, coordinator: KokonnaDataUpdateCoordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = f"{entry.data['name']} Select Image"
        self._attr_unique_id = f"{entry.entry_id}_image_picker"
        self._attr_icon = "mdi:image-multiple"
        # ✅ 无需设置 entity_category，Select 默认在 Controls 区域
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data["name"],
            "manufacturer": "Kokonna",
            "model": "Digital Frame",
        }

    @property
    def current_option(self) -> str | None:
        images = self.coordinator.data.get("images", []) if self.coordinator.data else []
        if not images:
            return None
        for img in images:
            if img.get("current") is True:
                return self._format_option(img)
        return None

    @property
    def options(self) -> list[str]:
        images = self.coordinator.data.get("images", []) if self.coordinator.data else []
        if not images:
            return ["请选择"]
        options = ["请选择"]
        for img in images:
            options.append(self._format_option(img))
        return options

    def _format_option(self, img: dict) -> str:
        base = f"[{img['id']}] {img.get('name', 'Unnamed')}"
        tags = img.get("tags", [])
        if tags:
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            if tags:
                tag_str = " (#" + " #".join(tags) + ")"
                return base + tag_str
        return base

    async def async_select_option(self, option: str) -> None:
        if option == "请选择":
            return
        match = re.search(r"\[(\d+)\]", option)
        if not match:
            return
        image_id = int(match.group(1))
        await self.coordinator.async_set_image(image_id)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None
