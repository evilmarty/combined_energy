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
    temperature: float | None = Field(default=None)


class SolarPvReading(CommonDeviceReadings):
    """Readings for the Solar PV device."""

    device_type: Literal["SolarPvReading"] = Field(alias="deviceType")
    operation_status: str | None = Field(default=None, alias="operationStatus")
    operation_message: str | None = Field(default=None, alias="operationMessage")

    energy_supplied: float | None = Field(default=None, alias="energySupplied")


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
    power_factor_a: float | None = Field(default=None, alias="powerFactorA")
    power_factor_b: float | None = Field(default=None, alias="powerFactorB")
    power_factor_c: float | None = Field(default=None, alias="powerFactorC")
    voltage_a: float | None = Field(default=None, alias="voltageA")
    voltage_b: float | None = Field(default=None, alias="voltageB")
    voltage_c: float | None = Field(default=None, alias="voltageC")


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


class WaterHeaterReading(GenericConsumerReading):
    """Readings for a Water heater device."""

    device_type: Literal["WaterHeaterReading"] = Field(alias="deviceType")

    available_energy: float | None = Field(alias="currentAmenityLitres")
    max_energy: float | None = Field(default=None, alias="maxAmenityLitres")
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
