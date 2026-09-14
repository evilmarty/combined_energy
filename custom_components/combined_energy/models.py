"""API Schema model."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from custom_components.combined_energy.const import (
    INSTALLATION_DEVICE_TYPE_COMBINER,
    INSTALLATION_DEVICE_TYPE_ENERGY_BALANCE,
    INSTALLATION_DEVICE_TYPE_GATEWAY,
    INSTALLATION_DEVICE_TYPE_GENERIC_CONSUMER,
    INSTALLATION_DEVICE_TYPE_GRID_METER,
    INSTALLATION_DEVICE_TYPE_SOLAR_PV,
    INSTALLATION_DEVICE_TYPE_WATER_HEATER,
)
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


class DeviceConnection(BaseModel):
    """Transport connection details for a device."""

    mac: str | None = None
    connection_type: str | None = Field(default=None, alias="type")
    protocol: str | None = None
    port: int | None = None


class DeviceChannel(BaseModel):
    """Power meter channel mapping."""

    channel: int = Field(alias="ch")
    phase: str | None = Field(default=None, alias="ph")


class DeviceConfiguration(BaseModel):
    """Power meter configuration details."""

    name: str
    channels: list[DeviceChannel]


class DeviceConnectionDetails(BaseModel):
    """Connection details for installation devices."""

    connection: DeviceConnection | None = None
    type: str | None = None
    channel_count: int | None = Field(default=None, alias="channelCount")
    configurations: list[DeviceConfiguration] | None = None
    modbus_unit: int | None = Field(default=None, alias="modbusUnit")
    supply: str | None = None
    phase_type: str | None = Field(default=None, alias="phaseType")
    device_reference: str | None = Field(default=None, alias="deviceReference")


class DeviceActionDetail(BaseModel):
    """Action metadata for a controllable device."""

    allow: list[str] = Field(default_factory=list)
    name: str
    label: str
    type: str
    accepts_null: bool = Field(alias="acceptsNull")
    expires_to: str | None = Field(default=None, alias="expiresTo")


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
    system_device: bool = Field(default=False, alias="system")
    connection_details: DeviceConnectionDetails | None = Field(
        default=None, alias="connectionDetails"
    )
    action_details: list[DeviceActionDetail] | None = Field(
        default=None, alias="actionDetails"
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


class TariffDetail(BaseModel):
    """Tariff details returned by intel payload."""

    tariff_type: str = Field(alias="tariffType")
    costs: list[float]
    months: list[int]
    dnsp_code: str = Field(alias="dnspCode")
    feed_in: float = Field(alias="feedIn")
    retailer_code: str = Field(alias="retailerCode")
    days: list[int]
    periods: list[float]
    state: str
    daily_fee: float = Field(alias="dailyFee")
    plan_id: int = Field(alias="planId")

    @staticmethod
    def _hour_fraction(dt: datetime) -> float:
        """Return hour-of-day as a fractional value."""
        return (
            dt.hour + dt.minute / 60 + dt.second / 3600 + dt.microsecond / 3_600_000_000
        )

    @staticmethod
    def _at_period(dt: datetime, period_hour: float) -> datetime:
        """Return datetime at the provided period hour."""
        hour = int(period_hour)
        minutes = int(round((period_hour - hour) * 60))
        if minutes == 60:
            hour += 1
            minutes = 0
        return dt.replace(hour=hour, minute=minutes, second=0, microsecond=0)

    def cost_at(self, dt: datetime) -> float | None:
        """Get the tariff cost at a specific datetime."""
        if (
            not self.days
            or not self.months
            or not self.periods
            or not self.costs
            or dt.month not in self.months
            or dt.isoweekday() not in self.days
        ):
            return None

        hour_fraction = self._hour_fraction(dt)
        for index, (start, end) in enumerate(
            zip(self.periods, self.periods[1:], strict=False)
        ):
            if start <= hour_fraction < end:
                return self.costs[min(index, len(self.costs) - 1)]

        return self.costs[-1]

    def next_cost_change(self, dt: datetime) -> datetime | None:
        """Get the next datetime when the cost changes."""
        if not self.days or not self.months or not self.periods:
            return None

        periods = sorted(self.periods)
        days = set(self.days)
        months = sorted(set(self.months))
        dt = dt.replace(second=0, microsecond=0)

        if dt.month in months and dt.isoweekday() in days:
            current_hour_fraction = self._hour_fraction(dt)
            if period := next((p for p in periods if p > current_hour_fraction), None):
                return self._at_period(dt, period)

        dt = self._at_period(dt, periods[0]) + timedelta(days=1)
        while dt.month in months:
            if dt.isoweekday() in days:
                return dt
            dt += timedelta(days=1)

        if next_month := next((month for month in months if month > dt.month), None):
            dt = dt.replace(month=next_month, day=1)
        else:
            dt = dt.replace(year=dt.year + 1, month=months[0], day=1)

        dt = self._at_period(dt, periods[0])
        while dt.month in months:
            if dt.isoweekday() in days:
                return dt
            dt += timedelta(days=1)

        return None


class SolarEnergyForecastDay(BaseModel):
    """Solar forecast for a single day."""

    cloud_cover: list[int] = Field(alias="cloudCover")
    temperature_c: list[int] = Field(alias="temperatureC")
    day: str
    period_end_hour: list[float] = Field(alias="periodEndHour")
    energy_supplied_pred: list[float] = Field(alias="energySuppliedPred")


class GeneralEnergyUsagePattern(BaseModel):
    """General energy usage profile."""

    period_end_hour: list[float] = Field(alias="periodEndHour")
    energy_consumed_avg: list[float] = Field(alias="energyConsumedAvg")


class WaterDischargeProfile(BaseModel):
    """Water discharge profile for a day-type."""

    hour_of_day: list[float] = Field(alias="hourOfDay")
    discharge_amenity_litres: list[float] = Field(alias="dischargeAmenityLitres")
    dow_type: str = Field(alias="dowType")
    energy_consumed_daily_avg: float = Field(alias="energyConsumedDailyAvg")


class WaterDischargePattern(BaseModel):
    """Water discharge data for a device."""

    profiles: list[WaterDischargeProfile]
    device_id: int = Field(alias="deviceId")
    ref_name: str = Field(alias="refName")


class Intel(BaseModel):
    """Intel payload model."""

    installation_id: int = Field(alias="installationId")
    request_time_str: str = Field(alias="requestTimeStr")
    version: float
    tariff_details: list[TariffDetail] = Field(alias="tariffDetails")
    solar_energy_forecast: list[SolarEnergyForecastDay] = Field(
        alias="solarEnergyForecast"
    )
    general_energy_usage_pattern: GeneralEnergyUsagePattern = Field(
        alias="generalEnergyUsagePattern"
    )
    nmi: str
    water_discharge_pattern: list[WaterDischargePattern] = Field(
        alias="waterDischargePattern"
    )

    def tariff_at(self, dt: datetime) -> TariffDetail | None:
        """Get tariff detail that applies at a specific datetime."""
        if not self.tariff_details:
            return None
        for tariff in self.tariff_details:
            if tariff.cost_at(dt) is not None:
                return tariff
        return self.tariff_details[0]

    def cost_at(self, dt: datetime) -> float | None:
        """Get tariff cost at a specific datetime."""
        tariff = self.tariff_at(dt)
        if tariff is None:
            return None
        return tariff.cost_at(dt)

    def next_cost_change(self, dt: datetime) -> datetime | None:
        """Get next datetime when any matching tariff cost changes."""
        next_changes = [
            change
            for tariff in self.tariff_details
            if (change := tariff.next_cost_change(dt)) is not None
        ]
        if not next_changes:
            return None
        return min(next_changes)


class CommonDeviceReadings(BaseModel):
    """Readings for a particular device."""

    device_id: int | None = Field(default=None, alias="deviceId")
    period_end: int = Field(alias="periodEnd")
    period_end_str: str | None = Field(default=None, alias="periodEndStr")
    reading_count: int | None = Field(default=None, alias="readingCount")


class SystemReading(CommonDeviceReadings):
    """Readings for system-level status."""

    installation_device_type: str = INSTALLATION_DEVICE_TYPE_GATEWAY
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

    installation_device_type: str = INSTALLATION_DEVICE_TYPE_COMBINER
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

    installation_device_type: str = INSTALLATION_DEVICE_TYPE_SOLAR_PV
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

    installation_device_type: str = INSTALLATION_DEVICE_TYPE_GRID_METER
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

    installation_device_type: str = INSTALLATION_DEVICE_TYPE_GENERIC_CONSUMER
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

    installation_device_type: str = INSTALLATION_DEVICE_TYPE_WATER_HEATER
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

    installation_device_type: str = INSTALLATION_DEVICE_TYPE_ENERGY_BALANCE
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
