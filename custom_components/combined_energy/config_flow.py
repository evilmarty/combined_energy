"""Config flow for Combined Energy integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .bridge import BridgeBootstrap, BridgeBootstrapError, validate_bridge_host
from .const import DEFAULT_NAME, DOMAIN, LOGGER


class CombinedEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Combined Energy."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._errors: dict[str, str] = {}

    async def _validate_host(self, host: str) -> BridgeBootstrap | None:
        """Validate bridge host and retrieve setup data."""
        try:
            bootstrap = await validate_bridge_host(self.hass, host)
        except BridgeBootstrapError as err:
            LOGGER.debug("Bridge bootstrap failed for host %s: %s", host, err)
            self._errors["base"] = "cannot_connect"
            return None
        return bootstrap

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        self._errors = {}

        if user_input:
            host = user_input[CONF_HOST].strip()
            if host and (bootstrap := await self._validate_host(host)) is not None:
                await self.async_set_unique_id(str(bootstrap.installation.id))
                self._abort_if_unique_id_configured()
                configured_name = (
                    user_input.get(CONF_NAME, "").strip()
                    or bootstrap.installation.name
                    or DEFAULT_NAME
                )
                return self.async_create_entry(
                    title=configured_name,
                    data=bootstrap.as_config_data(),
                )
        else:
            user_input = {
                CONF_NAME: "",
                CONF_HOST: "",
            }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=user_input[CONF_NAME]): str,
                    vol.Required(CONF_HOST, default=user_input[CONF_HOST]): str,
                }
            ),
            errors=self._errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a reconfigure flow."""
        self._errors = {}
        entry = self._get_reconfigure_entry()

        if user_input:
            host = user_input[CONF_HOST].strip()
            if host and (bootstrap := await self._validate_host(host)) is not None:
                await self.async_set_unique_id(str(bootstrap.installation.id))
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry,
                    title=user_input.get(CONF_NAME, "").strip() or entry.title,
                    data_updates=bootstrap.as_config_data(),
                )
        else:
            user_input = {
                CONF_NAME: entry.title or "",
                CONF_HOST: entry.data.get(CONF_HOST, ""),
            }

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=user_input[CONF_NAME]): str,
                    vol.Required(CONF_HOST, default=user_input[CONF_HOST]): str,
                }
            ),
            errors=self._errors,
        )
