"""Tests for MQTT readings store service."""

import pytest

from custom_components.combined_energy.models import GridMeterReading, Readings
from custom_components.combined_energy.storage import ReadingsStore


class InMemoryStateStore:
    """Simple test storage adapter."""

    def __init__(self, state=None):
        """Initialize in-memory state."""
        self.state = state
        self.saved_states: list[dict] = []

    async def async_load(self):
        """Load stored state."""
        return self.state

    async def async_save(self, state):
        """Save state."""
        self.saved_states.append(state)
        self.state = state


@pytest.mark.asyncio
async def test_store_converts_interval_energy_to_cumulative(
    example_log_payload: bytes,
):
    """Consumed interval energy should become cumulative positive totals."""
    persisted_state = InMemoryStateStore()
    store = ReadingsStore(hass=None, config_entry=None, persistence=persisted_state)

    readings = Readings.from_mqtt_message(example_log_payload)
    accumulated = await store.async_record_readings(readings)

    assert accumulated is not None
    grid = next(
        device for device in accumulated.devices if isinstance(device, GridMeterReading)
    )
    assert grid.energy_consumed > 0
    assert persisted_state.saved_states


@pytest.mark.asyncio
async def test_store_ignores_duplicate_period(
    example_log_payload: bytes,
):
    """Duplicate period payload should not be processed twice."""
    persisted_state = InMemoryStateStore()
    store = ReadingsStore(hass=None, config_entry=None, persistence=persisted_state)

    first = await store.async_record_readings(
        Readings.from_mqtt_message(example_log_payload)
    )
    second = await store.async_record_readings(
        Readings.from_mqtt_message(example_log_payload)
    )

    assert first is not None
    assert second is None


@pytest.mark.asyncio
async def test_store_restores_previous_state(example_log_payload: bytes):
    """Store should continue from restored totals."""
    restored_total = 42.0
    state = {
        "last_processed_period_end": 0,
        "energy_totals": {"GridMeterReading:4:energy_consumed": restored_total},
    }
    persisted_state = InMemoryStateStore(state=state)
    store = ReadingsStore(hass=None, config_entry=None, persistence=persisted_state)

    accumulated = await store.async_record_readings(
        Readings.from_mqtt_message(example_log_payload)
    )

    assert accumulated is not None
    grid = next(
        device for device in accumulated.devices if isinstance(device, GridMeterReading)
    )
    assert grid.energy_consumed > restored_total
