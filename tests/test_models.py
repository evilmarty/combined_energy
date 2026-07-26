"""Tests for combined energy models."""

from datetime import UTC, datetime
import json
from zoneinfo import ZoneInfo

from freezegun import freeze_time
from pydantic import ValidationError
import pytest

from custom_components.combined_energy.models import (
    CombinerReading,
    ConnectionStatus,
    Device,
    EnergyBalanceReading,
    GridMeterReading,
    Installation,
    Intel,
    Login,
    LogSession,
    Readings,
    SolarPvReading,
    SystemReading,
    TariffDetail,
    WaterHeaterReading,
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

    def test_installation(self, installation, fixture_path):
        """Test Installation model."""
        payload = json.loads((fixture_path / "installation.json").read_text())
        assert installation.status == "ACTIVE"
        assert installation.id == payload["id"]
        assert installation.name == payload["name"]
        assert installation.timezone == ZoneInfo(payload["timezone"])
        assert installation.address == payload["address"]
        assert installation.locality == payload["locality"]
        assert installation.state == payload["state"]
        assert installation.postcode == payload["postcode"]
        assert installation.phase == payload["phase"]
        assert int(installation.installed.timestamp()) == payload["installed"]
        assert installation.gateway_id == payload["gwId"]
        assert len(installation.devices) == len(payload["devices"])
        assert installation.devices[0] == Device.model_validate(payload["devices"][0])
        assert installation.devices[0].device_type == "GATEWAY"
        assert installation.devices[1].connection_details is not None
        assert installation.devices[1].connection_details.type == "PM2"
        assert installation.devices[1].connection_details.connection is not None
        assert (
            installation.devices[1].connection_details.connection.protocol
            == "MODBUS-RTU"
        )
        assert installation.devices[1].connection_details.configurations is not None
        assert (
            installation.devices[1]
            .connection_details.configurations[0]
            .channels[0]
            .channel
            == 0
        )
        assert installation.devices[2].connection_details is not None
        assert installation.devices[2].action_details is not None
        assert installation.devices[2].action_details[0].accepts_null is True
        assert installation.devices[2].action_details[1].expires_to == "none"
        assert installation.devices[3].connection_details is not None
        assert installation.devices[3].connection_details.phase_type == "1"
        assert installation.devices[3].action_details is not None
        assert installation.devices[4].connection_details is not None
        assert installation.devices[4].connection_details.supply == "GRD1"
        assert installation.devices[5].connection_details is not None
        assert installation.devices[5].connection_details.device_reference == "PM1.SOL1"
        assert installation.devices[6].connection_details is not None
        assert installation.devices[6].connection_details.device_reference == "PM1.GC1"
        assert installation.devices[7].connection_details is not None
        assert installation.devices[7].connection_details.device_reference == "PM1.AC1"

    def test_installation_from_bridge_payload(self, fixture_path):
        """Validate bridge installation payload directly with Installation model."""
        payload = json.loads((fixture_path / "installation.json").read_text())
        installation = Installation.model_validate(payload)

        assert installation.id == payload["id"]
        assert installation.name == payload["name"]
        assert installation.gateway_id == payload["gwId"]
        assert installation.timezone == ZoneInfo(payload["timezone"])
        assert any(
            device.device_type == "WATER_HEATER" for device in installation.devices
        )

    def test_installation_defaults_missing_device_flags(self, fixture_path):
        """Default missing storage/consumer flags to false."""
        payload = json.loads((fixture_path / "installation.json").read_text())
        for device in payload["devices"]:
            device.pop("storage", None)
            device.pop("consumer", None)

        installation = Installation.model_validate(payload)

        assert all(device.storage_device is False for device in installation.devices)
        assert all(device.consumer_device is False for device in installation.devices)

    def test_gw_id_from_installation_payload_missing(self):
        """Raise validation error when bridge payload omits gwId."""
        with pytest.raises(ValidationError):
            Installation.model_validate(
                {
                    "id": 1,
                    "name": "No GW",
                    "timezone": "UTC",
                    "address": "",
                    "locality": "",
                    "state": "",
                    "postcode": "",
                    "status": "ACTIVE",
                    "phase": 1,
                    "installed": 0,
                    "devices": [],
                }
            )


class TestReadings:
    """Test Readings model."""

    def test_readings_from_mqtt_message(self, example_log_payload: bytes):
        """Convert parsed MQTT message into typed Readings in the model layer."""
        readings = Readings.from_mqtt_message(example_log_payload)
        assert readings.period_duration_secs == 5
        assert len(readings.devices) == 8
        assert isinstance(readings.devices[0], SystemReading)
        assert readings.devices[0].installation_device_type == "GATEWAY"
        assert any(
            isinstance(device, WaterHeaterReading) for device in readings.devices
        )
        assert any(isinstance(device, GridMeterReading) for device in readings.devices)
        assert any(isinstance(device, SolarPvReading) for device in readings.devices)
        assert any(
            isinstance(device, EnergyBalanceReading) for device in readings.devices
        )
        assert (
            sum(
                1
                for device in readings.devices
                if getattr(device, "device_type", None) == "GenericConsumerReading"
            )
            == 2
        )
        assert any(isinstance(device, CombinerReading) for device in readings.devices)


class TestWaterHeaterReading:
    """Test WaterHeaterReading model."""

    @pytest.fixture
    def device_readings_water_heater(self):
        """Fixture for WaterHeaterReading model."""
        return WaterHeaterReading(
            deviceId=3,
            deviceType="WaterHeaterReading",
            periodEnd=1744748875,
            periodEndStr="25-04-15 2027 +0000",
            readingCount=5,
            operationStatus="CONNECTED_ACTIVE",
            operationMessage=None,
            energyConsumed=0.71111,
            energyConsumedSolar=0.71111,
            energyConsumedBattery=0,
            energyConsumedGrid=0,
            currentAmenityLitres=426,
            maxAmenityLitres=585,
            s1=42.6,
            s2=61.52,
            s3=69.7,
            s4=71.2,
            s5=71.3,
            s6=71.1,
        )

    @pytest.mark.parametrize(
        ("available_energy", "max_energy", "expected"),
        [
            (426, 585, pytest.approx(72.8, rel=1e-2)),
            (None, 585, None),
            (426, None, None),
            (426, 0, 0),
        ],
    )
    def test_available_percentage(
        self,
        device_readings_water_heater: WaterHeaterReading,
        available_energy,
        max_energy,
        expected,
    ):
        """Test available_percentage method."""
        device = WaterHeaterReading(
            **device_readings_water_heater.model_dump(
                exclude={"available_energy", "max_energy"}, by_alias=True
            ),
            currentAmenityLitres=available_energy,
            maxAmenityLitres=max_energy,
        )
        assert device.available_percentage == expected


class TestIntel:
    """Test Intel model."""

    def test_intel_payload_model(self):
        """Validate intel payload parsing and aliases."""
        intel = Intel.model_validate(
            {
                "installationId": 5076,
                "requestTimeStr": "Mon Jul 20 00:00:00 AEST 2026",
                "version": 1.2,
                "tariffDetails": [
                    {
                        "tariffType": "TOU",
                        "costs": [25.62, 30.02, 39.88],
                        "months": [1, 2, 3],
                        "dnspCode": "EX",
                        "feedIn": 2,
                        "retailerCode": "ALINTA_ENERGY",
                        "days": [1, 2, 3, 4, 5],
                        "periods": [0, 7, 16],
                        "state": "QLD",
                        "dailyFee": 132.92,
                        "planId": 55232,
                    }
                ],
                "solarEnergyForecast": [
                    {
                        "cloudCover": [68, 45],
                        "temperatureC": [17, 16],
                        "day": "2026-07-20",
                        "periodEndHour": [0, 0.5],
                        "energySuppliedPred": [0, 67],
                    }
                ],
                "generalEnergyUsagePattern": {
                    "periodEndHour": [0.5, 1.0],
                    "energyConsumedAvg": [-79, -78],
                },
                "nmi": "3116633733",
                "waterDischargePattern": [
                    {
                        "profiles": [
                            {
                                "hourOfDay": [0.5, 1.0],
                                "dischargeAmenityLitres": [-2.6, -5.0],
                                "dowType": "WD",
                                "energyConsumedDailyAvg": -5770,
                            }
                        ],
                        "deviceId": 3,
                        "refName": "WAT1",
                    }
                ],
            }
        )

        assert intel.installation_id == 5076
        assert intel.tariff_details[0].plan_id == 55232
        assert intel.solar_energy_forecast[0].period_end_hour == [0.0, 0.5]
        assert intel.general_energy_usage_pattern.energy_consumed_avg == [-79.0, -78.0]
        assert intel.water_discharge_pattern[0].profiles[0].dow_type == "WD"

    def test_cost_at(self):
        """Resolve cost from tariff details on Intel."""
        intel = Intel.model_validate(
            {
                "installationId": 5076,
                "requestTimeStr": "Mon Jul 20 00:00:00 AEST 2026",
                "version": 1.2,
                "tariffDetails": [
                    {
                        "tariffType": "TOU",
                        "costs": [25.62, 30.02],
                        "months": [7],
                        "dnspCode": "EX",
                        "feedIn": 2,
                        "retailerCode": "ALINTA_ENERGY",
                        "days": [1, 2, 3, 4, 5],
                        "periods": [0, 7],
                        "state": "QLD",
                        "dailyFee": 132.92,
                        "planId": 55232,
                    }
                ],
                "solarEnergyForecast": [],
                "generalEnergyUsagePattern": {
                    "periodEndHour": [],
                    "energyConsumedAvg": [],
                },
                "nmi": "3116633733",
                "waterDischargePattern": [],
            }
        )
        assert intel.cost_at(datetime(2026, 7, 20, 6, 30)) == 25.62
        assert intel.cost_at(datetime(2026, 7, 20, 8, 0)) == 30.02

    def test_next_cost_change(self):
        """Resolve next cost transition from tariff details on Intel."""
        intel = Intel.model_validate(
            {
                "installationId": 5076,
                "requestTimeStr": "Mon Jul 20 00:00:00 AEST 2026",
                "version": 1.2,
                "tariffDetails": [
                    {
                        "tariffType": "TOU",
                        "costs": [25.62, 30.02],
                        "months": [7],
                        "dnspCode": "EX",
                        "feedIn": 2,
                        "retailerCode": "ALINTA_ENERGY",
                        "days": [1, 2, 3, 4, 5],
                        "periods": [0, 7],
                        "state": "QLD",
                        "dailyFee": 132.92,
                        "planId": 55232,
                    }
                ],
                "solarEnergyForecast": [],
                "generalEnergyUsagePattern": {
                    "periodEndHour": [],
                    "energyConsumedAvg": [],
                },
                "nmi": "3116633733",
                "waterDischargePattern": [],
            }
        )
        assert intel.next_cost_change(datetime(2026, 7, 20, 6, 30)) == datetime(
            2026, 7, 20, 7, 0
        )


class TestTariffDetail:
    """Test TariffDetail utility methods."""

    @pytest.fixture
    def tariff_detail(self):
        """Build a representative TOU tariff detail."""
        return TariffDetail.model_validate(
            {
                "tariffType": "TOU",
                "costs": [25.62, 30.02, 39.88, 30.02, 25.62],
                "months": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                "dnspCode": "EX",
                "feedIn": 2,
                "retailerCode": "ALINTA_ENERGY",
                "days": [1, 2, 3, 4, 5],
                "periods": [0, 7, 16, 20, 22],
                "state": "QLD",
                "dailyFee": 132.92,
                "planId": 55232,
            }
        )

    def test_cost_at(self, tariff_detail):
        """Get cost based on month/day/time periods."""
        assert tariff_detail.cost_at(datetime(2026, 7, 20, 6, 30)) == 25.62
        assert tariff_detail.cost_at(datetime(2026, 7, 20, 8, 0)) == 30.02
        assert tariff_detail.cost_at(datetime(2026, 7, 20, 17, 0)) == 39.88
        assert tariff_detail.cost_at(datetime(2026, 7, 20, 21, 0)) == 30.02
        assert tariff_detail.cost_at(datetime(2026, 7, 20, 23, 0)) == 25.62
        assert tariff_detail.cost_at(datetime(2026, 7, 19, 8, 0)) is None

    def test_next_cost_change(self, tariff_detail):
        """Calculate next tariff transition datetime."""
        assert tariff_detail.next_cost_change(datetime(2026, 7, 20, 8, 15)) == datetime(
            2026, 7, 20, 16, 0
        )
        assert tariff_detail.next_cost_change(
            datetime(2026, 7, 20, 23, 30)
        ) == datetime(2026, 7, 21, 0, 0)
        assert tariff_detail.next_cost_change(
            datetime(2026, 7, 24, 23, 30)
        ) == datetime(2026, 7, 27, 0, 0)
