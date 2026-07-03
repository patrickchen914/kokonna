"""Image platform for Kokonna."""

import logging
from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from . import KokonnaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: KokonnaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([KokonnaImage(coordinator, entry)])


class KokonnaImage(CoordinatorEntity, ImageEntity):
    def __init__(self, coordinator: KokonnaDataUpdateCoordinator, entry: ConfigEntry):
        ImageEntity.__init__(self, coordinator.hass)
        CoordinatorEntity.__init__(self, coordinator)
        self._entry = entry
        self._attr_name = f"{entry.data['name']} Current Image"
        self._attr_unique_id = f"{entry.entry_id}_image"
        self._attr_entity_category = er.EntityCategory.DIAGNOSTIC
        # 关键：不设置设备类，防止时间戳解析
        self._attr_device_class = None
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data["name"],
            "manufacturer": "Kokonna",
            "model": "Digital Frame",
        }

    @property
    def state(self):
        """Return formatted state: [ID] Name (#tag1 #tag2)"""
        if not self.coordinator.data:
            return None
        
        device_data = self.coordinator.data.get("device", {})
        image_id = device_data.get("imageId")
        if image_id is None:
            return None
        
        # 从图片列表中查找当前图片的详细信息
        images = self.coordinator.data.get("images", [])
        current_image = None
        for img in images:
            if img.get("id") == image_id:
                current_image = img
                break
        
        if current_image:
            name = current_image.get("name", "Unnamed")
            tags = current_image.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            tag_str = " (#" + " #".join(tags) + ")" if tags else ""
            # 返回格式如 "[103378] 侯咪_1 (#侯咪 #顺理陈张)"
            return f"[{image_id}] {name}{tag_str}"
        else:
            # 如果未找到详细信息，只显示 ID
            return f"[{image_id}]"

    @property
    def image_url(self) -> str | None:
        if not self.coordinator.data:
            return None
        device_data = self.coordinator.data.get("device", {})
        image_id = device_data.get("imageId")
        if image_id is None:
            return None
        return self.coordinator.get_image_url(image_id)

    @property
    def available(self) -> bool:
        if not self.coordinator.last_update_success or not self.coordinator.data:
            return False
        return self.image_url is not None