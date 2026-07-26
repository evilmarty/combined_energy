"""Tests for Combined Energy repairs flow."""

from unittest.mock import AsyncMock, MagicMock

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
async def test_needs_reconfigure_flow_confirm_starts_reconfigure_flow():
    """Confirm starts reconfigure flow and exits repair flow."""
    flow = NeedsReconfigureRepairFlow("entry-1")
    flow.hass = MagicMock()
    flow.hass.config_entries = MagicMock()
    flow.hass.config_entries.flow = MagicMock()
    flow.hass.config_entries.flow.async_progress_by_handler = MagicMock(return_value=[])
    flow.hass.config_entries.flow.async_init = AsyncMock()

    result = await flow.async_step_confirm(user_input={})

    flow.hass.config_entries.flow.async_init.assert_awaited_once_with(
        DOMAIN,
        context={
            "source": "reconfigure",
            "entry_id": "entry-1",
        },
    )
    assert result["type"] == "abort"
    assert result["reason"] == "reconfigure_started"
