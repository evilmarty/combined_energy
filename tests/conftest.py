"""Fixtures for Combined Energy platform tests."""

from pathlib import Path

import pytest


@pytest.fixture
def fixture_path() -> Path:
    """Return the path to the fixture directory."""
    return Path(__file__).parent / "fixtures"
