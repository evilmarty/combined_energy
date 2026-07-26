"""Helpers for reconfigure issue handling."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import DOMAIN, NEEDS_RECONFIGURE_ISSUE_SUFFIX


def needs_reconfigure_issue_id(entry_id: str) -> str:
    """Build issue id for entries that need reconfigure."""
    return f"{entry_id}{NEEDS_RECONFIGURE_ISSUE_SUFFIX}"


def parse_needs_reconfigure_issue_entry_id(issue_id: str) -> str | None:
    """Extract config-entry id from a needs-reconfigure issue id."""
    if not issue_id.endswith(NEEDS_RECONFIGURE_ISSUE_SUFFIX):
        return None
    return issue_id.removesuffix(NEEDS_RECONFIGURE_ISSUE_SUFFIX)


async def async_start_reconfigure_if_needed(hass: HomeAssistant, entry_id: str) -> bool:
    """Start a reconfigure flow when one is not already in progress."""
    for flow in hass.config_entries.flow.async_progress_by_handler(DOMAIN):
        context = flow.get("context", {})
        if (
            context.get("source") == config_entries.SOURCE_RECONFIGURE
            and context.get("entry_id") == entry_id
        ):
            return False
    await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry_id,
        },
    )
    return True
