"""Config flow for Kokonna integration."""

import logging
import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, API_DEVICE

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("token", description="API Key"): str,
        vol.Optional("name", default=""): str,
    }
)


async def validate_token(hass: HomeAssistant, token: str) -> dict | None:
    """Validate token by calling device API."""
    session = async_get_clientsession(hass)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    try:
        async with session.post(API_DEVICE, headers=headers, json={}) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                _LOGGER.error("Invalid token, status: %s", resp.status)
                return None
    except Exception as e:
        _LOGGER.error("Error validating token: %s", e)
        return None


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kokonna."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            token = user_input["token"].strip()
            name = user_input.get("name", "").strip()

            device_info = await validate_token(self.hass, token)
            if device_info is None:
                errors["base"] = "invalid_auth"
            else:
                if not name:
                    name = device_info.get("nickname", "Kokonna Frame")
                await self.async_set_unique_id(token)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=name,
                    data={
                        "token": token,
                        "name": name,
                        "device_info": device_info,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )