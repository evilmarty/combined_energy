"""API Schema model."""

from datetime import UTC, datetime, timedelta
from itertools import pairwise, zip_longest
from typing import Annotated, Literal

from pydantic import BaseModel, Field


def now() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(tz=UTC)


class Login(BaseModel):
    """Response from Login."""

    status: str
    expire_minutes: int = Field(alias="expireMins")
    jwt: str

    # Capture time login was created
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

    id: int = Field(alias="deviceId")
    ref_name: str = Field(alias="refName")
    name: str = Field(alias="displayName")
    device_type: str = Field(alias="deviceType")
    manufacturer: None | str = Field(default=None, alias="deviceManufacturer")
    model_name: None | str = Field(default=None, alias="deviceModelName")
    serial_number: None | str = Field(default=None, alias="deviceSerialNumber")
    storage_device: bool = Field(alias="storageDevice")
    supplier_device: bool = Field(default=None, alias="supplierDevice")
    consumer_device: bool = Field(alias="consumerDevice")
    status: str
    max_power_supply: None | int = Field(default=None, alias="maxPowerSupply")
    max_power_consumption: None | int = Field(default=None, alias="maxPowerConsumption")
    category: str
    assets: list[str] = Field(default_factory=list)


class PowerManagementConfigChannel(BaseModel):
    """Configuration for a channel in power management."""

    channel: int = Field(alias="ch")
    phase: str = Field(alias="ph")


class PowerManagementConfig(BaseModel):
    """Configuration for power management of a device."""

    name: str
    channels: list[PowerManagementConfigChannel]


class PowerManagement(BaseModel):
    """Details of an installation power management."""

    config: list[PowerManagementConfig]


class Installation(BaseModel):
    """Details of an installation."""

    id: int = Field(alias="installationId")
    name: str = Field(alias="installationName")
    status: str
    source: str
    role: str
    read_only: bool = Field(alias="readOnly")
    dmg_id: int = Field(alias="dmgId")
    tags: list[str]

    mqtt_account_kura: str = Field(alias="mqttAccountKura")
    mqtt_broker_ems: str = Field(alias="mqttBrokerEms")

    timezone: str
    street_address: str = Field(alias="streetAddress")
    locality: str
    state: str
    postcode: str

    review_status: str = Field(alias="reviewStatus")
    nmi: str
    phase: int
    org_id: int = Field(alias="orgId")
    brand: str

    tariff_plan_id: int = Field(alias="tariffPlanId")
    tariff_plan_accepted: datetime = Field(alias="tariffPlanAccepted")

    devices: list[Device]
    power_management: PowerManagement = Field(alias="pm")


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
    range_start: datetime | None = Field(default=None, alias="rangeStart")
    range_end: datetime | None = Field(default=None, alias="rangeEnd")
    timestamp: list[datetime]
    sample_seconds: None | list[int] = Field(default=None, alias="sampleSecs")


class DeviceReadingsCombiner(CommonDeviceReadings):
    """Readings for the Combiner device."""

    device_type: Literal["COMBINER"] = Field(alias="deviceType")

    energy_supplied: None | list[None | float] = Field(
        default=None, alias="energySupplied"
    )
    energy_supplied_solar: None | list[None | float] = Field(
        default=None, alias="energySuppliedSolar"
    )
    energy_supplied_battery: None | list[None | float] = Field(
        default=None, alias="energySuppliedBattery"
    )
    energy_supplied_grid: None | list[None | float] = Field(
        default=None, alias="energySuppliedGrid"
    )
    energy_consumed: None | list[None | float] = Field(
        default=None, alias="energyConsumed"
    )
    energy_consumed_solar: None | list[None | float] = Field(
        default=None, alias="energyConsumedSolar"
    )
    energy_consumed_battery: None | list[None | float] = Field(
        default=None, alias="energyConsumedBattery"
    )
    energy_consumed_grid: None | list[None | float] = Field(
        default=None, alias="energyConsumedGrid"
    )
    energy_correction: None | list[None | float] = Field(
        default=None, alias="energyCorrection"
    )
    temperature: None | list[None | float] = Field(default=None)


class DeviceReadingsSolarPV(CommonDeviceReadings):
    """Readings for the Solar PV device."""

    device_type: Literal["SOLAR_PV"] = Field(alias="deviceType")
    operation_status: None | list[None | str] = Field(
        default=None, alias="operationStatus"
    )
    operation_message: None | list[None | str] = Field(
        default=None, alias="operationMessage"
    )

    energy_supplied: None | list[None | float] = Field(
        default=None, alias="energySupplied"
    )


class DeviceReadingsGridMeter(CommonDeviceReadings):
    """Readings for the Grid Meter device."""

    device_type: Literal["GRID_METER"] = Field(alias="deviceType")
    operation_status: None | list[None | str] = Field(
        default=None, alias="operationStatus"
    )
    operation_message: None | list[None | str] = Field(
        default=None, alias="operationMessage"
    )

    energy_supplied: None | list[None | float] = Field(
        default=None, alias="energySupplied"
    )
    energy_consumed: None | list[None | float] = Field(
        default=None, alias="energyConsumed"
    )
    energy_consumed_solar: None | list[None | float] = Field(
        default=None, alias="energyConsumedSolar"
    )
    energy_consumed_battery: None | list[None | float] = Field(
        default=None, alias="energyConsumedBattery"
    )
    power_factor_a: None | list[None | float] = Field(
        default=None, alias="powerFactorA"
    )
    power_factor_b: None | list[None | float] = Field(
        default=None, alias="powerFactorB"
    )
    power_factor_c: None | list[None | float] = Field(
        default=None, alias="powerFactorC"
    )
    voltage_a: None | list[None | float] = Field(default=None, alias="voltageA")
    voltage_b: None | list[None | float] = Field(default=None, alias="voltageB")
    voltage_c: None | list[None | float] = Field(default=None, alias="voltageC")


class DeviceReadingsGenericConsumer(CommonDeviceReadings):
    """Readings for a Generic consumer device."""

    device_type: Literal["GENERIC_CONSUMER"] = Field(alias="deviceType")
    operation_status: None | list[None | str] = Field(
        default=None, alias="operationStatus"
    )
    operation_message: None | list[None | str] = Field(
        default=None, alias="operationMessage"
    )

    energy_consumed: None | list[None | float] = Field(
        default=None, alias="energyConsumed"
    )
    energy_consumed_solar: None | list[None | float] = Field(
        default=None, alias="energyConsumedSolar"
    )
    energy_consumed_battery: None | list[None | float] = Field(
        default=None, alias="energyConsumedBattery"
    )
    energy_consumed_grid: None | list[None | float] = Field(
        default=None, alias="energyConsumedGrid"
    )


class DeviceReadingsWaterHeater(DeviceReadingsGenericConsumer):
    """Readings for a Water heater device."""

    device_type: Literal["WATER_HEATER"] = Field(alias="deviceType")

    available_energy: None | list[None | float] = Field(alias="availableEnergy")
    max_energy: None | list[None | float] = Field(default=None, alias="maxEnergy")
    temp_sensor1: None | list[None | float] = Field(default=None, alias="s1")
    temp_sensor2: None | list[None | float] = Field(default=None, alias="s2")
    temp_sensor3: None | list[None | float] = Field(default=None, alias="s3")
    temp_sensor4: None | list[None | float] = Field(default=None, alias="s4")
    temp_sensor5: None | list[None | float] = Field(default=None, alias="s5")
    temp_sensor6: None | list[None | float] = Field(default=None, alias="s6")

    @property
    def available_percentage(self) -> None | list[None | float]:
        """Get the available percentage of the water heater."""
        if self.available_energy is None or self.max_energy is None:
            return None
        return [
            ((a / m) * 100 if m > 0 else 0) if m is not None and a is not None else None
            for a, m in zip_longest(self.available_energy, self.max_energy)
        ]


class DeviceReadingsEnergyBalance(DeviceReadingsGenericConsumer):
    """Readings for the Energy Balance device."""

    device_type: Literal["ENERGY_BALANCE"] = Field(alias="deviceType")


ReadingsDevices = Annotated[
    (
        DeviceReadingsCombiner
        | DeviceReadingsSolarPV
        | DeviceReadingsGridMeter
        | DeviceReadingsGenericConsumer
        | DeviceReadingsWaterHeater
        | DeviceReadingsEnergyBalance
    ),
    Field(discriminator="device_type"),
]


class Readings(BaseModel):
    """Reading history data."""

    range_start: datetime = Field(alias="rangeStart")
    range_end: datetime = Field(alias="rangeEnd")
    range_count: int = Field(alias="rangeCount")
    seconds: int
    installation_id: int = Field(alias="installationId")
    server_time: datetime = Field(alias="serverTime")

    devices: list[ReadingsDevices]


class TariffGroup(BaseModel):
    """Details of a tariff group."""

    days: list[int]
    months: list[int]
    periods: list[int]
    costs: list[float]

    def cost_at(self, dt: datetime) -> float | None:
        """Get the cost at a specific datetime."""
        if dt.month in self.months and dt.weekday() + 1 in self.days:
            ranges = pairwise(self.periods)
            for i, range_ in enumerate(ranges):
                if range_[0] <= dt.hour < range_[1]:
                    return self.costs[i]
            # Handle the last period
            return self.costs[-1]
        return None


class Tariff(BaseModel):
    """Details of a tariff."""

    dnsp_code: str = Field(alias="dnspCode")
    state: str
    retailer_code: str = Field(alias="retailerCode")
    retailer_name: str = Field(alias="retailerName")
    plan_id: int = Field(alias="planId")
    plan_name: str = Field(alias="planName")
    tariff_type: str = Field(alias="tariffType")
    source: str
    daily_fee: float = Field(alias="dailyFee")
    feed_in_cost: float = Field(alias="feedInCost")
    as_at: datetime | None = Field(default=None, alias="asAt")
    updated: datetime

    groups: list[TariffGroup]

    def cost_at(self, dt: datetime) -> float | None:
        """Get the cost at a specific datetime."""
        for group in self.groups:
            if (cost := group.cost_at(dt)) is not None:
                return cost
        return None


class TariffDetails(BaseModel):
    """Details of a tariff."""

    status: str
    plan_id: int = Field(alias="planId")
    tariff: Tariff
