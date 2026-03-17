"""Tests for Combined Energy sensors."""

from unittest.mock import MagicMock, patch

from freezegun import freeze_time
import pytest

from custom_components.combined_energy.const import CURRENCY_AUD
from custom_components.combined_energy.coordinator import (
    CombinedEnergyTariffDetailsCoordinator,
)
from custom_components.combined_energy.models import Installation, TariffDetails
from custom_components.combined_energy.sensor import (
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
def mock_hass():
    """Mock HomeAssistant."""
    return MagicMock(spec=HomeAssistant)


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
