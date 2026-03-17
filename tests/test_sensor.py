"""Tests for Combined Energy sensors."""

from dataclasses import replace
from unittest.mock import MagicMock, patch

from freezegun import freeze_time
import pytest

from custom_components.combined_energy.const import CURRENCY_AUD
from custom_components.combined_energy.coordinator import (
    CombinedEnergyReadingsCoordinator,
    CombinedEnergyTariffDetailsCoordinator,
)
from custom_components.combined_energy.models import (
    Installation,
    Readings,
    TariffDetails,
)
from custom_components.combined_energy.sensor import (
    Aggregation,
    CombinedEnergyReadingsSensor,
    CombinedEnergySensorDescription,
    CombinedEnergyTariffSensor,
    PriceSensor,
)
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant


@pytest.fixture
def installation(fixture_path):
    """Fixture for Installation model."""
    return Installation.model_validate_json(
        (fixture_path / "installation.json").read_text()
    )


@pytest.fixture
def tariff_details(fixture_path):
    """Fixture for TariffDetails model."""
    return TariffDetails.model_validate_json(
        (fixture_path / "tariff-details.json").read_text()
    )


@pytest.fixture
def readings(fixture_path):
    """Fixture for Readings model."""
    return Readings.model_validate_json((fixture_path / "readings.json").read_text())


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
            aggregation=Aggregation.SUM,
        )

    @pytest.fixture
    def sensor(self, installation, mock_coordinator, entity_description, mock_hass):
        """CombinedEnergyReadingsSensor fixture."""
        device = installation.devices[
            3
        ]  # Use the fourth device (GRID_METER in installation.json)
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

    def test_readings_device(self, sensor, readings):
        """Test readings_device property."""
        assert sensor.readings_device.device_id == sensor.device_id
        assert sensor.readings_device.device_type == sensor.device_type

    def test_readings_device_none(self, sensor, mock_coordinator):
        """Test readings_device property when coordinator data is None."""
        mock_coordinator.data = None
        assert sensor.readings_device is None

    def test_readings_device_not_found(self, sensor, mock_coordinator, readings):
        """Test readings_device property when device is not found."""
        sensor.device_id = 999
        assert sensor.readings_device is None

    def test_available(self, sensor):
        """Test available property."""
        assert sensor.available is True

    def test_available_none(self, sensor, mock_coordinator):
        """Test available property when value is None."""
        # GRID_METER (device 4) is at index 1 in readings.json
        mock_coordinator.data.devices[1].energy_supplied = [None]
        assert sensor.available is False

    def test_available_sequence(self, sensor, mock_coordinator):
        """Test available property with sequence of values."""
        # GRID_METER (device 4) is at index 1 in readings.json
        mock_coordinator.data.devices[1].energy_supplied = [None, 1.0, None]
        assert sensor.available is True

    def test_available_sequence_all_none(self, sensor, mock_coordinator):
        """Test available property with sequence of all None values."""
        # GRID_METER (device 4) is at index 1 in readings.json
        mock_coordinator.data.devices[1].energy_supplied = [None, None]
        assert sensor.available is False

    def test_native_value_sum(self, sensor):
        """Test native_value with Aggregation.SUM."""
        # energySupplied for GRID_METER (device 4) is [0]
        assert sensor.native_value == 0

    def test_native_value_latest(self, sensor, entity_description, mock_coordinator):
        """Test native_value with Aggregation.LATEST."""
        # Use a new description because it is frozen
        entity_description = replace(entity_description, aggregation=Aggregation.LATEST)
        sensor.entity_description = entity_description
        # GRID_METER (device 4) is at index 1 in readings.json
        mock_coordinator.data.devices[1].energy_supplied = [1.0, 2.0, 3.0]
        assert sensor.native_value == 3.0

    def test_native_value_latest_with_none(
        self, sensor, entity_description, mock_coordinator
    ):
        """Test native_value with Aggregation.LATEST and Nones."""
        entity_description = replace(entity_description, aggregation=Aggregation.LATEST)
        sensor.entity_description = entity_description
        # GRID_METER (device 4) is at index 1 in readings.json
        mock_coordinator.data.devices[1].energy_supplied = [1.0, 2.0, None]
        assert sensor.native_value == 2.0

    def test_native_value_none(self, sensor, mock_coordinator):
        """Test native_value when raw value is None."""
        mock_coordinator.data = None
        assert sensor.native_value is None

    def test_last_reset_sum(self, sensor, readings):
        """Test last_reset with Aggregation.SUM."""
        # GRID_METER (device 4) is at index 1 in readings.json
        assert sensor.last_reset == readings.devices[1].range_start

    def test_last_reset_latest(self, sensor, entity_description, readings):
        """Test last_reset with Aggregation.LATEST."""
        entity_description = replace(entity_description, aggregation=Aggregation.LATEST)
        sensor.entity_description = entity_description
        # GRID_METER (device 4) is at index 1 in readings.json
        assert sensor.last_reset == readings.devices[1].range_end

    def test_last_reset_not_total(self, sensor, entity_description):
        """Test last_reset when state_class is not TOTAL."""
        entity_description = replace(
            entity_description, state_class=SensorStateClass.MEASUREMENT
        )
        sensor.entity_description = entity_description
        assert sensor.last_reset is None

    def test_last_reset_no_readings(self, sensor, mock_coordinator):
        """Test last_reset when no readings available."""
        mock_coordinator.data = None
        assert sensor.last_reset is None


class TestCombinedEnergyTariffSensor:
    """Tests for CombinedEnergyTariffSensor."""

    @pytest.fixture
    def mock_coordinator(self, tariff_details):
        """Mock CombinedEnergyTariffDetailsCoordinator."""
        return MagicMock(
            spec=CombinedEnergyTariffDetailsCoordinator, data=tariff_details
        )

    @pytest.fixture
    def entity_description(self):
        """CombinedEnergySensorDescription fixture."""
        return CombinedEnergySensorDescription(
            key="foobar",
            translation_key="foobar_translation",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
        )

    @pytest.fixture
    def sensor(self, installation, mock_coordinator, entity_description, mock_hass):
        """CombinedEnergyTariffSensor fixture."""
        sensor = CombinedEnergyTariffSensor(
            installation, mock_coordinator, entity_description
        )
        sensor.hass = mock_hass
        return sensor

    def test_init(self, sensor, installation, entity_description):
        """Test CombinedEnergyTariffSensor initialization."""
        assert (
            sensor.unique_id
            == f"install_{installation.id}-tariff-details-{entity_description.key}"
        )
        assert sensor.entity_description == entity_description

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (None, None),
            (MagicMock(tariff=MagicMock(foobar=1234)), 12.34),
        ],
    )
    def test_native_value(self, sensor, mock_coordinator, data, expected):
        """Test CombinedEnergyTariffSensor native_value."""
        mock_coordinator.data = data
        assert sensor.native_value == expected


class TestPriceSensor:
    """Tests for PriceSensor."""

    @pytest.fixture
    def mock_coordinator(self, tariff_details):
        """Mock CombinedEnergyTariffDetailsCoordinator."""
        return MagicMock(
            spec=CombinedEnergyTariffDetailsCoordinator, data=tariff_details
        )

    @pytest.fixture
    def sensor(self, installation, mock_coordinator, mock_hass):
        """PriceSensor fixture."""
        sensor = PriceSensor(installation, mock_coordinator)
        sensor.hass = mock_hass
        return sensor

    def test_init(self, installation, sensor: PriceSensor):
        """Test PriceSensor initialization."""
        assert sensor._timezone == installation.timezone  # noqa: SLF001
        assert sensor.unique_id == f"install_{installation.id}-tariff-details-cost"
        assert sensor.translation_key == "tariff_details_cost"
        assert sensor.icon == "mdi:cash-minus"
        assert sensor.suggested_display_precision == 2
        assert sensor.state_class == SensorStateClass.TOTAL
        assert sensor.device_class == SensorDeviceClass.MONETARY
        assert (
            sensor.native_unit_of_measurement
            == f"{CURRENCY_AUD}/{UnitOfEnergy.KILO_WATT_HOUR}"
        )

    @freeze_time("2025-04-13 06:51:50")
    def test_native_value(self, sensor):
        """Test PriceSensor native_value."""
        # 10.12 / 100.0 = 0.1012
        assert sensor.native_value == 0.1012

    @pytest.mark.asyncio
    async def test_async_added_to_hass(self, sensor):
        """Test PriceSensor async_added_to_hass."""
        with (
            patch(
                "custom_components.combined_energy.sensor.async_track_point_in_time"
            ) as mock_track,
            patch.object(sensor, "async_write_ha_state"),
        ):
            await sensor.async_added_to_hass()
            mock_track.assert_called_once()

    def test_schedule_refresh(self, sensor):
        """Test PriceSensor _schedule_refresh."""
        with patch(
            "custom_components.combined_energy.sensor.async_track_point_in_time"
        ) as mock_track:
            sensor._schedule_refresh()  # noqa: SLF001
            mock_track.assert_called_once()

    def test_refresh_price(self, sensor):
        """Test PriceSensor _refresh_price."""
        with (
            patch.object(sensor, "async_write_ha_state") as mock_write,
            patch.object(sensor, "_schedule_refresh") as mock_schedule,
        ):
            sensor._refresh_price()  # noqa: SLF001
            mock_write.assert_called_once()
            mock_schedule.assert_called_once()

    def test_native_value_none(self, sensor, mock_coordinator):
        """Test PriceSensor native_value with no data."""
        mock_coordinator.data = None
        assert sensor.native_value is None

    def test_refresh_no_data(self, sensor, mock_coordinator):
        """Test PriceSensor _schedule_refresh with no data."""
        mock_coordinator.data = None

        with patch(
            "homeassistant.helpers.event.async_track_point_in_time"
        ) as mock_track:
            sensor._schedule_refresh()  # noqa: SLF001
            mock_track.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_will_remove_from_hass(self, sensor):
        """Test PriceSensor async_will_remove_from_hass."""
        mock_cancel = MagicMock()
        sensor._cancel_next_refresh = mock_cancel  # noqa: SLF001

        await sensor.async_will_remove_from_hass()
        mock_cancel.assert_called_once()
        assert sensor._cancel_next_refresh is None  # noqa: SLF001

    def test_handle_coordinator_update(self, sensor):
        """Test PriceSensor _handle_coordinator_update."""
        with (
            patch.object(sensor, "async_write_ha_state"),
            patch.object(sensor, "_schedule_refresh") as mock_schedule,
        ):
            sensor._handle_coordinator_update()  # noqa: SLF001
            mock_schedule.assert_called_once()
