"""Tests for Combined Energy readings sensors."""

from unittest.mock import MagicMock

import pytest

from custom_components.combined_energy.coordinator import (
    CombinedEnergyReadingsCoordinator,
)
from custom_components.combined_energy.models import (
    Device,
    GridMeterReading,
    Installation,
    Readings,
    SystemReading,
)
from custom_components.combined_energy.sensor import (
    CombinedEnergyReadingsSensor,
    CombinedEnergySensorDescription,
)
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant


@pytest.fixture
def installation(fixture_path):
    """Fixture for Installation model."""
    return Installation.model_validate_json((fixture_path / "installation.json").read_text())


@pytest.fixture
def readings(example_log_payload: bytes):
    """Fixture for Readings model."""
    return Readings.from_mqtt_message(example_log_payload)


@pytest.fixture
def mock_hass():
    """Mock HomeAssistant."""
    return MagicMock(spec=HomeAssistant)


class TestCombinedEnergyReadingsSensor:
    """Tests for CombinedEnergyReadingsSensor."""

    @pytest.fixture
    def mock_coordinator(self, readings):
        """Mock CombinedEnergyReadingsCoordinator."""
        return MagicMock(spec=CombinedEnergyReadingsCoordinator, data=readings)

    @pytest.fixture
    def entity_description(self):
        """CombinedEnergySensorDescription fixture."""
        return CombinedEnergySensorDescription(
            key="energy_supplied",
            translation_key="energy_supplied",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
        )

    @pytest.fixture
    def sensor(self, installation, mock_coordinator, entity_description, mock_hass):
        """CombinedEnergyReadingsSensor fixture."""
        device = installation.devices[3]
        sensor = CombinedEnergyReadingsSensor(
            installation, device, entity_description, mock_coordinator
        )
        sensor.hass = mock_hass
        return sensor

    def test_init(self, sensor, installation, entity_description):
        """Test CombinedEnergyReadingsSensor initialization."""
        device = installation.devices[3]
        assert (
            sensor.unique_id
            == f"install_{installation.id}-device_{device.id}-{entity_description.key}"
        )
        assert sensor.entity_description == entity_description
        assert sensor.device_id == device.id
        assert sensor.device_type == device.device_type

    def test_readings_device(self, sensor):
        """Test readings_device property."""
        assert sensor.readings_device.device_id == sensor.device_id

    def test_readings_device_none(self, sensor, mock_coordinator):
        """Test readings_device property when coordinator data is None."""
        mock_coordinator.data = None
        assert sensor.readings_device is None

    def test_readings_device_not_found(self, sensor):
        """Test readings_device property when device is not found."""
        sensor.device_id = 999
        assert sensor.readings_device is None

    def test_available(self, sensor):
        """Test available property."""
        assert sensor.available is True

    def test_native_value(self, sensor):
        """Test native_value."""
        assert sensor.native_value == 0.0

    def test_native_value_after_reading_update(self, sensor, mock_coordinator):
        """Test native_value after updating underlying reading."""
        grid_meter = next(
            device
            for device in mock_coordinator.data.devices
            if isinstance(device, GridMeterReading)
        )
        grid_meter.energy_supplied = 3.0
        assert sensor.native_value == 3.0

    def test_system_sensor_reads_system_reading(self, installation, mock_coordinator, mock_hass):
        """System sensor should resolve values from SystemReading."""
        system_device = Device(
            id=0,
            type="SystemReading",
            refName="",
            name="System",
            manufacturer=None,
            model=None,
            serial=None,
            supplier=False,
            storage=False,
            consumer=False,
            max_power_consumption=None,
            status="",
            category="",
        )
        description = CombinedEnergySensorDescription(
            key="reading_count",
            translation_key="system_reading_count",
        )
        sensor = CombinedEnergyReadingsSensor(
            installation, system_device, description, mock_coordinator
        )
        sensor.hass = mock_hass

        assert isinstance(sensor.readings_device, SystemReading)
        assert sensor.native_value == sensor.readings_device.reading_count
