"""MQTT-backed coordinators for Combined Energy."""

from __future__ import annotations

from custom_components.combined_energy.bridge import MqttBridgeClient
from custom_components.combined_energy.const import (
    LOGGER,
    MQTT_READINGS_TOPIC_FILTER,
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
            update_interval=None,
            update_method=self._async_update,
            always_update=True,
        )
        self.client = client
        LOGGER.debug("Subscribing readings coordinator to topic %s", self._readings_topic)
        self.client.subscribe(self._readings_topic, self._handle_readings_message)

    @property
    def _readings_topic(self) -> str:
        """Topic filter for readings messages."""
        return self.client.topic(MQTT_READINGS_TOPIC_FILTER)

    async def _async_update(self) -> Readings:
        """Return latest reading from MQTT stream."""
        if self.data is not None:
            return self.data
        raise UpdateFailed("No MQTT readings available yet")

    def _handle_readings_message(self, topic: str, payload: bytes) -> None:
        """Parse and publish new readings from MQTT payloads."""
        LOGGER.debug(
            "Processing MQTT readings message topic=%s payload_bytes=%s",
            topic,
            len(payload),
        )
        self.async_set_updated_data(Readings.from_mqtt_message(payload))
