"""MQTT readings accumulation and persistence helpers."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from custom_components.combined_energy.const import (
    DOMAIN,
    LOGGER,
    READINGS_OUTLIER_MAX_WITHOUT_POWER_WH,
    READINGS_OUTLIER_MIN_WH,
    READINGS_OUTLIER_POWER_MULTIPLIER,
    READINGS_STORAGE_KEY_SUFFIX,
    READINGS_STORAGE_VERSION,
)
from custom_components.combined_energy.models import Readings
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store


class ReadingsStore:
    """Persistent accumulation store for MQTT readings."""

    def __init__(
        self,
        hass: HomeAssistant | None,
        config_entry: ConfigEntry | None,
        persistence: Any | None = None,
    ) -> None:
        """Initialize readings store."""
        storage_key = (
            f"{DOMAIN}_{config_entry.entry_id}{READINGS_STORAGE_KEY_SUFFIX}"
            if isinstance(config_entry, ConfigEntry)
            else f"{DOMAIN}{READINGS_STORAGE_KEY_SUFFIX}"
        )
        self._store: Store[dict[str, Any]] | Any | None = persistence
        if (
            self._store is None
            and hass is not None
            and hasattr(hass, "data")
            and hasattr(hass, "config")
        ):
            self._store = Store(hass, READINGS_STORAGE_VERSION, storage_key)

        self._last_processed_period_end: int | None = None
        self._energy_totals: dict[str, float] = {}
        self._last_saved_at: datetime | None = None
        self._restored = False
        self._processing_lock = asyncio.Lock()

    async def async_record_readings(self, readings: Readings) -> Readings | None:
        """Record raw readings and return accumulated readings, or None if duplicate."""
        async with self._processing_lock:
            if not self._restored:
                await self._async_restore_state()
                self._restored = True

            period_end = int(readings.period_end.timestamp())
            if (
                self._last_processed_period_end is not None
                and period_end <= self._last_processed_period_end
            ):
                LOGGER.debug(
                    "Skipping duplicate or stale readings message: period_end=%s last=%s",
                    period_end,
                    self._last_processed_period_end,
                )
                return None

            self._accumulate_energy_totals(readings)
            self._last_processed_period_end = period_end
            await self._async_save_state()
            return readings

    async def _async_restore_state(self) -> None:
        """Restore state from storage."""
        if self._store is None:
            return
        state = await self._store.async_load()
        if not isinstance(state, dict):
            return
        self._last_processed_period_end = state.get("last_processed_period_end")
        totals = state.get("energy_totals")
        if isinstance(totals, dict):
            self._energy_totals = {
                key: float(value)
                for key, value in totals.items()
                if isinstance(value, int | float)
            }
        LOGGER.debug(
            "Restored readings state with %s energy counters",
            len(self._energy_totals),
        )

    async def _async_save_state(self) -> None:
        """Persist state."""
        if self._store is None:
            return
        now = datetime.now(UTC)
        if self._last_saved_at and (now - self._last_saved_at).total_seconds() < 30:
            return
        await self._store.async_save(
            {
                "last_processed_period_end": self._last_processed_period_end,
                "energy_totals": self._energy_totals,
            }
        )
        self._last_saved_at = now

    def _accumulate_energy_totals(self, readings: Readings) -> None:
        """Convert interval energy deltas into cumulative totals."""
        period_seconds = readings.period_duration_secs
        for device in readings.devices:
            power_watts = self._extract_power_watts(device)
            for field_name in type(device).model_fields:
                if not field_name.startswith("energy_"):
                    continue
                value = getattr(device, field_name)
                if not isinstance(value, int | float):
                    continue
                normalized = self._normalize_energy_delta(
                    field_name=field_name,
                    value=float(value),
                    period_seconds=period_seconds,
                    power_watts=power_watts,
                )
                if normalized is None:
                    continue
                key = f"{device.device_type}:{device.device_id}:{field_name}"
                self._energy_totals[key] = (
                    self._energy_totals.get(key, 0.0) + normalized
                )
                setattr(device, field_name, self._energy_totals[key])

    def _normalize_energy_delta(
        self,
        field_name: str,
        value: float,
        period_seconds: int,
        power_watts: float | None,
    ) -> float | None:
        """Normalize a single interval energy value into a positive delta."""
        delta = -value if field_name.startswith("energy_consumed") else value
        if field_name == "energy_nett":
            delta = abs(value)
        if delta < 0:
            delta = abs(delta)
        if self._is_outlier_energy_delta(delta, power_watts, period_seconds):
            LOGGER.debug(
                "Skipping outlier energy delta field=%s value=%s power=%s period=%s",
                field_name,
                value,
                power_watts,
                period_seconds,
            )
            return None
        return delta

    def _is_outlier_energy_delta(
        self, delta_wh: float, power_watts: float | None, period_seconds: int
    ) -> bool:
        """Return True when interval energy delta is implausibly large."""
        if power_watts is None:
            return delta_wh > READINGS_OUTLIER_MAX_WITHOUT_POWER_WH
        expected_wh = abs(power_watts) * period_seconds / 3600
        max_wh = max(
            expected_wh * READINGS_OUTLIER_POWER_MULTIPLIER,
            READINGS_OUTLIER_MIN_WH,
        )
        return delta_wh > max_wh

    @staticmethod
    def _extract_power_watts(device: Any) -> float | None:
        """Extract a representative watts value for interval sanity checks."""
        for field_name in type(device).model_fields:
            if not field_name.startswith("power_"):
                continue
            if not field_name.endswith(("_last", "_avg")):
                continue
            value = getattr(device, field_name, None)
            if isinstance(value, int | float):
                return float(value)
        return None
