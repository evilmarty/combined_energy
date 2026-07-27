"""The Combined Energy integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir

from .bridge import BridgeBootstrapError, BridgeConnectionError, get_bridge_client
from .const import (
    CONF_STALE_ENTITY_CLEANUP_PENDING,
    DATA_BRIDGE_CLIENT,
    DATA_COORDINATOR,
    DATA_INTEL_COORDINATOR,
    DATA_READINGS_STORE,
    DOMAIN,
)
from .coordinator import (
    CombinedEnergyIntelCoordinator,
    CombinedEnergyReadingsCoordinator,
)
from .reconfigure import async_start_reconfigure_if_needed, needs_reconfigure_issue_id
from .storage import ReadingsStore

PLATFORMS: list[Platform] = [Platform.SENSOR]

type CombinedEnergyConfigEntry = ConfigEntry[CombinedEnergyReadingsCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: CombinedEnergyConfigEntry
) -> bool:
    """Set up Combined Energy from a config entry."""
    try:
        client = await get_bridge_client(hass=hass, data=entry.data)
        readings_store = ReadingsStore(hass=hass, config_entry=entry)
        coordinator = CombinedEnergyReadingsCoordinator(
            hass=hass,
            client=client,
            readings_store=readings_store,
            config_entry=entry,
        )
        intel_coordinator = CombinedEnergyIntelCoordinator(
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
        DATA_INTEL_COORDINATOR: intel_coordinator,
        DATA_READINGS_STORE: readings_store,
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


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entries."""
    if entry.version == 1:
        data = {**entry.data, CONF_STALE_ENTITY_CLEANUP_PENDING: True}
        hass.config_entries.async_update_entry(entry, version=2, data=data)
        ir.async_create_issue(
            hass,
            DOMAIN,
            needs_reconfigure_issue_id(entry.entry_id),
            is_fixable=True,
            is_persistent=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key="needs_reconfigure",
            data={"entry_id": entry.entry_id},
        )
        await async_start_reconfigure_if_needed(hass, entry.entry_id)
    return True
