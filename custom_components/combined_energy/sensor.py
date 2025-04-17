"""Sensors and factory for enumerating devices from the Combined Energy API."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Generator, Sequence
from datetime import datetime
from typing import Any, cast

from combined_energy import CombinedEnergy
from combined_energy.models import Device, DeviceReadings, Installation
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_API_CLIENT, DATA_INSTALLATION, DOMAIN, LOGGER
from .coordinator import CombinedEnergyReadingsCoordinator

# Common sensors for all consumer devices
SENSOR_DESCRIPTIONS_ENERGY_CONSUMER = [
    SensorEntityDescription(
        key="energy_consumed",
        translation_key="energy_consumed",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
    ),
    SensorEntityDescription(
        key="energy_consumed_solar",
        translation_key="energy_consumed_solar",
        icon="mdi:solar-power",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="energy_consumed_battery",
        translation_key="energy_consumed_battery",
        icon="mdi:home-battery",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="energy_consumed_grid",
        translation_key="energy_consumed_grid",
        icon="mdi:transmission-tower",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        entity_registry_enabled_default=False,
    ),
]
SENSOR_DESCRIPTIONS_POWER_CONSUMER = [
    SensorEntityDescription(
        key="power_consumption",
        translation_key="power_consumption",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
    ),
    SensorEntityDescription(
        key="power_consumption_solar",
        translation_key="power_consumption_solar",
        icon="mdi:solar-power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="power_consumption_battery",
        translation_key="power_consumption_battery",
        icon="mdi:home-battery",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="power_consumption_grid",
        translation_key="power_consumption_grid",
        icon="mdi:transmission-tower",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
    ),
]
SENSOR_DESCRIPTIONS_GENERIC_CONSUMER = (
    SENSOR_DESCRIPTIONS_ENERGY_CONSUMER + SENSOR_DESCRIPTIONS_POWER_CONSUMER
)
SENSOR_DESCRIPTIONS = {
    "SOLAR_PV": [
        SensorEntityDescription(
            key="energy_supplied",
            translation_key="solar_pv_energy_supplied",
            icon="mdi:solar-power",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
        ),
        SensorEntityDescription(
            key="power_supply",
            translation_key="solar_pv_power_supply",
            icon="mdi:solar-power",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=SensorDeviceClass.POWER,
        ),
    ],
    "WATER_HEATER": [
        *SENSOR_DESCRIPTIONS_GENERIC_CONSUMER,
        SensorEntityDescription(
            key="available_energy",
            translation_key="water_heater_available_energy",
            state_class=SensorStateClass.TOTAL_INCREASING,
            native_unit_of_measurement=UnitOfVolume.LITERS,
            device_class=SensorDeviceClass.WATER,
        ),
        SensorEntityDescription(
            key="max_energy",
            translation_key="water_heater_max_energy",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfVolume.LITERS,
            device_class=SensorDeviceClass.WATER,
        ),
        SensorEntityDescription(
            key="output_temp",
            translation_key="water_heater_output_temp",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
        ),
        SensorEntityDescription(
            key="temp_sensor1",
            translation_key="water_heater_temp_sensor1",
            icon="mdi:thermometer-water",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            entity_registry_enabled_default=False,
        ),
        SensorEntityDescription(
            key="temp_sensor2",
            translation_key="water_heater_temp_sensor2",
            icon="mdi:thermometer-water",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            entity_registry_enabled_default=False,
        ),
        SensorEntityDescription(
            key="temp_sensor3",
            translation_key="water_heater_temp_sensor3",
            icon="mdi:thermometer-water",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            entity_registry_enabled_default=False,
        ),
        SensorEntityDescription(
            key="temp_sensor4",
            translation_key="water_heater_temp_sensor4",
            icon="mdi:thermometer-water",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            entity_registry_enabled_default=False,
        ),
        SensorEntityDescription(
            key="temp_sensor5",
            translation_key="water_heater_temp_sensor5",
            icon="mdi:thermometer-water",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            entity_registry_enabled_default=False,
        ),
        SensorEntityDescription(
            key="temp_sensor6",
            translation_key="water_heater_temp_sensor6",
            icon="mdi:thermometer-water",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            entity_registry_enabled_default=False,
        ),
    ],
    "GRID_METER": [
        SensorEntityDescription(
            key="energy_supplied",
            translation_key="grid_meter_energy_supplied",
            icon="mdi:transmission-tower-export",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
        ),
        SensorEntityDescription(
            key="power_supply",
            translation_key="grid_meter_power_supply",
            icon="mdi:transmission-tower-export",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=SensorDeviceClass.POWER,
        ),
        SensorEntityDescription(
            key="energy_consumed",
            translation_key="grid_meter_energy_consumed",
            icon="mdi:transmission-tower-import",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
        ),
        SensorEntityDescription(
            key="power_consumption",
            translation_key="grid_meter_power_consumption",
            icon="mdi:transmission-tower-import",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=SensorDeviceClass.POWER,
        ),
        SensorEntityDescription(
            key="energy_consumed_solar",
            translation_key="grid_meter_energy_consumed_solar",
            icon="mdi:solar-power",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            entity_registry_enabled_default=False,
        ),
        SensorEntityDescription(
            key="power_consumption_solar",
            translation_key="grid_meter_power_consumption_solar",
            icon="mdi:solar-power",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=SensorDeviceClass.POWER,
            entity_registry_enabled_default=False,
        ),
        SensorEntityDescription(
            key="energy_consumed_battery",
            translation_key="grid_meter_energy_consumed_battery",
            icon="mdi:home-battery",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            entity_registry_enabled_default=False,
        ),
        SensorEntityDescription(
            key="power_consumption_battery",
            translation_key="grid_meter_power_consumption_battery",
            icon="mdi:home-battery",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=SensorDeviceClass.POWER,
            entity_registry_enabled_default=False,
        ),
        SensorEntityDescription(
            key="power_factor_a",
            translation_key="grid_meter_power_factor_a",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="%",
            device_class=SensorDeviceClass.POWER_FACTOR,
        ),
        SensorEntityDescription(
            key="power_factor_b",
            translation_key="grid_meter_power_factor_b",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="%",
            device_class=SensorDeviceClass.POWER_FACTOR,
            entity_registry_enabled_default=False,
        ),
        SensorEntityDescription(
            key="power_factor_c",
            translation_key="grid_meter_power_factor_c",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="%",
            device_class=SensorDeviceClass.POWER_FACTOR,
            entity_registry_enabled_default=False,
        ),
        SensorEntityDescription(
            key="voltage_a",
            translation_key="grid_meter_voltage_a",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="V",
            device_class=SensorDeviceClass.VOLTAGE,
        ),
        SensorEntityDescription(
            key="voltage_b",
            translation_key="grid_meter_voltage_b",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="V",
            device_class=SensorDeviceClass.VOLTAGE,
            entity_registry_enabled_default=False,
        ),
        SensorEntityDescription(
            key="voltage_c",
            translation_key="grid_meter_voltage_c",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="V",
            device_class=SensorDeviceClass.VOLTAGE,
            entity_registry_enabled_default=False,
        ),
    ],
    "GENERIC_CONSUMER": SENSOR_DESCRIPTIONS_GENERIC_CONSUMER,
    "ENERGY_BALANCE": SENSOR_DESCRIPTIONS_GENERIC_CONSUMER,
    "COMBINER": [
        *SENSOR_DESCRIPTIONS_ENERGY_CONSUMER,
        SensorEntityDescription(
            key="energy_supplied",
            translation_key="combiner_energy_supplied",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
        ),
        SensorEntityDescription(
            key="energy_supplied_solar",
            translation_key="combiner_energy_supplied_solar",
            icon="mdi:solar-power",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            entity_registry_enabled_default=False,
        ),
        SensorEntityDescription(
            key="energy_supplied_battery",
            translation_key="combiner_energy_supplied_battery",
            icon="mdi:home-battery",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            entity_registry_enabled_default=False,
        ),
        SensorEntityDescription(
            key="energy_supplied_grid",
            translation_key="combiner_energy_supplied_grid",
            icon="mdi:transmission-tower",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            entity_registry_enabled_default=False,
        ),
    ],
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""

    api: CombinedEnergy = hass.data[DOMAIN][entry.entry_id][DATA_API_CLIENT]
    installation: Installation = hass.data[DOMAIN][entry.entry_id][DATA_INSTALLATION]

    # Initialise readings coordinator
    readings = CombinedEnergyReadingsCoordinator(hass=hass, api=api, config_entry=entry)
    await readings.async_config_entry_first_refresh()

    LOGGER.info("Setting up Combined Energy sensors")
    async_add_entities(_generate_sensors(installation, readings))


def _generate_sensors(
    installation: Installation,
    readings: CombinedEnergyReadingsCoordinator,
) -> Generator[CombinedEnergyReadingsSensor, None, None]:
    """Generate sensor entities from installed devices."""

    for device in installation.devices:
        LOGGER.info(
            "Generating sensors for device %s (%s)",
            device.device_id,
            device.device_type,
        )
        if descriptions := SENSOR_DESCRIPTIONS.get(device.device_type):
            # Generate sensors from descriptions for the current device type
            for description in descriptions:
                if sensor_type := SENSOR_TYPE_MAP.get(
                    description.device_class, GenericSensor
                ):
                    yield sensor_type(device, description, readings)


class CombinedEnergyReadingsSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Combined Energy API reading energy sensor."""

    entity_description: SensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        device: Device,
        description: SensorEntityDescription,
        coordinator: CombinedEnergyReadingsCoordinator,
    ) -> None:
        """Initialise Readings Sensor."""
        super().__init__(coordinator)

        self.device_id = device.device_id
        self.entity_description = description

        identifier = (
            f"install_{self.coordinator.api.installation_id}-device_{device.device_id}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identifier)},
            manufacturer=device.device_manufacturer,
            model=device.device_model_name,
            name=device.display_name,
        )
        self._attr_unique_id = f"{identifier}-{description.key}"

    @property
    def device_readings(self) -> DeviceReadings | None:
        """Get readings for specific device."""
        if data := self.coordinator.data:
            return data.get(self.device_id, None)
        return None

    @property
    def _raw_value(self) -> Any:
        """Get raw reading value from device readings."""
        if device_readings := self.device_readings:
            return getattr(device_readings, self.entity_description.key)
        return None

    @property
    def available(self) -> bool:
        """Indicate if the entity is available."""
        return self._raw_value is not None

    @abstractmethod
    def _to_native_value(self, raw_value: Any) -> int | float | None:
        """Convert non-none raw value into usable sensor value."""

    @property
    def native_value(self) -> int | float | None:
        """Return the state of the sensor."""
        if (raw_value := self._raw_value) is not None:
            return self._to_native_value(raw_value)
        return None


class GenericSensor(CombinedEnergyReadingsSensor):
    """Sensor that returns the last value of a sequence of readings."""

    _attr_suggested_display_precision = 2

    def _to_native_value(self, raw_value: Any) -> float:
        """Convert non-none raw value into usable sensor value."""
        if isinstance(raw_value, Sequence):
            raw_value = raw_value[-1]
        return float(round(raw_value, self.suggested_display_precision))


class EnergySensor(CombinedEnergyReadingsSensor):
    """Sensor for energy readings."""

    _attr_suggested_display_precision = 2

    @property
    def last_reset(self) -> datetime | None:
        """Last time the data was reset."""
        if device_readings := self.device_readings:
            # mypy is struggling with a Pydantic model here, the cast isn't technically required
            return cast(datetime | None, device_readings.range_start)
        return None

    def _to_native_value(self, raw_value: Any) -> float:
        """Convert non-none raw value into usable sensor value."""
        value = sum(raw_value)
        return float(round(value, self.suggested_display_precision))


class PowerSensor(CombinedEnergyReadingsSensor):
    """Sensor for power readings."""

    _attr_suggested_display_precision = 2

    def _to_native_value(self, raw_value: Any) -> float:
        """Convert non-none raw value into usable sensor value."""
        return float(round(raw_value, self.suggested_display_precision))


class PowerFactorSensor(CombinedEnergyReadingsSensor):
    """Sensor for power factor readings."""

    _attr_suggested_display_precision = 1

    def _to_native_value(self, raw_value: Any) -> float:
        """Convert non-none raw value into usable sensor value."""
        # The API expresses the power factor as a fraction convert to %
        if isinstance(raw_value, Sequence):
            raw_value = raw_value[-1]
        if raw_value is not None:
            return float(round(raw_value * 100, self.suggested_display_precision))
        else:
            return None


class WaterVolumeSensor(CombinedEnergyReadingsSensor):
    """Sensor for water volume readings."""

    def _to_native_value(self, raw_value: Any) -> int:
        """Convert non-none raw value into usable sensor value."""
        if isinstance(raw_value, Sequence):
            raw_value = raw_value[-1]
        if raw_value is not None:
            return int(round(raw_value, 0))
        else:
            return None


# Map of common device classes to specific sensor types
SENSOR_TYPE_MAP: dict[
    SensorDeviceClass | str | None, type[CombinedEnergyReadingsSensor]
] = {
    SensorDeviceClass.ENERGY: EnergySensor,
    SensorDeviceClass.POWER: PowerSensor,
    SensorDeviceClass.WATER: WaterVolumeSensor,
    SensorDeviceClass.POWER_FACTOR: PowerFactorSensor,
}
