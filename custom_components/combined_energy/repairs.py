"""Repairs flow for Combined Energy issues."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .reconfigure import (
    async_start_reconfigure_if_needed,
    parse_needs_reconfigure_issue_entry_id,
)


class NeedsReconfigureRepairFlow(RepairsFlow):
    """Handle fix flow for reconfigure issues."""

    def __init__(self, entry_id: str) -> None:
        """Initialize the fix flow."""
        self._entry_id = entry_id

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
            await async_start_reconfigure_if_needed(self.hass, self._entry_id)
            return self.async_abort(reason="reconfigure_started")

        return self.async_show_form(step_id="confirm", data_schema=vol.Schema({}))


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
