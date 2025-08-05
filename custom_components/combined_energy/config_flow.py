"""Config flow for Combined Energy integration."""

from __future__ import annotations

from typing import Any

from aiohttp import ClientResponseError
import voluptuous as vol

from custom_components.combined_energy.client import ClientAuthError, get_client
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .const import DEFAULT_NAME, DOMAIN, LOGGER


class CombinedEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Combined Energy."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._errors: dict[str, str] = {}

    async def _get_installation(self, username: str, password: str) -> int | None:
        """Check if we can connect to the combined energy service."""
        client = await get_client(
            hass=self.hass,
            mobile_or_email=username,
            password=password,
        )
        try:
            installation = await client.installation()
        except ClientAuthError:
            self._errors["base"] = "invalid_auth"
        except ClientResponseError as err:
            LOGGER.exception("Unexpected error verifying connection to API", err)
            self._errors["base"] = "cannot_connect"
        else:
            return installation.id
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        self._errors = {}

        if user_input:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            if (
                installation_id := await self._get_installation(username, password)
            ) is not None:
                await self.async_set_unique_id(str(installation_id))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, DEFAULT_NAME),
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )

        else:
            user_input = {
                CONF_NAME: DEFAULT_NAME,
                CONF_USERNAME: "",
                CONF_PASSWORD: "",
            }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=user_input[CONF_NAME]): str,
                    vol.Required(CONF_USERNAME, default=user_input[CONF_USERNAME]): str,
                    vol.Required(CONF_PASSWORD, default=user_input[CONF_PASSWORD]): str,
                }
            ),
            errors=self._errors,
        )
