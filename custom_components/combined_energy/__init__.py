"""The Combined Energy integration."""

from __future__ import annotations

from aiohttp import ClientResponseError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .client import ClientAuthError, get_client
from .const import DATA_API_CLIENT, DATA_COORDINATOR, DOMAIN
from .coordinator import CombinedEnergyCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

type CombinedEnergyConfigEntry = ConfigEntry[CombinedEnergyCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: CombinedEnergyConfigEntry
) -> bool:
    """Set up Combined Energy from a config entry."""

    client = await get_client(
        hass=hass,
        mobile_or_email=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
    )

    try:
        await client.login()
    except ClientAuthError as ex:
        raise ConfigEntryAuthFailed from ex
    except ClientResponseError as ex:
        raise ConfigEntryNotReady from ex

    coordinator = CombinedEnergyCoordinator(
        hass=hass, client=client, config_entry=entry
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_API_CLIENT: client,
        DATA_COORDINATOR: coordinator,
    }
    entry.runtime_data = coordinator

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: CombinedEnergyConfigEntry
) -> bool:
    """Unload Combined Energy config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        del hass.data[DOMAIN][entry.entry_id]
    return unload_ok
