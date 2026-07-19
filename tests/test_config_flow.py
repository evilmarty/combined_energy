"""Tests for Combined Energy config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.combined_energy.bridge import BridgeBootstrap
from custom_components.combined_energy.config_flow import CombinedEnergyConfigFlow
from custom_components.combined_energy.models import Installation
from homeassistant.const import CONF_HOST, CONF_NAME


@pytest.mark.asyncio
async def test_async_step_user_sets_unique_id_from_installation_id(fixture_path):
    """Use installation id as config-entry unique id."""
    installation = Installation.model_validate_json(
        (fixture_path / "installation.json").read_text()
    )
    bootstrap = BridgeBootstrap(
        bridge_host="bridge.local",
        mqtt_password="bridge-secret",
        installation=installation,
    )
    flow = CombinedEnergyConfigFlow()
    flow.hass = MagicMock()
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()

    with patch(
        "custom_components.combined_energy.config_flow.validate_bridge_host",
        new=AsyncMock(return_value=bootstrap),
    ):
        result = await flow.async_step_user(
            {
                CONF_NAME: "Custom Name",
                CONF_HOST: "bridge.local",
            }
        )

    flow.async_set_unique_id.assert_awaited_once_with(str(installation.id))
    assert result["type"] == "create_entry"
    assert result["title"] == "Custom Name"
    assert result["data"] == bootstrap.as_config_data()


@pytest.mark.asyncio
async def test_async_step_user_keeps_explicit_default_name(fixture_path):
    """Keep user-provided name even when it equals integration default."""
    installation = Installation.model_validate_json(
        (fixture_path / "installation.json").read_text()
    )
    bootstrap = BridgeBootstrap(
        bridge_host="bridge.local",
        mqtt_password="bridge-secret",
        installation=installation,
    )
    flow = CombinedEnergyConfigFlow()
    flow.hass = MagicMock()
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()

    with patch(
        "custom_components.combined_energy.config_flow.validate_bridge_host",
        new=AsyncMock(return_value=bootstrap),
    ):
        result = await flow.async_step_user(
            {
                CONF_NAME: "Combined Energy",
                CONF_HOST: "bridge.local",
            }
        )

    assert result["type"] == "create_entry"
    assert result["title"] == "Combined Energy"


@pytest.mark.asyncio
async def test_async_step_reconfigure_updates_entry_with_validated_host(fixture_path):
    """Reconfigure updates data after validating the new host."""
    installation = Installation.model_validate_json(
        (fixture_path / "installation.json").read_text()
    )
    bootstrap = BridgeBootstrap(
        bridge_host="bridge.local",
        mqtt_password="bridge-secret",
        installation=installation,
    )
    flow = CombinedEnergyConfigFlow()
    flow.hass = MagicMock()
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_mismatch = MagicMock()
    entry = MagicMock()
    entry.title = "Combined Energy"
    entry.data = {CONF_HOST: "old-bridge.local"}
    flow._get_reconfigure_entry = MagicMock(return_value=entry)
    flow.async_update_reload_and_abort = MagicMock(
        return_value={"type": "abort", "reason": "reconfigure_successful"}
    )

    with patch(
        "custom_components.combined_energy.config_flow.validate_bridge_host",
        new=AsyncMock(return_value=bootstrap),
    ):
        result = await flow.async_step_reconfigure(
            {
                CONF_NAME: "Combined Energy Updated",
                CONF_HOST: "bridge.local",
            }
        )

    flow.async_set_unique_id.assert_awaited_once_with(str(installation.id))
    flow._abort_if_unique_id_mismatch.assert_called_once_with()
    flow.async_update_reload_and_abort.assert_called_once_with(
        entry,
        title="Combined Energy Updated",
        data_updates=bootstrap.as_config_data(),
    )
    assert result["type"] == "abort"
    assert result["reason"] == "reconfigure_successful"
