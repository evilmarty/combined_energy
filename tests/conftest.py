"""Fixtures for Combined Energy platform tests."""

from pathlib import Path

import pytest


@pytest.fixture
def fixture_path() -> Path:
    """Return the path to the fixture directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def example_log_payload() -> bytes:
    """Return real captured bridge readings payload sample."""
    return (Path(__file__).parent / "fixtures" / "captured_readings.bin").read_bytes()
