"""Tests for MQTT readings parser."""

import pytest

from custom_components.combined_energy.models import Readings
from custom_components.combined_energy.mqtt_parser import parse_mqtt_readings_message


def test_parse_example_log_messages(example_log_payload: bytes):
    """It parses captured bridge readings payload."""
    message = parse_mqtt_readings_message(example_log_payload)

    assert message["count"] == 8
    assert message["periodDurationSecs"] == 5


def test_parse_first_message_values(example_log_payload: bytes):
    """It parses known first-message values and null/meta fields."""
    message = parse_mqtt_readings_message(example_log_payload)

    assert message["periodEnd"] == 1784415110

    water_heater = message["records"]["WaterHeaterReading"][0]
    assert water_heater["deviceId"] == 3
    assert water_heater["currentAmenityLitres"] == 546.0
    assert water_heater["operationMessage"] is None
    assert water_heater["meta"] is None
    assert water_heater["status"]["mode"] == "HEAT"

    grid_meter = message["records"]["GridMeterReading"][0]
    assert grid_meter["energySupplied"] == 0.0
    assert grid_meter["voltageA"] == 244.77499

    combiner = message["records"]["CombinerReading"][0]
    assert combiner["deviceId"] is None
    assert combiner["energySuppliedTotal"] == 5.18947


def test_convert_parsed_message_to_readings(example_log_payload: bytes):
    """It converts parsed message into Readings schema."""
    message = parse_mqtt_readings_message(example_log_payload)
    readings = Readings.from_mqtt_message(message)
    assert readings.period_duration_secs == 5
    assert len(readings.devices) == 8
    assert any(
        getattr(device, "device_type", None) == "WaterHeaterReading"
        for device in readings.devices
    )


def test_parse_message_raises_on_expected_count_mismatch(example_log_payload: bytes):
    """It fails when summary expected count does not match parsed record rows."""
    tampered = example_log_payload.replace(b"1784415110,5,8", b"1784415110,5,9", 1)

    with pytest.raises(ValueError, match="Readings count mismatch"):
        parse_mqtt_readings_message(tampered)


def test_parse_message_raises_when_binary_marker_missing():
    """It fails when payload does not include the readings binary marker."""
    with pytest.raises(ValueError, match="No readings binary marker"):
        parse_mqtt_readings_message(b"periodEnd,periodDurationSecs,count\n1,5,8\n")
