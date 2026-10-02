"""Tests for integration manifest requirements."""

import json
from pathlib import Path


def test_mqtt_requirement_uses_minimum_version():
    """Allow MQTT updates shared with Home Assistant."""
    manifest_path = (
        Path(__file__).parents[1]
        / "custom_components"
        / "combined_energy"
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text())

    assert "paho-mqtt>=2.1.0" in manifest["requirements"]
