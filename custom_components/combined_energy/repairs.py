"""Repairs flow for Combined Energy issues."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import issue_registry as ir

from .bridge import BridgeBootstrap, BridgeBootstrapError, validate_bridge_host
from .const import CONF_STALE_ENTITY_CLEANUP_PENDING, DEFAULT_NAME, DOMAIN
from .reconfigure import parse_needs_reconfigure_issue_entry_id
from .sensor import cleanup_stale_sensor_entities


class NeedsReconfigureRepairFlow(RepairsFlow):
    """Handle fix flow for reconfigure issues."""

    def __init__(self, entry_id: str) -> None:
        """Initialize the fix flow."""
        self._entry_id = entry_id
        self._errors: dict[str, str] = {}

    async def _validate_host(self, host: str) -> BridgeBootstrap | None:
        """Validate bridge host and retrieve setup data."""
        try:
            bootstrap = await validate_bridge_host(self.hass, host)
        except BridgeBootstrapError:
            self._errors["base"] = "cannot_connect"
            return None
        return bootstrap

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the first step of the fix flow."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the confirm step."""
        if user_input is not None:
            return await self.async_step_reconfigure()

        return self.async_show_form(step_id="confirm", data_schema=vol.Schema({}))

    async def async_step_reconfigure(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the reconfigure step."""
        self._errors = {}
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if entry is None:
            return self.async_abort(reason="entry_not_found")

        if user_input:
            host = user_input[CONF_HOST].strip()
            if host and (bootstrap := await self._validate_host(host)) is not None:
                if entry.data.get(CONF_STALE_ENTITY_CLEANUP_PENDING):
                    cleanup_stale_sensor_entities(
                        self.hass, entry, bootstrap.installation
                    )
                ir.async_delete_issue(self.hass, DOMAIN, self.issue_id)
                updated_data = {**entry.data, **bootstrap.as_config_data()}
                updated_data.pop(CONF_STALE_ENTITY_CLEANUP_PENDING, None)
                self.hass.config_entries.async_update_entry(
                    entry,
                    title=user_input.get(CONF_NAME, "").strip() or entry.title,
                    data=updated_data,
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_create_entry(title="", data={})
        else:
            user_input = {
                CONF_NAME: entry.title or DEFAULT_NAME,
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


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create fix flow for an issue."""
    entry_id = (
        data.get("entry_id")
        if isinstance(data, dict) and isinstance(data.get("entry_id"), str)
        else None
    )
    if not entry_id:
        entry_id = parse_needs_reconfigure_issue_entry_id(issue_id)

    if entry_id and hass.config_entries.async_get_entry(entry_id) is not None:
        return NeedsReconfigureRepairFlow(entry_id)

    return ConfirmRepairFlow()
