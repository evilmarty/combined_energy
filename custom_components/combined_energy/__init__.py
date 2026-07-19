"""The Combined Energy integration."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir

from .bridge import BridgeBootstrapError, BridgeConnectionError, get_bridge_client
from .const import DATA_BRIDGE_CLIENT, DATA_COORDINATOR, DOMAIN
from .coordinator import CombinedEnergyReadingsCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

type CombinedEnergyConfigEntry = ConfigEntry[CombinedEnergyReadingsCoordinator]


def _needs_reconfigure_issue_id(entry: ConfigEntry) -> str:
    """Build issue id for entries that need reconfigure."""
    return f"{entry.entry_id}_needs_reconfigure"


async def _async_start_reconfigure_if_needed(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Start a reconfigure flow when one is not already in progress."""
    for flow in hass.config_entries.flow.async_progress_by_handler(DOMAIN):
        context = flow.get("context", {})
        if (
            context.get("source") == config_entries.SOURCE_RECONFIGURE
            and context.get("entry_id") == entry.entry_id
        ):
            return
    await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )


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


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entries."""
    if entry.version == 1:
        hass.config_entries.async_update_entry(entry, version=2)
        ir.async_create_issue(
            hass,
            DOMAIN,
            _needs_reconfigure_issue_id(entry),
            is_fixable=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key="needs_reconfigure",
        )
        await _async_start_reconfigure_if_needed(hass, entry)
    return True
