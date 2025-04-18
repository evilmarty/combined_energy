"""DataUpdateCoordinator for the PVOutput integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from logging import Logger

from custom_components.combined_energy.client import Client
from custom_components.combined_energy.models import LogSession, Readings, TariffDetails

from homeassistant.components.sensor import UndefinedType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    UNDEFINED,
    DataUpdateCoordinator,
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


class CombinedEnergyCoordinator:
    """Bulk creates coordinators for combined energy client."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: Client,
        config_entry: ConfigEntry | None | UndefinedType = UNDEFINED,
    ) -> None:
        """Initialize the coordinator."""
        self.client = client
        self.log_session = CombinedEnergyLogSessionCoordinator(
            hass=hass,
            logger=LOGGER,
            config_entry=config_entry,
            name="log_session",
            update_interval=LOG_SESSION_REFRESH_DELAY,
            update_method=client.start_log_session,
        )
        self.readings = CombinedEnergyReadingsCoordinator(
            hass=hass,
            client=client,
            logger=LOGGER,
            config_entry=config_entry,
            update_interval=READINGS_UPDATE_DELAY,
        )
        self.tariff_details = CombinedEnergyTariffDetailsCoordinator(
            hass=hass,
            logger=LOGGER,
            config_entry=config_entry,
            name="tariff_details",
            update_interval=TARIFF_DETAILS_UPDATE_DELAY,
            update_method=client.tariff_details,
        )

    async def async_config_entry_first_refresh(self) -> None:
        """Refresh all coordinators."""
        await asyncio.gather(
            self.log_session.async_config_entry_first_refresh(),
            self.readings.async_config_entry_first_refresh(),
            self.tariff_details.async_config_entry_first_refresh(),
        )


class CombinedEnergyReadingsCoordinator(DataUpdateCoordinator[Readings]):
    """Coordinator for readings."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: Client,
        logger: Logger,
        update_interval: int,
        config_entry: ConfigEntry | None | UndefinedType = UNDEFINED,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass=hass,
            logger=logger,
            config_entry=config_entry,
            name="readings",
            update_interval=update_interval,
        )
        self.client = client

    async def _async_update_data(self) -> Readings:
        """Fetch data from the API."""
        range_start = getattr(self.data, "range_end", None)
        return await self.client.readings(range_start=range_start)
