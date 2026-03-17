"""Tests for Combined Energy coordinators."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import ClientResponseError
import pytest

from custom_components.combined_energy.coordinator import CombinedEnergyCoordinator
from custom_components.combined_energy.models import (
    Installation,
    LogSession,
    Readings,
    TariffDetails,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed


@pytest.fixture
def installation(fixture_path):
    """Fixture for Installation model."""
    return Installation.model_validate_json(
        (fixture_path / "installation.json").read_text()
    )


@pytest.fixture
def log_session(fixture_path):
    """Fixture for LogSession model."""
    return LogSession.model_validate_json(
        (fixture_path / "log-session.json").read_text()
    )


@pytest.fixture
def readings(fixture_path):
    """Fixture for Readings model."""
    return Readings.model_validate_json((fixture_path / "readings.json").read_text())


@pytest.fixture
def tariff_details(fixture_path):
    """Fixture for TariffDetails model."""
    return TariffDetails.model_validate_json(
        (fixture_path / "tariff-details.json").read_text()
    )


@pytest.fixture
def mock_hass():
    """Mock HomeAssistant."""
    hass = MagicMock(spec=HomeAssistant)
    try:
        hass.loop = asyncio.get_running_loop()
    except RuntimeError:
        hass.loop = MagicMock()

    with patch("homeassistant.helpers.frame._hass.hass", hass):
        yield hass


@pytest.fixture
def mock_client():
    """Mock Combined Energy API Client."""
    return MagicMock()


@pytest.fixture
def mock_entry():
    """Mock ConfigEntry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.pref_disable_polling = False
    return entry


class TestCombinedEnergyCoordinator:
    """Tests for CombinedEnergyCoordinator."""

    def test_init(self, mock_hass, mock_client, mock_entry):
        """Test coordinator initialization."""
        with patch(
            "custom_components.combined_energy.coordinator.CombinedEnergyLogSessionCoordinator.async_add_listener"
        ) as mock_add_listener:
            coordinator = CombinedEnergyCoordinator(mock_hass, mock_client, mock_entry)

            assert coordinator.client == mock_client
            assert coordinator.log_session.name == "log_session"
            assert coordinator.readings.name == "readings"
            assert coordinator.tariff_details.name == "tariff_details"
            assert coordinator._last_range_end is None  # noqa: SLF001
            mock_add_listener.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_log_session(
        self, mock_hass, mock_client, mock_entry, log_session
    ):
        """Test _update_log_session."""
        mock_client.start_log_session = AsyncMock(return_value=log_session)
        coordinator = CombinedEnergyCoordinator(mock_hass, mock_client, mock_entry)

        result = await coordinator._update_log_session()  # noqa: SLF001
        assert result == log_session
        mock_client.start_log_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_log_session_error(self, mock_hass, mock_client, mock_entry):
        """Test _update_log_session with API error."""
        mock_client.start_log_session = AsyncMock(
            side_effect=ClientResponseError(MagicMock(), MagicMock())
        )
        coordinator = CombinedEnergyCoordinator(mock_hass, mock_client, mock_entry)

        with pytest.raises(UpdateFailed):
            await coordinator._update_log_session()  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_update_readings(self, mock_hass, mock_client, mock_entry, readings):
        """Test _update_readings."""
        mock_client.readings = AsyncMock(return_value=readings)
        coordinator = CombinedEnergyCoordinator(mock_hass, mock_client, mock_entry)

        result = await coordinator._update_readings()  # noqa: SLF001
        assert result == readings
        assert coordinator._last_range_end == readings.range_end  # noqa: SLF001
        mock_client.readings.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_readings_error(self, mock_hass, mock_client, mock_entry):
        """Test _update_readings with API error."""
        mock_client.readings = AsyncMock(
            side_effect=ClientResponseError(MagicMock(), MagicMock())
        )
        coordinator = CombinedEnergyCoordinator(mock_hass, mock_client, mock_entry)

        with pytest.raises(UpdateFailed):
            await coordinator._update_readings()  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_update_tariff_details(
        self, mock_hass, mock_client, mock_entry, tariff_details
    ):
        """Test _update_tariff_details."""
        mock_client.tariff_details = AsyncMock(return_value=tariff_details)
        coordinator = CombinedEnergyCoordinator(mock_hass, mock_client, mock_entry)

        result = await coordinator._update_tariff_details()  # noqa: SLF001
        assert result == tariff_details
        mock_client.tariff_details.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_tariff_details_error(
        self, mock_hass, mock_client, mock_entry
    ):
        """Test _update_tariff_details with API error."""
        mock_client.tariff_details = AsyncMock(
            side_effect=ClientResponseError(MagicMock(), MagicMock())
        )
        coordinator = CombinedEnergyCoordinator(mock_hass, mock_client, mock_entry)

        with pytest.raises(UpdateFailed):
            await coordinator._update_tariff_details()  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_async_config_entry_first_refresh(
        self, mock_hass, mock_client, mock_entry
    ):
        """Test async_config_entry_first_refresh."""
        coordinator = CombinedEnergyCoordinator(mock_hass, mock_client, mock_entry)

        coordinator.log_session.async_config_entry_first_refresh = AsyncMock()
        coordinator.readings.async_config_entry_first_refresh = AsyncMock()
        coordinator.tariff_details.async_config_entry_first_refresh = AsyncMock()

        await coordinator.async_config_entry_first_refresh()

        coordinator.log_session.async_config_entry_first_refresh.assert_called_once()
        coordinator.readings.async_config_entry_first_refresh.assert_called_once()
        coordinator.tariff_details.async_config_entry_first_refresh.assert_called_once()
