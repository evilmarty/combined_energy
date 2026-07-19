"""Sensors and factory for enumerating devices from bridge MQTT readings."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from typing import Any

from custom_components.combined_energy.bridge import MqttBridgeClient
from custom_components.combined_energy.models import (
    Device,
    Installation,
    ReadingsDevices,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_BRIDGE_CLIENT, DATA_COORDINATOR, DOMAIN, LOGGER
from .coordinator import CombinedEnergyReadingsCoordinator


class CombinedEnergySensorDescription(SensorEntityDescription, frozen_or_thawed=True):
    """Describes Combined Energy sensor entity."""


# Common sensors for all consumer devices
SENSOR_DESCRIPTIONS_GENERIC_CONSUMER = [
    CombinedEnergySensorDescription(
        key="energy_consumed",
        translation_key="energy_consumed",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
    ),
    CombinedEnergySensorDescription(
        key="energy_consumed_solar",
        translation_key="energy_consumed_solar",
        icon="mdi:solar-power",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    CombinedEnergySensorDescription(
        key="energy_consumed_battery",
        translation_key="energy_consumed_battery",
        icon="mdi:home-battery",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    CombinedEnergySensorDescription(
        key="energy_consumed_grid",
        translation_key="energy_consumed_grid",
        icon="mdi:transmission-tower",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
]
SENSOR_DESCRIPTIONS = {
    "SOLAR_PV": [
        CombinedEnergySensorDescription(
            key="energy_supplied",
            translation_key="solar_pv_energy_supplied",
            icon="mdi:solar-power",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
        ),
    ],
    "WATER_HEATER": [
        *SENSOR_DESCRIPTIONS_GENERIC_CONSUMER,
        CombinedEnergySensorDescription(
            key="available_energy",
            translation_key="water_heater_available_energy",
            native_unit_of_measurement=UnitOfVolume.LITERS,
            device_class=SensorDeviceClass.WATER,
            suggested_display_precision=2,
        ),
        CombinedEnergySensorDescription(
            key="available_percentage",
            translation_key="water_heater_available_percentage",
            icon="mdi:water-percent",
            native_unit_of_measurement=PERCENTAGE,
            suggested_display_precision=0,
        ),
        CombinedEnergySensorDescription(
            key="max_energy",
            translation_key="water_heater_max_energy",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfVolume.LITERS,
            device_class=SensorDeviceClass.WATER,
            suggested_display_precision=2,
        ),
        CombinedEnergySensorDescription(
            key="temp_sensor1",
            translation_key="water_heater_temp_sensor1",
            icon="mdi:thermometer-water",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="temp_sensor2",
            translation_key="water_heater_temp_sensor2",
            icon="mdi:thermometer-water",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="temp_sensor3",
            translation_key="water_heater_temp_sensor3",
            icon="mdi:thermometer-water",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="temp_sensor4",
            translation_key="water_heater_temp_sensor4",
            icon="mdi:thermometer-water",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="temp_sensor5",
            translation_key="water_heater_temp_sensor5",
            icon="mdi:thermometer-water",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="temp_sensor6",
            translation_key="water_heater_temp_sensor6",
            icon="mdi:thermometer-water",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
    ],
    "GRID_METER": [
        CombinedEnergySensorDescription(
            key="energy_supplied",
            translation_key="grid_meter_energy_supplied",
            icon="mdi:transmission-tower-export",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
        ),
        CombinedEnergySensorDescription(
            key="energy_consumed",
            translation_key="grid_meter_energy_consumed",
            icon="mdi:transmission-tower-import",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
        ),
        CombinedEnergySensorDescription(
            key="energy_consumed_solar",
            translation_key="grid_meter_energy_consumed_solar",
            icon="mdi:solar-power",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="energy_consumed_battery",
            translation_key="grid_meter_energy_consumed_battery",
            icon="mdi:home-battery",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_factor_a",
            translation_key="grid_meter_power_factor_a",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=PERCENTAGE,
            device_class=SensorDeviceClass.POWER_FACTOR,
            suggested_display_precision=1,
        ),
        CombinedEnergySensorDescription(
            key="power_factor_b",
            translation_key="grid_meter_power_factor_b",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=PERCENTAGE,
            device_class=SensorDeviceClass.POWER_FACTOR,
            suggested_display_precision=1,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_factor_c",
            translation_key="grid_meter_power_factor_c",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=PERCENTAGE,
            device_class=SensorDeviceClass.POWER_FACTOR,
            suggested_display_precision=1,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="voltage_a",
            translation_key="grid_meter_voltage_a",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            suggested_display_precision=2,
            device_class=SensorDeviceClass.VOLTAGE,
        ),
        CombinedEnergySensorDescription(
            key="voltage_b",
            translation_key="grid_meter_voltage_b",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="voltage_c",
            translation_key="grid_meter_voltage_c",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
    ],
    "GENERIC_CONSUMER": SENSOR_DESCRIPTIONS_GENERIC_CONSUMER,
    "ENERGY_BALANCE": SENSOR_DESCRIPTIONS_GENERIC_CONSUMER,
}

SYSTEM_SENSOR_DESCRIPTIONS = [
    CombinedEnergySensorDescription(
        key="reading_count",
        translation_key="system_reading_count",
    ),
    CombinedEnergySensorDescription(
        key="connected_devices",
        translation_key="system_connected_devices",
    ),
    CombinedEnergySensorDescription(
        key="registered_devices",
        translation_key="system_registered_devices",
    ),
    CombinedEnergySensorDescription(
        key="jvm_startup",
        translation_key="system_jvm_startup",
    ),
    CombinedEnergySensorDescription(
        key="os_startup",
        translation_key="system_os_startup",
    ),
    CombinedEnergySensorDescription(
        key="plugin_startup",
        translation_key="system_plugin_startup",
    ),
    CombinedEnergySensorDescription(
        key="operation_status",
        translation_key="system_operation_status",
    ),
    CombinedEnergySensorDescription(
        key="operation_message",
        translation_key="system_operation_message",
    ),
    CombinedEnergySensorDescription(
        key="temperature",
        translation_key="system_temperature",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
    ),
]

COMBINER_SENSOR_DESCRIPTIONS = [
    *SENSOR_DESCRIPTIONS_GENERIC_CONSUMER,
    CombinedEnergySensorDescription(
        key="energy_supplied",
        translation_key="combiner_energy_supplied",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
    ),
    CombinedEnergySensorDescription(
        key="energy_supplied_solar",
        translation_key="combiner_energy_supplied_solar",
        icon="mdi:solar-power",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    CombinedEnergySensorDescription(
        key="energy_supplied_battery",
        translation_key="combiner_energy_supplied_battery",
        icon="mdi:home-battery",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    CombinedEnergySensorDescription(
        key="energy_supplied_grid",
        translation_key="combiner_energy_supplied_grid",
        icon="mdi:transmission-tower",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    CombinedEnergySensorDescription(
        key="energy_correction",
        translation_key="combiner_energy_correction",
        icon="mdi:transmission-tower",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
]

# System isn't listed in installation devices but it is included in readings.
SYSTEM_DEVICE = Device(
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

# Combiner isn't a real device but it's included in the readings with all the other devices
COMBINER_DEVICE = Device(
    id=0,
    type="CombinerReading",
    refName="",
    name="Combiner",
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

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""

    client: MqttBridgeClient = hass.data[DOMAIN][entry.entry_id][DATA_BRIDGE_CLIENT]
    coordinator: CombinedEnergyReadingsCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]
    installation = client.bootstrap.installation

    LOGGER.info("Setting up Combined Energy sensors")
    async_add_entities(_generate_readings_sensors(installation, coordinator))


def _generate_readings_sensors(
    installation: Installation,
    coordinator: CombinedEnergyReadingsCoordinator,
) -> Generator[CombinedEnergyReadingsSensor]:
    """Generate sensor entities from installed devices."""

    for description in SYSTEM_SENSOR_DESCRIPTIONS:
        sensor_type = SENSOR_TYPE_MAP.get(description.device_class, GenericSensor)
        yield sensor_type(
            installation=installation,
            device=SYSTEM_DEVICE,
            description=description,
            coordinator=coordinator,
        )

    # Generate sensors from descriptions for the combiner device
    for description in COMBINER_SENSOR_DESCRIPTIONS:
        sensor_type = SENSOR_TYPE_MAP.get(description.device_class, GenericSensor)
        yield sensor_type(
            installation=installation,
            device=COMBINER_DEVICE,
            description=description,
            coordinator=coordinator,
        )

    for device in installation.devices:
        descriptions = SENSOR_DESCRIPTIONS.get(device.device_type, [])
        # Generate sensors from descriptions for the current device type
        for description in descriptions:
            sensor_type = SENSOR_TYPE_MAP.get(description.device_class, GenericSensor)
            yield sensor_type(
                installation=installation,
                device=device,
                description=description,
                coordinator=coordinator,
            )


class CombinedEnergyReadingsSensor(
    CoordinatorEntity[CombinedEnergyReadingsCoordinator], SensorEntity
):
    """Representation of a Combined Energy bridge reading sensor."""

    entity_description: CombinedEnergySensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        installation: Installation,
        device: Device,
        description: SensorEntityDescription,
        coordinator: CombinedEnergyReadingsCoordinator,
    ) -> None:
        """Initialise Readings Sensor."""
        super().__init__(coordinator)

        self.device_id = device.id if device.id != 0 else None
        self.device_type = device.device_type
        self.entity_description = description

        identifier = f"install_{installation.id}-device_{device.id}"
        self._attr_unique_id = f"{identifier}-{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identifier)},
            manufacturer=device.manufacturer,
            serial_number=device.serial_number,
            model=device.model_name,
            name=device.name,
        )

    @property
    def readings_device(self) -> ReadingsDevices | None:
        """Get readings for specific device."""
        if self.coordinator.data is None:
            return None
        if self.device_id is not None:
            for device in self.coordinator.data.devices:
                if getattr(device, "device_id", None) == self.device_id:
                    return device
            return None
        for device in self.coordinator.data.devices:
            if getattr(device, "device_type", None) == self.device_type:
                return device
        return None

    @property
    def _raw_value(self) -> Any:
        """Get raw reading value from device readings."""
        if readings_device := self.readings_device:
            return getattr(readings_device, self.entity_description.key)
        return None

    @property
    def available(self) -> bool:
        """Indicate if the entity is available."""
        return self._raw_value is not None

    @property
    def native_value(self) -> int | float | str | datetime | None:
        """Return the state of the sensor."""
        return self._raw_value


class GenericSensor(CombinedEnergyReadingsSensor):
    """Sensor for generic scalar readings."""


class EnergySensor(CombinedEnergyReadingsSensor):
    """Sensor for energy readings."""


class PowerSensor(CombinedEnergyReadingsSensor):
    """Sensor for power readings."""


class PowerFactorSensor(CombinedEnergyReadingsSensor):
    """Sensor for power factor readings."""


class WaterVolumeSensor(CombinedEnergyReadingsSensor):
    """Sensor for water volume readings."""


# Map of common device classes to specific sensor types
SENSOR_TYPE_MAP: dict[
    SensorDeviceClass | str | None, type[CombinedEnergyReadingsSensor]
] = {
    SensorDeviceClass.ENERGY: EnergySensor,
    SensorDeviceClass.POWER: PowerSensor,
    SensorDeviceClass.WATER: WaterVolumeSensor,
    SensorDeviceClass.POWER_FACTOR: PowerFactorSensor,
}
