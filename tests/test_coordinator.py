"""Tests for Combined Energy coordinators."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from custom_components.combined_energy.bridge import BridgeBootstrap, MqttBridgeClient
from custom_components.combined_energy.coordinator import (
    CombinedEnergyIntelCoordinator,
    CombinedEnergyReadingsCoordinator,
)
from custom_components.combined_energy.models import (
    GridMeterReading,
    Installation,
    Intel,
    Readings,
)
from custom_components.combined_energy.storage import ReadingsStore
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
    hass.data = {}
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


@pytest.fixture
def readings_store(mock_hass, mock_entry):
    """Return a readings store for coordinator tests."""
    return ReadingsStore(mock_hass, mock_entry)


@pytest.mark.asyncio
async def test_coordinator_updates_from_mqtt_listener(
    bridge_client: MqttBridgeClient,
    mock_hass,
    mock_entry,
    readings_store,
    sample_readings: Readings,
    example_log_payload: bytes,
):
    """Coordinator parses subscribed readings messages."""
    coordinator = CombinedEnergyReadingsCoordinator(
        mock_hass, bridge_client, readings_store, mock_entry
    )
    assert coordinator.data is None

    coordinator._handle_readings_message(  # noqa: SLF001
        "cet-ecn/21723/dmg/readings/stream",
        example_log_payload,
    )
    await asyncio.sleep(0)

    assert coordinator.data is not None
    source_grid = next(
        device
        for device in sample_readings.devices
        if isinstance(device, GridMeterReading)
    )
    result_grid = next(
        device
        for device in coordinator.data.devices
        if isinstance(device, GridMeterReading)
    )
    assert result_grid.energy_consumed == abs(source_grid.energy_consumed)


@pytest.mark.asyncio
async def test_coordinator_ignores_duplicate_period_messages(
    bridge_client: MqttBridgeClient,
    mock_hass,
    mock_entry,
    readings_store,
    example_log_payload: bytes,
):
    """Duplicate period messages should not double-count totals."""
    coordinator = CombinedEnergyReadingsCoordinator(
        mock_hass, bridge_client, readings_store, mock_entry
    )

    await coordinator._async_process_readings_message(example_log_payload)  # noqa: SLF001
    first_grid = next(
        device
        for device in coordinator.data.devices
        if isinstance(device, GridMeterReading)
    )
    first_energy_consumed = first_grid.energy_consumed

    await coordinator._async_process_readings_message(example_log_payload)  # noqa: SLF001
    second_grid = next(
        device
        for device in coordinator.data.devices
        if isinstance(device, GridMeterReading)
    )
    assert second_grid.energy_consumed == first_energy_consumed


@pytest.mark.asyncio
async def test_watchdog_triggers_logging_start_when_no_new_messages(
    bridge_client: MqttBridgeClient,
    mock_hass,
    mock_entry,
    readings_store,
    sample_readings: Readings,
):
    """Watchdog requests logging start when no fresh message arrived."""
    coordinator = CombinedEnergyReadingsCoordinator(
        mock_hass, bridge_client, readings_store, mock_entry
    )
    bridge_client.publish_logging_start = MagicMock()

    coordinator._last_message_received_at = None  # noqa: SLF001
    coordinator._last_watchdog_check_at = datetime.now(UTC)  # noqa: SLF001

    coordinator._check_for_stale_messages()  # noqa: SLF001

    bridge_client.publish_logging_start.assert_called_once()


@pytest.mark.asyncio
async def test_readings_coordinator_requests_logging_on_schedule_refresh(
    bridge_client: MqttBridgeClient,
    mock_hass,
    mock_entry,
    readings_store,
):
    """Coordinator should request logging when scheduling starts."""
    bridge_client.publish_logging_start = MagicMock()
    coordinator = CombinedEnergyReadingsCoordinator(
        mock_hass, bridge_client, readings_store, mock_entry
    )
    bridge_client.publish_logging_start.assert_not_called()

    coordinator._schedule_refresh()  # noqa: SLF001
    coordinator._schedule_refresh()  # noqa: SLF001

    bridge_client.publish_logging_start.assert_called_once()


@pytest.mark.asyncio
async def test_watchdog_skips_logging_start_when_new_message_received(
    bridge_client: MqttBridgeClient,
    mock_hass,
    mock_entry,
    readings_store,
    sample_readings: Readings,
):
    """Scheduled update does not request logging start when message is fresh."""
    coordinator = CombinedEnergyReadingsCoordinator(
        mock_hass, bridge_client, readings_store, mock_entry
    )
    bridge_client.publish_logging_start = MagicMock()

    coordinator.async_set_updated_data(sample_readings)
    coordinator._last_message_received_at = datetime.now(UTC)  # noqa: SLF001

    result = await coordinator._async_update_data()  # noqa: SLF001

    assert result == sample_readings
    bridge_client.publish_logging_start.assert_not_called()


@pytest.mark.asyncio
async def test_intel_coordinator_updates_from_mqtt_listener(
    bridge_client: MqttBridgeClient,
    mock_hass,
    mock_entry,
):
    """Coordinator parses subscribed intel messages."""
    bridge_client.publish_request_intel = MagicMock()
    coordinator = CombinedEnergyIntelCoordinator(mock_hass, bridge_client, mock_entry)
    bridge_client.publish_request_intel.assert_not_called()
    assert coordinator.data is None

    payload = b"""{
        "installationId": 5076,
        "requestTimeStr": "Mon Jul 20 00:00:00 AEST 2026",
        "version": 1.2,
        "tariffDetails": [],
        "solarEnergyForecast": [],
        "generalEnergyUsagePattern": {
            "periodEndHour": [],
            "energyConsumedAvg": []
        },
        "nmi": "3116633733",
        "waterDischargePattern": []
    }"""
    coordinator._handle_intel_message(  # noqa: SLF001
        "cet-ecn/21723/dmg/response/1.2/intel",
        payload,
    )
    await asyncio.sleep(0)

    assert coordinator.data is not None
    assert isinstance(coordinator.data, Intel)
    assert coordinator.data.installation_id == 5076


@pytest.mark.asyncio
async def test_intel_coordinator_strips_non_json_prefix(
    bridge_client: MqttBridgeClient,
    mock_hass,
    mock_entry,
):
    """Coordinator should strip request metadata prefix before JSON parsing."""
    bridge_client.publish_request_intel = MagicMock()
    coordinator = CombinedEnergyIntelCoordinator(mock_hass, bridge_client, mock_entry)

    payload = (
        b" \xc2\xb8\x02 \n\trequestId\x10\x05B\x111785048075796-730\n"
        b"""{
        "installationId": 5076,
        "requestTimeStr": "Mon Jul 20 00:00:00 AEST 2026",
        "version": 1.2,
        "tariffDetails": [],
        "solarEnergyForecast": [],
        "generalEnergyUsagePattern": {
            "periodEndHour": [],
            "energyConsumedAvg": []
        },
        "nmi": "3116633733",
        "waterDischargePattern": []
    }"""
    )

    await coordinator._async_process_intel_message(payload)  # noqa: SLF001

    assert coordinator.data is not None
    assert isinstance(coordinator.data, Intel)
    assert coordinator.data.installation_id == 5076


@pytest.mark.asyncio
async def test_intel_coordinator_requests_on_schedule_refresh(
    bridge_client: MqttBridgeClient,
    mock_hass,
    mock_entry,
):
    """Coordinator should request intel when scheduling starts."""
    bridge_client.publish_request_intel = MagicMock()
    coordinator = CombinedEnergyIntelCoordinator(mock_hass, bridge_client, mock_entry)

    coordinator._schedule_refresh()  # noqa: SLF001
    coordinator._schedule_refresh()  # noqa: SLF001

    bridge_client.publish_request_intel.assert_called_once()
