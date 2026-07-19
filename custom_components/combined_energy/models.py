"""API Schema model."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from custom_components.combined_energy.mqtt_parser import parse_mqtt_readings_message


def now() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(tz=UTC)


class Login(BaseModel):
    """Response from Login."""

    status: str
    expire_minutes: int = Field(alias="expireMins")
    jwt: str
    created: datetime = Field(default_factory=now)

    @property
    def expires(self) -> datetime:
        """Calculate when this login expires."""
        offset = timedelta(minutes=self.expire_minutes)
        return self.created + offset

    @property
    def expired(self) -> bool:
        """Check if the login has expired."""
        return datetime.now(UTC) > self.expires


class LogSession(BaseModel):
    """Common attributes for most models."""

    status: str
    installation_id: int = Field(alias="installationId")
    archive_saved: bool = Field(alias="archiveSaved")


class User(BaseModel):
    """Individual user."""

    type: str
    id: int
    email: str
    mobile: str
    fullname: str
    dsa_ok: bool = Field(alias="dsaOk")
    show_introduction: None | str = Field(alias="showIntroduction")


class ConnectionStatus(BaseModel):
    """Connection Status of the monitor."""

    status: str
    installation_id: int = Field(alias="installationId")
    connected: bool
    since: datetime


class Device(BaseModel):
    """Details of a device."""

    id: int
    ref_name: str = Field(alias="refName")
    name: str
    device_type: str = Field(alias="type")
    manufacturer: None | str = None
    model_name: None | str = Field(default=None, alias="model")
    serial_number: None | str = Field(default=None, alias="serial")
    storage_device: bool = Field(
        default=False,
        alias="storage",
    )
    supplier_device: bool = Field(
        default=False,
        alias="supplier",
    )
    consumer_device: bool = Field(
        default=False,
        alias="consumer",
    )
    status: str
    max_power_consumption: None | int = Field(default=None, alias="maxPowerConsumption")
    category: str


class Installation(BaseModel):
    """Details of an installation."""

    id: int
    name: str
    status: str
    timezone: ZoneInfo
    address: str
    locality: str
    state: str
    postcode: str
    phase: int
    installed: datetime

    devices: list[Device]
    gateway_id: int = Field(alias="gwId")


class Customer(BaseModel):
    """Individual customer."""

    customer_id: int = Field(alias="customerId")
    phone: None | str = Field(default=None)
    email: str
    name: str
    primary: bool


class InstallationCustomers(BaseModel):
    """Response from customers."""

    status: str
    installation_id: int = Field(alias="installationId")
    customers: list[Customer]


class CommonDeviceReadings(BaseModel):
    """Readings for a particular device."""

    device_id: int | None = Field(default=None, alias="deviceId")
    period_end: int = Field(alias="periodEnd")
    period_end_str: str | None = Field(default=None, alias="periodEndStr")
    reading_count: int | None = Field(default=None, alias="readingCount")


class SystemReading(CommonDeviceReadings):
    """Readings for system-level status."""

    device_type: Literal["SystemReading"] = Field(alias="deviceType")
    connected_devices: int | None = Field(default=None, alias="connectedDevices")
    registered_devices: int | None = Field(default=None, alias="registeredDevices")
    dmg_id: int | None = Field(default=None, alias="dmgId")
    jvm_startup: int | None = Field(default=None, alias="jvmStartup")
    os_startup: int | None = Field(default=None, alias="osStartup")
    plugin_startup: int | None = Field(default=None, alias="pluginStartup")
    operation_status: str | None = Field(default=None, alias="operationStatus")
    operation_message: str | None = Field(default=None, alias="operationMessage")
    state: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None
    temperature: float | None = None


class CombinerReading(CommonDeviceReadings):
    """Readings for the Combiner device."""

    device_type: Literal["CombinerReading"] = Field(alias="deviceType")

    energy_supplied: float | None = Field(default=None, alias="energySuppliedTotal")
    energy_supplied_solar: float | None = Field(
        default=None, alias="energySuppliedSolar"
    )
    energy_supplied_battery: float | None = Field(
        default=None, alias="energySuppliedBattery"
    )
    energy_supplied_grid: float | None = Field(default=None, alias="energySuppliedGrid")
    energy_consumed: float | None = Field(default=None, alias="energyConsumedTotal")
    energy_consumed_solar: float | None = Field(
        default=None, alias="energyConsumedTotalSolar"
    )
    energy_consumed_battery: float | None = Field(
        default=None, alias="energyConsumedTotalBattery"
    )
    energy_consumed_grid: float | None = Field(
        default=None, alias="energyConsumedTotalGrid"
    )
    energy_correction: float | None = Field(default=None, alias="energyCorrection")
    energy_exported: float | None = Field(default=None, alias="energyExported")
    energy_exported_battery: float | None = Field(
        default=None, alias="energyExportedBattery"
    )
    energy_exported_grid: float | None = Field(default=None, alias="energyExportedGrid")
    energy_exported_solar: float | None = Field(
        default=None, alias="energyExportedSolar"
    )
    energy_stored: float | None = Field(default=None, alias="energyStored")
    energy_stored_battery: float | None = Field(
        default=None, alias="energyStoredBattery"
    )
    energy_stored_grid: float | None = Field(default=None, alias="energyStoredGrid")
    energy_stored_solar: float | None = Field(default=None, alias="energyStoredSolar")
    invalid_reason: str | None = Field(default=None, alias="invalidReason")
    meta: dict[str, Any] | None = None
    operation_message: str | None = Field(default=None, alias="operationMessage")
    operation_status: str | None = Field(default=None, alias="operationStatus")
    valid: bool | None = None


class SolarPvReading(CommonDeviceReadings):
    """Readings for the Solar PV device."""

    device_type: Literal["SolarPvReading"] = Field(alias="deviceType")
    operation_status: str | None = Field(default=None, alias="operationStatus")
    operation_message: str | None = Field(default=None, alias="operationMessage")

    energy_supplied: float | None = Field(default=None, alias="energySupplied")
    energy_supplied_consumed: float | None = Field(
        default=None, alias="energySuppliedConsumed"
    )
    energy_supplied_exported: float | None = Field(
        default=None, alias="energySuppliedExported"
    )
    energy_supplied_stored: float | None = Field(
        default=None, alias="energySuppliedStored"
    )
    max_power_production: float | None = Field(default=None, alias="maxPowerProduction")
    meta: dict[str, Any] | None = None
    power_avg: float | None = Field(default=None, alias="powerAvg")
    power_last: float | None = Field(default=None, alias="powerLast")
    power_max: float | None = Field(default=None, alias="powerMax")
    power_min: float | None = Field(default=None, alias="powerMin")
    power_reactive_avg: float | None = Field(default=None, alias="powerReactiveAvg")
    power_reactive_last: float | None = Field(default=None, alias="powerReactiveLast")
    power_reactive_max: float | None = Field(default=None, alias="powerReactiveMax")
    power_reactive_min: float | None = Field(default=None, alias="powerReactiveMin")
    requested_power: float | None = Field(default=None, alias="requestedPower")


class GridMeterReading(CommonDeviceReadings):
    """Readings for the Grid Meter device."""

    device_type: Literal["GridMeterReading"] = Field(alias="deviceType")
    operation_status: str | None = Field(default=None, alias="operationStatus")
    operation_message: str | None = Field(default=None, alias="operationMessage")

    energy_supplied: float | None = Field(default=None, alias="energySupplied")
    energy_consumed: float | None = Field(default=None, alias="energyConsumed")
    energy_consumed_solar: float | None = Field(
        default=None, alias="energyConsumedSolar"
    )
    energy_consumed_battery: float | None = Field(
        default=None, alias="energyConsumedBattery"
    )
    energy_consumed_grid: float | None = Field(default=None, alias="energyConsumedGrid")
    energy_nett: float | None = Field(default=None, alias="energyNett")
    energy_supplied_consumed: float | None = Field(
        default=None, alias="energySuppliedConsumed"
    )
    energy_supplied_exported: float | None = Field(
        default=None, alias="energySuppliedExported"
    )
    energy_supplied_stored: float | None = Field(
        default=None, alias="energySuppliedStored"
    )
    frequency_avg: float | None = Field(default=None, alias="frequencyAvg")
    frequency_max: float | None = Field(default=None, alias="frequencyMax")
    frequency_min: float | None = Field(default=None, alias="frequencyMin")
    max_power_production: float | None = Field(default=None, alias="maxPowerProduction")
    meta: dict[str, Any] | None = None
    power_a_avg: float | None = Field(default=None, alias="powerAAvg")
    power_a_last: float | None = Field(default=None, alias="powerALast")
    power_a_max: float | None = Field(default=None, alias="powerAMax")
    power_a_min: float | None = Field(default=None, alias="powerAMin")
    power_avg: float | None = Field(default=None, alias="powerAvg")
    power_b_avg: float | None = Field(default=None, alias="powerBAvg")
    power_b_last: float | None = Field(default=None, alias="powerBLast")
    power_b_max: float | None = Field(default=None, alias="powerBMax")
    power_b_min: float | None = Field(default=None, alias="powerBMin")
    power_c_avg: float | None = Field(default=None, alias="powerCAvg")
    power_c_last: float | None = Field(default=None, alias="powerCLast")
    power_c_max: float | None = Field(default=None, alias="powerCMax")
    power_c_min: float | None = Field(default=None, alias="powerCMin")
    power_factor_a: float | None = Field(default=None, alias="powerFactorA")
    power_factor_b: float | None = Field(default=None, alias="powerFactorB")
    power_factor_c: float | None = Field(default=None, alias="powerFactorC")
    power_last: float | None = Field(default=None, alias="powerLast")
    power_max: float | None = Field(default=None, alias="powerMax")
    power_min: float | None = Field(default=None, alias="powerMin")
    power_reactive_a_avg: float | None = Field(default=None, alias="powerReactiveAAvg")
    power_reactive_a_last: float | None = Field(
        default=None, alias="powerReactiveALast"
    )
    power_reactive_a_max: float | None = Field(default=None, alias="powerReactiveAMax")
    power_reactive_a_min: float | None = Field(default=None, alias="powerReactiveAMin")
    power_reactive_avg: float | None = Field(default=None, alias="powerReactiveAvg")
    power_reactive_b_avg: float | None = Field(default=None, alias="powerReactiveBAvg")
    power_reactive_b_last: float | None = Field(
        default=None, alias="powerReactiveBLast"
    )
    power_reactive_b_max: float | None = Field(default=None, alias="powerReactiveBMax")
    power_reactive_b_min: float | None = Field(default=None, alias="powerReactiveBMin")
    power_reactive_c_avg: float | None = Field(default=None, alias="powerReactiveCAvg")
    power_reactive_c_last: float | None = Field(
        default=None, alias="powerReactiveCLast"
    )
    power_reactive_c_max: float | None = Field(default=None, alias="powerReactiveCMax")
    power_reactive_c_min: float | None = Field(default=None, alias="powerReactiveCMin")
    power_reactive_last: float | None = Field(default=None, alias="powerReactiveLast")
    power_reactive_max: float | None = Field(default=None, alias="powerReactiveMax")
    power_reactive_min: float | None = Field(default=None, alias="powerReactiveMin")
    voltage_a: float | None = Field(default=None, alias="voltageA")
    voltage_a_avg: float | None = Field(default=None, alias="voltageAAvg")
    voltage_a_last: float | None = Field(default=None, alias="voltageALast")
    voltage_a_max: float | None = Field(default=None, alias="voltageAMax")
    voltage_a_min: float | None = Field(default=None, alias="voltageAMin")
    voltage_b: float | None = Field(default=None, alias="voltageB")
    voltage_b_avg: float | None = Field(default=None, alias="voltageBAvg")
    voltage_b_last: float | None = Field(default=None, alias="voltageBLast")
    voltage_b_max: float | None = Field(default=None, alias="voltageBMax")
    voltage_b_min: float | None = Field(default=None, alias="voltageBMin")
    voltage_c: float | None = Field(default=None, alias="voltageC")
    voltage_c_avg: float | None = Field(default=None, alias="voltageCAvg")
    voltage_c_last: float | None = Field(default=None, alias="voltageCLast")
    voltage_c_max: float | None = Field(default=None, alias="voltageCMax")
    voltage_c_min: float | None = Field(default=None, alias="voltageCMin")


class GenericConsumerReading(CommonDeviceReadings):
    """Readings for a Generic consumer device."""

    device_type: Literal["GenericConsumerReading"] = Field(alias="deviceType")
    operation_status: str | None = Field(default=None, alias="operationStatus")
    operation_message: str | None = Field(default=None, alias="operationMessage")

    energy_consumed: float | None = Field(default=None, alias="energyConsumed")
    energy_consumed_solar: float | None = Field(
        default=None, alias="energyConsumedSolar"
    )
    energy_consumed_battery: float | None = Field(
        default=None, alias="energyConsumedBattery"
    )
    energy_consumed_grid: float | None = Field(default=None, alias="energyConsumedGrid")
    meta: dict[str, Any] | None = None
    power_avg: float | None = Field(default=None, alias="powerAvg")
    power_last: float | None = Field(default=None, alias="powerLast")
    power_max: float | None = Field(default=None, alias="powerMax")
    power_min: float | None = Field(default=None, alias="powerMin")
    power_reactive_avg: float | None = Field(default=None, alias="powerReactiveAvg")
    power_reactive_last: float | None = Field(default=None, alias="powerReactiveLast")
    power_reactive_max: float | None = Field(default=None, alias="powerReactiveMax")
    power_reactive_min: float | None = Field(default=None, alias="powerReactiveMin")


class WaterHeaterReading(GenericConsumerReading):
    """Readings for a Water heater device."""

    device_type: Literal["WaterHeaterReading"] = Field(alias="deviceType")

    amenity_water_temp: float | None = Field(default=None, alias="amenityWaterTemp")
    available_energy: float | None = Field(alias="currentAmenityLitres")
    cumulative_charge_energy: float | None = Field(
        default=None, alias="cumChargeEnergy"
    )
    cumulative_discharge_seconds: int | None = Field(
        default=None, alias="cumDischargeSecs"
    )
    estimated_flow_rate: float | None = Field(default=None, alias="estFlowRate")
    external_inlet_temperature: float | None = Field(default=None, alias="extInletTemp")
    external_outlet_temperature: float | None = Field(
        default=None, alias="extOutletTemp"
    )
    inlet_temperature: float | None = Field(default=None, alias="inletTemp")
    max_energy: float | None = Field(default=None, alias="maxAmenityLitres")
    max_energy_estimate: float | None = Field(default=None, alias="maxEnergy")
    max_power_consumption: float | None = Field(
        default=None, alias="maxPowerConsumption"
    )
    min_amenity_litres: float | None = Field(default=None, alias="minAmenityLitres")
    optimal_amenity_litres: float | None = Field(default=None, alias="optAmenityLitres")
    state_of_charge: float | None = Field(default=None, alias="sOC")
    state_of_energy: float | None = Field(default=None, alias="sOE")
    status: dict[str, Any] | None = None
    temp_sensor1: float | None = Field(default=None, alias="s1")
    temp_sensor2: float | None = Field(default=None, alias="s2")
    temp_sensor3: float | None = Field(default=None, alias="s3")
    temp_sensor4: float | None = Field(default=None, alias="s4")
    temp_sensor5: float | None = Field(default=None, alias="s5")
    temp_sensor6: float | None = Field(default=None, alias="s6")

    @property
    def available_percentage(self) -> float | None:
        """Get the available percentage of the water heater."""
        if self.available_energy is None or self.max_energy is None:
            return None
        if self.max_energy <= 0:
            return 0
        return (self.available_energy / self.max_energy) * 100


class EnergyBalanceReading(GenericConsumerReading):
    """Readings for the Energy Balance device."""

    device_type: Literal["EnergyBalanceReading"] = Field(alias="deviceType")


class DeviceReadingsUnknown(BaseModel):
    """Readings for an unknown device type."""

    device_type: str = Field(alias="deviceType")


ReadingsDevices = Annotated[
    Annotated[
        (
            SystemReading
            | CombinerReading
            | SolarPvReading
            | GridMeterReading
            | GenericConsumerReading
            | WaterHeaterReading
            | EnergyBalanceReading
        ),
        Field(discriminator="device_type"),
    ]
    | DeviceReadingsUnknown,
    Field(union_mode="left_to_right"),
]


class Readings(BaseModel):
    """Reading history data."""

    period_duration_secs: int = Field(alias="periodDurationSecs")
    period_end: datetime = Field(alias="periodEnd")

    devices: list[ReadingsDevices]

    @classmethod
    def from_mqtt_message(cls, payload: bytes | str | dict[str, Any]) -> "Readings":
        """Parse MQTT payload and convert it into the Readings model."""
        message = (
            payload
            if isinstance(payload, dict)
            else parse_mqtt_readings_message(payload)
        )
        range_end = datetime.fromtimestamp(int(message["periodEnd"]), tz=UTC)
        period_duration_secs = int(message["periodDurationSecs"])
        devices: list[dict[str, Any]] = []
        for record_type, rows in message["records"].items():
            devices.extend(
                {
                    "deviceType": record_type,
                    **row,
                }
                for row in rows
            )

        return cls.model_validate(
            {
                "periodDurationSecs": period_duration_secs,
                "periodEnd": range_end,
                "devices": devices,
            }
        )
