"""Tests for Combined Energy config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.combined_energy.bridge import BridgeBootstrap
from custom_components.combined_energy.config_flow import CombinedEnergyConfigFlow
from custom_components.combined_energy.const import (
    CONF_MQTT_PASSWORD,
    CONF_STALE_ENTITY_CLEANUP_PENDING,
    DEFAULT_NAME,
)
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
    flow._abort_if_unique_id_configured = MagicMock()  # noqa: SLF001

    with patch(
        "custom_components.combined_energy.config_flow.validate_bridge_host",
        new=AsyncMock(return_value=bootstrap),
    ):
        result = await flow.async_step_user(
            {
                CONF_HOST: "bridge.local",
            }
        )

    flow.async_set_unique_id.assert_awaited_once_with(str(installation.id))
    assert result["type"] == "create_entry"
    assert result["title"] == installation.name
    assert result["data"] == bootstrap.as_config_data()


@pytest.mark.asyncio
async def test_async_step_user_uses_default_name_when_installation_has_no_name(fixture_path):
    """Fallback to integration default when installation has no name."""
    installation = Installation.model_validate_json(
        (fixture_path / "installation.json").read_text()
    ).model_copy(update={"name": ""})
    bootstrap = BridgeBootstrap(
        bridge_host="bridge.local",
        mqtt_password="bridge-secret",
        installation=installation,
    )
    flow = CombinedEnergyConfigFlow()
    flow.hass = MagicMock()
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()  # noqa: SLF001

    with patch(
        "custom_components.combined_energy.config_flow.validate_bridge_host",
        new=AsyncMock(return_value=bootstrap),
    ):
        result = await flow.async_step_user(
            {
                CONF_HOST: "bridge.local",
            }
        )

    assert result["type"] == "create_entry"
    assert result["title"] == DEFAULT_NAME


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
    flow.hass.config_entries = MagicMock()
    flow.hass.config_entries.async_update_entry = MagicMock()
    flow.hass.config_entries.async_reload = AsyncMock()
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_mismatch = MagicMock()  # noqa: SLF001
    entry = MagicMock()
    entry.title = "Combined Energy"
    entry.entry_id = "entry-1"
    entry.data = {
        CONF_HOST: "old-bridge.local",
        CONF_STALE_ENTITY_CLEANUP_PENDING: True,
    }
    flow._get_reconfigure_entry = MagicMock(return_value=entry)  # noqa: SLF001

    with (
        patch(
            "custom_components.combined_energy.config_flow.validate_bridge_host",
            new=AsyncMock(return_value=bootstrap),
        ),
        patch(
            "custom_components.combined_energy.config_flow.cleanup_stale_sensor_entities"
        ) as cleanup_stale_sensor_entities,
    ):
        result = await flow.async_step_reconfigure(
            {
                CONF_NAME: "Combined Energy Updated",
                CONF_HOST: "bridge.local",
            }
        )

    flow.async_set_unique_id.assert_awaited_once_with(str(installation.id))
    flow._abort_if_unique_id_mismatch.assert_called_once_with()  # noqa: SLF001
    cleanup_stale_sensor_entities.assert_called_once_with(
        flow.hass, entry, installation
    )
    flow.hass.config_entries.async_update_entry.assert_called_once_with(
        entry,
        title="Combined Energy Updated",
        data={
            CONF_HOST: "bridge.local",
            CONF_MQTT_PASSWORD: "bridge-secret",
        },
    )
    flow.hass.config_entries.async_reload.assert_awaited_once_with(entry.entry_id)
    assert result["type"] == "abort"
    assert result["reason"] == "reconfigure_successful"
