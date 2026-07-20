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
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DATA_BRIDGE_CLIENT,
    DATA_COORDINATOR,
    DOMAIN,
    INSTALLATION_DEVICE_TYPE_COMBINER,
    LOGGER,
)
from .coordinator import CombinedEnergyReadingsCoordinator


class CombinedEnergySensorDescription(SensorEntityDescription, frozen_or_thawed=True):
    """Describes Combined Energy sensor entity."""

    absolute: bool = False


# Common sensors for all consumer devices
SENSOR_DESCRIPTIONS_GENERIC_CONSUMER = [
    CombinedEnergySensorDescription(
        key="energy_consumed",
        translation_key="energy_consumed",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        absolute=True,
    ),
    CombinedEnergySensorDescription(
        key="energy_consumed_solar",
        translation_key="energy_consumed_solar",
        icon="mdi:solar-power",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        absolute=True,
    ),
    CombinedEnergySensorDescription(
        key="energy_consumed_battery",
        translation_key="energy_consumed_battery",
        icon="mdi:home-battery",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        absolute=True,
    ),
    CombinedEnergySensorDescription(
        key="energy_consumed_grid",
        translation_key="energy_consumed_grid",
        icon="mdi:transmission-tower",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        absolute=True,
    ),
    CombinedEnergySensorDescription(
        key="power_avg",
        translation_key="power_avg",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        absolute=True,
    ),
    CombinedEnergySensorDescription(
        key="power_last",
        translation_key="power_last",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        absolute=True,
    ),
    CombinedEnergySensorDescription(
        key="power_max",
        translation_key="power_max",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        absolute=True,
    ),
    CombinedEnergySensorDescription(
        key="power_min",
        translation_key="power_min",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        absolute=True,
    ),
    CombinedEnergySensorDescription(
        key="power_reactive_avg",
        translation_key="power_reactive_avg",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="var",
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    CombinedEnergySensorDescription(
        key="power_reactive_last",
        translation_key="power_reactive_last",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="var",
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    CombinedEnergySensorDescription(
        key="power_reactive_max",
        translation_key="power_reactive_max",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="var",
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    CombinedEnergySensorDescription(
        key="power_reactive_min",
        translation_key="power_reactive_min",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="var",
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
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
        ),
        CombinedEnergySensorDescription(
            key="energy_supplied_consumed",
            translation_key="solar_pv_energy_supplied_consumed",
            icon="mdi:home-lightning-bolt",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="energy_supplied_exported",
            translation_key="solar_pv_energy_supplied_exported",
            icon="mdi:transmission-tower-export",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="energy_supplied_stored",
            translation_key="solar_pv_energy_supplied_stored",
            icon="mdi:home-battery",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="max_power_production",
            translation_key="solar_pv_max_power_production",
            icon="mdi:solar-power-variant",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_avg",
            translation_key="solar_pv_power_avg",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_last",
            translation_key="solar_pv_power_last",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_max",
            translation_key="solar_pv_power_max",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_min",
            translation_key="solar_pv_power_min",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_reactive_avg",
            translation_key="solar_pv_power_reactive_avg",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="var",
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_reactive_last",
            translation_key="solar_pv_power_reactive_last",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="var",
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_reactive_max",
            translation_key="solar_pv_power_reactive_max",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="var",
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_reactive_min",
            translation_key="solar_pv_power_reactive_min",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="var",
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="requested_power",
            translation_key="solar_pv_requested_power",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
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
            key="amenity_water_temp",
            translation_key="water_heater_amenity_water_temp",
            icon="mdi:thermometer-water",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="cumulative_charge_energy",
            translation_key="water_heater_cumulative_charge_energy",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="cumulative_discharge_seconds",
            translation_key="water_heater_cumulative_discharge_seconds",
            state_class=SensorStateClass.TOTAL_INCREASING,
            native_unit_of_measurement="s",
            suggested_display_precision=0,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="estimated_flow_rate",
            translation_key="water_heater_estimated_flow_rate",
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="external_inlet_temperature",
            translation_key="water_heater_external_inlet_temperature",
            icon="mdi:thermometer-water",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="external_outlet_temperature",
            translation_key="water_heater_external_outlet_temperature",
            icon="mdi:thermometer-water",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="inlet_temperature",
            translation_key="water_heater_inlet_temperature",
            icon="mdi:thermometer-water",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="max_energy_estimate",
            translation_key="water_heater_max_energy_estimate",
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="max_power_consumption",
            translation_key="water_heater_max_power_consumption",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="min_amenity_litres",
            translation_key="water_heater_min_amenity_litres",
            native_unit_of_measurement=UnitOfVolume.LITERS,
            device_class=SensorDeviceClass.WATER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="optimal_amenity_litres",
            translation_key="water_heater_optimal_amenity_litres",
            native_unit_of_measurement=UnitOfVolume.LITERS,
            device_class=SensorDeviceClass.WATER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="state_of_charge",
            translation_key="water_heater_state_of_charge",
            native_unit_of_measurement=PERCENTAGE,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="state_of_energy",
            translation_key="water_heater_state_of_energy",
            native_unit_of_measurement=PERCENTAGE,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
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
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
        ),
        CombinedEnergySensorDescription(
            key="energy_consumed",
            translation_key="grid_meter_energy_consumed",
            icon="mdi:transmission-tower-import",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
            absolute=True,
        ),
        CombinedEnergySensorDescription(
            key="energy_consumed_solar",
            translation_key="grid_meter_energy_consumed_solar",
            icon="mdi:solar-power",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
            absolute=True,
        ),
        CombinedEnergySensorDescription(
            key="energy_consumed_battery",
            translation_key="grid_meter_energy_consumed_battery",
            icon="mdi:home-battery",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
            absolute=True,
        ),
        CombinedEnergySensorDescription(
            key="energy_consumed_grid",
            translation_key="grid_meter_energy_consumed_grid",
            icon="mdi:transmission-tower",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
            absolute=True,
        ),
        CombinedEnergySensorDescription(
            key="energy_nett",
            translation_key="grid_meter_energy_nett",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="energy_supplied_consumed",
            translation_key="grid_meter_energy_supplied_consumed",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="energy_supplied_exported",
            translation_key="grid_meter_energy_supplied_exported",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="energy_supplied_stored",
            translation_key="grid_meter_energy_supplied_stored",
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="frequency_avg",
            translation_key="grid_meter_frequency_avg",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfFrequency.HERTZ,
            device_class=SensorDeviceClass.FREQUENCY,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="frequency_max",
            translation_key="grid_meter_frequency_max",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfFrequency.HERTZ,
            device_class=SensorDeviceClass.FREQUENCY,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="frequency_min",
            translation_key="grid_meter_frequency_min",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfFrequency.HERTZ,
            device_class=SensorDeviceClass.FREQUENCY,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="max_power_production",
            translation_key="grid_meter_max_power_production",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_avg",
            translation_key="grid_meter_power_avg",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_last",
            translation_key="grid_meter_power_last",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_max",
            translation_key="grid_meter_power_max",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_min",
            translation_key="grid_meter_power_min",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_a_avg",
            translation_key="grid_meter_power_a_avg",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_a_last",
            translation_key="grid_meter_power_a_last",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_a_max",
            translation_key="grid_meter_power_a_max",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_a_min",
            translation_key="grid_meter_power_a_min",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_b_avg",
            translation_key="grid_meter_power_b_avg",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_b_last",
            translation_key="grid_meter_power_b_last",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_b_max",
            translation_key="grid_meter_power_b_max",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_b_min",
            translation_key="grid_meter_power_b_min",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_c_avg",
            translation_key="grid_meter_power_c_avg",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_c_last",
            translation_key="grid_meter_power_c_last",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_c_max",
            translation_key="grid_meter_power_c_max",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_c_min",
            translation_key="grid_meter_power_c_min",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_reactive_avg",
            translation_key="grid_meter_power_reactive_avg",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="var",
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_reactive_last",
            translation_key="grid_meter_power_reactive_last",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="var",
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_reactive_max",
            translation_key="grid_meter_power_reactive_max",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="var",
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_reactive_min",
            translation_key="grid_meter_power_reactive_min",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="var",
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_reactive_a_avg",
            translation_key="grid_meter_power_reactive_a_avg",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="var",
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_reactive_a_last",
            translation_key="grid_meter_power_reactive_a_last",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="var",
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_reactive_a_max",
            translation_key="grid_meter_power_reactive_a_max",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="var",
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_reactive_a_min",
            translation_key="grid_meter_power_reactive_a_min",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="var",
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_reactive_b_avg",
            translation_key="grid_meter_power_reactive_b_avg",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="var",
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_reactive_b_last",
            translation_key="grid_meter_power_reactive_b_last",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="var",
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_reactive_b_max",
            translation_key="grid_meter_power_reactive_b_max",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="var",
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_reactive_b_min",
            translation_key="grid_meter_power_reactive_b_min",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="var",
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_reactive_c_avg",
            translation_key="grid_meter_power_reactive_c_avg",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="var",
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_reactive_c_last",
            translation_key="grid_meter_power_reactive_c_last",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="var",
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_reactive_c_max",
            translation_key="grid_meter_power_reactive_c_max",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="var",
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="power_reactive_c_min",
            translation_key="grid_meter_power_reactive_c_min",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="var",
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
            key="voltage_a_avg",
            translation_key="grid_meter_voltage_a_avg",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            suggested_display_precision=2,
            device_class=SensorDeviceClass.VOLTAGE,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="voltage_a_last",
            translation_key="grid_meter_voltage_a_last",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            suggested_display_precision=2,
            device_class=SensorDeviceClass.VOLTAGE,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="voltage_a_max",
            translation_key="grid_meter_voltage_a_max",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            suggested_display_precision=2,
            device_class=SensorDeviceClass.VOLTAGE,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="voltage_a_min",
            translation_key="grid_meter_voltage_a_min",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            suggested_display_precision=2,
            device_class=SensorDeviceClass.VOLTAGE,
            entity_registry_enabled_default=False,
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
            key="voltage_b_avg",
            translation_key="grid_meter_voltage_b_avg",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="voltage_b_last",
            translation_key="grid_meter_voltage_b_last",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="voltage_b_max",
            translation_key="grid_meter_voltage_b_max",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="voltage_b_min",
            translation_key="grid_meter_voltage_b_min",
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
        CombinedEnergySensorDescription(
            key="voltage_c_avg",
            translation_key="grid_meter_voltage_c_avg",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="voltage_c_last",
            translation_key="grid_meter_voltage_c_last",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="voltage_c_max",
            translation_key="grid_meter_voltage_c_max",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
        CombinedEnergySensorDescription(
            key="voltage_c_min",
            translation_key="grid_meter_voltage_c_min",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            suggested_display_precision=2,
            entity_registry_enabled_default=False,
        ),
    ],
    "GATEWAY": [
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
            device_class=SensorDeviceClass.TIMESTAMP,
        ),
        CombinedEnergySensorDescription(
            key="os_startup",
            translation_key="system_os_startup",
            device_class=SensorDeviceClass.TIMESTAMP,
        ),
        CombinedEnergySensorDescription(
            key="plugin_startup",
            translation_key="system_plugin_startup",
            device_class=SensorDeviceClass.TIMESTAMP,
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
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
    ),
    CombinedEnergySensorDescription(
        key="energy_supplied_solar",
        translation_key="combiner_energy_supplied_solar",
        icon="mdi:solar-power",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    CombinedEnergySensorDescription(
        key="energy_supplied_battery",
        translation_key="combiner_energy_supplied_battery",
        icon="mdi:home-battery",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    CombinedEnergySensorDescription(
        key="energy_supplied_grid",
        translation_key="combiner_energy_supplied_grid",
        icon="mdi:transmission-tower",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    CombinedEnergySensorDescription(
        key="energy_correction",
        translation_key="combiner_energy_correction",
        icon="mdi:transmission-tower",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    CombinedEnergySensorDescription(
        key="energy_exported",
        translation_key="combiner_energy_exported",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        absolute=True,
    ),
    CombinedEnergySensorDescription(
        key="energy_exported_solar",
        translation_key="combiner_energy_exported_solar",
        icon="mdi:solar-power",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        absolute=True,
    ),
    CombinedEnergySensorDescription(
        key="energy_exported_battery",
        translation_key="combiner_energy_exported_battery",
        icon="mdi:home-battery",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        absolute=True,
    ),
    CombinedEnergySensorDescription(
        key="energy_exported_grid",
        translation_key="combiner_energy_exported_grid",
        icon="mdi:transmission-tower",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        absolute=True,
    ),
    CombinedEnergySensorDescription(
        key="energy_stored",
        translation_key="combiner_energy_stored",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    CombinedEnergySensorDescription(
        key="energy_stored_solar",
        translation_key="combiner_energy_stored_solar",
        icon="mdi:solar-power",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    CombinedEnergySensorDescription(
        key="energy_stored_battery",
        translation_key="combiner_energy_stored_battery",
        icon="mdi:home-battery",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    CombinedEnergySensorDescription(
        key="energy_stored_grid",
        translation_key="combiner_energy_stored_grid",
        icon="mdi:transmission-tower",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
]

# Combiner isn't a real device but it's included in the readings with all the other devices
COMBINER_DEVICE = Device(
    id=0,
    type=INSTALLATION_DEVICE_TYPE_COMBINER,
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


def _sensor_unique_id(installation_id: int, device_id: int, key: str) -> str:
    """Build sensor unique id."""
    return f"install_{installation_id}-device_{device_id}-{key}"


def _expected_sensor_unique_ids(installation: Installation) -> set[str]:
    """Build all expected sensor unique ids for an installation."""
    expected = {
        _sensor_unique_id(installation.id, COMBINER_DEVICE.id, description.key)
        for description in COMBINER_SENSOR_DESCRIPTIONS
    }
    for device in installation.devices:
        for description in SENSOR_DESCRIPTIONS.get(device.device_type, []):
            expected.add(_sensor_unique_id(installation.id, device.id, description.key))
    return expected


def cleanup_stale_sensor_entities(
    hass: HomeAssistant, entry: ConfigEntry, installation: Installation
) -> None:
    """Remove stale sensor entities no longer produced after reconfigure."""
    expected = _expected_sensor_unique_ids(installation)
    unique_id_prefix = f"install_{installation.id}-"
    registry = er.async_get(hass)

    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if (
            entity.unique_id.startswith(unique_id_prefix)
            and entity.unique_id not in expected
        ):
            LOGGER.debug(
                "Removing stale entity during reconfigure %s (%s)",
                entity.entity_id,
                entity.unique_id,
            )
            registry.async_remove(entity.entity_id)


def _generate_readings_sensors(
    installation: Installation,
    coordinator: CombinedEnergyReadingsCoordinator,
) -> Generator[CombinedEnergyReadingsSensor]:
    """Generate sensor entities from installed devices."""

    # Generate sensors from descriptions for the combiner device
    for description in COMBINER_SENSOR_DESCRIPTIONS:
        yield CombinedEnergyReadingsSensor(
            installation=installation,
            device=COMBINER_DEVICE,
            description=description,
            coordinator=coordinator,
        )

    for device in installation.devices:
        descriptions = SENSOR_DESCRIPTIONS.get(device.device_type, [])
        # Generate sensors from descriptions for the current device type
        for description in descriptions:
            yield CombinedEnergyReadingsSensor(
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
        self._installation_timezone = installation.timezone
        self.entity_description = description

        identifier = f"install_{installation.id}-device_{device.id}"
        self._attr_unique_id = f"{identifier}-{description.key}"
        connections = None
        if (
            device.connection_details is not None
            and device.connection_details.connection is not None
            and device.connection_details.connection.mac is not None
        ):
            connections = {
                (CONNECTION_NETWORK_MAC, device.connection_details.connection.mac)
            }
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identifier)},
            connections=connections,
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
                getattr(device, "installation_device_type", None) == self.device_type
                and getattr(device, "device_id", None) == self.device_id
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
        return self._raw_value is not None

    @property
    def native_value(self) -> int | float | str | datetime | None:
        """Return the state of the sensor."""
        value = self._raw_value
        if (
            self.entity_description.device_class == SensorDeviceClass.TIMESTAMP
            and isinstance(value, int | float)
        ):
            return datetime.fromtimestamp(value, self._installation_timezone)
        if self.entity_description.absolute and isinstance(value, int | float):
            return abs(value)
        return value
