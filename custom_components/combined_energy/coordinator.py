"""MQTT-backed coordinators for Combined Energy."""

from __future__ import annotations

from datetime import UTC, datetime

from custom_components.combined_energy.bridge import MqttBridgeClient
from custom_components.combined_energy.const import (
    LOGGER,
    MQTT_READINGS_TOPIC_FILTER,
    READINGS_WATCHDOG_INTERVAL,
    READINGS_COORDINATOR_NAME,
)
from custom_components.combined_energy.models import Readings
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    UNDEFINED,
    DataUpdateCoordinator,
    UndefinedType,
    UpdateFailed,
)


class CombinedEnergyReadingsCoordinator(DataUpdateCoordinator[Readings]):
    """Update coordinator for MQTT readings."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: MqttBridgeClient,
        config_entry: ConfigEntry | None | UndefinedType = UNDEFINED,
    ) -> None:
        """Initialize readings coordinator."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            config_entry=config_entry,
            name=READINGS_COORDINATOR_NAME,
            update_interval=READINGS_WATCHDOG_INTERVAL,
            always_update=True,
        )
        self.client = client
        self._last_message_received_at: datetime | None = None
        LOGGER.debug(
            "Subscribing readings coordinator to topic %s", self._readings_topic
        )
        self.client.subscribe(self._readings_topic, self._handle_readings_message)

    @property
    def _readings_topic(self) -> str:
        """Topic filter for readings messages."""
        return self.client.topic(MQTT_READINGS_TOPIC_FILTER)

    async def _async_update_data(self) -> Readings:
        """Return latest reading from MQTT stream."""
        if self._last_message_received_at is None:
            try:
                self.client.publish_logging_start()
            except Exception as ex:
                raise UpdateFailed(
                    "Data is stale and failed to request logging start from bridge"
                    if self.data
                    else "Data is not available and failed to request logging start from bridge"
                ) from ex
            raise UpdateFailed(
                "Data is stale, requested logging start from bridge"
                if self.data
                else "No MQTT readings received yet, requested logging start from bridge"
            )
        if self.data is not None:
            self._last_message_received_at = None
            return self.data
        raise UpdateFailed("No MQTT readings available yet")

    def _handle_readings_message(self, topic: str, payload: bytes) -> None:
        """Parse and publish new readings from MQTT payloads."""
        LOGGER.debug(
            "Processing MQTT readings message topic=%s payload_bytes=%s",
            topic,
            len(payload),
        )
        self._last_message_received_at = datetime.now(UTC)
        self.async_set_updated_data(Readings.from_mqtt_message(payload))
