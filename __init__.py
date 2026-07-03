"""The Kokonna integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    API_DEVICE,
    API_LIST_IMAGES,
    API_DISPLAY_IMAGE,
    DEFAULT_SCAN_INTERVAL,
    SERVICE_SET_IMAGE,
    ATTR_DEVICE_ID,
    ATTR_IMAGE_ID,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.SELECT, Platform.IMAGE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Kokonna from a config entry."""
    _LOGGER.error("=== async_setup_entry called for entry %s ===", entry.entry_id)
    coordinator = KokonnaDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # 兼容新旧版本 HA
    if hasattr(hass.config_entries, "async_forward_entry_setups"):
        _LOGGER.error("Using async_forward_entry_setups for platforms: %s", PLATFORMS)
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    else:
        _LOGGER.error("Using legacy async_forward_entry_setup")
        for platform in PLATFORMS:
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(entry, platform)
            )

    # 注册服务
    async def handle_set_image(call):
        device_id = call.data.get(ATTR_DEVICE_ID)
        image_id = call.data.get(ATTR_IMAGE_ID)
        if device_id is None or image_id is None:
            _LOGGER.error("Missing device_id or image_id")
            return
        for entry_id, coord in hass.data[DOMAIN].items():
            if coord.device_id == device_id:
                await coord.async_set_image(image_id)
                return
        _LOGGER.error("Device %s not found", device_id)

    hass.services.async_register(DOMAIN, SERVICE_SET_IMAGE, handle_set_image)
    _LOGGER.error("=== async_setup_entry completed successfully ===")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if hasattr(hass.config_entries, "async_unload_platforms"):
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    else:
        unload_ok = all(
            await asyncio.gather(
                *[
                    hass.config_entries.async_forward_entry_unload(entry, platform)
                    for platform in PLATFORMS
                ]
            )
        )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_SET_IMAGE)
    return unload_ok


class KokonnaDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Kokonna data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        self.hass = hass
        self.entry = entry
        self.token = entry.data["token"]
        self.device_name = entry.data["name"]
        self.device_info = entry.data.get("device_info", {})
        self.device_id = self.device_info.get("id", entry.entry_id)

        self.session = async_get_clientsession(hass)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        _LOGGER.error("Coordinator initialized for device %s", self.device_name)

    async def _async_update_data(self) -> dict:
        """Fetch data from API."""
        try:
            device_data = await self._fetch_device()
            images_data = await self._fetch_images()
            _LOGGER.error("Fetched data: device keys: %s, images count: %d", list(device_data.keys()), len(images_data.get("list", [])))
            return {
                "device": device_data,
                "images": images_data.get("list", []),
            }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _fetch_device(self) -> dict:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        async with self.session.post(API_DEVICE, headers=headers, json={}) as resp:
            if resp.status != 200:
                raise UpdateFailed(f"Device API error: {resp.status}")
            return await resp.json()

    async def _fetch_images(self) -> dict:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        async with self.session.post(API_LIST_IMAGES, headers=headers, json={}) as resp:
            if resp.status != 200:
                raise UpdateFailed(f"ListImages API error: {resp.status}")
            return await resp.json()

    async def async_set_image(self, image_id: int) -> bool:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload = {"imageId": image_id}
        try:
            async with self.session.post(API_DISPLAY_IMAGE, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    await self.async_refresh()
                    return True
                return False
        except Exception:
            return False

    def get_image_url(self, image_id: int | None = None) -> str | None:
        if image_id is None:
            if self.data and "device" in self.data:
                image_id = self.data["device"].get("imageId")
            else:
                image_id = self.device_info.get("imageId")
        if image_id is None:
            return None
        return f"https://api.galaxyguide.cn/openapi/image/{self.token}/{image_id}"