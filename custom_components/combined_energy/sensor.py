"""Sensors and factory for enumerating devices from the Combined Energy API."""

from __future__ import annotations

from collections.abc import Generator, Sequence
from datetime import datetime
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo

from custom_components.combined_energy.client import Client
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

from .const import CURRENCY_AUD, DATA_API_CLIENT, DATA_COORDINATOR, DOMAIN, LOGGER
from .coordinator import (
    CombinedEnergyCoordinator,
    CombinedEnergyReadingsCoordinator,
    CombinedEnergyTariffDetailsCoordinator,
)


class Aggregation(Enum):
    """Aggregation type for Combined Energy sensors."""

    SUM = "sum"
    LATEST = "latest"


class CombinedEnergySensorDescription(SensorEntityDescription, frozen_or_thawed=True):
    """Describes Combined Energy sensor entity."""

    aggregation: Aggregation = Aggregation.LATEST


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
        aggregation=Aggregation.SUM,
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
        aggregation=Aggregation.SUM,
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
        aggregation=Aggregation.SUM,
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
            aggregation=Aggregation.SUM,
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
            aggregation=Aggregation.SUM,
        ),
        CombinedEnergySensorDescription(
            key="energy_consumed",
            translation_key="grid_meter_energy_consumed",
            icon="mdi:transmission-tower-import",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
            aggregation=Aggregation.SUM,
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
            aggregation=Aggregation.SUM,
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
            aggregation=Aggregation.SUM,
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

COMBINER_SENSOR_DESCRIPTIONS = [
    *SENSOR_DESCRIPTIONS_GENERIC_CONSUMER,
    CombinedEnergySensorDescription(
        key="energy_supplied",
        translation_key="combiner_energy_supplied",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        aggregation=Aggregation.SUM,
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
        aggregation=Aggregation.SUM,
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
        aggregation=Aggregation.SUM,
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
        aggregation=Aggregation.SUM,
    ),
    CombinedEnergySensorDescription(
        key="energy_consumed_other",
        translation_key="combiner_energy_consumed_other",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        aggregation=Aggregation.SUM,
    ),
    CombinedEnergySensorDescription(
        key="energy_consumed_other_solar",
        translation_key="combiner_energy_consumed_other_solar",
        icon="mdi:solar-power",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        aggregation=Aggregation.SUM,
    ),
    CombinedEnergySensorDescription(
        key="energy_consumed_other_battery",
        translation_key="combiner_energy_consumed_other_battery",
        icon="mdi:home-battery",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        aggregation=Aggregation.SUM,
    ),
    CombinedEnergySensorDescription(
        key="energy_consumed_other_grid",
        translation_key="combiner_energy_consumed_other_grid",
        icon="mdi:transmission-tower",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        aggregation=Aggregation.SUM,
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
        aggregation=Aggregation.SUM,
    ),
]

# Combiner isn't a real device but it's included in the readings with all the other devices
COMBINER_DEVICE = Device(
    deviceId=0,
    deviceType="COMBINER",
    refName="",
    displayName="Combiner",
    deviceManufacturer=None,
    deviceModelName=None,
    deviceSerialNumber=None,
    supplierDevice=False,
    storageDevice=False,
    consumerDevice=False,
    maxPowerSupply=None,
    maxPowerConsumption=None,
    iconOverride=None,
    orderOverride=None,
    status="",
    category="",
)

SENSOR_DESCRIPTIONS_TARIFF_DETAILS = [
    CombinedEnergySensorDescription(
        key="daily_fee",
        translation_key="tariff_details_daily_fee",
        icon="mdi:cash-sync",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=f"{CURRENCY_AUD}/{UnitOfEnergy.KILO_WATT_HOUR}",
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
    ),
    CombinedEnergySensorDescription(
        key="feed_in_cost",
        translation_key="tariff_details_feed_in_cost",
        icon="mdi:cash-plus",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=f"{CURRENCY_AUD}/{UnitOfEnergy.KILO_WATT_HOUR}",
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""

    client: Client = hass.data[DOMAIN][entry.entry_id][DATA_API_CLIENT]
    coordinator: CombinedEnergyCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]
    installation = await client.installation()

    LOGGER.info("Setting up Combined Energy sensors")
    async_add_entities(_generate_sensors(installation, coordinator))


def _generate_sensors(
    installation: Installation,
    coordinator: CombinedEnergyCoordinator,
) -> Generator[SensorEntity]:
    """Generate sensor entities from installed devices."""
    yield from _generate_readings_sensors(installation, coordinator.readings)
    yield from _generate_tariff_details_sensors(
        installation, coordinator.tariff_details
    )


def _generate_readings_sensors(
    installation: Installation,
    coordinator: CombinedEnergyTariffDetailsCoordinator,
) -> Generator[CombinedEnergyReadingsSensor]:
    """Generate sensor entities from installed devices."""

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


def _generate_tariff_details_sensors(
    installation: Installation,
    coordinator: CombinedEnergyTariffDetailsCoordinator,
) -> Generator[CombinedEnergyTariffSensor]:
    """Generate sensor entities from tariff details."""
    if coordinator.data is not None:
        yield PriceSensor(installation=installation, coordinator=coordinator)
    for description in SENSOR_DESCRIPTIONS_TARIFF_DETAILS:
        yield CombinedEnergyTariffSensor(
            installation=installation, coordinator=coordinator, description=description
        )


class CombinedEnergyReadingsSensor(
    CoordinatorEntity[CombinedEnergyReadingsCoordinator], SensorEntity
):
    """Representation of a Combined Energy API reading energy sensor."""

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
        for device in self.coordinator.data.devices:
            if (
                device.device_type == self.device_type
                and device.device_id == self.device_id
            ):
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
        if (readings_device := self.readings_device) and hasattr(
            readings_device, "operation_status"
        ):
            return readings_device.operation_status[-1] == "CONNECTED_ACTIVE"
        return self._raw_value is not None

    def _to_native_value(self, raw_value: Any) -> float | None:
        """Convert non-none raw value into usable sensor value."""
        return float(raw_value)

    def _aggregate_sum(self, raw_values: Sequence[Any]) -> float | None:
        """Sum all non-none raw values."""
        if all(rv is None for rv in raw_values):
            return None
        return sum(self._to_native_value(rv) for rv in raw_values if rv is not None)

    def _aggregate_latest(self, raw_values: Sequence[Any]) -> float | None:
        """Return the last non-none raw value."""
        latest = raw_values[-1]
        return self._to_native_value(latest) if latest is not None else None

    @property
    def last_reset(self) -> datetime | None:
        """Last time the data was reset."""
        if self.entity_description.state_class != SensorStateClass.TOTAL:
            return None
        readings_device = self.readings_device
        if readings_device is None:
            return None
        if self.entity_description.aggregation == Aggregation.SUM:
            return readings_device.range_start
        return readings_device.range_end

    @property
    def native_value(self) -> int | float | None:
        """Return the state of the sensor."""
        raw_value = self._raw_value
        if raw_value is None:
            return None
        if isinstance(raw_value, Sequence):
            match self.entity_description.aggregation:
                case Aggregation.SUM:
                    return self._aggregate_sum(raw_value)
                case Aggregation.LATEST:
                    return self._aggregate_latest(raw_value)
        return self._to_native_value(raw_value)


class GenericSensor(CombinedEnergyReadingsSensor):
    """Sensor that returns the last value of a sequence of readings."""


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


class CombinedEnergyTariffSensor(
    CoordinatorEntity[CombinedEnergyTariffDetailsCoordinator], SensorEntity
):
    """Representation of a Combined Energy API tariff sensor."""

    entity_description: SensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        installation: Installation,
        coordinator: CombinedEnergyReadingsCoordinator,
        description: CombinedEnergySensorDescription,
    ) -> None:
        """Initialise Tariff Sensor."""
        super().__init__(coordinator)
        identifier = f"install_{installation.id}-tariff-details"
        self.entity_description = description
        self._attr_unique_id = f"{identifier}-{description.key}"
        if data := self.coordinator.data:
            self._attr_device_info = DeviceInfo(
                identifiers={
                    (DOMAIN, identifier),
                    (DOMAIN, f"tariff_plan_{data.tariff.plan_id}"),
                },
                manufacturer=data.tariff.retailer_name,
                name=data.tariff.plan_name,
                serial_number=str(data.tariff.plan_id),
                created_at=data.tariff.as_at.isoformat(),
                modified_at=data.tariff.updated.isoformat(),
            )
        else:
            self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, identifier)})

    @property
    def native_value(self) -> float | None:
        """Return the value reported by the sensor."""
        if data := self.coordinator.data:
            return getattr(data.tariff, self.entity_description.key) / 100.0
        return None


class PriceSensor(CombinedEnergyTariffSensor):
    """Sensor for group price readings."""

    def __init__(
        self,
        installation: Installation,
        coordinator: CombinedEnergyTariffDetailsCoordinator,
    ) -> None:
        """Initialise Group Price Sensor."""
        super().__init__(
            installation=installation,
            coordinator=coordinator,
            description=SensorEntityDescription(
                key="cost",
                translation_key="tariff_details_cost",
                icon="mdi:cash-minus",
                state_class=SensorStateClass.TOTAL,
                native_unit_of_measurement=f"{CURRENCY_AUD}/{UnitOfEnergy.KILO_WATT_HOUR}",
                device_class=SensorDeviceClass.MONETARY,
                suggested_display_precision=2,
            ),
        )

    @property
    def native_value(self) -> float | None:
        """Return the value reported by the sensor."""
        if self.coordinator.data is None:
            return None
        tz = ZoneInfo(self.hass.config.time_zone)
        now = datetime.now(tz=tz)
        if (cost := self.coordinator.data.tariff.cost_at(now)) is not None:
            return cost / 100.0
        return None
