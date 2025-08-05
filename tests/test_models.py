"""Tests for combined energy models."""

from datetime import UTC, datetime

from freezegun import freeze_time
import pytest

from custom_components.combined_energy.models import (
    ConnectionStatus,
    Device,
    DeviceReadingsCombiner,
    DeviceReadingsEnergyBalance,
    DeviceReadingsGenericConsumer,
    DeviceReadingsGridMeter,
    DeviceReadingsSolarPV,
    DeviceReadingsWaterHeater,
    Installation,
    Login,
    LogSession,
    PowerManagementConfig,
    PowerManagementConfigChannel,
    Readings,
    Tariff,
    TariffDetails,
    TariffGroup,
)


class TestConnectionStatus:
    """Test ConnectionStatus model."""

    @pytest.fixture
    def connection_status(self, fixture_path):
        """Fixture for ConnectionStatus  model."""
        return ConnectionStatus.model_validate_json(
            (fixture_path / "comm-stat.json").read_text()
        )

    def test_connection_status(self, connection_status):
        """Test ConnectionStatus model."""
        assert connection_status.status == "ok"
        assert connection_status.installation_id == 1234
        assert connection_status.connected is True
        assert connection_status.since == datetime(2025, 4, 13, 6, 51, 50, tzinfo=UTC)


class TestLogin:
    """Test Login model."""

    @pytest.fixture
    @freeze_time("2025-04-13 06:51:50")
    def login(self, fixture_path):
        """Fixture for Login model."""
        return Login.model_validate_json((fixture_path / "login.json").read_text())

    def test_login(self, login):
        """Test Login model."""
        assert login.status == "ok"
        assert login.expire_minutes == 180
        assert login.jwt == "xxxx"
        assert login.expires == datetime(2025, 4, 13, 9, 51, 50, tzinfo=UTC)


class TestLogSession:
    """Test LogSession model."""

    @pytest.fixture
    def log_session(self, fixture_path):
        """Fixture for LogSession model."""
        return LogSession.model_validate_json(
            (fixture_path / "log-session.json").read_text()
        )

    def test_log_session(self, log_session):
        """Test LogSession model."""
        assert log_session.status == "ok"
        assert log_session.installation_id == 1234
        assert not log_session.archive_saved


class TestInstallation:
    """Test Installation model."""

    @pytest.fixture
    def installation(self, fixture_path):
        """Fixture for Installation model."""
        return Installation.model_validate_json(
            (fixture_path / "installation.json").read_text()
        )

    def test_installation(self, installation):
        """Test Installation model."""
        assert installation.status == "ACTIVE"
        assert installation.id == 1234
        assert installation.name == "xxxx"
        assert installation.source == "a"
        assert installation.role == "OWNER"
        assert installation.read_only is False
        assert installation.timezone == "Etc/UTC"
        assert installation.dmg_id == 12345
        assert installation.tags == [
            "emu1",
            "ems",
            "dnsp-ex",
            "tariff-flat",
            "meter-pm2",
            "water-ps2",
            "solar-generic",
            "phase-1",
        ]
        assert installation.mqtt_account_kura == "cet-ecn"
        assert installation.mqtt_broker_ems == "mqtt2.combined.energy"
        assert installation.street_address == "xxxx"
        assert installation.locality == "xxxx"
        assert installation.state == "XXX"
        assert installation.postcode == "0000"
        assert installation.review_status == "VALIDATED"
        assert installation.nmi == "1111111111"
        assert installation.brand == "xxxx"
        assert installation.phase == 1
        assert installation.org_id == 1234
        assert installation.tariff_plan_id == 12345
        assert installation.tariff_plan_accepted == datetime(
            2024, 9, 9, 8, 12, 38, 78000, tzinfo=UTC
        )
        assert installation.devices == [
            Device(
                deviceId=1,
                status="ACTIVE",
                refName="GW1",
                deviceType="GATEWAY",
                category="SYSTEM",
                displayName="Gateway",
                deviceManufacturer="CET",
                deviceModelName="EMU1",
                deviceSerialNumber="EMU1-XXXXXXXXXXXX",
                supplierDevice=False,
                storageDevice=False,
                consumerDevice=False,
                maxPowerSupply=None,
                maxPowerConsumption=None,
                iconOverride=None,
                orderOverride=None,
            ),
            Device(
                deviceId=2,
                status="ACTIVE",
                refName="PM1",
                deviceType="POWER_METER",
                category="SYSTEM",
                displayName="Power Meter",
                deviceManufacturer="CET",
                deviceModelName="PM2",
                deviceSerialNumber="PM2-XXXXXXXXXXXX",
                supplierDevice=False,
                storageDevice=False,
                consumerDevice=False,
                maxPowerSupply=None,
                maxPowerConsumption=None,
                iconOverride=None,
                orderOverride=None,
            ),
            Device(
                deviceId=3,
                status="ACTIVE",
                refName="WAT1",
                deviceType="WATER_HEATER",
                category="WATER_HEATER",
                displayName="Water Heater",
                deviceManufacturer="XXX",
                deviceModelName="PS2",
                deviceSerialNumber="PS2-XXXXXXXXXXXX",
                supplierDevice=False,
                storageDevice=True,
                consumerDevice=True,
                maxPowerSupply=None,
                maxPowerConsumption=3500,
                iconOverride=None,
                orderOverride=None,
            ),
            Device(
                deviceId=4,
                status="ACTIVE",
                refName="GRD1",
                deviceType="GRID_METER",
                category="GRID_METER",
                displayName="Grid Meter",
                deviceManufacturer="CET",
                deviceModelName=None,
                deviceSerialNumber=None,
                supplierDevice=True,
                storageDevice=False,
                consumerDevice=False,
                maxPowerSupply=None,
                maxPowerConsumption=None,
                iconOverride=None,
                orderOverride=None,
                assets=["PM1"],
            ),
            Device(
                deviceId=5,
                status="ACTIVE",
                refName="EB1",
                deviceType="ENERGY_BALANCE",
                category="BUILDING",
                displayName="House",
                deviceManufacturer="CET",
                deviceModelName=None,
                deviceSerialNumber=None,
                supplierDevice=False,
                storageDevice=False,
                consumerDevice=True,
                maxPowerSupply=None,
                maxPowerConsumption=None,
                iconOverride=None,
                orderOverride=None,
            ),
            Device(
                deviceId=6,
                status="ACTIVE",
                refName="SOL1",
                deviceType="SOLAR_PV",
                category="SOLAR_PV",
                displayName="Solar",
                deviceManufacturer="GENERIC",
                deviceModelName=None,
                deviceSerialNumber=None,
                supplierDevice=True,
                storageDevice=False,
                consumerDevice=False,
                maxPowerSupply=None,
                maxPowerConsumption=None,
                iconOverride=None,
                orderOverride=None,
                assets=["PM1"],
            ),
            Device(
                deviceId=7,
                status="ACTIVE",
                refName="GC1",
                deviceType="GENERIC_CONSUMER",
                category="COOKING",
                displayName="Cooking",
                deviceManufacturer="",
                deviceModelName=None,
                deviceSerialNumber=None,
                supplierDevice=False,
                storageDevice=False,
                consumerDevice=True,
                maxPowerSupply=None,
                maxPowerConsumption=None,
                iconOverride=None,
                orderOverride=None,
                assets=["PM1"],
            ),
            Device(
                deviceId=8,
                status="ACTIVE",
                refName="AC1",
                deviceType="GENERIC_CONSUMER",
                category="AIRCON",
                displayName="Aircon",
                deviceManufacturer="",
                deviceModelName=None,
                deviceSerialNumber=None,
                supplierDevice=False,
                storageDevice=False,
                consumerDevice=True,
                maxPowerSupply=None,
                maxPowerConsumption=None,
                iconOverride=None,
                orderOverride=None,
                assets=["PM1"],
            ),
        ]
        assert installation.power_management.config == [
            PowerManagementConfig(
                name="GRD1",
                channels=[PowerManagementConfigChannel(ch=0, ph="A")],
            ),
            PowerManagementConfig(
                name="SOL1",
                channels=[PowerManagementConfigChannel(ch=1, ph="A")],
            ),
            PowerManagementConfig(
                name="GC1",
                channels=[PowerManagementConfigChannel(ch=2, ph="A")],
            ),
            PowerManagementConfig(
                name="AC1",
                channels=[PowerManagementConfigChannel(ch=3, ph="A")],
            ),
        ]


class TestReadings:
    """Test Readings model."""

    @pytest.fixture
    def readings(self, fixture_path):
        """Fixture for Readings model."""
        return Readings.model_validate_json(
            (fixture_path / "readings.json").read_text()
        )

    def test_readings(self, readings):
        """Test Readings model."""
        assert readings.installation_id == 1234
        assert readings.range_start == datetime(2025, 4, 15, 20, 27, 50, tzinfo=UTC)
        assert readings.range_end == datetime(2025, 4, 15, 20, 27, 55, tzinfo=UTC)
        assert readings.seconds == 5
        assert readings.server_time == datetime(2025, 4, 15, 20, 27, 57, tzinfo=UTC)
        assert readings.devices == [
            DeviceReadingsCombiner(
                deviceType="COMBINER",
                rangeStart=datetime(2025, 4, 15, 20, 27, 50, tzinfo=UTC),
                rangeEnd=datetime(2025, 4, 15, 20, 27, 55, tzinfo=UTC),
                timestamp=[datetime(2025, 4, 15, 20, 27, 55, tzinfo=UTC)],
                sampleSecs=[5],
                energySupplied=[1.18328],
                energySuppliedSolar=[1.18328],
                energySuppliedBattery=[0],
                energySuppliedGrid=[0],
                energyConsumedOther=[0.44113],
                energyConsumedOtherSolar=[0.44113],
                energyConsumedOtherBattery=[0],
                energyConsumedOtherGrid=[0],
                energyConsumed=[1.15311],
                energyConsumedSolar=[1.15311],
                energyConsumedBattery=[0],
                energyConsumedGrid=[0],
                energyCorrection=[0],
                temperature=[None],
            ),
            DeviceReadingsGridMeter(
                deviceId=4,
                deviceType="GRID_METER",
                rangeStart=datetime(2025, 4, 15, 20, 27, 50, tzinfo=UTC),
                rangeEnd=datetime(2025, 4, 15, 20, 27, 55, tzinfo=UTC),
                timestamp=[datetime(2025, 4, 15, 20, 27, 55, tzinfo=UTC)],
                sampleSecs=[5],
                operationStatus=["CONNECTED_ACTIVE"],
                operationMessage=[None],
                energyConsumed=[0.03017],
                energyConsumedSolar=[0.03017],
                energyConsumedBattery=[0],
                energySupplied=[0],
                energyNett=[-0.03017],
                voltageA=[245.075],
                voltageB=[None],
                voltageC=[None],
                powerFactorA=[-0.06593],
                powerFactorB=[None],
                powerFactorC=[None],
                powerA=[-21.72115],
                powerB=[None],
                powerC=[None],
            ),
            DeviceReadingsSolarPV(
                deviceId=6,
                deviceType="SOLAR_PV",
                rangeStart=datetime(2025, 4, 15, 20, 27, 50, tzinfo=UTC),
                rangeEnd=datetime(2025, 4, 15, 20, 27, 55, tzinfo=UTC),
                timestamp=[datetime(2025, 4, 15, 20, 27, 55, tzinfo=UTC)],
                sampleSecs=[5],
                operationStatus=["CONNECTED_ACTIVE"],
                operationMessage=[None],
                energySupplied=[1.18328],
            ),
            DeviceReadingsWaterHeater(
                deviceId=3,
                deviceType="WATER_HEATER",
                rangeStart=datetime(2025, 4, 15, 20, 27, 50, tzinfo=UTC),
                rangeEnd=datetime(2025, 4, 15, 20, 27, 55, tzinfo=UTC),
                timestamp=[datetime(2025, 4, 15, 20, 27, 55, tzinfo=UTC)],
                sampleSecs=[5],
                operationStatus=["CONNECTED_ACTIVE"],
                operationMessage=[None],
                energyConsumed=[0.71111],
                energyConsumedSolar=[0.71111],
                energyConsumedBattery=[0],
                energyConsumedGrid=[0],
                availableEnergy=[426],
                maxEnergy=[585],
                s1=[42.6],
                s2=[61.52],
                s3=[69.7],
                s4=[71.2],
                s5=[71.3],
                s6=[71.1],
            ),
            DeviceReadingsEnergyBalance(
                deviceId=5,
                deviceType="ENERGY_BALANCE",
                rangeStart=datetime(2025, 4, 15, 20, 27, 50, tzinfo=UTC),
                rangeEnd=datetime(2025, 4, 15, 20, 27, 55, tzinfo=UTC),
                timestamp=[datetime(2025, 4, 15, 20, 27, 55, tzinfo=UTC)],
                sampleSecs=[5],
                operationStatus=["CONNECTED_ACTIVE"],
                operationMessage=[None],
                energyConsumed=[0.44113],
                energyConsumedSolar=[0.44113],
                energyConsumedBattery=[0],
                energyConsumedGrid=[0],
            ),
            DeviceReadingsGenericConsumer(
                deviceId=7,
                deviceType="GENERIC_CONSUMER",
                rangeStart=1744748870,
                rangeEnd=1744748875,
                timestamp=[1744748875],
                sampleSecs=[5],
                operationStatus=["CONNECTED_ACTIVE"],
                operationMessage=[None],
                energyConsumed=[0],
                energyConsumedSolar=[0],
                energyConsumedBattery=[0],
                energyConsumedGrid=[0],
            ),
            DeviceReadingsGenericConsumer(
                deviceId=8,
                deviceType="GENERIC_CONSUMER",
                rangeStart=1744748870,
                rangeEnd=1744748875,
                timestamp=[1744748875],
                sampleSecs=[5],
                operationStatus=["CONNECTED_ACTIVE"],
                operationMessage=[None],
                energyConsumed=[8.7e-4],
                energyConsumedSolar=[8.7e-4],
                energyConsumedBattery=[0],
                energyConsumedGrid=[0],
            ),
        ]


class TestTariffDetails:
    """Test TariffDetails model."""

    @pytest.fixture
    def tariff_details(self, fixture_path):
        """Fixture for TariffDetails model."""
        return TariffDetails.model_validate_json(
            (fixture_path / "tariff-details.json").read_text()
        )

    def test_tariff_details(self, tariff_details):
        """Test TariffDetails model."""
        assert tariff_details.status == "ok"
        assert tariff_details.plan_id == 12345
        assert tariff_details.tariff == Tariff(
            dnspCode="EX",
            state="XXX",
            retailerCode="XXXX",
            retailerName="X",
            planId=12345,
            planName="My custom plan",
            tariffType="FLAT",
            source="CUSTOM",
            dailyFee=100.1,
            feedInCost=1,
            asAt=1659664663927,
            updated=1725869558078,
            groups=[
                TariffGroup(
                    days=[1, 2, 3, 4, 5, 6, 7],
                    months=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                    periods=[0],
                    costs=[10.12],
                ),
            ],
        )

    @pytest.mark.parametrize(
        "datetime",
        [
            datetime(2025, 1, 1, 0, 27, 50),
            datetime(2025, 1, 1, 6, 27, 50),
            datetime(2025, 1, 1, 7, 27, 50),
            datetime(2025, 1, 1, 15, 27, 50),
            datetime(2025, 1, 1, 16, 27, 50),
            datetime(2025, 1, 1, 19, 27, 50),
            datetime(2025, 1, 1, 20, 27, 50),
            datetime(2025, 1, 1, 21, 27, 50),
            datetime(2025, 1, 1, 22, 27, 50),
            datetime(2025, 1, 1, 23, 27, 50),
            datetime(2025, 1, 4, 0, 27, 50),
            datetime(2025, 1, 4, 6, 27, 50),
            datetime(2025, 1, 4, 7, 27, 50),
            datetime(2025, 1, 4, 21, 27, 50),
            datetime(2025, 1, 4, 22, 27, 50),
            datetime(2025, 1, 4, 23, 27, 50),
        ],
    )
    @pytest.mark.parametrize("expected", [10.12])
    def test_cost_at__flat(self, tariff_details: TariffDetails, datetime, expected):
        """Test cost_at method with flat tariff."""
        assert tariff_details.tariff.cost_at(datetime) == expected

    @pytest.mark.parametrize(
        ("datetime", "expected"),
        [
            (datetime(2025, 1, 1, 0, 27, 50), 15.74),
            (datetime(2025, 1, 1, 6, 27, 50), 15.74),
            (datetime(2025, 1, 1, 7, 27, 50), 16.93),
            (datetime(2025, 1, 1, 15, 27, 50), 16.93),
            (datetime(2025, 1, 1, 16, 27, 50), 27.96),
            (datetime(2025, 1, 1, 19, 27, 50), 27.96),
            (datetime(2025, 1, 1, 20, 27, 50), 16.93),
            (datetime(2025, 1, 1, 21, 27, 50), 16.93),
            (datetime(2025, 1, 1, 22, 27, 50), 15.74),
            (datetime(2025, 1, 1, 23, 27, 50), 15.74),
            (datetime(2025, 1, 4, 0, 27, 50), 15.74),
            (datetime(2025, 1, 4, 6, 27, 50), 15.74),
            (datetime(2025, 1, 4, 7, 27, 50), 16.93),
            (datetime(2025, 1, 4, 21, 27, 50), 16.93),
            (datetime(2025, 1, 4, 22, 27, 50), 15.74),
            (datetime(2025, 1, 4, 23, 27, 50), 15.74),
        ],
    )
    def test_cost_at__scheduled(
        self, tariff_details: TariffDetails, datetime, expected
    ):
        """Test cost_at method with variable schedules."""
        tariff_details.tariff.groups = [
            TariffGroup(
                days=[1, 2, 3, 4, 5],
                months=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                periods=[0, 7, 16, 20, 22],
                costs=[15.74, 16.93, 27.96, 16.93, 15.74],
            ),
            TariffGroup(
                days=[6, 7],
                months=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                periods=[0, 7, 22],
                costs=[15.74, 16.93, 15.74],
            ),
        ]
        assert tariff_details.tariff.cost_at(datetime) == expected


class TestDeviceReadingsWaterHeater:
    """Test DeviceReadingsWaterHeater model."""

    @pytest.fixture
    def device_readings_water_heater(self):
        """Fixture for DeviceReadingsWaterHeater model."""
        return DeviceReadingsWaterHeater(
            deviceId=3,
            deviceType="WATER_HEATER",
            rangeStart=datetime(2025, 4, 15, 20, 27, 50, tzinfo=UTC),
            rangeEnd=datetime(2025, 4, 15, 20, 27, 55, tzinfo=UTC),
            timestamp=[datetime(2025, 4, 15, 20, 27, 55, tzinfo=UTC)],
            sampleSecs=[5],
            operationStatus=["CONNECTED_ACTIVE"],
            operationMessage=[None],
            energyConsumed=[0.71111],
            energyConsumedSolar=[0.71111],
            energyConsumedBattery=[0],
            energyConsumedGrid=[0],
            availableEnergy=[426],
            maxEnergy=[585],
            s1=[42.6],
            s2=[61.52],
            s3=[69.7],
            s4=[71.2],
            s5=[71.3],
            s6=[71.1],
        )

    @pytest.mark.parametrize(
        ("available_energy", "max_energy", "expected"),
        [
            ([426, 123], [585, 585], pytest.approx([72.8, 21.0], rel=1e-2)),
            (None, [585], None),
            ([426], None, None),
            ([None], [585], [None]),
            ([426], [None], [None]),
        ],
    )
    def test_available_percentage(
        self,
        device_readings_water_heater: DeviceReadingsWaterHeater,
        available_energy,
        max_energy,
        expected,
    ):
        """Test available_percentage method."""
        device = DeviceReadingsWaterHeater(
            **device_readings_water_heater.model_dump(
                exclude={"available_energy", "max_energy"}, by_alias=True
            ),
            availableEnergy=available_energy,
            maxEnergy=max_energy,
        )
        assert device.available_percentage == expected
