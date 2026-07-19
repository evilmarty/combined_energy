"""The Combined Energy integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .bridge import BridgeBootstrapError, BridgeConnectionError, get_bridge_client
from .const import DATA_BRIDGE_CLIENT, DATA_COORDINATOR, DOMAIN
from .coordinator import CombinedEnergyReadingsCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

type CombinedEnergyConfigEntry = ConfigEntry[CombinedEnergyReadingsCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: CombinedEnergyConfigEntry
) -> bool:
    """Set up Combined Energy from a config entry."""
    try:
        client = await get_bridge_client(hass=hass, data=entry.data)
        coordinator = CombinedEnergyReadingsCoordinator(
            hass=hass,
            client=client,
            config_entry=entry,
        )
        await client.async_start()
    except (BridgeBootstrapError, BridgeConnectionError, TimeoutError) as ex:
        raise ConfigEntryNotReady from ex

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_BRIDGE_CLIENT: client,
        DATA_COORDINATOR: coordinator,
    }
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: CombinedEnergyConfigEntry
) -> bool:
    """Unload Combined Energy config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        client = hass.data[DOMAIN][entry.entry_id][DATA_BRIDGE_CLIENT]
        await client.async_stop()
        del hass.data[DOMAIN][entry.entry_id]
    return unload_ok


async def async_migrate_entry(_hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entries."""
    if entry.version == 1:
        return False
    return True
