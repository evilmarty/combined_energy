"""Tests for Combined Energy repairs flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.combined_energy.const import DOMAIN
from custom_components.combined_energy.repairs import (
    NeedsReconfigureRepairFlow,
    async_create_fix_flow,
)


@pytest.mark.asyncio
async def test_async_create_fix_flow_returns_reconfigure_flow_for_issue_data():
    """Return custom repair flow when issue data contains a valid entry id."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry = MagicMock(return_value=MagicMock())

    flow = await async_create_fix_flow(
        hass,
        issue_id="ignored",
        data={"entry_id": "entry-1"},
    )

    assert isinstance(flow, NeedsReconfigureRepairFlow)


@pytest.mark.asyncio
async def test_async_create_fix_flow_parses_entry_id_from_issue_id():
    """Return custom repair flow when issue id matches needs-reconfigure format."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry = MagicMock(return_value=MagicMock())

    flow = await async_create_fix_flow(
        hass,
        issue_id="entry-1_needs_reconfigure",
        data=None,
    )

    assert isinstance(flow, NeedsReconfigureRepairFlow)


@pytest.mark.asyncio
async def test_needs_reconfigure_flow_confirm_advances_to_reconfigure_form():
    """Confirm should advance to the reconfigure form."""
    flow = NeedsReconfigureRepairFlow("entry-1")
    flow.hass = MagicMock()
    flow.hass.config_entries = MagicMock()
    entry = MagicMock()
    entry.title = "Combined Energy"
    entry.data = {"host": "old-bridge.local"}
    flow.hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    result = await flow.async_step_confirm(user_input={})

    assert result["type"] == "form"
    assert result["step_id"] == "reconfigure"


@pytest.mark.asyncio
async def test_needs_reconfigure_flow_reconfigure_updates_entry_and_reloads():
    """Reconfigure step should update the entry and reload the integration."""
    flow = NeedsReconfigureRepairFlow("entry-1")
    flow.hass = MagicMock()
    flow.hass.config_entries = MagicMock()
    flow.hass.config_entries.async_get_entry = MagicMock()
    flow.hass.config_entries.async_update_entry = MagicMock()
    flow.hass.config_entries.async_reload = AsyncMock()
    flow.issue_id = "entry-1_needs_reconfigure"

    entry = MagicMock()
    entry.title = "Combined Energy"
    entry.entry_id = "entry-1"
    entry.data = {
        "host": "old-bridge.local",
        "stale_entity_cleanup_pending": True,
    }
    flow.hass.config_entries.async_get_entry.return_value = entry

    bootstrap = MagicMock()
    bootstrap.installation = MagicMock()
    bootstrap.as_config_data.return_value = {
        "host": "bridge.local",
        "mqtt_password": "bridge-secret",
    }

    with (
        patch(
            "custom_components.combined_energy.repairs.validate_bridge_host",
            new=AsyncMock(return_value=bootstrap),
        ),
        patch(
            "custom_components.combined_energy.repairs.cleanup_stale_sensor_entities"
        ) as cleanup_stale_sensor_entities,
        patch(
            "custom_components.combined_energy.repairs.ir.async_delete_issue"
        ) as delete_issue,
    ):
        result = await flow.async_step_reconfigure(
            {
                "name": "Combined Energy Updated",
                "host": "bridge.local",
            }
        )

    cleanup_stale_sensor_entities.assert_called_once_with(
        flow.hass, entry, bootstrap.installation
    )
    delete_issue.assert_called_once_with(flow.hass, DOMAIN, "entry-1_needs_reconfigure")
    flow.hass.config_entries.async_update_entry.assert_called_once_with(
        entry,
        title="Combined Energy Updated",
        data={
            "host": "bridge.local",
            "mqtt_password": "bridge-secret",
        },
    )
    flow.hass.config_entries.async_reload.assert_awaited_once_with("entry-1")
    assert result["type"] == "create_entry"
