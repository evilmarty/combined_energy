"""DataUpdateCoordinator for the PVOutput integration."""

from __future__ import annotations

import asyncio
from datetime import datetime

from aiohttp import ClientResponseError
from custom_components.combined_energy.client import Client
from custom_components.combined_energy.models import LogSession, Readings, TariffDetails

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    UNDEFINED,
    DataUpdateCoordinator,
    UndefinedType,
    UpdateFailed,
)

from .const import (
    LOG_SESSION_REFRESH_DELAY,
    LOGGER,
    READINGS_UPDATE_DELAY,
    TARIFF_DETAILS_UPDATE_DELAY,
)

CombinedEnergyLogSessionCoordinator = DataUpdateCoordinator[LogSession]
CombinedEnergyTariffDetailsCoordinator = DataUpdateCoordinator[TariffDetails]
CombinedEnergyReadingsCoordinator = DataUpdateCoordinator[Readings]


class CombinedEnergyCoordinator:
    """Bulk creates coordinators for combined energy client."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: Client,
        config_entry: ConfigEntry | None | UndefinedType = UNDEFINED,
    ) -> None:
        """Initialize the coordinator."""
        self._last_range_end = None
        self.client = client
        self.log_session = CombinedEnergyLogSessionCoordinator(
            hass=hass,
            logger=LOGGER,
            config_entry=config_entry,
            name="log_session",
            update_interval=LOG_SESSION_REFRESH_DELAY,
            update_method=self._update_log_session,
            always_update=True,
        )
        self.readings = CombinedEnergyReadingsCoordinator(
            hass=hass,
            logger=LOGGER,
            config_entry=config_entry,
            name="readings",
            update_interval=READINGS_UPDATE_DELAY,
            update_method=self._update_readings,
            always_update=True,
        )
        self.tariff_details = CombinedEnergyTariffDetailsCoordinator(
            hass=hass,
            logger=LOGGER,
            config_entry=config_entry,
            name="tariff_details",
            update_interval=TARIFF_DETAILS_UPDATE_DELAY,
            update_method=self._update_tariff_details,
            always_update=False,
        )
        # This ensures that the log session coordinator triggers updates
        self.log_session.async_add_listener(
            lambda: LOGGER.debug("Log session has been restarted")
        )

    async def _update_log_session(self) -> LogSession:
        """Fetch log session from the API."""
        try:
            log_session = await self.client.start_log_session()
        except ClientResponseError as err:
            raise UpdateFailed from err
        return log_session

    async def _update_readings(self) -> Readings:
        """Fetch readings from the API."""
        try:
            readings = await self.client.readings(
                range_start=self._last_range_end, range_end=datetime.now()
            )
        except ClientResponseError as err:
            raise UpdateFailed from err
        self._last_range_end = readings.range_end
        return readings

    async def _update_tariff_details(self) -> TariffDetails:
        """Fetch tariff details from the API."""
        try:
            tariff_details = await self.client.tariff_details()
        except ClientResponseError as err:
            raise UpdateFailed from err
        return tariff_details

    async def async_config_entry_first_refresh(self) -> None:
        """Refresh all coordinators."""
        await asyncio.gather(
            self.log_session.async_config_entry_first_refresh(),
            self.readings.async_config_entry_first_refresh(),
            self.tariff_details.async_config_entry_first_refresh(),
        )
