"""Image platform for Kokonna."""

import datetime
import logging
from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from . import KokonnaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kokonna image based on a config entry."""
    coordinator: KokonnaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([KokonnaImage(coordinator, entry)])


class KokonnaImage(CoordinatorEntity, ImageEntity):
    """Representation of a Kokonna Image."""

    def __init__(self, coordinator: KokonnaDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the image entity."""
        ImageEntity.__init__(self, coordinator.hass)
        CoordinatorEntity.__init__(self, coordinator)
        self._entry = entry
        self._attr_name = f"{entry.data['name']} Current Image"
        self._attr_unique_id = f"{entry.entry_id}_image"
        self._attr_entity_category = er.EntityCategory.DIAGNOSTIC
        self._attr_device_class = None  # 防止时间戳解析
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data["name"],
            "manufacturer": "Kokonna",
            "model": "Digital Frame",
        }
        
        # 初始化时，记录当前 ID，并给一个初始时间戳
        self._last_image_id = None
        self._attr_image_last_updated = dt_util.utcnow()

    @callback
    def _handle_coordinator_update(self) -> None:
        """精准拦截：只有 imageId 真的变了，才更新时间戳，强制前端刷新缓存。"""
        if self.coordinator.data:
            device_data = self.coordinator.data.get("device", {})
            current_image_id = device_data.get("imageId")
            
            # 如果这是第一次加载，或者图片ID真的发生了变化
            if current_image_id is not None and current_image_id != self._last_image_id:
                self._last_image_id = current_image_id
                
                # 重新生成当前最新的时间戳！这是打破前端缓存的终极武器
                self._attr_image_last_updated = dt_util.utcnow()
                _LOGGER.debug("Kokonna image changed to ID: %s, updated timestamp", current_image_id)
                
        # 必须调用父类，通知 HA 核心状态和属性已改变
        super()._handle_coordinator_update()

    @property
    def image_last_updated(self) -> datetime.datetime | None:
        """The time when the image was last updated."""
        return self._attr_image_last_updated

    @property
    def state(self):
        """Return formatted state: [ID] Name (#tag1 #tag2)"""
        if not self.coordinator.data:
            return None
        
        device_data = self.coordinator.data.get("device", {})
        image_id = device_data.get("imageId")
        if image_id is None:
            return None
        
        # 从图片列表中查找当前图片信息
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
            return f"[{image_id}] {name}{tag_str}"
        else:
            return f"[{image_id}]"

    @property
    def image_url(self) -> str | None:
        """Return the URL of the current image."""
        if not self.coordinator.data:
            return None
        device_data = self.coordinator.data.get("device", {})
        image_id = device_data.get("imageId")
        if image_id is None:
            return None
        
        # 获取基础 URL
        base_url = self.coordinator.get_image_url(image_id)
        if base_url is None:
            return None
        
        # 增加参数以确保后端不会给出旧的缓存图片
        return f"{base_url}?v={image_id}"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not self.coordinator.last_update_success or not self.coordinator.data:
            return False
        return self.image_url is not None
