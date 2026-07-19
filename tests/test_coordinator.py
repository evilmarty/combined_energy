"""Tests for Combined Energy coordinators."""

import asyncio
from unittest.mock import MagicMock

import pytest

from custom_components.combined_energy.bridge import BridgeBootstrap, MqttBridgeClient
from custom_components.combined_energy.coordinator import (
    CombinedEnergyReadingsCoordinator,
)
from custom_components.combined_energy.models import (
    Installation,
    Readings,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_hass():
    """Mock HomeAssistant."""
    hass = MagicMock(spec=HomeAssistant)
    try:
        hass.loop = asyncio.get_running_loop()
    except RuntimeError:
        hass.loop = MagicMock()
    hass.async_create_task = asyncio.create_task
    return hass


@pytest.fixture
def mock_entry():
    """Mock ConfigEntry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    return entry


@pytest.fixture
def sample_readings(example_log_payload: bytes) -> Readings:
    """Parse readings from sample bridge payload."""
    return Readings.from_mqtt_message(example_log_payload)


@pytest.fixture
def bridge_client(mock_hass, fixture_path):
    """Bridge client configured with test bootstrap."""
    installation = Installation.model_validate_json(
        (fixture_path / "installation.json").read_text()
    )
    bootstrap = BridgeBootstrap(
        bridge_host="bridge.local",
        mqtt_password="secret",
        installation=installation,
    )
    return MqttBridgeClient(mock_hass, bootstrap)


@pytest.mark.asyncio
async def test_coordinator_updates_from_mqtt_listener(
    bridge_client: MqttBridgeClient,
    mock_hass,
    mock_entry,
    sample_readings: Readings,
    example_log_payload: bytes,
):
    """Coordinator parses subscribed readings messages."""
    coordinator = CombinedEnergyReadingsCoordinator(mock_hass, bridge_client, mock_entry)
    assert coordinator.data is None

    coordinator._handle_readings_message(  # noqa: SLF001
        "cet-ecn/21723/dmg/readings/stream",
        example_log_payload,
    )

    assert coordinator.data == sample_readings
